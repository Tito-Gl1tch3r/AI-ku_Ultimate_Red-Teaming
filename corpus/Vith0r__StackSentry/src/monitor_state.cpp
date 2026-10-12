struct WorkCallbackRecord {
    PTP_WORK work = nullptr;
    void* callback = nullptr;
};

struct ThreadpoolChainRecord {
    PTP_WORK work = nullptr;
    PTP_WORK_CALLBACK callback = nullptr;
    PVOID context = nullptr;
    uint64_t tick_ms = 0;
};

struct ThreadStartTraceRecord {
    LPTHREAD_START_ROUTINE start = nullptr;
    void* parameter = nullptr;
};

static HMODULE g_module = nullptr;
static HANDLE g_pipe = INVALID_HANDLE_VALUE;
static MonitorConfig g_config{};
static volatile LONG g_emit_enabled = 0;
static LdrLoadDllFn g_original_ldr_load_dll = nullptr;
static NtDelayExecutionFn g_original_nt_delay_execution = nullptr;
static SleepFn g_original_sleep = nullptr;
static SleepExFn g_original_sleep_ex = nullptr;
static WaitForSingleObjectFn g_original_wait_for_single_object = nullptr;
static WaitForMultipleObjectsFn g_original_wait_for_multiple_objects = nullptr;
static MsgWaitForMultipleObjectsExFn g_original_msg_wait_for_multiple_objects_ex = nullptr;
static LoadLibraryAFn g_original_load_library_a = nullptr;
static LoadLibraryWFn g_original_load_library_w = nullptr;
static LoadLibraryExAFn g_original_load_library_ex_a = nullptr;
static LoadLibraryExWFn g_original_load_library_ex_w = nullptr;
static CreateThreadFn g_original_create_thread = nullptr;
static QueueUserAPCFn g_original_queue_user_apc = nullptr;
static TpAllocWorkFn g_original_tp_alloc_work = nullptr;
static TpPostWorkFn g_original_tp_post_work = nullptr;
static TpReleaseWorkFn g_original_tp_release_work = nullptr;
static NtAllocateVirtualMemoryFn g_original_nt_allocate_virtual_memory = nullptr;
static NtProtectVirtualMemoryFn g_original_nt_protect_virtual_memory = nullptr;
static NtMapViewOfSectionFn g_original_nt_map_view_of_section = nullptr;
static NtUnmapViewOfSectionFn g_original_nt_unmap_view_of_section = nullptr;
static NtWriteVirtualMemoryFn g_original_nt_write_virtual_memory = nullptr;
static NtCreateThreadExFn g_original_nt_create_thread_ex = nullptr;
static NtQueueApcThreadFn g_original_nt_queue_apc_thread = nullptr;
static NtSetContextThreadFn g_original_nt_set_context_thread = nullptr;
static SetThreadContextFn g_original_set_thread_context = nullptr;
static OpenProcessFn g_original_open_process = nullptr;
static NtOpenProcessFn g_original_nt_open_process = nullptr;
static ResumeThreadFn g_original_resume_thread = nullptr;
static NtResumeThreadFn g_original_nt_resume_thread = nullptr;
static AddVectoredExceptionHandlerFn g_original_add_vectored_exception_handler = nullptr;
static AddVectoredExceptionHandlerFn g_original_rtl_add_vectored_exception_handler = nullptr;
static RtlAddFunctionTableFn g_original_rtl_add_function_table = nullptr;
static RtlDeleteFunctionTableFn g_original_rtl_delete_function_table = nullptr;
static RtlInstallFunctionTableCallbackFn g_original_rtl_install_function_table_callback = nullptr;
static PostThreadMessageAFn g_original_post_thread_message_a = nullptr;
static PostThreadMessageWFn g_original_post_thread_message_w = nullptr;
static CreateThreadpoolWorkFn g_original_create_threadpool_work = nullptr;
static SubmitThreadpoolWorkFn g_original_submit_threadpool_work = nullptr;
static WaitForThreadpoolWorkCallbacksFn g_original_wait_for_threadpool_work_callbacks = nullptr;
static CloseThreadpoolWorkFn g_original_close_threadpool_work = nullptr;
static ConnectFn g_original_connect = nullptr;
static WSAConnectFn g_original_wsa_connect = nullptr;
static SendFn g_original_send = nullptr;
static RecvFn g_original_recv = nullptr;
static WSASendFn g_original_wsa_send = nullptr;
static WSARecvFn g_original_wsa_recv = nullptr;
static GetAddrInfoAFn g_original_getaddrinfo = nullptr;
static GetAddrInfoWFn g_original_getaddrinfow = nullptr;
static InternetConnectAFn g_original_internet_connect_a = nullptr;
static InternetConnectWFn g_original_internet_connect_w = nullptr;
static InternetOpenUrlAFn g_original_internet_open_url_a = nullptr;
static InternetOpenUrlWFn g_original_internet_open_url_w = nullptr;
static HttpOpenRequestAFn g_original_http_open_request_a = nullptr;
static HttpOpenRequestWFn g_original_http_open_request_w = nullptr;
static HttpSendRequestAFn g_original_http_send_request_a = nullptr;
static HttpSendRequestWFn g_original_http_send_request_w = nullptr;
static InternetReadFileFn g_original_internet_read_file = nullptr;
static InternetWriteFileFn g_original_internet_write_file = nullptr;
static WinHttpOpenFn g_original_winhttp_open = nullptr;
static WinHttpConnectFn g_original_winhttp_connect = nullptr;
static WinHttpOpenRequestFn g_original_winhttp_open_request = nullptr;
static WinHttpSendRequestFn g_original_winhttp_send_request = nullptr;
static WinHttpReceiveResponseFn g_original_winhttp_receive_response = nullptr;
static WinHttpReadDataFn g_original_winhttp_read_data = nullptr;
static WinHttpWriteDataFn g_original_winhttp_write_data = nullptr;
static DnsQueryAFn g_original_dns_query_a = nullptr;
static DnsQueryWFn g_original_dns_query_w = nullptr;
static SRWLOCK g_work_lock = SRWLOCK_INIT;
static WorkCallbackRecord g_work_callbacks[128]{};
static SRWLOCK g_threadpool_chain_lock = SRWLOCK_INIT;
static ThreadpoolChainRecord* g_threadpool_chain_records[128]{};
static SRWLOCK g_remote_follow_lock = SRWLOCK_INIT;
static DWORD g_remote_follow_pids[128]{};
static thread_local bool g_remote_follow_in_progress = false;
static thread_local ThreadpoolChainRecord* g_active_threadpool_chain_record = nullptr;
static DWORD g_inside_hook_tls = TLS_OUT_OF_INDEXES;
static DWORD g_inside_load_library_hook_tls = TLS_OUT_OF_INDEXES;
static volatile LONG g_inside_hook_fallback = 0;
static volatile LONG g_inside_load_library_hook_fallback = 0;

static bool GetDynamicTlsFlag(DWORD index, volatile LONG* fallback) {
    if (index != TLS_OUT_OF_INDEXES) {
        return TlsGetValue(index) != nullptr;
    }
    return InterlockedCompareExchange(fallback, 0, 0) != 0;
}

static void SetDynamicTlsFlag(DWORD index, volatile LONG* fallback, bool value) {
    if (index != TLS_OUT_OF_INDEXES) {
        TlsSetValue(index, value ? reinterpret_cast<void*>(1) : nullptr);
        return;
    }
    InterlockedExchange(fallback, value ? 1 : 0);
}

struct DynamicTlsFlag {
    DWORD* index = nullptr;
    volatile LONG* fallback = nullptr;

    operator bool() const {
        return index && fallback && GetDynamicTlsFlag(*index, fallback);
    }

    DynamicTlsFlag& operator=(bool value) {
        if (index && fallback) {
            SetDynamicTlsFlag(*index, fallback, value);
        }
        return *this;
    }
};

static DynamicTlsFlag g_inside_hook{&g_inside_hook_tls, &g_inside_hook_fallback};
static DynamicTlsFlag g_inside_load_library_hook{
    &g_inside_load_library_hook_tls,
    &g_inside_load_library_hook_fallback};

struct TraceRange {
    uintptr_t begin = 0;
    uintptr_t end = 0;
    uintptr_t module_base = 0;
    bool dynamic = false;
    wchar_t module_name[kMonitorEventNameChars]{};
};

struct TraceState {
    bool active = false;
    bool has_previous = false;
    uint32_t instruction_budget = 0;
    uint32_t next_record = 0;
    uint32_t record_count = 0;
    uint64_t last_target_rip = 0;
    uint64_t last_target_tick_ms = 0;
    uintptr_t active_entry_address = 0;
    CONTEXT previous{};
    MonitorOriginRecord records[kMonitorMaxOriginRecords]{};
};

static constexpr uint32_t kRegTraceMaxInstructions = 32768;
static constexpr DWORD kLargeTraceImageThreshold = 32u * 1024u * 1024u;
static constexpr DWORD kTraceGuardRefreshIntervalMs = 5;
static TraceRange g_trace_ranges[128]{};
static uint32_t g_trace_range_count = 0;
static void* g_trace_handler = nullptr;
static HANDLE g_trace_guard_thread = nullptr;
static volatile LONG g_trace_guard_thread_stop = 0;
static volatile LONG g_active_register_traces = 0;
static volatile LONG g_register_trace_runtime_suspended = 0;
static volatile LONG g_managed_runtime_loaded = 0;
static uintptr_t g_loader_api_addresses[16]{};
static wchar_t g_loader_api_names[16][kMonitorEventNameChars]{};
static uint32_t g_loader_api_count = 0;
static SRWLOCK g_trace_range_lock = SRWLOCK_INIT;
static SRWLOCK g_trace_seed_lock = SRWLOCK_INIT;
static DWORD g_trace_seed_tids[64]{};
static uintptr_t g_main_module_base = 0;
static wchar_t g_main_module_dir[MAX_PATH * 4]{};
static thread_local TraceState g_trace_state;
static thread_local uintptr_t g_trace_suppress_begin = 0;
static thread_local uintptr_t g_trace_suppress_end = 0;
static thread_local uint64_t g_trace_suppress_tick_ms = 0;

struct VehWrapperRecord {
    PVECTORED_EXCEPTION_HANDLER original = nullptr;
    PVECTORED_EXCEPTION_HANDLER wrapper = nullptr;
};

static SRWLOCK g_veh_wrapper_lock = SRWLOCK_INIT;
static VehWrapperRecord g_veh_wrappers[16]{};

struct DispatchTraceRecord {
    bool valid = false;
    DWORD source_tid = 0;
    DWORD target_tid = 0;
    UINT message = 0;
    WPARAM wparam = 0;
    LPARAM lparam = 0;
    uintptr_t function_value = 0;
    uintptr_t argument_value = 0;
    uintptr_t requester_rip = 0;
    HANDLE wait_handle = nullptr;
    uint64_t tick_ms = 0;
    uint32_t flags = 0;
    wchar_t api_name[kMonitorEventNameChars]{};
    wchar_t dll_name[kMonitorTargetNameChars]{};
};

static SRWLOCK g_dispatch_trace_lock = SRWLOCK_INIT;
static DispatchTraceRecord g_dispatch_trace_records[128]{};
static uint32_t g_dispatch_trace_next_record = 0;
static volatile LONG g_dispatch_trace_hooks_installed = 0;
static volatile LONG g_dispatch_trace_installer_started = 0;

struct NetworkUseEmitRecord {
    uintptr_t caller = 0;
    DWORD tid = 0;
    uint32_t api_hash = 0;
    uint64_t tick_ms = 0;
};

static SRWLOCK g_network_use_emit_lock = SRWLOCK_INIT;
static NetworkUseEmitRecord g_network_use_emit_records[256]{};
static uint32_t g_network_use_emit_next_record = 0;

struct TemporalImageMonitorRecord {
    uintptr_t module_base = 0;
    uintptr_t module_end = 0;
    bool dirty = false;
    bool ever_dirty = false;
    bool restored_reported = false;
    bool unmap_reported = false;
    wchar_t path[kMonitorTargetNameChars]{};
};

static SRWLOCK g_temporal_image_lock = SRWLOCK_INIT;
static TemporalImageMonitorRecord g_temporal_image_records[64]{};

static wchar_t ToLowerChar(wchar_t ch) {
    return static_cast<wchar_t>(towlower(ch));
}

static void LowerInPlace(wchar_t* text) {
    if (!text) {
        return;
    }
    for (; *text; ++text) {
        *text = ToLowerChar(*text);
    }
}

static void SafeCopyWideString(wchar_t* destination, size_t destination_cch, const wchar_t* source) {
    if (!destination || destination_cch == 0) {
        return;
    }

    size_t out = 0;
    if (source) {
        while (out + 1 < destination_cch && source[out]) {
            destination[out] = source[out];
            ++out;
        }
    }
    destination[out] = L'\0';
}

static bool SafeAppendWideString(wchar_t* destination, size_t destination_cch, const wchar_t* suffix) {
    if (!destination || destination_cch == 0) {
        return false;
    }

    size_t out = 0;
    while (out < destination_cch && destination[out]) {
        ++out;
    }
    if (out >= destination_cch) {
        destination[destination_cch - 1] = L'\0';
        return false;
    }

    size_t in = 0;
    while (suffix && suffix[in] && out + 1 < destination_cch) {
        destination[out++] = suffix[in++];
    }
    destination[out] = L'\0';
    return !suffix || suffix[in] == L'\0';
}

static bool HasExtension(const wchar_t* text) {
    if (!text) {
        return false;
    }
    const wchar_t* last_sep = text;
    for (const wchar_t* cursor = text; *cursor; ++cursor) {
        if (*cursor == L'\\' || *cursor == L'/' || *cursor == L':') {
            last_sep = cursor + 1;
        }
    }
    return wcschr(last_sep, L'.') != nullptr;
}

static void CopyLowerBasenameFromUnicodeString(PUNICODE_STRING input, wchar_t* output, size_t output_cch) {
    if (!output || output_cch == 0) {
        return;
    }

    output[0] = L'\0';
    if (!input || !input->Buffer || input->Length == 0) {
        return;
    }

    const size_t input_cch = input->Length / sizeof(wchar_t);
    size_t start = 0;
    for (size_t i = 0; i < input_cch; ++i) {
        const wchar_t ch = input->Buffer[i];
        if (ch == L'\\' || ch == L'/' || ch == L':') {
            start = i + 1;
        }
    }

    size_t out = 0;
    for (size_t i = start; i < input_cch && out + 1 < output_cch; ++i) {
        output[out++] = ToLowerChar(input->Buffer[i]);
    }
    output[out] = L'\0';
}

static bool IsWatchedDll(const wchar_t* lower_basename) {
    if (!lower_basename || !lower_basename[0]) {
        return false;
    }

    wchar_t canonical[kMonitorWatchedDllNameChars]{};
    SafeCopyWideString(canonical, _countof(canonical), lower_basename);
    if (!HasExtension(canonical)) {
        SafeAppendWideString(canonical, _countof(canonical), L".dll");
    }

    const uint32_t count = std::min(g_config.watched_dll_count, kMonitorMaxWatchedDlls);
    for (uint32_t i = 0; i < count; ++i) {
        if (g_config.watched_dlls[i][0] &&
            (wcscmp(g_config.watched_dlls[i], lower_basename) == 0 ||
                wcscmp(g_config.watched_dlls[i], canonical) == 0)) {
            return true;
        }
    }
    return false;
}

static bool OriginTraceEnabled() {
    return (g_config.hook_flags & (
        kMonitorHookOriginTrace |
        kMonitorHookRegisterTrace |
        kMonitorHookDispatchTrace |
        kMonitorHookThreadpoolChainTrace)) != 0;
}

static bool RegisterTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookRegisterTrace) != 0;
}

static void InitializeMonitorTlsFlags() {
    if (g_inside_hook_tls == TLS_OUT_OF_INDEXES) {
        g_inside_hook_tls = TlsAlloc();
    }
    if (g_inside_load_library_hook_tls == TLS_OUT_OF_INDEXES) {
        g_inside_load_library_hook_tls = TlsAlloc();
    }
}

static void FreeMonitorTlsFlags() {
    if (g_inside_hook_tls != TLS_OUT_OF_INDEXES) {
        TlsFree(g_inside_hook_tls);
        g_inside_hook_tls = TLS_OUT_OF_INDEXES;
    }
    if (g_inside_load_library_hook_tls != TLS_OUT_OF_INDEXES) {
        TlsFree(g_inside_load_library_hook_tls);
        g_inside_load_library_hook_tls = TLS_OUT_OF_INDEXES;
    }
    InterlockedExchange(&g_inside_hook_fallback, 0);
    InterlockedExchange(&g_inside_load_library_hook_fallback, 0);
}

static bool RegisterTraceRuntimeSuspended() {
    return InterlockedCompareExchange(&g_register_trace_runtime_suspended, 0, 0) != 0;
}

static bool RegisterTraceCanInstrument() {
    return RegisterTraceEnabled() && !RegisterTraceRuntimeSuspended();
}

static bool ManagedRuntimeLoaded() {
    return InterlockedCompareExchange(&g_managed_runtime_loaded, 0, 0) != 0;
}

static bool FollowRemoteEnabled() {
    return (g_config.hook_flags & kMonitorHookFollowRemote) != 0;
}

static bool NetResetEnabled() {
    return (g_config.hook_flags & kMonitorHookNetReset) != 0;
}

static bool LdrIntegrityEnabled() {
    return (g_config.hook_flags & kMonitorHookLdrIntegrity) != 0;
}

static bool DispatchTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookDispatchTrace) != 0;
}

static bool ThreadpoolChainTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookThreadpoolChainTrace) != 0;
}

static bool ByoudTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookByoudTrace) != 0;
}

static bool ShadowStackEnabled() {
    return (g_config.hook_flags & kMonitorHookShadowStack) != 0;
}

static bool NetworkUseTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookNetworkUseTrace) != 0;
}

static bool MemoryApiEventsEnabled() {
    return (g_config.hook_flags & kMonitorHookMemoryApis) != 0;
}

static bool TemporalImageTraceEnabled() {
    return (g_config.hook_flags & kMonitorHookTemporalImageTrace) != 0;
}

static bool IsAddressInTraceRangeNoLock(uintptr_t address) {
    for (uint32_t i = 0; i < g_trace_range_count; ++i) {
        if (address >= g_trace_ranges[i].begin && address < g_trace_ranges[i].end) {
            return true;
        }
    }
    return false;
}

static bool IsAddressInTraceRange(uintptr_t address) {
    bool result = false;
    AcquireSRWLockShared(&g_trace_range_lock);
    result = IsAddressInTraceRangeNoLock(address);
    ReleaseSRWLockShared(&g_trace_range_lock);
    return result;
}

static bool GetTraceRangeForAddress(uintptr_t address, uintptr_t* begin, uintptr_t* end) {
    bool result = false;
    AcquireSRWLockShared(&g_trace_range_lock);
    for (uint32_t i = 0; i < g_trace_range_count; ++i) {
        const TraceRange& range = g_trace_ranges[i];
        if (address >= range.begin && address < range.end) {
            if (begin) {
                *begin = range.begin;
            }
            if (end) {
                *end = range.end;
            }
            result = true;
            break;
        }
    }
    ReleaseSRWLockShared(&g_trace_range_lock);
    return result;
}

static bool IsExecutableMemoryProtect(DWORD protect) {
    const DWORD clean = protect & ~(PAGE_GUARD | PAGE_NOCACHE | PAGE_WRITECOMBINE);
    return clean == PAGE_EXECUTE ||
        clean == PAGE_EXECUTE_READ ||
        clean == PAGE_EXECUTE_READWRITE ||
        clean == PAGE_EXECUTE_WRITECOPY;
}

static DWORD RemoveGuardFlag(DWORD protect) {
    return protect & ~PAGE_GUARD;
}

static const wchar_t* BasenamePtr(const wchar_t* path) {
    if (!path) {
        return L"";
    }
    const wchar_t* basename = path;
    for (const wchar_t* cursor = path; *cursor; ++cursor) {
        if (*cursor == L'\\' || *cursor == L'/' || *cursor == L':') {
            basename = cursor + 1;
        }
    }
    return basename;
}

static bool StartsWithString(const wchar_t* text, const wchar_t* prefix) {
    if (!text || !prefix || !prefix[0]) {
        return false;
    }
    const size_t prefix_len = wcslen(prefix);
    return wcsncmp(text, prefix, prefix_len) == 0;
}

static bool ContainsString(const wchar_t* text, const wchar_t* needle) {
    return text && needle && needle[0] && wcsstr(text, needle) != nullptr;
}

static bool GetLowerModulePath(HMODULE module, wchar_t* output, size_t output_cch) {
    if (!module || !output || output_cch == 0) {
        return false;
    }
    output[0] = L'\0';
    if (!GetModuleFileNameW(module, output, static_cast<DWORD>(output_cch))) {
        return false;
    }
    output[output_cch - 1] = L'\0';
    LowerInPlace(output);
    return output[0] != L'\0';
}

static bool IsSystemLikeModulePath(const wchar_t* lower_path) {
    if (!lower_path || !lower_path[0]) {
        return true;
    }
    return ContainsString(lower_path, L"\\windows\\") ||
        ContainsString(lower_path, L"\\program files\\") ||
        ContainsString(lower_path, L"\\program files (x86)\\");
}

static bool IsTraceExcludedModuleName(const wchar_t* lower_name) {
    if (!lower_name || !lower_name[0]) {
        return true;
    }
    if (wcscmp(lower_name, L"callstackmonitor.dll") == 0 ||
        wcscmp(lower_name, L"ntdll.dll") == 0 ||
        wcscmp(lower_name, L"kernel32.dll") == 0 ||
        wcscmp(lower_name, L"kernelbase.dll") == 0 ||
        wcscmp(lower_name, L"wow64.dll") == 0 ||
        wcscmp(lower_name, L"wow64cpu.dll") == 0 ||
        wcscmp(lower_name, L"ucrtbase.dll") == 0 ||
        wcscmp(lower_name, L"msvcrt.dll") == 0 ||
        wcscmp(lower_name, L"mscoree.dll") == 0 ||
        wcscmp(lower_name, L"clr.dll") == 0 ||
        wcscmp(lower_name, L"clrjit.dll") == 0 ||
        wcscmp(lower_name, L"coreclr.dll") == 0 ||
        wcscmp(lower_name, L"mscorwks.dll") == 0) {
        return true;
    }
    return IsWatchedDll(lower_name);
}

static void CopyWideString(wchar_t* destination, size_t destination_cch, const wchar_t* source) {
    SafeCopyWideString(destination, destination_cch, source);
}

static void ModuleBasenameForAddress(uintptr_t address, wchar_t* output, size_t output_cch) {
    if (!output || output_cch == 0) {
        return;
    }
    output[0] = L'\0';

    HMODULE module = nullptr;
    if (!GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(address),
        &module) || !module) {
        return;
    }

    wchar_t path[MAX_PATH * 4]{};
    if (!GetModuleFileNameW(module, path, _countof(path))) {
        return;
    }

    const wchar_t* basename = path;
    for (const wchar_t* cursor = path; *cursor; ++cursor) {
        if (*cursor == L'\\' || *cursor == L'/' || *cursor == L':') {
            basename = cursor + 1;
        }
    }
    CopyWideString(output, output_cch, basename);
    LowerInPlace(output);
}

static bool IsClrLikeModuleName(const wchar_t* lower_name) {
    if (!lower_name || !lower_name[0]) {
        return false;
    }
    return wcscmp(lower_name, L"mscoree.dll") == 0 ||
        wcscmp(lower_name, L"clr.dll") == 0 ||
        wcscmp(lower_name, L"clrjit.dll") == 0 ||
        wcscmp(lower_name, L"coreclr.dll") == 0 ||
        wcscmp(lower_name, L"mscorwks.dll") == 0;
}

static bool IsAddressInClrLikeModule(uintptr_t address) {
    if (!address) {
        return false;
    }
    wchar_t module_name[kMonitorEventNameChars]{};
    ModuleBasenameForAddress(address, module_name, _countof(module_name));
    return IsClrLikeModuleName(module_name);
}

static bool CurrentStackHasClrLikeFrame() {
    void* frames[24]{};
    const USHORT captured = RtlCaptureStackBackTrace(1, _countof(frames), frames, nullptr);
    for (USHORT i = 0; i < captured; ++i) {
        if (IsAddressInClrLikeModule(reinterpret_cast<uintptr_t>(frames[i]))) {
            return true;
        }
    }
    return false;
}

static bool ReadProcessBytes(uintptr_t address, void* buffer, size_t size) {
    if (!address || !buffer || size == 0) {
        return false;
    }
    SIZE_T bytes_read = 0;
    return ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(address), buffer, size, &bytes_read) &&
        bytes_read == size;
}

static uintptr_t FindExecutableAddressInSameAllocation(uintptr_t address) {
    if (!address) {
        return 0;
    }

    MEMORY_BASIC_INFORMATION seed{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &seed, sizeof(seed)) ||
        seed.State != MEM_COMMIT ||
        !seed.AllocationBase) {
        return 0;
    }

    const uintptr_t allocation_base = reinterpret_cast<uintptr_t>(seed.AllocationBase);
    uintptr_t cursor = allocation_base;
    for (uint32_t i = 0; i < 1024; ++i) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) ||
            mbi.RegionSize == 0 ||
            mbi.AllocationBase != seed.AllocationBase) {
            break;
        }

        if (mbi.State == MEM_COMMIT &&
            IsExecutableMemoryProtect(mbi.Protect) &&
            (mbi.Type == MEM_PRIVATE || mbi.Type == MEM_MAPPED || mbi.Type == MEM_IMAGE)) {
            return reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        }

        const uintptr_t next = reinterpret_cast<uintptr_t>(mbi.BaseAddress) + static_cast<uintptr_t>(mbi.RegionSize);
        if (next <= cursor) {
            break;
        }
        cursor = next;
    }

    return 0;
}

static uintptr_t FindExecutableOriginNearPointer(uintptr_t address) {
    if (!address) {
        return 0;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) &&
        mbi.State == MEM_COMMIT &&
        IsExecutableMemoryProtect(mbi.Protect)) {
        return address;
    }

    return FindExecutableAddressInSameAllocation(address);
}

static void AddLoaderApi(HMODULE module, const char* proc_name, const wchar_t* display_name) {
    if (!module || !proc_name || !display_name || g_loader_api_count >= _countof(g_loader_api_addresses)) {
        return;
    }
    void* address = reinterpret_cast<void*>(GetProcAddress(module, proc_name));
    if (!address) {
        return;
    }
    const uintptr_t value = reinterpret_cast<uintptr_t>(address);
    for (uint32_t i = 0; i < g_loader_api_count; ++i) {
        if (g_loader_api_addresses[i] == value) {
            return;
        }
    }
    g_loader_api_addresses[g_loader_api_count] = value;
    CopyWideString(g_loader_api_names[g_loader_api_count], _countof(g_loader_api_names[g_loader_api_count]), display_name);
    ++g_loader_api_count;
}

static void ResolveLoaderApis() {
    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    HMODULE kernelbase = GetModuleHandleW(L"kernelbase.dll");
    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");

    AddLoaderApi(kernel32, "LoadLibraryA", L"LoadLibraryA");
    AddLoaderApi(kernel32, "LoadLibraryW", L"LoadLibraryW");
    AddLoaderApi(kernel32, "LoadLibraryExA", L"LoadLibraryExA");
    AddLoaderApi(kernel32, "LoadLibraryExW", L"LoadLibraryExW");
    AddLoaderApi(kernelbase, "LoadLibraryA", L"LoadLibraryA");
    AddLoaderApi(kernelbase, "LoadLibraryW", L"LoadLibraryW");
    AddLoaderApi(kernelbase, "LoadLibraryExA", L"LoadLibraryExA");
    AddLoaderApi(kernelbase, "LoadLibraryExW", L"LoadLibraryExW");
    AddLoaderApi(ntdll, "LdrLoadDll", L"LdrLoadDll");
}

static bool IsLoaderApiPointer(uintptr_t value, wchar_t* output, size_t output_cch) {
    for (uint32_t i = 0; i < g_loader_api_count; ++i) {
        if (g_loader_api_addresses[i] == value) {
            CopyWideString(output, output_cch, g_loader_api_names[i]);
            return true;
        }
    }
    return false;
}

static bool NormalizeWatchedName(std::wstring& value) {
    if (value.empty()) {
        return false;
    }
    size_t end = value.find(L'\0');
    if (end != std::wstring::npos) {
        value.resize(end);
    }
    size_t start = value.find_last_of(L"\\/:");
    if (start == std::wstring::npos) {
        start = 0;
    } else {
        ++start;
    }
    value = value.substr(start);
    std::transform(value.begin(), value.end(), value.begin(), [](wchar_t ch) {
        return static_cast<wchar_t>(towlower(ch));
    });
    return !value.empty();
}

static bool IsWatchedDllStringPointer(uintptr_t value, wchar_t* output, size_t output_cch) {
    if (!value) {
        return false;
    }

    char ansi[128]{};
    if (ReadProcessBytes(value, ansi, sizeof(ansi) - 1)) {
        std::string text;
        for (char ch : ansi) {
            if (!ch) {
                break;
            }
            if (static_cast<unsigned char>(ch) < 0x20 || static_cast<unsigned char>(ch) > 0x7e) {
                text.clear();
                break;
            }
            text.push_back(ch);
        }
        if (!text.empty()) {
            const int needed = MultiByteToWideChar(CP_ACP, 0, text.c_str(), static_cast<int>(text.size()), nullptr, 0);
            if (needed > 0) {
                std::wstring wide(static_cast<size_t>(needed), L'\0');
                MultiByteToWideChar(CP_ACP, 0, text.c_str(), static_cast<int>(text.size()), wide.data(), needed);
                if (NormalizeWatchedName(wide) && IsWatchedDll(wide.c_str())) {
                    CopyWideString(output, output_cch, wide.c_str());
                    return true;
                }
            }
        }
    }

    wchar_t wide_buffer[128]{};
    if (ReadProcessBytes(value, wide_buffer, sizeof(wide_buffer) - sizeof(wchar_t))) {
        std::wstring wide;
        for (wchar_t ch : wide_buffer) {
            if (!ch) {
                break;
            }
            if (ch < 0x20 || ch > 0x7e) {
                wide.clear();
                break;
            }
            wide.push_back(ch);
        }
        if (NormalizeWatchedName(wide) && IsWatchedDll(wide.c_str())) {
            CopyWideString(output, output_cch, wide.c_str());
            return true;
        }
    }
    return false;
}

static bool IsWatchedDllUnicodeStringPointer(uintptr_t value, wchar_t* output, size_t output_cch,
    uintptr_t* buffer_address = nullptr) {
    if (!value) {
        return false;
    }

    UNICODE_STRING unicode_string{};
    if (!ReadProcessBytes(value, &unicode_string, sizeof(unicode_string)) ||
        !unicode_string.Buffer ||
        unicode_string.Length == 0 ||
        unicode_string.MaximumLength < unicode_string.Length ||
        unicode_string.Length > 512) {
        return false;
    }

    const size_t cch = std::min<size_t>(unicode_string.Length / sizeof(wchar_t), 255);
    if (cch == 0) {
        return false;
    }

    wchar_t buffer[256]{};
    if (!ReadProcessBytes(reinterpret_cast<uintptr_t>(unicode_string.Buffer), buffer, cch * sizeof(wchar_t))) {
        return false;
    }

    std::wstring text(buffer, cch);
    if (NormalizeWatchedName(text) && IsWatchedDll(text.c_str())) {
        CopyWideString(output, output_cch, text.c_str());
        if (buffer_address) {
            *buffer_address = reinterpret_cast<uintptr_t>(unicode_string.Buffer);
        }
        return true;
    }

    return false;
}

static bool IsWatchedDllPointer(uintptr_t value, wchar_t* output, size_t output_cch,
    uintptr_t* content_address = nullptr) {
    if (IsWatchedDllStringPointer(value, output, output_cch)) {
        if (content_address) {
            *content_address = value;
        }
        return true;
    }
    return IsWatchedDllUnicodeStringPointer(value, output, output_cch, content_address);
}

static bool LooksLikeGadgetPointer(uintptr_t value, wchar_t* output, size_t output_cch) {
    if (!value || IsAddressInTraceRange(value)) {
        return false;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(reinterpret_cast<void*>(value), &mbi, sizeof(mbi)) ||
        mbi.State != MEM_COMMIT ||
        mbi.Type != MEM_IMAGE ||
        !IsExecutableMemoryProtect(mbi.Protect)) {
        return false;
    }

    uint8_t bytes[16]{};
    if (!ReadProcessBytes(value, bytes, sizeof(bytes))) {
        return false;
    }

    if (!ZydisLooksLikeRegisterProxyGadget(bytes, sizeof(bytes), value)) {
        return false;
    }

    wchar_t module_name[kMonitorEventNameChars]{};
    ModuleBasenameForAddress(value, module_name, _countof(module_name));
    if (module_name[0]) {
        CopyWideString(output, output_cch, module_name);
    } else {
        CopyWideString(output, output_cch, L"image-gadget");
    }
    return true;
}

static bool ClassifyOriginValue(uintptr_t value, uint32_t& kind, wchar_t* name, size_t name_cch) {
    kind = kMonitorOriginNone;
    if (IsLoaderApiPointer(value, name, name_cch)) {
        kind = kMonitorOriginLoaderApiPointer;
        return true;
    }
    if (IsWatchedDllStringPointer(value, name, name_cch)) {
        kind = kMonitorOriginDllStringPointer;
        return true;
    }
    if (IsWatchedDllUnicodeStringPointer(value, name, name_cch)) {
        kind = kMonitorOriginDllStringPointer;
        return true;
    }
    if (LooksLikeGadgetPointer(value, name, name_cch)) {
        kind = kMonitorOriginGadgetPointer;
        return true;
    }
    return false;
}

static void RecordOriginTrace(uint32_t kind, uint32_t reg, uintptr_t writer_rip, uintptr_t value,
    uintptr_t target_rip, const wchar_t* name, const wchar_t* value_name) {
    if (!OriginTraceEnabled() || kind == kMonitorOriginNone || !writer_rip) {
        return;
    }

    MonitorOriginRecord& record = g_trace_state.records[g_trace_state.next_record % kMonitorMaxOriginRecords];
    record = {};
    record.kind = kind;
    record.reg = reg;
    record.writer_rip = static_cast<uint64_t>(writer_rip);
    record.value = static_cast<uint64_t>(value);
    record.target_rip = static_cast<uint64_t>(target_rip);
    record.tick_ms = GetTickCount64();
    CopyWideString(record.name, _countof(record.name), name);
    CopyWideString(record.value_name, _countof(record.value_name), value_name);

    g_trace_state.next_record = (g_trace_state.next_record + 1) % kMonitorMaxOriginRecords;
    if (g_trace_state.record_count < kMonitorMaxOriginRecords) {
        ++g_trace_state.record_count;
    }
}

static void RecordDispatchOriginTrace(const DispatchTraceRecord& dispatch, uintptr_t return_address, const wchar_t* dll_name) {
    if (!DispatchTraceEnabled() || !dispatch.valid || !dispatch.requester_rip) {
        return;
    }

    MonitorOriginRecord& record = g_trace_state.records[g_trace_state.next_record % kMonitorMaxOriginRecords];
    record = {};
    record.kind = kMonitorOriginDllStringPointer;
    record.reg = kMonitorRegNone;
    record.writer_rip = static_cast<uint64_t>(dispatch.requester_rip);
    record.value = static_cast<uint64_t>(dispatch.function_value);
    record.target_rip = static_cast<uint64_t>(return_address);
    record.tick_ms = GetTickCount64();
    record.source_tid = dispatch.source_tid;
    record.target_tid = dispatch.target_tid;
    record.message = dispatch.message;
    record.origin_flags = dispatch.flags;
    record.dispatch_wparam = static_cast<uint64_t>(dispatch.wparam);
    record.dispatch_lparam = static_cast<uint64_t>(dispatch.lparam);
    CopyWideString(record.name, _countof(record.name), L"thread-message-dispatch");
    const wchar_t* value_name = dispatch.api_name[0]
        ? dispatch.api_name
        : (dll_name && dll_name[0] ? dll_name : L"loader-api");
    CopyWideString(record.value_name, _countof(record.value_name), value_name);

    g_trace_state.next_record = (g_trace_state.next_record + 1) % kMonitorMaxOriginRecords;
    if (g_trace_state.record_count < kMonitorMaxOriginRecords) {
        ++g_trace_state.record_count;
    }
}

static void TraceRegisterChange(uint32_t reg, uintptr_t writer_rip, uintptr_t value, uintptr_t current_rip) {
    if (!IsAddressInTraceRange(writer_rip)) {
        return;
    }

    uint32_t kind = kMonitorOriginNone;
    wchar_t value_name[kMonitorTargetNameChars]{};
    if (ClassifyOriginValue(value, kind, value_name, _countof(value_name))) {
        RecordOriginTrace(kind, reg, writer_rip, value, current_rip, L"register-write", value_name);
    }
}

static bool IsCommonLoaderModuleName(const wchar_t* name) {
    if (!name || !name[0]) {
        return false;
    }
    return wcscmp(name, L"ntdll.dll") == 0 ||
        wcscmp(name, L"kernel32.dll") == 0 ||
        wcscmp(name, L"kernelbase.dll") == 0 ||
        wcscmp(name, L"wow64.dll") == 0 ||
        wcscmp(name, L"wow64cpu.dll") == 0;
}

static void TraceRegisterDiff(const CONTEXT& previous, const CONTEXT& current) {
    const uintptr_t writer = static_cast<uintptr_t>(previous.Rip);
    if (!IsAddressInTraceRange(writer)) {
        return;
    }

    g_trace_state.last_target_rip = writer;
    g_trace_state.last_target_tick_ms = GetTickCount64();

    if (previous.Rax != current.Rax) TraceRegisterChange(kMonitorRegRax, writer, static_cast<uintptr_t>(current.Rax), static_cast<uintptr_t>(current.Rip));
    if (previous.Rbx != current.Rbx) TraceRegisterChange(kMonitorRegRbx, writer, static_cast<uintptr_t>(current.Rbx), static_cast<uintptr_t>(current.Rip));
    if (previous.Rcx != current.Rcx) TraceRegisterChange(kMonitorRegRcx, writer, static_cast<uintptr_t>(current.Rcx), static_cast<uintptr_t>(current.Rip));
    if (previous.Rdx != current.Rdx) TraceRegisterChange(kMonitorRegRdx, writer, static_cast<uintptr_t>(current.Rdx), static_cast<uintptr_t>(current.Rip));
    if (previous.Rsi != current.Rsi) TraceRegisterChange(kMonitorRegRsi, writer, static_cast<uintptr_t>(current.Rsi), static_cast<uintptr_t>(current.Rip));
    if (previous.Rdi != current.Rdi) TraceRegisterChange(kMonitorRegRdi, writer, static_cast<uintptr_t>(current.Rdi), static_cast<uintptr_t>(current.Rip));
    if (previous.Rbp != current.Rbp) TraceRegisterChange(kMonitorRegRbp, writer, static_cast<uintptr_t>(current.Rbp), static_cast<uintptr_t>(current.Rip));
    if (previous.Rsp != current.Rsp) TraceRegisterChange(kMonitorRegRsp, writer, static_cast<uintptr_t>(current.Rsp), static_cast<uintptr_t>(current.Rip));
    if (previous.R8 != current.R8) TraceRegisterChange(kMonitorRegR8, writer, static_cast<uintptr_t>(current.R8), static_cast<uintptr_t>(current.Rip));
    if (previous.R9 != current.R9) TraceRegisterChange(kMonitorRegR9, writer, static_cast<uintptr_t>(current.R9), static_cast<uintptr_t>(current.Rip));
    if (previous.R10 != current.R10) TraceRegisterChange(kMonitorRegR10, writer, static_cast<uintptr_t>(current.R10), static_cast<uintptr_t>(current.Rip));
    if (previous.R11 != current.R11) TraceRegisterChange(kMonitorRegR11, writer, static_cast<uintptr_t>(current.R11), static_cast<uintptr_t>(current.Rip));
    if (previous.R12 != current.R12) TraceRegisterChange(kMonitorRegR12, writer, static_cast<uintptr_t>(current.R12), static_cast<uintptr_t>(current.Rip));
    if (previous.R13 != current.R13) TraceRegisterChange(kMonitorRegR13, writer, static_cast<uintptr_t>(current.R13), static_cast<uintptr_t>(current.Rip));
    if (previous.R14 != current.R14) TraceRegisterChange(kMonitorRegR14, writer, static_cast<uintptr_t>(current.R14), static_cast<uintptr_t>(current.Rip));
    if (previous.R15 != current.R15) TraceRegisterChange(kMonitorRegR15, writer, static_cast<uintptr_t>(current.R15), static_cast<uintptr_t>(current.Rip));

    const uintptr_t current_rip = static_cast<uintptr_t>(current.Rip);
    if (previous.Rip != current.Rip &&
        IsAddressInTraceRange(writer) &&
        !IsAddressInTraceRange(current_rip)) {
        wchar_t gadget_name[kMonitorTargetNameChars]{};
        if (LooksLikeGadgetPointer(current_rip, gadget_name, _countof(gadget_name))) {
            RecordOriginTrace(
                kMonitorOriginProxyTransfer,
                kMonitorRegRip,
                writer,
                current_rip,
                current_rip,
                L"proxy-transfer",
                gadget_name);
        } else {
            ModuleBasenameForAddress(current_rip, gadget_name, _countof(gadget_name));
            if (gadget_name[0] && !IsCommonLoaderModuleName(gadget_name)) {
                RecordOriginTrace(
                    kMonitorOriginProxyTransfer,
                    kMonitorRegRip,
                    writer,
                    current_rip,
                    current_rip,
                    L"image-transfer",
                    gadget_name);
            }
        }
    }
}

static void FillRegisterSnapshot(const CONTEXT& context, MonitorRegisterSnapshot& snapshot) {
    snapshot.rip = context.Rip;
    snapshot.rsp = context.Rsp;
    snapshot.rax = context.Rax;
    snapshot.rbx = context.Rbx;
    snapshot.rcx = context.Rcx;
    snapshot.rdx = context.Rdx;
    snapshot.rsi = context.Rsi;
    snapshot.rdi = context.Rdi;
    snapshot.rbp = context.Rbp;
    snapshot.r8 = context.R8;
    snapshot.r9 = context.R9;
    snapshot.r10 = context.R10;
    snapshot.r11 = context.R11;
    snapshot.r12 = context.R12;
    snapshot.r13 = context.R13;
    snapshot.r14 = context.R14;
    snapshot.r15 = context.R15;
}

static USHORT CaptureShadowStackFrames(void** frames, uint32_t frames_to_skip, uint32_t frames_to_capture);

static void CopyOriginTraceRecords(MonitorEvent& event) {
    if (!OriginTraceEnabled() || g_trace_state.record_count == 0) {
        if (RegisterTraceEnabled() && g_trace_state.last_target_rip != 0) {
            event.origin_records[0] = {};
            event.origin_records[0].kind = kMonitorOriginProxyTransfer;
            event.origin_records[0].reg = kMonitorRegRip;
            event.origin_records[0].writer_rip = g_trace_state.last_target_rip;
            event.origin_records[0].tick_ms = g_trace_state.last_target_tick_ms;
            CopyWideString(event.origin_records[0].name, _countof(event.origin_records[0].name), L"last-target-rip");
            CopyWideString(event.origin_records[0].value_name, _countof(event.origin_records[0].value_name), L"traced-target-code");
            event.origin_record_count = 1;
        }
        return;
    }

    const uint32_t shadow_reserve = ShadowStackEnabled()
        ? std::min<uint32_t>(6, kMonitorMaxOriginRecords / 2)
        : 0;
    const uint32_t max_origin_records = std::max<uint32_t>(1, kMonitorMaxOriginRecords - shadow_reserve);
    const uint32_t count = std::min<uint32_t>(g_trace_state.record_count, max_origin_records);
    const uint32_t start = (g_trace_state.next_record + kMonitorMaxOriginRecords - count) % kMonitorMaxOriginRecords;
    for (uint32_t i = 0; i < count; ++i) {
        event.origin_records[i] = g_trace_state.records[(start + i) % kMonitorMaxOriginRecords];
    }
    event.origin_record_count = count;
}

static void AppendShadowStackRecords(MonitorEvent& event) {
    if (!ShadowStackEnabled() || event.origin_record_count >= kMonitorMaxOriginRecords) {
        return;
    }

    void* shadow_frames[kMonitorMaxOriginRecords]{};
    const USHORT captured = CaptureShadowStackFrames(shadow_frames, 4, kMonitorMaxOriginRecords);
    for (USHORT i = 0; i < captured && event.origin_record_count < kMonitorMaxOriginRecords; ++i) {
        if (!shadow_frames[i]) {
            continue;
        }
        MonitorOriginRecord& record = event.origin_records[event.origin_record_count++];
        record = {};
        record.kind = kMonitorOriginShadowStackFrame;
        record.reg = kMonitorRegNone;
        record.writer_rip = reinterpret_cast<uint64_t>(shadow_frames[i]);
        record.value = i;
        record.target_rip = event.registers.rip;
        record.tick_ms = GetTickCount64();
        CopyWideString(record.name, _countof(record.name), L"shadow-stack");
        CopyWideString(record.value_name, _countof(record.value_name), L"cet-return-address");
    }
}

static bool SameDllNameLoose(const wchar_t* left, const wchar_t* right) {
    if (!left || !right || !left[0] || !right[0]) {
        return false;
    }

    wchar_t a[kMonitorWatchedDllNameChars]{};
    wchar_t b[kMonitorWatchedDllNameChars]{};
    CopyWideString(a, _countof(a), left);
    CopyWideString(b, _countof(b), right);
    LowerInPlace(a);
    LowerInPlace(b);
    if (!HasExtension(a)) {
        SafeAppendWideString(a, _countof(a), L".dll");
    }
    if (!HasExtension(b)) {
        SafeAppendWideString(b, _countof(b), L".dll");
    }
    return wcscmp(a, b) == 0;
}

static void RememberDispatchTraceRecord(const DispatchTraceRecord& record) {
    if (!DispatchTraceEnabled() || !record.valid || !record.target_tid || !record.source_tid) {
        return;
    }

    AcquireSRWLockExclusive(&g_dispatch_trace_lock);
    g_dispatch_trace_records[g_dispatch_trace_next_record % _countof(g_dispatch_trace_records)] = record;
    ++g_dispatch_trace_next_record;
    ReleaseSRWLockExclusive(&g_dispatch_trace_lock);
}

static bool FindRecentDispatchTraceForThread(DWORD target_tid, const wchar_t* dll_name, DispatchTraceRecord& out) {
    if (!DispatchTraceEnabled() || !target_tid || !dll_name || !dll_name[0]) {
        return false;
    }

    const uint64_t now = GetTickCount64();
    constexpr uint64_t kDispatchCorrelationWindowMs = 30000;
    bool found = false;
    DispatchTraceRecord best{};

    AcquireSRWLockShared(&g_dispatch_trace_lock);
    for (const auto& record : g_dispatch_trace_records) {
        if (!record.valid ||
            record.target_tid != target_tid ||
            !SameDllNameLoose(record.dll_name, dll_name) ||
            record.tick_ms == 0 ||
            now < record.tick_ms ||
            now - record.tick_ms > kDispatchCorrelationWindowMs) {
            continue;
        }
        if (!found || record.tick_ms > best.tick_ms) {
            best = record;
            found = true;
        }
    }
    ReleaseSRWLockShared(&g_dispatch_trace_lock);

    if (found) {
        out = best;
    }
    return found;
}

static void MarkDispatchWaitForHandle(HANDLE handle) {
    if (!DispatchTraceEnabled() || !handle || handle == INVALID_HANDLE_VALUE) {
        return;
    }

    const DWORD tid = GetCurrentThreadId();
    const uint64_t now = GetTickCount64();
    constexpr uint64_t kDispatchWaitWindowMs = 30000;
    AcquireSRWLockExclusive(&g_dispatch_trace_lock);
    for (auto& record : g_dispatch_trace_records) {
        if (!record.valid ||
            record.source_tid != tid ||
            record.wait_handle != handle ||
            record.tick_ms == 0 ||
            now < record.tick_ms ||
            now - record.tick_ms > kDispatchWaitWindowMs) {
            continue;
        }
        record.flags |= kMonitorOriginFlagDispatchWaitObserved;
    }
    ReleaseSRWLockExclusive(&g_dispatch_trace_lock);
}

static void SetTrapFlag(CONTEXT* context) {
    if (context) {
        context->EFlags |= 0x100;
    }
}

static void ClearTrapFlag(CONTEXT* context) {
    if (context) {
        context->EFlags &= ~0x100u;
    }
}

static bool IsRegisterTraceSuppressed(uintptr_t address) {
    if (!address || !g_trace_suppress_begin || address < g_trace_suppress_begin || address >= g_trace_suppress_end) {
        return false;
    }
    const uint64_t now = GetTickCount64();
    if (g_trace_suppress_tick_ms == 0 || now < g_trace_suppress_tick_ms || now - g_trace_suppress_tick_ms > 30000) {
        g_trace_suppress_begin = 0;
        g_trace_suppress_end = 0;
        g_trace_suppress_tick_ms = 0;
        return false;
    }
    return true;
}

static void SuppressRegisterTraceForAddress(uintptr_t address) {
    if (!address) {
        return;
    }

    uintptr_t begin = 0;
    uintptr_t end = 0;
    if (!GetTraceRangeForAddress(address, &begin, &end)) {
        constexpr uintptr_t kPageSize = 0x1000;
        begin = address & ~(kPageSize - 1);
        end = begin + kPageSize;
    }

    g_trace_suppress_begin = begin;
    g_trace_suppress_end = end;
    g_trace_suppress_tick_ms = GetTickCount64();
}

static bool ArmTraceGuardForAddress(uintptr_t address) {
    if (!RegisterTraceCanInstrument() || IsRegisterTraceSuppressed(address) || !IsAddressInTraceRange(address)) {
        return false;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) ||
        mbi.State != MEM_COMMIT ||
        !IsExecutableMemoryProtect(mbi.Protect)) {
        return false;
    }
    if (mbi.Protect & PAGE_GUARD) {
        return true;
    }

    DWORD old_protect = 0;
    return VirtualProtect(
        mbi.BaseAddress,
        mbi.RegionSize,
        RemoveGuardFlag(mbi.Protect) | PAGE_GUARD,
        &old_protect) != FALSE;
}

static void ArmTraceGuardForRange(uintptr_t begin, uintptr_t end) {
    if (!RegisterTraceCanInstrument() || begin >= end) {
        return;
    }

    uintptr_t cursor = begin;
    while (cursor < end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) ||
            mbi.RegionSize == 0) {
            break;
        }

        const uintptr_t region_begin = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t region_end = region_begin + static_cast<uintptr_t>(mbi.RegionSize);
        const uintptr_t protect_begin = std::max(cursor, region_begin);
        const uintptr_t protect_end = std::min(end, region_end);
        if (protect_end <= protect_begin) {
            cursor = region_end > cursor ? region_end : cursor + 0x1000;
            continue;
        }

        if (mbi.State == MEM_COMMIT &&
            IsExecutableMemoryProtect(mbi.Protect) &&
            (mbi.Protect & PAGE_GUARD) == 0) {
            DWORD old_protect = 0;
            VirtualProtect(
                reinterpret_cast<void*>(protect_begin),
                protect_end - protect_begin,
                RemoveGuardFlag(mbi.Protect) | PAGE_GUARD,
                &old_protect);
        }

        cursor = protect_end > cursor ? protect_end : cursor + 0x1000;
    }
}

static void ArmTraceGuardsForRanges(bool dynamic_only) {
    TraceRange snapshot[_countof(g_trace_ranges)]{};
    uint32_t count = 0;
    AcquireSRWLockShared(&g_trace_range_lock);
    count = std::min<uint32_t>(g_trace_range_count, _countof(snapshot));
    for (uint32_t i = 0; i < count; ++i) {
        snapshot[i] = g_trace_ranges[i];
    }
    ReleaseSRWLockShared(&g_trace_range_lock);

    for (uint32_t i = 0; i < count; ++i) {
        if (dynamic_only && !snapshot[i].dynamic) {
            continue;
        }
        ArmTraceGuardForRange(snapshot[i].begin, snapshot[i].end);
    }
}

static void ArmTraceGuardsForAllRanges() {
    ArmTraceGuardsForRanges(false);
}

static void ArmTraceGuardsForDynamicRanges() {
    ArmTraceGuardsForRanges(true);
}

static DWORD WINAPI TraceGuardRefreshThread(void*) {
    g_inside_hook = true;
    while (InterlockedCompareExchange(&g_trace_guard_thread_stop, 0, 0) == 0) {
        if (InterlockedCompareExchange(&g_active_register_traces, 0, 0) == 0) {
            ArmTraceGuardsForDynamicRanges();
        }
        Sleep(kTraceGuardRefreshIntervalMs);
    }
    g_inside_hook = false;
    return 0;
}

static void StartTraceGuardRefresher() {
    if (!RegisterTraceCanInstrument() || g_trace_guard_thread) {
        return;
    }

    InterlockedExchange(&g_trace_guard_thread_stop, 0);
    const bool was_inside_hook = g_inside_hook;
    g_inside_hook = true;
    HANDLE thread = CreateThread(nullptr, 0, TraceGuardRefreshThread, nullptr, 0, nullptr);
    g_inside_hook = was_inside_hook;
    if (thread) {
        g_trace_guard_thread = thread;
    }
}

static void StopTraceGuardRefresher() {
    InterlockedExchange(&g_trace_guard_thread_stop, 1);
}

static void SuspendRegisterTraceForManagedRuntime() {
    if (!RegisterTraceEnabled()) {
        return;
    }
    InterlockedExchange(&g_register_trace_runtime_suspended, 1);
    StopTraceGuardRefresher();
}

static void MarkManagedRuntimeLoaded() {
    InterlockedExchange(&g_managed_runtime_loaded, 1);
    SuspendRegisterTraceForManagedRuntime();
}

static void ArmTraceGuardForLikelyReturn(CONTEXT* context) {
    if (!context) {
        return;
    }
    uintptr_t return_address = 0;
    if (ReadProcessBytes(static_cast<uintptr_t>(context->Rsp), &return_address, sizeof(return_address)) &&
        IsAddressInTraceRange(return_address)) {
        ArmTraceGuardForAddress(return_address);
    }
}

static bool AddTraceRangesForAddress(void* address);

static bool ShouldRegisterTraceAddress(void* address) {
    if (!RegisterTraceCanInstrument() || !address) {
        return false;
    }
    if (IsAddressInClrLikeModule(reinterpret_cast<uintptr_t>(address))) {
        return false;
    }
    if (IsAddressInTraceRange(reinterpret_cast<uintptr_t>(address))) {
        return true;
    }
    return AddTraceRangesForAddress(address) && IsAddressInTraceRange(reinterpret_cast<uintptr_t>(address));
}

static bool ShouldWrapThreadStartForRegisterTrace(void* address) {
    if (!RegisterTraceCanInstrument() || !address) {
        return false;
    }
    if (IsAddressInClrLikeModule(reinterpret_cast<uintptr_t>(address))) {
        return false;
    }
    if (CurrentStackHasClrLikeFrame()) {
        return false;
    }
    return true;
}

static LONG CALLBACK RegisterTraceVectoredHandler(PEXCEPTION_POINTERS info);
static void SendCallbackEvent(const wchar_t* api_name, void* callback, uint64_t event_value, int32_t status);
static LONG CALLBACK DispatchVehWrapper(uint32_t index, PEXCEPTION_POINTERS info);
static LONG CALLBACK VehWrapper0(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(0, info); }
static LONG CALLBACK VehWrapper1(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(1, info); }
static LONG CALLBACK VehWrapper2(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(2, info); }
static LONG CALLBACK VehWrapper3(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(3, info); }
static LONG CALLBACK VehWrapper4(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(4, info); }
static LONG CALLBACK VehWrapper5(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(5, info); }
static LONG CALLBACK VehWrapper6(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(6, info); }
static LONG CALLBACK VehWrapper7(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(7, info); }
static LONG CALLBACK VehWrapper8(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(8, info); }
static LONG CALLBACK VehWrapper9(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(9, info); }
static LONG CALLBACK VehWrapper10(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(10, info); }
static LONG CALLBACK VehWrapper11(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(11, info); }
static LONG CALLBACK VehWrapper12(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(12, info); }
static LONG CALLBACK VehWrapper13(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(13, info); }
static LONG CALLBACK VehWrapper14(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(14, info); }
static LONG CALLBACK VehWrapper15(PEXCEPTION_POINTERS info) { return DispatchVehWrapper(15, info); }

static PVECTORED_EXCEPTION_HANDLER VehWrapperForIndex(uint32_t index) {
    static PVECTORED_EXCEPTION_HANDLER wrappers[] = {
        VehWrapper0, VehWrapper1, VehWrapper2, VehWrapper3,
        VehWrapper4, VehWrapper5, VehWrapper6, VehWrapper7,
        VehWrapper8, VehWrapper9, VehWrapper10, VehWrapper11,
        VehWrapper12, VehWrapper13, VehWrapper14, VehWrapper15
    };
    return index < _countof(wrappers) ? wrappers[index] : nullptr;
}

static PVECTORED_EXCEPTION_HANDLER WrapVectoredExceptionHandler(PVECTORED_EXCEPTION_HANDLER handler) {
    if (!OriginTraceEnabled() || !handler || handler == RegisterTraceVectoredHandler) {
        return handler;
    }
    if (IsAddressInClrLikeModule(reinterpret_cast<uintptr_t>(handler)) || CurrentStackHasClrLikeFrame()) {
        return handler;
    }

    AcquireSRWLockExclusive(&g_veh_wrapper_lock);
    for (uint32_t i = 0; i < _countof(g_veh_wrappers); ++i) {
        if (g_veh_wrappers[i].original == handler && g_veh_wrappers[i].wrapper) {
            PVECTORED_EXCEPTION_HANDLER wrapper = g_veh_wrappers[i].wrapper;
            ReleaseSRWLockExclusive(&g_veh_wrapper_lock);
            return wrapper;
        }
    }
    for (uint32_t i = 0; i < _countof(g_veh_wrappers); ++i) {
        if (!g_veh_wrappers[i].original) {
            PVECTORED_EXCEPTION_HANDLER wrapper = VehWrapperForIndex(i);
            g_veh_wrappers[i].original = handler;
            g_veh_wrappers[i].wrapper = wrapper;
            ReleaseSRWLockExclusive(&g_veh_wrapper_lock);
            return wrapper ? wrapper : handler;
        }
    }
    ReleaseSRWLockExclusive(&g_veh_wrapper_lock);
    return handler;
}

static LONG CALLBACK DispatchVehWrapper(uint32_t index, PEXCEPTION_POINTERS info) {
    PVECTORED_EXCEPTION_HANDLER original = nullptr;
    AcquireSRWLockShared(&g_veh_wrapper_lock);
    if (index < _countof(g_veh_wrappers)) {
        original = g_veh_wrappers[index].original;
    }
    ReleaseSRWLockShared(&g_veh_wrapper_lock);

    if (!original) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    const LONG result = original(info);
    if (result == EXCEPTION_CONTINUE_EXECUTION &&
        info &&
        info->ContextRecord &&
        info->ContextRecord->Rip != 0) {
        const uintptr_t redirected_rip = static_cast<uintptr_t>(info->ContextRecord->Rip);
        RecordOriginTrace(
            kMonitorOriginProxyTransfer,
            kMonitorRegRip,
            redirected_rip,
            redirected_rip,
            redirected_rip,
            L"veh-rip-redirect",
            L"veh-context-rip");
        SuppressRegisterTraceForAddress(redirected_rip);
        const bool was_inside_hook = g_inside_hook;
        g_inside_hook = true;
        SendCallbackEvent(
            L"VehRipRedirect",
            reinterpret_cast<void*>(redirected_rip),
            reinterpret_cast<uint64_t>(original),
            0);
        g_inside_hook = was_inside_hook;
    }
    return result;
}

static void AddTraceSeedThread(DWORD tid);
static bool IsTraceSeedThread(DWORD tid);
static void RemoveTraceSeedThread(DWORD tid);

static void AddTraceSeedThread(DWORD tid) {
    if (!tid) {
        return;
    }
    AcquireSRWLockExclusive(&g_trace_seed_lock);
    for (DWORD& slot : g_trace_seed_tids) {
        if (slot == tid) {
            ReleaseSRWLockExclusive(&g_trace_seed_lock);
            return;
        }
        if (slot == 0) {
            slot = tid;
            ReleaseSRWLockExclusive(&g_trace_seed_lock);
            return;
        }
    }
    g_trace_seed_tids[0] = tid;
    ReleaseSRWLockExclusive(&g_trace_seed_lock);
}

static bool IsTraceSeedThread(DWORD tid) {
    bool found = false;
    AcquireSRWLockShared(&g_trace_seed_lock);
    for (DWORD slot : g_trace_seed_tids) {
        if (slot == tid) {
            found = true;
            break;
        }
    }
    ReleaseSRWLockShared(&g_trace_seed_lock);
    return found;
}

static void RemoveTraceSeedThread(DWORD tid) {
    AcquireSRWLockExclusive(&g_trace_seed_lock);
    for (DWORD& slot : g_trace_seed_tids) {
        if (slot == tid) {
            slot = 0;
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_trace_seed_lock);
}

static void SeedCurrentThreadRegisterTrace() {
    if (!RegisterTraceCanInstrument()) {
        return;
    }
    AddTraceSeedThread(GetCurrentThreadId());
    const unsigned __int64 flags = __readeflags();
    __writeeflags(flags | 0x100);
}

static ThreadStartTraceRecord* CreateThreadStartTraceRecord(LPTHREAD_START_ROUTINE start, void* parameter) {
    auto* record = reinterpret_cast<ThreadStartTraceRecord*>(
        HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(ThreadStartTraceRecord)));
    if (!record) {
        return nullptr;
    }
    record->start = start;
    record->parameter = parameter;
    return record;
}

static DWORD WINAPI RegTraceThreadStartThunk(void* raw_record) {
    auto* record = reinterpret_cast<ThreadStartTraceRecord*>(raw_record);
    if (!record || !record->start) {
        if (record) {
            HeapFree(GetProcessHeap(), 0, record);
        }
        return 0;
    }

    const LPTHREAD_START_ROUTINE start = record->start;
    void* parameter = record->parameter;
    HeapFree(GetProcessHeap(), 0, record);

    RecordOriginTrace(
        kMonitorOriginProxyTransfer,
        kMonitorRegRip,
        reinterpret_cast<uintptr_t>(start),
        reinterpret_cast<uintptr_t>(start),
        reinterpret_cast<uintptr_t>(start),
        L"thread-start",
        L"traced-thread-start");
    SeedCurrentThreadRegisterTrace();
    return start(parameter);
}

static void StartRegisterTrace(CONTEXT* context) {
    if (!context || !RegisterTraceCanInstrument()) {
        return;
    }
    if (!g_trace_state.active) {
        InterlockedIncrement(&g_active_register_traces);
    }
    g_trace_state.active = true;
    g_trace_state.has_previous = true;
    g_trace_state.instruction_budget = 0;
    g_trace_state.active_entry_address = static_cast<uintptr_t>(context->Rip);
    g_trace_state.previous = *context;
    SetTrapFlag(context);
}

static void StopRegisterTrace(CONTEXT* context) {
    if (g_trace_state.active) {
        InterlockedDecrement(&g_active_register_traces);
    }
    g_trace_state.active = false;
    g_trace_state.has_previous = false;
    g_trace_state.active_entry_address = 0;
    ClearTrapFlag(context);
}

static LONG CALLBACK RegisterTraceVectoredHandler(PEXCEPTION_POINTERS info) {
    if (!RegisterTraceEnabled() || !info || !info->ExceptionRecord || !info->ContextRecord) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    const DWORD code = info->ExceptionRecord->ExceptionCode;
    CONTEXT* context = info->ContextRecord;
    const uintptr_t rip = static_cast<uintptr_t>(context->Rip);

    if (RegisterTraceRuntimeSuspended()) {
        if (code == EXCEPTION_GUARD_PAGE) {
            const uintptr_t address = info->ExceptionRecord->ExceptionInformation[1]
                ? static_cast<uintptr_t>(info->ExceptionRecord->ExceptionInformation[1])
                : rip;
            if (IsAddressInTraceRange(rip) || IsAddressInTraceRange(address) ||
                IsRegisterTraceSuppressed(rip) || IsRegisterTraceSuppressed(address)) {
                ClearTrapFlag(context);
                return EXCEPTION_CONTINUE_EXECUTION;
            }
            return EXCEPTION_CONTINUE_SEARCH;
        }
        if (code == EXCEPTION_SINGLE_STEP) {
            const DWORD tid = GetCurrentThreadId();
            if (g_trace_state.active) {
                StopRegisterTrace(context);
                RemoveTraceSeedThread(tid);
                return EXCEPTION_CONTINUE_EXECUTION;
            }
            if (IsTraceSeedThread(tid) || IsAddressInTraceRange(rip) || IsRegisterTraceSuppressed(rip)) {
                RemoveTraceSeedThread(tid);
                ClearTrapFlag(context);
                return EXCEPTION_CONTINUE_EXECUTION;
            }
        }
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (code == EXCEPTION_GUARD_PAGE) {
        const uintptr_t address = info->ExceptionRecord->ExceptionInformation[1]
            ? static_cast<uintptr_t>(info->ExceptionRecord->ExceptionInformation[1])
            : rip;
        if (IsRegisterTraceSuppressed(rip) || IsRegisterTraceSuppressed(address)) {
            ClearTrapFlag(context);
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (IsAddressInTraceRange(rip)) {
            RecordOriginTrace(
                kMonitorOriginProxyTransfer,
                kMonitorRegRip,
                rip,
                address,
                rip,
                L"execution-guard",
                L"guarded-user-code");
            StartRegisterTrace(context);
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (IsAddressInTraceRange(address)) {
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (code != EXCEPTION_SINGLE_STEP) {
        if (g_trace_state.active) {
            if (IsAddressInTraceRange(rip)) {
                RecordOriginTrace(
                    kMonitorOriginProxyTransfer,
                    kMonitorRegRip,
                    rip,
                    static_cast<uintptr_t>(code),
                    rip,
                    L"exception-dispatch",
                    L"target-exception");
                ArmTraceGuardForAddress(rip);
            }
            StopRegisterTrace(context);
        }
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (code == EXCEPTION_SINGLE_STEP && !g_trace_state.active) {
        const DWORD tid = GetCurrentThreadId();
        if (IsAddressInClrLikeModule(rip) || CurrentStackHasClrLikeFrame()) {
            return EXCEPTION_CONTINUE_SEARCH;
        }
        if (IsRegisterTraceSuppressed(rip)) {
            ClearTrapFlag(context);
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (IsTraceSeedThread(tid)) {
            if (IsAddressInTraceRange(rip)) {
                RemoveTraceSeedThread(tid);
                StartRegisterTrace(context);
            } else {
                SetTrapFlag(context);
            }
            return EXCEPTION_CONTINUE_EXECUTION;
        }
        if (IsAddressInTraceRange(rip)) {
            StartRegisterTrace(context);
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }

    if (!g_trace_state.active) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (IsRegisterTraceSuppressed(rip)) {
        StopRegisterTrace(context);
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (g_trace_state.has_previous) {
        TraceRegisterDiff(g_trace_state.previous, *context);
    }

    ++g_trace_state.instruction_budget;
    const bool rip_in_trace_range = IsAddressInTraceRange(rip);
    if (rip_in_trace_range && g_trace_state.instruction_budget < kRegTraceMaxInstructions) {
        g_trace_state.previous = *context;
        g_trace_state.has_previous = true;
        SetTrapFlag(context);
    } else {
        const uintptr_t entry_address = g_trace_state.active_entry_address;
        if (rip_in_trace_range && g_trace_state.instruction_budget >= kRegTraceMaxInstructions) {
            SuppressRegisterTraceForAddress(rip);
        }
        StopRegisterTrace(context);
        if (entry_address && !rip_in_trace_range) {
            ArmTraceGuardForAddress(entry_address);
        }
        ArmTraceGuardForLikelyReturn(context);
    }

    return EXCEPTION_CONTINUE_EXECUTION;
}

static void RememberMainModuleDirectory(HMODULE main_module) {
    wchar_t path[MAX_PATH * 4]{};
    if (!GetLowerModulePath(main_module, path, _countof(path))) {
        return;
    }

    wchar_t* last_sep = nullptr;
    for (wchar_t* cursor = path; *cursor; ++cursor) {
        if (*cursor == L'\\' || *cursor == L'/') {
            last_sep = cursor;
        }
    }
    if (!last_sep) {
        return;
    }
    *(last_sep + 1) = L'\0';
    CopyWideString(g_main_module_dir, _countof(g_main_module_dir), path);
}

static bool IsTraceableUserModule(HMODULE module, bool force_main, wchar_t* module_name, size_t module_name_cch) {
    if (!module || module == g_module) {
        return false;
    }

    wchar_t lower_path[MAX_PATH * 4]{};
    if (!GetLowerModulePath(module, lower_path, _countof(lower_path))) {
        return false;
    }

    const wchar_t* basename = BasenamePtr(lower_path);
    if (module_name && module_name_cch) {
        CopyWideString(module_name, module_name_cch, basename);
    }

    if (force_main) {
        return true;
    }
    if (IsTraceExcludedModuleName(basename)) {
        return false;
    }
    if (IsSystemLikeModulePath(lower_path)) {
        return false;
    }
    if (g_main_module_dir[0] && StartsWithString(lower_path, g_main_module_dir)) {
        return true;
    }

    return true;
}

static bool AddTraceRangeIfNew(uintptr_t begin, uintptr_t end, uintptr_t module_base, const wchar_t* module_name, bool dynamic = false) {
    if (begin == 0 || end <= begin) {
        return false;
    }

    bool added = false;
    AcquireSRWLockExclusive(&g_trace_range_lock);
    for (uint32_t i = 0; i < g_trace_range_count; ++i) {
        if (g_trace_ranges[i].begin == begin && g_trace_ranges[i].end == end) {
            ReleaseSRWLockExclusive(&g_trace_range_lock);
            return false;
        }
    }
    if (g_trace_range_count < _countof(g_trace_ranges)) {
        TraceRange& range = g_trace_ranges[g_trace_range_count++];
        range.begin = begin;
        range.end = end;
        range.module_base = module_base;
        range.dynamic = dynamic;
        CopyWideString(range.module_name, _countof(range.module_name), module_name);
        added = true;
    }
    ReleaseSRWLockExclusive(&g_trace_range_lock);

    if (added) {
        ArmTraceGuardForRange(begin, end);
    }
    return added;
}

static bool AddTraceRangesForExecutableRegion(void* address, SIZE_T requested_size, const wchar_t* fallback_name) {
    if (!RegisterTraceCanInstrument() || !address) {
        return false;
    }
    if (CurrentStackHasClrLikeFrame()) {
        return false;
    }

    MEMORY_BASIC_INFORMATION first_mbi{};
    if (!VirtualQuery(address, &first_mbi, sizeof(first_mbi)) ||
        first_mbi.State != MEM_COMMIT ||
        !IsExecutableMemoryProtect(first_mbi.Protect)) {
        return false;
    }

    const uintptr_t start = reinterpret_cast<uintptr_t>(first_mbi.BaseAddress);
    uintptr_t end = start + static_cast<uintptr_t>(first_mbi.RegionSize);
    if (requested_size != 0) {
        const uintptr_t requested_end = reinterpret_cast<uintptr_t>(address) + static_cast<uintptr_t>(requested_size);
        if (requested_end > end) {
            end = requested_end;
        }
    }

    bool added_any = false;
    uintptr_t cursor = start;
    while (cursor < end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) || mbi.RegionSize == 0) {
            break;
        }

        const uintptr_t region_begin = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t region_end = region_begin + static_cast<uintptr_t>(mbi.RegionSize);
        if (mbi.State == MEM_COMMIT &&
            IsExecutableMemoryProtect(mbi.Protect) &&
            (mbi.Type == MEM_MAPPED || mbi.Type == MEM_PRIVATE)) {
            const wchar_t* label = fallback_name && fallback_name[0]
                ? fallback_name
                : (mbi.Type == MEM_MAPPED ? L"mapped-exec" : L"private-exec");
            const uintptr_t allocation_base = reinterpret_cast<uintptr_t>(mbi.AllocationBase);
            added_any = AddTraceRangeIfNew(region_begin, region_end, allocation_base, label, true) || added_any;
        }

        if (region_end <= cursor) {
            break;
        }
        cursor = region_end;
    }

    return added_any || IsAddressInTraceRange(reinterpret_cast<uintptr_t>(address));
}

static bool AddTraceRangesForModule(HMODULE module, bool force_main) {
    if (!RegisterTraceCanInstrument() || !module) {
        return false;
    }

    wchar_t module_name[kMonitorEventNameChars]{};
    if (!IsTraceableUserModule(module, force_main, module_name, _countof(module_name))) {
        return false;
    }

    const auto base = reinterpret_cast<uintptr_t>(module);
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
        return false;
    }

    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) {
        return false;
    }
    if (!force_main && nt->OptionalHeader.SizeOfImage > kLargeTraceImageThreshold) {
        return false;
    }

    bool added_any = false;
    const IMAGE_SECTION_HEADER* section = IMAGE_FIRST_SECTION(nt);
    const uint16_t section_count = nt->FileHeader.NumberOfSections;
    for (uint16_t i = 0; i < section_count; ++i) {
        if ((section[i].Characteristics & IMAGE_SCN_MEM_EXECUTE) == 0) {
            continue;
        }
        const uint32_t raw_size = std::max<uint32_t>(section[i].Misc.VirtualSize, section[i].SizeOfRawData);
        if (raw_size == 0) {
            continue;
        }
        const uintptr_t begin = base + section[i].VirtualAddress;
        const uintptr_t end = begin + raw_size;
        added_any = AddTraceRangeIfNew(begin, end, base, module_name, false) || added_any;
    }
    return added_any || IsAddressInTraceRange(base);
}

static bool IsLargeTraceModule(HMODULE module) {
    if (!module) {
        return false;
    }

    const auto base = reinterpret_cast<uintptr_t>(module);
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
        return false;
    }

    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) {
        return false;
    }

    return nt->OptionalHeader.SizeOfImage > kLargeTraceImageThreshold;
}

static bool AddTraceRangeNearAddress(HMODULE module, uintptr_t address, const wchar_t* module_name) {
    if (!module || !address) {
        return false;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) ||
        mbi.State != MEM_COMMIT ||
        !IsExecutableMemoryProtect(mbi.Protect)) {
        return false;
    }

    constexpr uintptr_t kPageSize = 0x1000;
    constexpr uintptr_t kTraceWindowBytes = 0x4000;
    const uintptr_t page = address & ~(kPageSize - 1);
    uintptr_t begin = page > (kTraceWindowBytes / 2) ? page - (kTraceWindowBytes / 2) : page;
    uintptr_t end = page + (kTraceWindowBytes / 2) + kPageSize;

    const uintptr_t region_begin = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
    const uintptr_t region_end = region_begin + static_cast<uintptr_t>(mbi.RegionSize);
    begin = std::max(begin, region_begin);
    end = std::min(end, region_end);
    if (end <= begin) {
        return false;
    }

    return AddTraceRangeIfNew(
        begin,
        end,
        reinterpret_cast<uintptr_t>(module),
        module_name && module_name[0] ? module_name : L"large-module-window",
        false) || IsAddressInTraceRange(address);
}

static bool AddTraceRangesForAddress(void* address) {
    if (!RegisterTraceCanInstrument() || !address) {
        return false;
    }

    HMODULE module = nullptr;
    if (!GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(address),
        &module) || !module) {
        return AddTraceRangesForExecutableRegion(address, 0, L"dynamic-exec");
    }

    const bool force_main = module == reinterpret_cast<HMODULE>(g_main_module_base);
    if (!force_main && IsLargeTraceModule(module)) {
        wchar_t module_name[kMonitorEventNameChars]{};
        if (!IsTraceableUserModule(module, false, module_name, _countof(module_name))) {
            return false;
        }
        return AddTraceRangeNearAddress(module, reinterpret_cast<uintptr_t>(address), module_name);
    }

    return AddTraceRangesForModule(module, force_main);
}

static bool InitializeTraceRanges() {
    HMODULE main_module = GetModuleHandleW(nullptr);
    if (!main_module) {
        return false;
    }

    g_main_module_base = reinterpret_cast<uintptr_t>(main_module);
    RememberMainModuleDirectory(main_module);
    const bool added_main = AddTraceRangesForModule(main_module, true);
    return added_main && g_trace_range_count > 0;
}

static bool InitializeRegisterTrace() {
    if (!RegisterTraceEnabled() && !DispatchTraceEnabled()) {
        return true;
    }

    ResolveLoaderApis();
    if (!RegisterTraceEnabled()) {
        return true;
    }

    if (!InitializeTraceRanges()) {
        return false;
    }

    g_trace_handler = AddVectoredExceptionHandler(1, RegisterTraceVectoredHandler);
    if (!g_trace_handler) {
        return false;
    }

    ArmTraceGuardsForAllRanges();
    StartTraceGuardRefresher();
    return true;
}

static USHORT CaptureFrames(void** frames) {
    const uint32_t requested_frames = g_config.max_frames == 0
        ? kMonitorMaxFrames
        : std::min(g_config.max_frames, kMonitorMaxFrames);
    __try {
        return RtlCaptureStackBackTrace(0, requested_frames, frames, nullptr);
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        if (frames && requested_frames > 0) {
            memset(frames, 0, sizeof(void*) * requested_frames);
        }
        return 0;
    }
}

static void* GetCurrentThreadShadowStackPointer() {
    DWORD64 enabled_features = 0;
    __try {
        enabled_features = GetEnabledXStateFeatures();
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        return nullptr;
    }
    if ((enabled_features & XSTATE_MASK_CET_U) == 0) {
        return nullptr;
    }

#if defined(_M_X64)
    __try {
        const unsigned __int64 live_ssp = _rdsspq();
        if (live_ssp != 0) {
            return reinterpret_cast<void*>(live_ssp);
        }
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
    }
#endif

    DWORD context_length = 0;
    (void)InitializeContext2(nullptr, CONTEXT_XSTATE, nullptr, &context_length, XSTATE_MASK_CET_U);
    if (context_length == 0 || context_length > (64u * 1024u)) {
        return nullptr;
    }

    auto* buffer = static_cast<uint8_t*>(HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, context_length));
    if (!buffer) {
        return nullptr;
    }

    PCONTEXT context = nullptr;
    void* ssp = nullptr;
    DWORD feature_length = 0;
    DWORD64 feature_mask = 0;
    __try {
        if (InitializeContext2(buffer, CONTEXT_XSTATE, &context, &context_length, XSTATE_MASK_CET_U) &&
            GetThreadContext(GetCurrentThread(), context) &&
            GetXStateFeaturesMask(context, &feature_mask) &&
            (feature_mask & XSTATE_MASK_CET_U) != 0) {
            auto* cet = static_cast<PXSAVE_CET_U_FORMAT>(
                LocateXStateFeature(context, XSTATE_CET_U, &feature_length));
            if (cet && feature_length >= sizeof(*cet)) {
                ssp = reinterpret_cast<void*>(cet->Ia32Pl3SspMsr);
            }
        }
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        ssp = nullptr;
    }

    HeapFree(GetProcessHeap(), 0, buffer);
    return ssp;
}

static USHORT CaptureShadowStackFrames(void** frames, uint32_t frames_to_skip, uint32_t frames_to_capture) {
    if (!ShadowStackEnabled() || !frames || frames_to_capture == 0) {
        return 0;
    }

    void** ssp = static_cast<void**>(GetCurrentThreadShadowStackPointer());
    if (!ssp) {
        return 0;
    }

    USHORT captured = 0;
    __try {
        const uint32_t max_scan = frames_to_skip + frames_to_capture;
        for (uint32_t i = 0; i < max_scan; ++i) {
            if ((reinterpret_cast<uintptr_t>(ssp) & 0xFFFu) == 0) {
                break;
            }
            void* frame = *ssp++;
            if (i < frames_to_skip || !frame) {
                continue;
            }
            frames[captured++] = frame;
            if (captured >= frames_to_capture) {
                break;
            }
        }
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        captured = 0;
    }
    return captured;
}

static void CaptureFrameContexts(
    void** frames,
    USHORT frame_count,
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    uint8_t frame_context_size[kMonitorMaxFrames]) {
    const HANDLE process = GetCurrentProcess();
    for (USHORT i = 0; i < frame_count && i < kMonitorMaxFrames; ++i) {
        const auto address = reinterpret_cast<uintptr_t>(frames[i]);
        if (address < kMonitorFrameContextBytes) {
            continue;
        }
        SIZE_T bytes_read = 0;
        __try {
            if (ReadProcessMemory(
                process,
                reinterpret_cast<void*>(address - kMonitorFrameContextBytes),
                frame_context[i],
                kMonitorFrameContextBytes,
                &bytes_read) && bytes_read > 0) {
                frame_context_size[i] = static_cast<uint8_t>(std::min<SIZE_T>(bytes_read, kMonitorFrameContextBytes));
            }
        }
        __except (EXCEPTION_EXECUTE_HANDLER) {
            frame_context_size[i] = 0;
        }
    }
}

struct MonitorPeSectionInfo {
    uint32_t virtual_address = 0;
    uint32_t virtual_size = 0;
    uint32_t raw_address = 0;
    uint32_t raw_size = 0;
};

struct MonitorPeLayoutInfo {
    uint32_t exception_rva = 0;
    uint32_t exception_size = 0;
    uint16_t section_count = 0;
    MonitorPeSectionInfo sections[32]{};
};

static bool ReadWholeFileLimited(const wchar_t* path, uint8_t** bytes, size_t* size) {
    if (!path || !bytes || !size) {
        return false;
    }
    *bytes = nullptr;
    *size = 0;

    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        return false;
    }

    LARGE_INTEGER file_size{};
    if (!GetFileSizeEx(file, &file_size) || file_size.QuadPart <= 0 ||
        file_size.QuadPart > 64ll * 1024ll * 1024ll) {
        CloseHandle(file);
        return false;
    }

    auto* buffer = static_cast<uint8_t*>(HeapAlloc(GetProcessHeap(), 0, static_cast<SIZE_T>(file_size.QuadPart)));
    if (!buffer) {
        CloseHandle(file);
        return false;
    }

    DWORD read = 0;
    const BOOL ok = ReadFile(file, buffer, static_cast<DWORD>(file_size.QuadPart), &read, nullptr);
    CloseHandle(file);
    if (!ok || read != static_cast<DWORD>(file_size.QuadPart)) {
        HeapFree(GetProcessHeap(), 0, buffer);
        return false;
    }

    *bytes = buffer;
    *size = static_cast<size_t>(read);
    return true;
}

static bool ParseDiskPeLayout(const uint8_t* bytes, size_t size, MonitorPeLayoutInfo& layout) {
    if (!bytes || size < sizeof(IMAGE_DOS_HEADER)) {
        return false;
    }
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(bytes);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE ||
        dos->e_lfanew <= 0 ||
        static_cast<size_t>(dos->e_lfanew) + sizeof(IMAGE_NT_HEADERS64) > size) {
        return false;
    }

    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(bytes + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE ||
        nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        return false;
    }

    const auto& exception_dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];
    layout.exception_rva = exception_dir.VirtualAddress;
    layout.exception_size = exception_dir.Size;

    const IMAGE_SECTION_HEADER* sections = IMAGE_FIRST_SECTION(nt);
    const uint16_t count = std::min<uint16_t>(nt->FileHeader.NumberOfSections, _countof(layout.sections));
    if (reinterpret_cast<const uint8_t*>(sections + count) > bytes + size) {
        return false;
    }
    layout.section_count = count;
    for (uint16_t i = 0; i < count; ++i) {
        layout.sections[i].virtual_address = sections[i].VirtualAddress;
        layout.sections[i].virtual_size = sections[i].Misc.VirtualSize;
        layout.sections[i].raw_address = sections[i].PointerToRawData;
        layout.sections[i].raw_size = sections[i].SizeOfRawData;
    }
    return true;
}

static bool RvaToDiskOffset(const MonitorPeLayoutInfo& layout, uint32_t rva, size_t length,
    size_t file_size, size_t& offset) {
    for (uint16_t i = 0; i < layout.section_count; ++i) {
        const auto& section = layout.sections[i];
        const uint32_t span = std::max(section.virtual_size, section.raw_size);
        if (span == 0 || rva < section.virtual_address) {
            continue;
        }
        const uint64_t delta = static_cast<uint64_t>(rva - section.virtual_address);
        if (delta + length > span) {
            continue;
        }
        const uint64_t raw = static_cast<uint64_t>(section.raw_address) + delta;
        if (raw + length <= file_size) {
            offset = static_cast<size_t>(raw);
            return true;
        }
    }
    if (rva + length <= file_size) {
        offset = rva;
        return true;
    }
    return false;
}

static bool ReadLiveExceptionDirectory(uintptr_t module_base, uint32_t& exception_rva, uint32_t& exception_size) {
    __try {
        const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(module_base);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) {
            return false;
        }
        const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(module_base + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
            return false;
        }
        const auto& exception_dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];
        exception_rva = exception_dir.VirtualAddress;
        exception_size = exception_dir.Size;
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool ReadLiveRuntimeFunction(uintptr_t module_base, uint32_t exception_rva,
    uint32_t index, RUNTIME_FUNCTION& entry) {
    __try {
        const auto* entries = reinterpret_cast<const RUNTIME_FUNCTION*>(module_base + exception_rva);
        entry = entries[index];
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool LiveBytesDiffer(uintptr_t module_base, uint32_t rva,
    const uint8_t* disk_bytes, size_t disk_size, const MonitorPeLayoutInfo& layout,
    size_t length, uint64_t& old_value, uint64_t& new_value) {
    size_t offset = 0;
    if (!RvaToDiskOffset(layout, rva, length, disk_size, offset)) {
        return false;
    }

    uint8_t live[32]{};
    if (length > sizeof(live)) {
        length = sizeof(live);
    }

    __try {
        memcpy(live, reinterpret_cast<const void*>(module_base + rva), length);
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }

    if (memcmp(live, disk_bytes + offset, length) == 0) {
        return false;
    }
    old_value = 0;
    new_value = 0;
    memcpy(&old_value, disk_bytes + offset, std::min<size_t>(sizeof(old_value), length));
    memcpy(&new_value, live, std::min<size_t>(sizeof(new_value), length));
    return true;
}

static void SendEvent(
    uint32_t event_type,
    const wchar_t* event_name,
    const wchar_t* target_name,
    int32_t status,
    uint64_t event_value,
    uint32_t event_flags,
    uint64_t callback_address,
    void** frames,
    USHORT frame_count,
    const uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    const uint8_t frame_context_size[kMonitorMaxFrames],
    const MonitorEvent* extra);

static void SendByoudTraceEvent(const wchar_t* rule_name, HMODULE module, uint64_t rva, uint64_t size,
    void** frames, USHORT frame_count,
    const uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    const uint8_t frame_context_size[kMonitorMaxFrames]) {
    if (!rule_name || !module) {
        return;
    }

    wchar_t path[MAX_PATH * 4]{};
    wchar_t module_name[kMonitorTargetNameChars]{};
    if (GetModuleFileNameW(module, path, _countof(path))) {
        path[_countof(path) - 1] = L'\0';
        CopyWideString(module_name, _countof(module_name), BasenamePtr(path));
        LowerInPlace(module_name);
    }

    const uint64_t base = reinterpret_cast<uint64_t>(module);
    SendEvent(
        kMonitorEventUnwindTable,
        rule_name,
        module_name,
        0,
        base + rva,
        static_cast<uint32_t>(std::min<uint64_t>(size, 0xffffffffu)),
        base,
        frames,
        frame_count,
        frame_context,
        frame_context_size,
        nullptr);
}

static uint32_t EmitByoudDiffsForModule(HMODULE module, void** frames, USHORT frame_count,
    const uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    const uint8_t frame_context_size[kMonitorMaxFrames],
    uint32_t remaining_records) {
    if (!module || module == g_module || remaining_records == 0) {
        return 0;
    }

    const uintptr_t module_base = reinterpret_cast<uintptr_t>(module);
    wchar_t path[MAX_PATH * 4]{};
    if (!GetModuleFileNameW(module, path, _countof(path))) {
        return 0;
    }
    path[_countof(path) - 1] = L'\0';

    uint8_t* disk_bytes = nullptr;
    size_t disk_size = 0;
    if (!ReadWholeFileLimited(path, &disk_bytes, &disk_size)) {
        return 0;
    }

    MonitorPeLayoutInfo layout{};
    uint32_t live_exception_rva = 0;
    uint32_t live_exception_size = 0;
    uint32_t emitted = 0;
    if (ParseDiskPeLayout(disk_bytes, disk_size, layout) &&
        layout.exception_rva != 0 &&
        layout.exception_size >= sizeof(RUNTIME_FUNCTION) &&
        ReadLiveExceptionDirectory(module_base, live_exception_rva, live_exception_size) &&
        live_exception_rva != 0 &&
        live_exception_size >= sizeof(RUNTIME_FUNCTION)) {

        bool structural_recorded = false;
        if ((live_exception_rva != layout.exception_rva || live_exception_size > layout.exception_size) &&
            emitted < remaining_records) {
            SendByoudTraceEvent(L"byoud_runtime_function_entry_injected", module,
                live_exception_rva ? live_exception_rva : layout.exception_rva,
                live_exception_size, frames, frame_count, frame_context, frame_context_size);
            ++emitted;
            structural_recorded = true;
        }

        size_t disk_entries_offset = 0;
        const uint32_t disk_count = layout.exception_size / sizeof(RUNTIME_FUNCTION);
        const uint32_t live_count = live_exception_size / sizeof(RUNTIME_FUNCTION);
        const uint32_t comparable = std::min<uint32_t>(std::min(disk_count, live_count), 8192);
        if (RvaToDiskOffset(layout, layout.exception_rva, comparable * sizeof(RUNTIME_FUNCTION),
            disk_size, disk_entries_offset)) {
            const auto* disk_entries = reinterpret_cast<const RUNTIME_FUNCTION*>(disk_bytes + disk_entries_offset);
            bool range_recorded = false;
            bool unwind_recorded = false;
            bool info_recorded = false;
            for (uint32_t i = 0; i < comparable && emitted < remaining_records; ++i) {
                RUNTIME_FUNCTION live_entry{};
                if (!ReadLiveRuntimeFunction(module_base, live_exception_rva, i, live_entry)) {
                    break;
                }
                const auto& disk_entry = disk_entries[i];
                const uint64_t entry_rva = static_cast<uint64_t>(live_exception_rva) + i * sizeof(RUNTIME_FUNCTION);
                if (!range_recorded &&
                    (disk_entry.BeginAddress != live_entry.BeginAddress ||
                        disk_entry.EndAddress != live_entry.EndAddress)) {
                    SendByoudTraceEvent(L"byoud_runtime_function_range_hijack", module,
                        entry_rva, sizeof(RUNTIME_FUNCTION), frames, frame_count, frame_context, frame_context_size);
                    ++emitted;
                    range_recorded = true;
                    structural_recorded = true;
                }
                if (emitted >= remaining_records) {
                    break;
                }
                if (!unwind_recorded && disk_entry.UnwindData != live_entry.UnwindData) {
                    SendByoudTraceEvent(L"byoud_runtime_function_unwind_hijack", module,
                        entry_rva, sizeof(RUNTIME_FUNCTION), frames, frame_count, frame_context, frame_context_size);
                    ++emitted;
                    unwind_recorded = true;
                    structural_recorded = true;
                }
                if (emitted >= remaining_records) {
                    break;
                }
                if (!info_recorded && structural_recorded && disk_entry.UnwindData != 0) {
                    uint64_t old_value = 0;
                    uint64_t new_value = 0;
                    if (LiveBytesDiffer(module_base, disk_entry.UnwindData,
                        disk_bytes, disk_size, layout, 32, old_value, new_value)) {
                        SendByoudTraceEvent(L"byoud_unwind_info_tampered", module,
                            disk_entry.UnwindData, 32, frames, frame_count, frame_context, frame_context_size);
                        ++emitted;
                        info_recorded = true;
                    }
                }
                if (range_recorded && unwind_recorded && info_recorded) {
                    break;
                }
            }
        }
    }

    HeapFree(GetProcessHeap(), 0, disk_bytes);
    return emitted;
}

static void EmitByoudDiffsForCapturedModules(void** frames, USHORT frame_count,
    const uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    const uint8_t frame_context_size[kMonitorMaxFrames]) {
    if (!ByoudTraceEnabled()) {
        return;
    }

    HMODULE modules[16]{};
    uint32_t module_count = 0;
    uint32_t emitted = 0;
    for (USHORT i = 0; i < frame_count && i < kMonitorMaxFrames && emitted < 6; ++i) {
        if (!frames[i]) {
            continue;
        }
        HMODULE module = nullptr;
        if (!GetModuleHandleExW(
            GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            reinterpret_cast<LPCWSTR>(frames[i]),
            &module) || !module) {
            continue;
        }
        bool seen = false;
        for (uint32_t j = 0; j < module_count; ++j) {
            if (modules[j] == module) {
                seen = true;
                break;
            }
        }
        if (seen || module == g_module) {
            continue;
        }
        if (module_count < _countof(modules)) {
            modules[module_count++] = module;
        }
        emitted += EmitByoudDiffsForModule(module, frames, frame_count, frame_context, frame_context_size, 6 - emitted);
    }
}

static uint64_t CalculateLocalAllocationSize(uintptr_t allocation_base) {
    if (!allocation_base) {
        return 0;
    }

    uintptr_t cursor = allocation_base;
    uintptr_t end = allocation_base;
    constexpr uintptr_t kMaxAllocationWalk = 1024ull * 1024ull * 1024ull;

    while (cursor >= allocation_base && cursor - allocation_base < kMaxAllocationWalk) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
            break;
        }
        if (reinterpret_cast<uintptr_t>(mbi.AllocationBase) != allocation_base) {
            break;
        }

        const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t region_end = region_base + static_cast<uintptr_t>(mbi.RegionSize);
        end = std::max(end, region_end);
        if (region_end <= cursor) {
            break;
        }
        cursor = region_end;
    }

    return end > allocation_base ? static_cast<uint64_t>(end - allocation_base) : 0;
}

static uint64_t GetModuleSizeOfImage(HMODULE module) {
    if (!module) {
        return 0;
    }

    const auto base = reinterpret_cast<uintptr_t>(module);
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
        return 0;
    }

    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) {
        return 0;
    }
    return nt->OptionalHeader.SizeOfImage;
}

static void FillFrameMetadata(MonitorEvent& event, uint32_t index, uint64_t address) {
    if (index >= kMonitorMaxFrames || address == 0) {
        return;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) == sizeof(mbi)) {
        event.frame_region_base[index] = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        event.frame_region_size[index] = static_cast<uint64_t>(mbi.RegionSize);
        event.frame_allocation_base[index] = reinterpret_cast<uint64_t>(mbi.AllocationBase);
        event.frame_allocation_size[index] = CalculateLocalAllocationSize(
            reinterpret_cast<uintptr_t>(mbi.AllocationBase));
        event.frame_state[index] = mbi.State;
        event.frame_protect[index] = mbi.Protect;
        event.frame_allocation_protect[index] = mbi.AllocationProtect;
        event.frame_type[index] = mbi.Type;
    }

    HMODULE module = nullptr;
    if (GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(address),
        &module) && module) {
        event.frame_module_base[index] = reinterpret_cast<uint64_t>(module);
        wchar_t path[MAX_PATH * 4]{};
        if (GetModuleFileNameW(module, path, _countof(path))) {
            path[_countof(path) - 1] = L'\0';
            CopyWideString(event.frame_module_name[index], _countof(event.frame_module_name[index]), BasenamePtr(path));
            LowerInPlace(event.frame_module_name[index]);
        }
    }
}

static void FillEventValueModuleMetadata(MonitorEvent& event) {
    if (event.event_type != kMonitorEventDllLoad || event.event_value == 0) {
        return;
    }

    const auto module = reinterpret_cast<HMODULE>(event.event_value);
    event.event_value_module_size = GetModuleSizeOfImage(module);
    wchar_t path[MAX_PATH * 4]{};
    if (GetModuleFileNameW(module, path, _countof(path))) {
        path[_countof(path) - 1] = L'\0';
        CopyWideString(event.event_value_module_path, _countof(event.event_value_module_path), path);
    }
}

static void SendEvent(
    uint32_t event_type,
    const wchar_t* event_name,
    const wchar_t* target_name,
    int32_t status,
    uint64_t event_value,
    uint32_t event_flags,
    uint64_t callback_address,
    void** frames,
    USHORT frame_count,
    const uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes],
    const uint8_t frame_context_size[kMonitorMaxFrames],
    const MonitorEvent* extra = nullptr) {
    if (g_pipe == INVALID_HANDLE_VALUE || InterlockedCompareExchange(&g_emit_enabled, 0, 0) == 0) {
        return;
    }

    MonitorEvent event{};
    event.magic = kCallstackProtocolMagic;
    event.version = kCallstackProtocolVersion;
    event.size = sizeof(event);
    event.pid = GetCurrentProcessId();
    event.tid = GetCurrentThreadId();
    event.status = status;
    event.frame_count = std::min<uint32_t>(frame_count, kMonitorMaxFrames);
    event.event_type = event_type;
    event.event_flags = event_flags;
    event.event_value = event_value;
    event.callback_address = callback_address;
    if (event_name) {
        CopyWideString(event.event_name, _countof(event.event_name), event_name);
    }
    if (target_name) {
        CopyWideString(event.target_name, _countof(event.target_name), target_name);
    }

    CONTEXT register_context{};
    RtlCaptureContext(&register_context);
    FillRegisterSnapshot(register_context, event.registers);
    CopyOriginTraceRecords(event);
    AppendShadowStackRecords(event);
    if (extra) {
        event.ldr_table_entry = extra->ldr_table_entry;
        event.ldr_dll_base = extra->ldr_dll_base;
        event.ldr_size_of_image = extra->ldr_size_of_image;
        event.ldr_entrypoint = extra->ldr_entrypoint;
        event.ldr_expected_entrypoint = extra->ldr_expected_entrypoint;
        event.ldr_original_base = extra->ldr_original_base;
        event.ldr_entrypoint_region_base = extra->ldr_entrypoint_region_base;
        event.ldr_entrypoint_region_size = extra->ldr_entrypoint_region_size;
        event.ldr_entrypoint_protect = extra->ldr_entrypoint_protect;
        event.ldr_entrypoint_type = extra->ldr_entrypoint_type;
        event.ldr_original_base_region_base = extra->ldr_original_base_region_base;
        event.ldr_original_base_region_size = extra->ldr_original_base_region_size;
        event.ldr_original_base_protect = extra->ldr_original_base_protect;
        event.ldr_original_base_type = extra->ldr_original_base_type;
    }
    FillEventValueModuleMetadata(event);

    for (uint32_t i = 0; i < event.frame_count; ++i) {
        event.frames[i] = reinterpret_cast<uint64_t>(frames[i]);
        FillFrameMetadata(event, i, event.frames[i]);
        if (frame_context && frame_context_size) {
            event.frame_context_size[i] = frame_context_size[i];
            memcpy(event.frame_context[i], frame_context[i], kMonitorFrameContextBytes);
        }
    }

    DWORD written = 0;
    WriteFile(g_pipe, &event, sizeof(event), &written, nullptr);
}

static bool ShouldSendTimedEvent(uint64_t timeout_ms, bool infinite) {
    if (infinite) {
        return true;
    }
    return timeout_ms >= g_config.long_sleep_ms;
}

static void SendTimedEvent(const wchar_t* api_name, uint64_t timeout_ms, bool infinite) {
    if (!ShouldSendTimedEvent(timeout_ms, infinite)) {
        return;
    }

    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        kMonitorEventSleepWait,
        api_name,
        api_name,
        0,
        timeout_ms,
        infinite ? kMonitorEventFlagTimeoutInfinite : 0,
        0,
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static void SendCallbackEvent(const wchar_t* api_name, void* callback, uint64_t event_value, int32_t status) {
    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        kMonitorEventCallback,
        api_name,
        api_name,
        status,
        event_value,
        0,
        reinterpret_cast<uint64_t>(callback),
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static void SendAddressEvent(uint32_t event_type, const wchar_t* api_name, uint64_t address,
    uint32_t event_flags, uint64_t secondary_address, int32_t status) {
    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        event_type,
        api_name,
        api_name,
        status,
        address,
        event_flags,
        secondary_address,
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static void SendNamedEvent(uint32_t event_type, const wchar_t* api_name, const wchar_t* target_name,
    uint64_t event_value, uint64_t secondary_address, int32_t status) {
    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        event_type,
        api_name,
        target_name,
        status,
        event_value,
        0,
        secondary_address,
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static uint16_t NetworkPortToHost(uint16_t value) {
    return static_cast<uint16_t>((value >> 8) | (value << 8));
}

static uint32_t HashWideString32(const wchar_t* text) {
    uint32_t hash = 2166136261u;
    if (!text) {
        return hash;
    }
    while (*text) {
        hash ^= static_cast<uint32_t>(ToLowerChar(*text++));
        hash *= 16777619u;
    }
    return hash;
}

static void CopyAnsiToWide(wchar_t* destination, size_t destination_cch, const char* source) {
    if (!destination || destination_cch == 0) {
        return;
    }
    destination[0] = L'\0';
    if (!source) {
        return;
    }

    const int converted = MultiByteToWideChar(
        CP_ACP,
        0,
        source,
        -1,
        destination,
        static_cast<int>(destination_cch));
    if (converted <= 0) {
        destination[0] = L'\0';
    } else {
        destination[destination_cch - 1] = L'\0';
    }
}

static void BuildHostPortTarget(wchar_t* output, size_t output_cch, const wchar_t* host, uint16_t port) {
    if (!output || output_cch == 0) {
        return;
    }
    output[0] = L'\0';
    if (host && host[0]) {
        CopyWideString(output, output_cch, host);
    } else {
        CopyWideString(output, output_cch, L"network-endpoint");
    }
    if (port != 0) {
        wchar_t suffix[32]{};
        swprintf_s(suffix, L":%u", static_cast<unsigned>(port));
        SafeAppendWideString(output, output_cch, suffix);
    }
}

static bool FormatSockaddrTarget(const sockaddr* address, int address_length, wchar_t* output, size_t output_cch) {
    if (!output || output_cch == 0) {
        return false;
    }
    output[0] = L'\0';
    if (!address || address_length < static_cast<int>(sizeof(sockaddr))) {
        return false;
    }

    __try {
        if (address->sa_family == AF_INET && address_length >= static_cast<int>(sizeof(sockaddr_in))) {
            const auto* ipv4 = reinterpret_cast<const sockaddr_in*>(address);
            const auto* bytes = reinterpret_cast<const uint8_t*>(&ipv4->sin_addr.S_un.S_addr);
            swprintf_s(
                output,
                output_cch,
                L"%u.%u.%u.%u:%u",
                static_cast<unsigned>(bytes[0]),
                static_cast<unsigned>(bytes[1]),
                static_cast<unsigned>(bytes[2]),
                static_cast<unsigned>(bytes[3]),
                static_cast<unsigned>(NetworkPortToHost(ipv4->sin_port)));
            return true;
        }
        if (address->sa_family == AF_INET6 && address_length >= static_cast<int>(sizeof(sockaddr_in6))) {
            const auto* ipv6 = reinterpret_cast<const sockaddr_in6*>(address);
            swprintf_s(
                output,
                output_cch,
                L"ipv6:%u",
                static_cast<unsigned>(NetworkPortToHost(ipv6->sin6_port)));
            return true;
        }
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        output[0] = L'\0';
        return false;
    }
    return false;
}

static bool ShouldSendNetworkUseEvent(const wchar_t* api_name, uintptr_t caller) {
    if (!NetworkUseTraceEnabled() || !caller) {
        return false;
    }

    const DWORD tid = GetCurrentThreadId();
    const uint64_t now = GetTickCount64();
    const uint32_t api_hash = HashWideString32(api_name);
    bool should_send = true;

    AcquireSRWLockExclusive(&g_network_use_emit_lock);
    for (const auto& record : g_network_use_emit_records) {
        if (record.caller == caller &&
            record.tid == tid &&
            record.api_hash == api_hash &&
            now >= record.tick_ms &&
            now - record.tick_ms < 1000) {
            should_send = false;
            break;
        }
    }

    if (should_send) {
        NetworkUseEmitRecord& slot = g_network_use_emit_records[
            g_network_use_emit_next_record % _countof(g_network_use_emit_records)];
        slot = {};
        slot.caller = caller;
        slot.tid = tid;
        slot.api_hash = api_hash;
        slot.tick_ms = now;
        g_network_use_emit_next_record = (g_network_use_emit_next_record + 1) % _countof(g_network_use_emit_records);
    }
    ReleaseSRWLockExclusive(&g_network_use_emit_lock);
    return should_send;
}

static void SendNetworkUseEvent(const wchar_t* api_name, const wchar_t* target_name,
    uintptr_t caller, int32_t status) {
    if (!ShouldSendNetworkUseEvent(api_name, caller)) {
        return;
    }

    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        kMonitorEventNetworkApi,
        api_name,
        (target_name && target_name[0]) ? target_name : L"network-use",
        status,
        static_cast<uint64_t>(caller),
        0,
        0,
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static void SendTemporalImageEvent(const wchar_t* rule, const wchar_t* module_path,
    uintptr_t address, uint32_t modified_bytes, uintptr_t module_base, int32_t status) {
    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    SendEvent(
        kMonitorEventMemoryApi,
        rule,
        module_path,
        status,
        static_cast<uint64_t>(address),
        modified_bytes,
        static_cast<uint64_t>(module_base),
        frames,
        captured,
        frame_context,
        frame_context_size);
}

static bool IsTemporalImageModuleAllowed(const wchar_t* path) {
    wchar_t lower[kMonitorTargetNameChars]{};
    CopyWideString(lower, _countof(lower), BasenamePtr(path));
    LowerInPlace(lower);
    return wcscmp(lower, L"ntdll.dll") == 0 ||
        wcscmp(lower, L"kernel32.dll") == 0 ||
        wcscmp(lower, L"kernelbase.dll") == 0 ||
        wcscmp(lower, L"callstackmonitor.dll") == 0 ||
        wcscmp(lower, L"windhawk.dll") == 0 ||
        wcscmp(lower, L"ucrtbase.dll") == 0 ||
        wcscmp(lower, L"msvcrt.dll") == 0 ||
        wcscmp(lower, L"vcruntime140.dll") == 0 ||
        wcscmp(lower, L"vcruntime140_1.dll") == 0 ||
        wcscmp(lower, L"concrt140.dll") == 0 ||
        wcscmp(lower, L"mscoree.dll") == 0 ||
        wcscmp(lower, L"clr.dll") == 0 ||
        wcscmp(lower, L"clrjit.dll") == 0 ||
        wcscmp(lower, L"system.ni.dll") == 0 ||
        wcscmp(lower, L"mscorlib.ni.dll") == 0;
}

static bool TemporalImageShouldAuditSection(const IMAGE_SECTION_HEADER& section) {
    const bool executable = (section.Characteristics & IMAGE_SCN_MEM_EXECUTE) != 0;
    if (executable) {
        return true;
    }

    char name[9]{};
    memcpy(name, section.Name, sizeof(section.Name));
    return _stricmp(name, ".pdata") == 0 ||
        _stricmp(name, ".xdata") == 0 ||
        _stricmp(name, ".rdata") == 0;
}

static bool ReadDiskRange(const wchar_t* path, uint64_t offset, void* buffer, DWORD size) {
    if (!path || !path[0] || !buffer || size == 0) {
        return false;
    }

    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        return false;
    }

    LARGE_INTEGER distance{};
    distance.QuadPart = static_cast<LONGLONG>(offset);
    bool ok = SetFilePointerEx(file, distance, nullptr, FILE_BEGIN) != FALSE;
    DWORD bytes_read = 0;
    if (ok) {
        ok = ReadFile(file, buffer, size, &bytes_read, nullptr) != FALSE && bytes_read == size;
    }
    CloseHandle(file);
    return ok;
}

struct TemporalImageSnapshot {
    bool valid = false;
    bool modified = false;
    uintptr_t module_base = 0;
    uintptr_t module_end = 0;
    uintptr_t first_modified = 0;
    uint32_t modified_bytes = 0;
    wchar_t path[kMonitorTargetNameChars]{};
};

static bool BuildTemporalImageSnapshot(uintptr_t address, size_t requested_size, TemporalImageSnapshot& snapshot) {
    snapshot = {};
    if (!address) {
        return false;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) ||
        mbi.State != MEM_COMMIT ||
        mbi.Type != MEM_IMAGE ||
        !mbi.AllocationBase) {
        return false;
    }

    const auto module_base = reinterpret_cast<uintptr_t>(mbi.AllocationBase);
    wchar_t path[MAX_PATH * 4]{};
    if (!GetModuleFileNameW(reinterpret_cast<HMODULE>(module_base), path, _countof(path)) || !path[0]) {
        return false;
    }
    if (IsTemporalImageModuleAllowed(path)) {
        return false;
    }

    IMAGE_DOS_HEADER dos{};
    if (!ReadProcessBytes(module_base, &dos, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew <= 0 || dos.e_lfanew > 0x100000) {
        return false;
    }

    IMAGE_NT_HEADERS64 nt{};
    if (!ReadProcessBytes(module_base + static_cast<uintptr_t>(dos.e_lfanew), &nt, sizeof(nt)) ||
        nt.Signature != IMAGE_NT_SIGNATURE ||
        nt.OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        nt.FileHeader.NumberOfSections == 0 ||
        nt.FileHeader.NumberOfSections > 96 ||
        nt.OptionalHeader.SizeOfImage == 0) {
        return false;
    }

    IMAGE_SECTION_HEADER sections[96]{};
    const uintptr_t section_table = module_base + static_cast<uintptr_t>(dos.e_lfanew) +
        FIELD_OFFSET(IMAGE_NT_HEADERS64, OptionalHeader) + nt.FileHeader.SizeOfOptionalHeader;
    const size_t section_bytes = static_cast<size_t>(nt.FileHeader.NumberOfSections) * sizeof(IMAGE_SECTION_HEADER);
    if (!ReadProcessBytes(section_table, sections, section_bytes)) {
        return false;
    }

    const uintptr_t module_end = module_base + nt.OptionalHeader.SizeOfImage;
    uintptr_t range_begin = address;
    uintptr_t range_end = requested_size ? address + requested_size : address + 1;
    if (range_end < range_begin || range_end > module_end) {
        range_end = module_end;
    }
    if (range_begin < module_base || range_begin >= module_end || range_end <= range_begin) {
        return false;
    }

    snapshot.valid = true;
    snapshot.module_base = module_base;
    snapshot.module_end = module_end;
    CopyWideString(snapshot.path, _countof(snapshot.path), path);

    constexpr size_t kChunkSize = 4096;
    constexpr size_t kMaxCompareBytes = 64 * 1024;
    uint8_t live[kChunkSize]{};
    uint8_t disk[kChunkSize]{};
    size_t compared = 0;

    for (uint16_t i = 0; i < nt.FileHeader.NumberOfSections && compared < kMaxCompareBytes; ++i) {
        const IMAGE_SECTION_HEADER& section = sections[i];
        if (!TemporalImageShouldAuditSection(section) || section.PointerToRawData == 0 || section.SizeOfRawData == 0) {
            continue;
        }

        const uint32_t virtual_size = section.Misc.VirtualSize ? section.Misc.VirtualSize : section.SizeOfRawData;
        const uintptr_t section_begin = module_base + section.VirtualAddress;
        const uintptr_t section_end = section_begin + std::max<uint32_t>(virtual_size, section.SizeOfRawData);
        const uintptr_t begin = std::max(range_begin, section_begin);
        const uintptr_t end = std::min(range_end, section_end);
        if (end <= begin) {
            continue;
        }

        uintptr_t cursor = begin;
        while (cursor < end && compared < kMaxCompareBytes) {
            const size_t remaining = static_cast<size_t>(end - cursor);
            const size_t chunk = std::min({ remaining, kChunkSize, kMaxCompareBytes - compared });
            const uint64_t raw_offset = static_cast<uint64_t>(section.PointerToRawData) +
                static_cast<uint64_t>(cursor - section_begin);
            if (!ReadProcessBytes(cursor, live, chunk) ||
                !ReadDiskRange(path, raw_offset, disk, static_cast<DWORD>(chunk))) {
                break;
            }

            for (size_t j = 0; j < chunk; ++j) {
                if (live[j] != disk[j]) {
                    if (!snapshot.modified) {
                        snapshot.first_modified = cursor + j;
                    }
                    snapshot.modified = true;
                    if (snapshot.modified_bytes < UINT32_MAX) {
                        ++snapshot.modified_bytes;
                    }
                }
            }

            cursor += chunk;
            compared += chunk;
        }
    }

    return snapshot.valid;
}

static TemporalImageMonitorRecord* FindTemporalImageRecordNoLock(uintptr_t module_base, uintptr_t module_end, bool create) {
    TemporalImageMonitorRecord* empty = nullptr;
    for (auto& record : g_temporal_image_records) {
        if (record.module_base == module_base) {
            return &record;
        }
        if (!record.module_base && !empty) {
            empty = &record;
        }
    }
    if (create && empty) {
        empty->module_base = module_base;
        empty->module_end = module_end;
        return empty;
    }
    return nullptr;
}

static void ProbeTemporalImageForAddress(uintptr_t address, size_t region_size, int32_t status) {
    if (!TemporalImageTraceEnabled() || !address) {
        return;
    }

    TemporalImageSnapshot snapshot{};
    if (!BuildTemporalImageSnapshot(address, region_size, snapshot)) {
        return;
    }

    const wchar_t* rule_to_send = nullptr;
    uintptr_t send_address = snapshot.modified ? snapshot.first_modified : address;
    uint32_t modified_bytes = snapshot.modified_bytes;

    AcquireSRWLockExclusive(&g_temporal_image_lock);
    TemporalImageMonitorRecord* record = FindTemporalImageRecordNoLock(snapshot.module_base, snapshot.module_end, true);
    if (record) {
        CopyWideString(record->path, _countof(record->path), snapshot.path);
        if (snapshot.modified) {
            if (!record->dirty) {
                record->dirty = true;
                record->ever_dirty = true;
                rule_to_send = L"image_module_temporally_stomped";
            }
        } else if (record->dirty && !record->restored_reported) {
            record->dirty = false;
            record->restored_reported = true;
            rule_to_send = L"image_module_restored_after_temporal_stomp";
        }
    }
    ReleaseSRWLockExclusive(&g_temporal_image_lock);

    if (rule_to_send) {
        SendTemporalImageEvent(rule_to_send, snapshot.path, send_address, modified_bytes, snapshot.module_base, status);
    }
}

static void ProbeTemporalImageBeforeUnmap(uintptr_t address) {
    if (!TemporalImageTraceEnabled() || !address) {
        return;
    }

    MEMORY_BASIC_INFORMATION mbi{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) || !mbi.AllocationBase) {
        return;
    }
    const uintptr_t module_base = reinterpret_cast<uintptr_t>(mbi.AllocationBase);

    wchar_t path[kMonitorTargetNameChars]{};
    bool should_send = false;
    AcquireSRWLockExclusive(&g_temporal_image_lock);
    TemporalImageMonitorRecord* record = FindTemporalImageRecordNoLock(module_base, 0, false);
    if (record && record->ever_dirty && !record->unmap_reported) {
        record->unmap_reported = true;
        CopyWideString(path, _countof(path), record->path);
        should_send = true;
    }
    ReleaseSRWLockExclusive(&g_temporal_image_lock);

    if (should_send) {
        SendTemporalImageEvent(L"modified_image_unmapped_after_temporal_stomp", path, address, 0, module_base, 0);
    }
}

#include "monitor_ldr.cpp"
#include "monitor_remote.cpp"

static void StoreWorkCallback(PTP_WORK work, void* callback) {
    if (!work || !callback) {
        return;
    }
    AcquireSRWLockExclusive(&g_work_lock);
    for (auto& record : g_work_callbacks) {
        if (!record.work || record.work == work) {
            record.work = work;
            record.callback = callback;
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_work_lock);
}

static void* LookupWorkCallback(PTP_WORK work) {
    void* callback = nullptr;
    AcquireSRWLockShared(&g_work_lock);
    for (const auto& record : g_work_callbacks) {
        if (record.work == work) {
            callback = record.callback;
            break;
        }
    }
    ReleaseSRWLockShared(&g_work_lock);
    return callback;
}

static void RemoveWorkCallback(PTP_WORK work) {
    AcquireSRWLockExclusive(&g_work_lock);
    for (auto& record : g_work_callbacks) {
        if (record.work == work) {
            record = {};
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_work_lock);
}

static ThreadpoolChainRecord* AllocateThreadpoolChainRecord(PTP_WORK_CALLBACK callback, PVOID context) {
    if (!callback) {
        return nullptr;
    }
    auto* record = static_cast<ThreadpoolChainRecord*>(
        HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(ThreadpoolChainRecord)));
    if (!record) {
        return nullptr;
    }
    record->callback = callback;
    record->context = context;
    record->tick_ms = GetTickCount64();
    return record;
}

static void StoreThreadpoolChainRecord(ThreadpoolChainRecord* record, PTP_WORK work) {
    if (!record || !work) {
        return;
    }
    record->work = work;
    AcquireSRWLockExclusive(&g_threadpool_chain_lock);
    for (auto& slot : g_threadpool_chain_records) {
        if (!slot || slot->work == work) {
            slot = record;
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_threadpool_chain_lock);
}

static ThreadpoolChainRecord* LookupThreadpoolChainRecord(PTP_WORK work) {
    ThreadpoolChainRecord* result = nullptr;
    AcquireSRWLockShared(&g_threadpool_chain_lock);
    for (auto* record : g_threadpool_chain_records) {
        if (record && record->work == work) {
            result = record;
            break;
        }
    }
    ReleaseSRWLockShared(&g_threadpool_chain_lock);
    return result;
}

static ThreadpoolChainRecord* RemoveThreadpoolChainRecord(PTP_WORK work) {
    ThreadpoolChainRecord* result = nullptr;
    AcquireSRWLockExclusive(&g_threadpool_chain_lock);
    for (auto& record : g_threadpool_chain_records) {
        if (record && record->work == work) {
            result = record;
            record = nullptr;
            break;
        }
    }
    ReleaseSRWLockExclusive(&g_threadpool_chain_lock);
    return result;
}

static uint64_t NtDelayIntervalToMs(PLARGE_INTEGER delay_interval, bool* infinite) {
    *infinite = false;
    if (!delay_interval) {
        *infinite = true;
        return UINT64_MAX;
    }
    const LONGLONG value = delay_interval->QuadPart;
    if (value >= 0) {
        return static_cast<uint64_t>(value / 10000);
    }
    return static_cast<uint64_t>((-value) / 10000);
}
