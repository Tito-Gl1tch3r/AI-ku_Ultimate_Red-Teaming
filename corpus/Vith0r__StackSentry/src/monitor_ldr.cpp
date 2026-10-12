struct MonitorPebLdrData {
    ULONG Length;
    BOOLEAN Initialized;
    PVOID SsHandle;
    LIST_ENTRY InLoadOrderModuleList;
    LIST_ENTRY InMemoryOrderModuleList;
    LIST_ENTRY InInitializationOrderModuleList;
};

struct MonitorPeb {
    BYTE InheritedAddressSpace;
    BYTE ReadImageFileExecOptions;
    BYTE BeingDebugged;
    BYTE BitField;
    PVOID Mutant;
    PVOID ImageBaseAddress;
    MonitorPebLdrData* Ldr;
};

struct MonitorRtlBalancedNode {
    union {
        struct {
            MonitorRtlBalancedNode* Left;
            MonitorRtlBalancedNode* Right;
        };
        struct {
            UCHAR Red : 1;
            UCHAR Balance : 2;
            ULONG_PTR ParentValue;
        };
    };
};

struct MonitorLdrDataTableEntry {
    LIST_ENTRY InLoadOrderLinks;
    LIST_ENTRY InMemoryOrderLinks;
    union {
        LIST_ENTRY InInitializationOrderLinks;
        LIST_ENTRY InProgressLinks;
    };
    PVOID DllBase;
    PVOID EntryPoint;
    ULONG SizeOfImage;
    UNICODE_STRING FullDllName;
    UNICODE_STRING BaseDllName;
    union {
        UCHAR FlagGroup[4];
        ULONG Flags;
        struct {
            ULONG PackagedBinary : 1;
            ULONG MarkedForRemoval : 1;
            ULONG ImageDll : 1;
            ULONG LoadNotificationsSent : 1;
            ULONG TelemetryEntryProcessed : 1;
            ULONG ProcessStaticImport : 1;
            ULONG InLegacyLists : 1;
            ULONG InIndexes : 1;
            ULONG ShimDll : 1;
            ULONG InExceptionTable : 1;
            ULONG ReservedFlags1 : 2;
            ULONG LoadInProgress : 1;
            ULONG LoadConfigProcessed : 1;
            ULONG EntryProcessed : 1;
            ULONG ProtectDelayLoad : 1;
            ULONG ReservedFlags3 : 2;
            ULONG DontCallForThreads : 1;
            ULONG ProcessAttachCalled : 1;
            ULONG ProcessAttachFailed : 1;
            ULONG CorDeferredValidate : 1;
            ULONG CorImage : 1;
            ULONG DontRelocate : 1;
            ULONG CorILOnly : 1;
            ULONG ChpeImage : 1;
            ULONG ReservedFlags5 : 2;
            ULONG Redirected : 1;
            ULONG ReservedFlags6 : 2;
            ULONG CompatDatabaseProcessed : 1;
        };
    };
    USHORT ObsoleteLoadCount;
    USHORT TlsIndex;
    LIST_ENTRY HashLinks;
    ULONG TimeDateStamp;
    PVOID EntryPointActivationContext;
    PVOID Lock;
    PVOID DdagNode;
    LIST_ENTRY NodeModuleLink;
    PVOID LoadContext;
    PVOID ParentDllBase;
    PVOID SwitchBackContext;
    MonitorRtlBalancedNode BaseAddressIndexNode;
    MonitorRtlBalancedNode MappingInfoIndexNode;
    ULONG_PTR OriginalBase;
};

struct LdrIntegrityAlertRecord {
    uintptr_t table_entry = 0;
    uintptr_t dll_base = 0;
    uintptr_t entrypoint = 0;
    uintptr_t original_base = 0;
    uint32_t flags = 0;
};

static constexpr DWORD kLdrIntegrityScanIntervalMs = 250;
static SRWLOCK g_ldr_integrity_lock = SRWLOCK_INIT;
static LdrIntegrityAlertRecord g_ldr_integrity_alerts[256]{};
static uint32_t g_ldr_integrity_next_alert = 0;
static HANDLE g_ldr_integrity_thread = nullptr;
static volatile LONG g_ldr_integrity_thread_stop = 0;
static volatile LONG g_ldr_integrity_scan_active = 0;
static volatile LONG g_monitor_unlinked_from_ldr = 0;

static MonitorPeb* CurrentPeb() {
#if defined(_M_X64)
    return reinterpret_cast<MonitorPeb*>(__readgsqword(0x60));
#else
    return nullptr;
#endif
}

static void UnlinkListEntryIfLinked(LIST_ENTRY* entry) {
    if (!entry || !entry->Flink || !entry->Blink ||
        entry->Flink == entry || entry->Blink == entry) {
        return;
    }

    entry->Blink->Flink = entry->Flink;
    entry->Flink->Blink = entry->Blink;
    entry->Flink = entry;
    entry->Blink = entry;
}

static void HideMonitorFromPebLoaderLists() {
    if (!g_module ||
        InterlockedCompareExchange(&g_monitor_unlinked_from_ldr, 1, 0) != 0) {
        return;
    }

    __try {
        MonitorPeb* peb = CurrentPeb();
        MonitorPebLdrData* ldr = peb ? peb->Ldr : nullptr;
        if (!ldr) {
            return;
        }

        LIST_ENTRY* head = &ldr->InMemoryOrderModuleList;
        for (LIST_ENTRY* cursor = head->Flink; cursor && cursor != head; cursor = cursor->Flink) {
            auto* entry = reinterpret_cast<MonitorLdrDataTableEntry*>(
                reinterpret_cast<uintptr_t>(cursor) - FIELD_OFFSET(MonitorLdrDataTableEntry, InMemoryOrderLinks));
            if (entry && entry->DllBase == g_module) {
                UnlinkListEntryIfLinked(&entry->InLoadOrderLinks);
                UnlinkListEntryIfLinked(&entry->InMemoryOrderLinks);
                UnlinkListEntryIfLinked(&entry->InInitializationOrderLinks);
                break;
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }
}

static bool ReadImageEntrypoint(uintptr_t dll_base, uint64_t& expected_entrypoint) {
    expected_entrypoint = 0;
    if (!dll_base) {
        return false;
    }

    __try {
        const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(dll_base);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 0x100000) {
            return false;
        }
        const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(dll_base + static_cast<uintptr_t>(dos->e_lfanew));
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
            nt->OptionalHeader.AddressOfEntryPoint == 0) {
            return false;
        }
        expected_entrypoint = dll_base + nt->OptionalHeader.AddressOfEntryPoint;
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool QueryAddress(uintptr_t address, MEMORY_BASIC_INFORMATION& mbi) {
    memset(&mbi, 0, sizeof(mbi));
    if (!address) {
        return false;
    }
    return VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) == sizeof(mbi);
}

static bool IsOriginalBaseSuspicious(uintptr_t original_base, uintptr_t dll_base, uintptr_t image_end,
    MEMORY_BASIC_INFORMATION& original_mbi) {
    if (!original_base) {
        return false;
    }
    if (original_base >= dll_base && original_base < image_end) {
        return false;
    }
    if (!QueryAddress(original_base, original_mbi)) {
        return false;
    }
    return original_mbi.State == MEM_COMMIT && original_mbi.Type != MEM_IMAGE;
}

static bool ShouldReportLdrIntegrityFinding(
    uintptr_t table_entry,
    uintptr_t dll_base,
    uintptr_t entrypoint,
    uintptr_t original_base,
    uint32_t flags) {
    AcquireSRWLockExclusive(&g_ldr_integrity_lock);
    for (const auto& record : g_ldr_integrity_alerts) {
        if (record.table_entry == table_entry &&
            record.dll_base == dll_base &&
            record.entrypoint == entrypoint &&
            record.original_base == original_base &&
            record.flags == flags) {
            ReleaseSRWLockExclusive(&g_ldr_integrity_lock);
            return false;
        }
    }

    LdrIntegrityAlertRecord& slot = g_ldr_integrity_alerts[g_ldr_integrity_next_alert % _countof(g_ldr_integrity_alerts)];
    slot.table_entry = table_entry;
    slot.dll_base = dll_base;
    slot.entrypoint = entrypoint;
    slot.original_base = original_base;
    slot.flags = flags;
    ++g_ldr_integrity_next_alert;
    ReleaseSRWLockExclusive(&g_ldr_integrity_lock);
    return true;
}

static void SendLdrIntegrityEvent(
    const wchar_t* reason,
    const wchar_t* module_name,
    const MonitorLdrDataTableEntry* entry,
    uint64_t expected_entrypoint,
    const MEMORY_BASIC_INFORMATION& entrypoint_mbi,
    const MEMORY_BASIC_INFORMATION& original_mbi,
    uint32_t flags) {
    MonitorEvent extra{};
    extra.ldr_table_entry = reinterpret_cast<uint64_t>(entry);
    extra.ldr_dll_base = reinterpret_cast<uint64_t>(entry->DllBase);
    extra.ldr_size_of_image = entry->SizeOfImage;
    extra.ldr_entrypoint = reinterpret_cast<uint64_t>(entry->EntryPoint);
    extra.ldr_expected_entrypoint = expected_entrypoint;
    extra.ldr_original_base = static_cast<uint64_t>(entry->OriginalBase);
    extra.ldr_entrypoint_region_base = reinterpret_cast<uint64_t>(entrypoint_mbi.BaseAddress);
    extra.ldr_entrypoint_region_size = static_cast<uint64_t>(entrypoint_mbi.RegionSize);
    extra.ldr_entrypoint_protect = entrypoint_mbi.Protect;
    extra.ldr_entrypoint_type = entrypoint_mbi.Type;
    extra.ldr_original_base_region_base = reinterpret_cast<uint64_t>(original_mbi.BaseAddress);
    extra.ldr_original_base_region_size = static_cast<uint64_t>(original_mbi.RegionSize);
    extra.ldr_original_base_protect = original_mbi.Protect;
    extra.ldr_original_base_type = original_mbi.Type;

    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        kMonitorEventLdrIntegrity,
        reason ? reason : L"ldr_scan",
        module_name && module_name[0] ? module_name : L"unknown_module",
        0,
        extra.ldr_entrypoint,
        flags,
        extra.ldr_dll_base,
        frames,
        captured,
        frame_context,
        frame_context_size,
        &extra);
}

static void ScanLdrIntegrity(const wchar_t* reason) {
    if (!LdrIntegrityEnabled() ||
        InterlockedCompareExchange(&g_emit_enabled, 0, 0) == 0 ||
        InterlockedCompareExchange(&g_ldr_integrity_scan_active, 1, 0) != 0) {
        return;
    }

    __try {
        MonitorPeb* peb = CurrentPeb();
        MonitorPebLdrData* ldr = peb ? peb->Ldr : nullptr;
        if (!ldr) {
            InterlockedExchange(&g_ldr_integrity_scan_active, 0);
            return;
        }

        LIST_ENTRY* head = &ldr->InMemoryOrderModuleList;
        LIST_ENTRY* cursor = head->Flink;
        uint32_t visited = 0;
        while (cursor && cursor != head && visited++ < 512) {
            auto* entry = reinterpret_cast<MonitorLdrDataTableEntry*>(
                reinterpret_cast<uintptr_t>(cursor) - FIELD_OFFSET(MonitorLdrDataTableEntry, InMemoryOrderLinks));
            cursor = cursor->Flink;

            const uintptr_t dll_base = reinterpret_cast<uintptr_t>(entry->DllBase);
            const uintptr_t entrypoint = reinterpret_cast<uintptr_t>(entry->EntryPoint);
            const uintptr_t image_size = static_cast<uintptr_t>(entry->SizeOfImage);
            if (!dll_base || !entrypoint || image_size < 0x1000 || image_size > 0x40000000) {
                continue;
            }

            const uintptr_t image_end = dll_base + image_size;
            uint64_t expected_entrypoint = 0;
            const bool has_expected_entrypoint = ReadImageEntrypoint(dll_base, expected_entrypoint);

            MEMORY_BASIC_INFORMATION entrypoint_mbi{};
            const bool has_entrypoint_mbi = QueryAddress(entrypoint, entrypoint_mbi);
            MEMORY_BASIC_INFORMATION original_mbi{};

            uint32_t flags = 0;
            if (entrypoint < dll_base || entrypoint >= image_end) {
                flags |= kMonitorEventFlagLdrEntryPointOutsideImage;
            }
            if (!has_entrypoint_mbi || entrypoint_mbi.Type != MEM_IMAGE) {
                flags |= kMonitorEventFlagLdrEntryPointNotImage;
            }
            if (has_expected_entrypoint && entrypoint != static_cast<uintptr_t>(expected_entrypoint)) {
                flags |= kMonitorEventFlagLdrEntryPointMismatch;
            }
            const uint32_t primary_alert_flags =
                kMonitorEventFlagLdrEntryPointOutsideImage |
                kMonitorEventFlagLdrEntryPointNotImage;
            if ((flags & primary_alert_flags) != 0 &&
                IsOriginalBaseSuspicious(static_cast<uintptr_t>(entry->OriginalBase), dll_base, image_end, original_mbi)) {
                flags |= kMonitorEventFlagLdrOriginalBaseSuspicious;
            }

            if ((flags & primary_alert_flags) == 0) {
                continue;
            }
            if (!ShouldReportLdrIntegrityFinding(
                reinterpret_cast<uintptr_t>(entry),
                dll_base,
                entrypoint,
                static_cast<uintptr_t>(entry->OriginalBase),
                flags)) {
                continue;
            }

            wchar_t module_name[kMonitorTargetNameChars]{};
            CopyLowerBasenameFromUnicodeString(&entry->BaseDllName, module_name, _countof(module_name));
            SendLdrIntegrityEvent(reason, module_name, entry, expected_entrypoint, entrypoint_mbi, original_mbi, flags);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
    }

    InterlockedExchange(&g_ldr_integrity_scan_active, 0);
}

static DWORD WINAPI LdrIntegrityScannerThread(void*) {
    g_inside_hook = true;
    while (InterlockedCompareExchange(&g_ldr_integrity_thread_stop, 0, 0) == 0) {
        ScanLdrIntegrity(L"periodic");
        Sleep(kLdrIntegrityScanIntervalMs);
    }
    g_inside_hook = false;
    return 0;
}

static void StartLdrIntegrityScanner() {
    if (!LdrIntegrityEnabled() || g_ldr_integrity_thread) {
        return;
    }
    InterlockedExchange(&g_ldr_integrity_thread_stop, 0);
    const bool was_inside_hook = g_inside_hook;
    g_inside_hook = true;
    HANDLE thread = CreateThread(nullptr, 0, LdrIntegrityScannerThread, nullptr, 0, nullptr);
    g_inside_hook = was_inside_hook;
    if (thread) {
        g_ldr_integrity_thread = thread;
    }
}

static void StopLdrIntegrityScanner() {
    InterlockedExchange(&g_ldr_integrity_thread_stop, 1);
}
