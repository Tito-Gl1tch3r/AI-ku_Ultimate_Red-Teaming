struct OriginProbeCandidate {
    uintptr_t value;
    uint32_t reg;
};

static bool TryRecordProxyBlockAt(
    uintptr_t block_address,
    uint32_t reg,
    uintptr_t return_address,
    bool visible_proxy_gadget,
    const wchar_t* visible_gadget,
    const wchar_t* record_name,
    bool allow_nonexec_origin = false,
    uintptr_t origin_hint = 0) {
    if (!block_address) {
        return false;
    }

    uintptr_t words[8]{};
    size_t word_count = _countof(words);
    if (!ReadProcessBytes(block_address, words, word_count * sizeof(uintptr_t))) {
        word_count = 4;
        if (!ReadProcessBytes(block_address, words, word_count * sizeof(uintptr_t))) {
            word_count = 3;
            if (!ReadProcessBytes(block_address, words, word_count * sizeof(uintptr_t))) {
                return false;
            }
        }
    }

    uintptr_t dll_value = 0;
    uintptr_t dll_content = 0;
    uintptr_t loader_value = 0;
    uintptr_t loader_container = 0;
    uintptr_t gadget_value = 0;
    wchar_t dll_name[kMonitorTargetNameChars]{};
    wchar_t loader_name[kMonitorEventNameChars]{};
    wchar_t gadget_name[kMonitorEventNameChars]{};

    for (size_t i = 0; i < word_count; ++i) {
        const uintptr_t word = words[i];
        if (!dll_value) {
            uintptr_t content = 0;
            wchar_t candidate_name[kMonitorTargetNameChars]{};
            if (IsWatchedDllPointer(word, candidate_name, _countof(candidate_name), &content)) {
                dll_value = word;
                dll_content = content ? content : word;
                CopyWideString(dll_name, _countof(dll_name), candidate_name);
            }
        }
        if (!loader_value) {
            if (IsLoaderApiPointer(word, loader_name, _countof(loader_name))) {
                loader_value = word;
            } else if (word) {
                uintptr_t indirect = 0;
                wchar_t indirect_name[kMonitorEventNameChars]{};
                if (ReadProcessBytes(word, &indirect, sizeof(indirect)) &&
                    IsLoaderApiPointer(indirect, indirect_name, _countof(indirect_name))) {
                    loader_value = indirect;
                    loader_container = word;
                    CopyWideString(loader_name, _countof(loader_name), indirect_name);
                }
            }
        }
        if (!gadget_value && LooksLikeGadgetPointer(word, gadget_name, _countof(gadget_name))) {
            gadget_value = word;
        }
    }

    if (!dll_value || (!loader_value && !gadget_value && !visible_proxy_gadget)) {
        return false;
    }

    uintptr_t origin = origin_hint ? FindExecutableOriginNearPointer(origin_hint) : 0;
    if (!origin && dll_content) {
        origin = FindExecutableOriginNearPointer(dll_content);
    }
    if (!origin && dll_value) {
        origin = FindExecutableOriginNearPointer(dll_value);
    }
    if (!origin) {
        origin = FindExecutableOriginNearPointer(block_address);
    }
    if (!origin && allow_nonexec_origin) {
        origin = block_address;
    }
    if (!origin) {
        return false;
    }

    AddTraceRangesForExecutableRegion(reinterpret_cast<void*>(origin), 0, L"mapped-exec");
    RecordOriginTrace(
        kMonitorOriginDllStringPointer,
        reg,
        origin,
        dll_content ? dll_content : dll_value,
        return_address,
        record_name,
        dll_name);
    if (loader_value) {
        RecordOriginTrace(
            kMonitorOriginLoaderApiPointer,
            reg,
            origin,
            loader_container ? loader_container : loader_value,
            return_address,
            record_name,
            loader_name);
    }
    if (gadget_value) {
        RecordOriginTrace(
            kMonitorOriginGadgetPointer,
            reg,
            origin,
            gadget_value,
            return_address,
            record_name,
            gadget_name);
    } else if (visible_proxy_gadget) {
        const uintptr_t gadget_start = return_address >= 3 ? return_address - 3 : return_address;
        RecordOriginTrace(
            kMonitorOriginGadgetPointer,
            kMonitorRegRip,
            origin,
            gadget_start,
            return_address,
            record_name,
            visible_gadget);
    }
    return true;
}

static bool TryRecordProxyBlockCandidates(
    const OriginProbeCandidate* candidates,
    size_t candidate_count,
    uintptr_t return_address,
    const wchar_t* record_name,
    bool scan_near_candidates) {
    const uintptr_t gadget_start = return_address >= 3 ? return_address - 3 : return_address;
    wchar_t visible_gadget[kMonitorEventNameChars]{};
    const bool visible_proxy_gadget = LooksLikeGadgetPointer(gadget_start, visible_gadget, _countof(visible_gadget));

    for (size_t i = 0; i < candidate_count; ++i) {
        const OriginProbeCandidate& candidate = candidates[i];
        if (!candidate.value) {
            continue;
        }

        if (TryRecordProxyBlockAt(
            candidate.value,
            candidate.reg,
            return_address,
            visible_proxy_gadget,
            visible_gadget,
            record_name)) {
            return true;
        }

        if (!scan_near_candidates) {
            continue;
        }

        constexpr intptr_t kScanWindow = 0x40;
        for (intptr_t offset = -kScanWindow; offset <= kScanWindow; offset += static_cast<intptr_t>(sizeof(uintptr_t))) {
            if (offset == 0) {
                continue;
            }
            if (offset < 0 && candidate.value < static_cast<uintptr_t>(-offset)) {
                continue;
            }
            const uintptr_t probe = static_cast<uintptr_t>(static_cast<intptr_t>(candidate.value) + offset);
            if (TryRecordProxyBlockAt(
                probe,
                candidate.reg,
                return_address,
                visible_proxy_gadget,
                visible_gadget,
                record_name)) {
                return true;
            }
        }
    }

    return false;
}

static bool IsIndirectCallsiteEndingAt(uintptr_t return_address, uintptr_t* callsite_address = nullptr) {
    if (!return_address || return_address < 32) {
        return false;
    }

    uint8_t bytes[32]{};
    const uintptr_t start = return_address - sizeof(bytes);
    if (!ReadProcessBytes(start, bytes, sizeof(bytes))) {
        return false;
    }

    ZydisDecodedInstruction instruction{};
    ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]{};
    if (!ZydisDecodeInstructionEndingAt(
        bytes,
        sizeof(bytes),
        start,
        sizeof(bytes),
        instruction,
        operands) ||
        ZydisBranchKindOf(instruction) != ZydisBranchKind::Call) {
        return false;
    }

    bool indirect = false;
    for (uint8_t i = 0; i < instruction.operand_count; ++i) {
        const auto& operand = operands[i];
        if (operand.visibility != ZYDIS_OPERAND_VISIBILITY_EXPLICIT) {
            continue;
        }
        if (operand.type == ZYDIS_OPERAND_TYPE_REGISTER ||
            operand.type == ZYDIS_OPERAND_TYPE_MEMORY) {
            indirect = true;
            break;
        }
    }
    if (!indirect) {
        return false;
    }

    if (callsite_address) {
        *callsite_address = return_address - instruction.length;
    }
    return true;
}

static bool TryRecordFunctionProxyBlockFromStack(
    uintptr_t stack_address,
    uintptr_t return_address,
    const wchar_t* record_name,
    bool indirect_callsite) {
    if (!stack_address) {
        return false;
    }

    const wchar_t* visible_name = indirect_callsite ? L"indirect-loader-callsite" : L"worker-proxy-context";
    constexpr intptr_t kStackScanBefore = 0x300;
    constexpr intptr_t kStackScanAfter = 0x900;
    for (intptr_t offset = -kStackScanBefore;
        offset <= kStackScanAfter;
        offset += static_cast<intptr_t>(sizeof(uintptr_t))) {
        if (offset < 0 && stack_address < static_cast<uintptr_t>(-offset)) {
            continue;
        }

        const uintptr_t slot = static_cast<uintptr_t>(static_cast<intptr_t>(stack_address) + offset);
        uintptr_t word = 0;
        if (!ReadProcessBytes(slot, &word, sizeof(word))) {
            continue;
        }

        if (TryRecordProxyBlockAt(
            slot,
            kMonitorRegRsp,
            return_address,
            indirect_callsite,
            visible_name,
            record_name)) {
            return true;
        }

        if (word &&
            TryRecordProxyBlockAt(
                word,
                kMonitorRegRsp,
                return_address,
                indirect_callsite,
                visible_name,
                record_name)) {
            return true;
        }
    }

    return false;
}

static bool MaybeRecordFunctionProxyOrigin(
    uintptr_t stack_address,
    uintptr_t return_address,
    const wchar_t* record_name) {
    if (!DispatchTraceEnabled() || !return_address) {
        return false;
    }

    uintptr_t callsite = 0;
    const bool indirect_callsite = IsIndirectCallsiteEndingAt(return_address, &callsite);
    if (!indirect_callsite || !callsite) {
        return false;
    }

    if (TryRecordFunctionProxyBlockFromStack(
        stack_address,
        return_address,
        record_name,
        indirect_callsite)) {
        return true;
    }

    wchar_t module_name[kMonitorEventNameChars]{};
    ModuleBasenameForAddress(callsite, module_name, _countof(module_name));
    if (!module_name[0]) {
        CopyWideString(module_name, _countof(module_name), L"indirect-callsite");
    }

    RecordOriginTrace(
        kMonitorOriginProxyTransfer,
        kMonitorRegRip,
        callsite,
        return_address,
        return_address,
        L"function-proxy-indirect-callsite",
        module_name);
    return true;
}

static bool TryRecordThreadpoolChainContextAt(
    uintptr_t block_address,
    uintptr_t return_address,
    uintptr_t callback_address) {
    const uintptr_t gadget_start = return_address >= 3 ? return_address - 3 : return_address;
    wchar_t visible_gadget[kMonitorEventNameChars]{};
    const bool visible_proxy_gadget = LooksLikeGadgetPointer(gadget_start, visible_gadget, _countof(visible_gadget));
    if (!visible_proxy_gadget) {
        CopyWideString(visible_gadget, _countof(visible_gadget), L"threadpool-proxy-frame");
    }

    return TryRecordProxyBlockAt(
        block_address,
        kMonitorRegRsp,
        return_address,
        true,
        visible_gadget,
        L"threadpool-chain-proxy-context",
        true,
        callback_address);
}

static bool MaybeRecordThreadpoolChainOrigin(uintptr_t return_address) {
    if (!ThreadpoolChainTraceEnabled() || !return_address || !g_active_threadpool_chain_record) {
        return false;
    }

    const uintptr_t callback_address = reinterpret_cast<uintptr_t>(g_active_threadpool_chain_record->callback);
    const uintptr_t context = reinterpret_cast<uintptr_t>(g_active_threadpool_chain_record->context);
    if (!callback_address || !context) {
        return false;
    }

    if (TryRecordThreadpoolChainContextAt(context, return_address, callback_address)) {
        return true;
    }

    constexpr intptr_t kContextScanBytes = 0x300;
    for (intptr_t offset = 0; offset <= kContextScanBytes; offset += static_cast<intptr_t>(sizeof(uintptr_t))) {
        const uintptr_t probe = context + static_cast<uintptr_t>(offset);
        if (TryRecordThreadpoolChainContextAt(probe, return_address, callback_address)) {
            return true;
        }
    }

    return false;
}

static bool IsDispatchTraceFrameModule(const wchar_t* module_name) {
    if (!module_name || !module_name[0]) {
        return true;
    }

    return wcscmp(module_name, L"callstackmonitor.dll") == 0 ||
        wcscmp(module_name, L"user32.dll") == 0 ||
        wcscmp(module_name, L"win32u.dll") == 0 ||
        wcscmp(module_name, L"ntdll.dll") == 0 ||
        wcscmp(module_name, L"kernel32.dll") == 0 ||
        wcscmp(module_name, L"kernelbase.dll") == 0;
}

static uintptr_t SelectDispatchRequesterRip() {
    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uintptr_t fallback = 0;
    for (USHORT i = 0; i < captured; ++i) {
        const uintptr_t address = reinterpret_cast<uintptr_t>(frames[i]);
        if (!address) {
            continue;
        }
        wchar_t module_name[kMonitorEventNameChars]{};
        ModuleBasenameForAddress(address, module_name, _countof(module_name));
        if (!module_name[0]) {
            return address;
        }
        if (!fallback && !IsDispatchTraceFrameModule(module_name)) {
            fallback = address;
        }
    }
    return fallback;
}

static bool TryBuildDispatchTraceRecord(
    DWORD target_tid,
    UINT message,
    WPARAM wparam,
    LPARAM lparam,
    DispatchTraceRecord& record) {
    if (!DispatchTraceEnabled() || !target_tid || !lparam) {
        return false;
    }

    uintptr_t words[16]{};
    size_t word_count = _countof(words);
    if (!ReadProcessBytes(static_cast<uintptr_t>(lparam), words, word_count * sizeof(uintptr_t))) {
        word_count = 8;
        if (!ReadProcessBytes(static_cast<uintptr_t>(lparam), words, word_count * sizeof(uintptr_t))) {
            word_count = 4;
            if (!ReadProcessBytes(static_cast<uintptr_t>(lparam), words, word_count * sizeof(uintptr_t))) {
                return false;
            }
        }
    }

    uintptr_t function_value = 0;
    uintptr_t argument_value = 0;
    wchar_t api_name[kMonitorEventNameChars]{};
    wchar_t dll_name[kMonitorTargetNameChars]{};

    for (size_t i = 0; i < word_count; ++i) {
        const uintptr_t word = words[i];
        if (!function_value && IsLoaderApiPointer(word, api_name, _countof(api_name))) {
            function_value = word;
        }
        if (!argument_value) {
            uintptr_t content = 0;
            wchar_t candidate_name[kMonitorTargetNameChars]{};
            if (IsWatchedDllPointer(word, candidate_name, _countof(candidate_name), &content)) {
                argument_value = content ? content : word;
                CopyWideString(dll_name, _countof(dll_name), candidate_name);
            }
        }
    }

    if (!function_value || !argument_value || !dll_name[0]) {
        return false;
    }

    record = {};
    record.valid = true;
    record.source_tid = GetCurrentThreadId();
    record.target_tid = target_tid;
    record.message = message;
    record.wparam = wparam;
    record.lparam = lparam;
    record.function_value = function_value;
    record.argument_value = argument_value;
    record.requester_rip = SelectDispatchRequesterRip();
    if (!record.requester_rip) {
        record.requester_rip = static_cast<uintptr_t>(lparam);
    }
    record.wait_handle = reinterpret_cast<HANDLE>(words[0]);
    record.tick_ms = GetTickCount64();
    CopyWideString(record.api_name, _countof(record.api_name), api_name);
    CopyWideString(record.dll_name, _countof(record.dll_name), dll_name);
    return true;
}

static void MaybeRecordThreadMessageDispatchOrigin(uintptr_t return_address, const wchar_t* dll_name) {
    if (!DispatchTraceEnabled() || !dll_name || !dll_name[0]) {
        return;
    }

    DispatchTraceRecord dispatch{};
    if (FindRecentDispatchTraceForThread(GetCurrentThreadId(), dll_name, dispatch)) {
        RecordDispatchOriginTrace(dispatch, return_address, dll_name);
    }
}

static BOOL WINAPI HookedPostThreadMessageA(DWORD target_tid, UINT message, WPARAM wparam, LPARAM lparam) {
    if (!g_inside_hook && g_original_post_thread_message_a) {
        g_inside_hook = true;
        DispatchTraceRecord record{};
        const bool should_remember = TryBuildDispatchTraceRecord(target_tid, message, wparam, lparam, record);
        if (should_remember) {
            RememberDispatchTraceRecord(record);
        }
        const BOOL result = g_original_post_thread_message_a(target_tid, message, wparam, lparam);
        g_inside_hook = false;
        return result;
    }
    return g_original_post_thread_message_a ? g_original_post_thread_message_a(target_tid, message, wparam, lparam) : FALSE;
}

static BOOL WINAPI HookedPostThreadMessageW(DWORD target_tid, UINT message, WPARAM wparam, LPARAM lparam) {
    if (!g_inside_hook && g_original_post_thread_message_w) {
        g_inside_hook = true;
        DispatchTraceRecord record{};
        const bool should_remember = TryBuildDispatchTraceRecord(target_tid, message, wparam, lparam, record);
        if (should_remember) {
            RememberDispatchTraceRecord(record);
        }
        const BOOL result = g_original_post_thread_message_w(target_tid, message, wparam, lparam);
        g_inside_hook = false;
        return result;
    }
    return g_original_post_thread_message_w ? g_original_post_thread_message_w(target_tid, message, wparam, lparam) : FALSE;
}

static void InstallDispatchTraceHooks() {
    if (!DispatchTraceEnabled()) {
        return;
    }
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (!user32) {
        return;
    }
    if (InterlockedCompareExchange(&g_dispatch_trace_hooks_installed, 1, 0) != 0) {
        return;
    }

    bool hooked = false;
    void* post_a = reinterpret_cast<void*>(GetProcAddress(user32, "PostThreadMessageA"));
    if (post_a && MH_CreateHook(post_a, reinterpret_cast<void*>(&HookedPostThreadMessageA),
        reinterpret_cast<void**>(&g_original_post_thread_message_a)) == MH_OK &&
        MH_EnableHook(post_a) == MH_OK) {
        hooked = true;
    }

    void* post_w = reinterpret_cast<void*>(GetProcAddress(user32, "PostThreadMessageW"));
    if (post_w && MH_CreateHook(post_w, reinterpret_cast<void*>(&HookedPostThreadMessageW),
        reinterpret_cast<void**>(&g_original_post_thread_message_w)) == MH_OK &&
        MH_EnableHook(post_w) == MH_OK) {
        hooked = true;
    }

    if (!hooked) {
        InterlockedExchange(&g_dispatch_trace_hooks_installed, 0);
    }
}

static DWORD WINAPI DispatchTraceInstallerThread(LPVOID) {
    for (uint32_t i = 0; i < 5000; ++i) {
        if (InterlockedCompareExchange(&g_dispatch_trace_hooks_installed, 0, 0) != 0) {
            break;
        }
        InstallDispatchTraceHooks();
        if (InterlockedCompareExchange(&g_dispatch_trace_hooks_installed, 0, 0) != 0) {
            break;
        }
        g_inside_hook = true;
        Sleep(1);
        g_inside_hook = false;
    }
    InterlockedExchange(&g_dispatch_trace_installer_started, 0);
    return 0;
}

static void StartDispatchTraceInstaller() {
    if (!DispatchTraceEnabled() ||
        InterlockedCompareExchange(&g_dispatch_trace_hooks_installed, 0, 0) != 0 ||
        InterlockedCompareExchange(&g_dispatch_trace_installer_started, 1, 0) != 0) {
        return;
    }

    HANDLE thread = CreateThread(nullptr, 0, DispatchTraceInstallerThread, nullptr, 0, nullptr);
    if (!thread) {
        InterlockedExchange(&g_dispatch_trace_installer_started, 0);
        return;
    }
    CloseHandle(thread);
}

static void MaybeRecordLoadLibraryOrigin(
    uintptr_t library_name,
    uintptr_t return_address,
    uintptr_t stack_address,
    uintptr_t rdx_value,
    uintptr_t r8_value,
    uintptr_t r9_value) {
    if (!OriginTraceEnabled() || !library_name) {
        return;
    }

    wchar_t dll_name[kMonitorTargetNameChars]{};
    if (!IsWatchedDllStringPointer(library_name, dll_name, _countof(dll_name))) {
        return;
    }

    MaybeRecordThreadMessageDispatchOrigin(return_address, dll_name);
    MaybeRecordThreadpoolChainOrigin(return_address);
    MaybeRecordFunctionProxyOrigin(stack_address, return_address, L"loadlibrary-function-proxy-stack");

    if (DispatchTraceEnabled()) {
        const OriginProbeCandidate function_proxy_candidates[] = {
            { rdx_value, kMonitorRegRdx },
            { r8_value, kMonitorRegR8 },
            { r9_value, kMonitorRegR9 },
        };
        TryRecordProxyBlockCandidates(function_proxy_candidates, _countof(function_proxy_candidates),
            return_address, L"loadlibrary-function-proxy-stack", true);
    }

    const OriginProbeCandidate candidates[] = {
        { rdx_value, kMonitorRegRdx },
        { r8_value, kMonitorRegR8 },
        { r9_value, kMonitorRegR9 },
    };
    if (TryRecordProxyBlockCandidates(candidates, _countof(candidates), return_address, L"loadlibrary-proxy-params", false)) {
        return;
    }

    uintptr_t origin = FindExecutableAddressInSameAllocation(library_name);
    if (!origin) {
        return;
    }
    AddTraceRangesForExecutableRegion(reinterpret_cast<void*>(origin), 0, L"mapped-exec");
    RecordOriginTrace(
        kMonitorOriginDllStringPointer,
        kMonitorRegRcx,
        origin,
        library_name,
        return_address,
        L"loadlibrary-entry-string",
        dll_name);
    const uintptr_t gadget_start = return_address >= 3 ? return_address - 3 : return_address;
    wchar_t visible_gadget[kMonitorEventNameChars]{};
    const bool visible_proxy_gadget = LooksLikeGadgetPointer(gadget_start, visible_gadget, _countof(visible_gadget));
    if (visible_proxy_gadget) {
        RecordOriginTrace(
            kMonitorOriginGadgetPointer,
            kMonitorRegRip,
            origin,
            gadget_start,
            return_address,
            L"loadlibrary-visible-gadget",
            visible_gadget);
    }
}

static void MaybeRecordLdrLoadDllOrigin(
    PUNICODE_STRING module_file_name,
    uintptr_t return_address,
    uintptr_t stack_address,
    uintptr_t search_path,
    uintptr_t dll_characteristics,
    uintptr_t module_file_name_arg,
    uintptr_t module_handle) {
    if (!OriginTraceEnabled() || !module_file_name) {
        return;
    }

    wchar_t dll_name[kMonitorTargetNameChars]{};
    uintptr_t dll_buffer = 0;
    if (!IsWatchedDllUnicodeStringPointer(
        reinterpret_cast<uintptr_t>(module_file_name),
        dll_name,
        _countof(dll_name),
        &dll_buffer)) {
        return;
    }

    MaybeRecordThreadMessageDispatchOrigin(return_address, dll_name);
    MaybeRecordThreadpoolChainOrigin(return_address);
    MaybeRecordFunctionProxyOrigin(stack_address, return_address, L"ldrloaddll-function-proxy-stack");

    const OriginProbeCandidate candidates[] = {
        { search_path, kMonitorRegRcx },
        { dll_characteristics, kMonitorRegRdx },
        { module_file_name_arg, kMonitorRegR8 },
        { module_handle, kMonitorRegR9 },
        { dll_buffer, kMonitorRegR8 },
    };
    if (TryRecordProxyBlockCandidates(candidates, _countof(candidates), return_address, L"ldrloaddll-proxy-params", true)) {
        return;
    }

    uintptr_t origin = FindExecutableAddressInSameAllocation(reinterpret_cast<uintptr_t>(module_file_name));
    if (!origin && dll_buffer) {
        origin = FindExecutableAddressInSameAllocation(dll_buffer);
    }
    if (!origin) {
        return;
    }

    AddTraceRangesForExecutableRegion(reinterpret_cast<void*>(origin), 0, L"mapped-exec");
    RecordOriginTrace(
        kMonitorOriginDllStringPointer,
        kMonitorRegR8,
        origin,
        dll_buffer ? dll_buffer : reinterpret_cast<uintptr_t>(module_file_name),
        return_address,
        L"ldrloaddll-entry-unicode-string",
        dll_name);

    const uintptr_t gadget_start = return_address >= 3 ? return_address - 3 : return_address;
    wchar_t visible_gadget[kMonitorEventNameChars]{};
    if (LooksLikeGadgetPointer(gadget_start, visible_gadget, _countof(visible_gadget))) {
        RecordOriginTrace(
            kMonitorOriginGadgetPointer,
            kMonitorRegRip,
            origin,
            gadget_start,
            return_address,
            L"ldrloaddll-visible-gadget",
            visible_gadget);
    }
}

static HMODULE WINAPI HookedLoadLibraryA(LPCSTR library_name, uintptr_t rdx_value, uintptr_t r8_value, uintptr_t r9_value) {
    if (g_inside_load_library_hook || !g_original_load_library_a) {
        return g_original_load_library_a ? g_original_load_library_a(library_name) : nullptr;
    }

    g_inside_load_library_hook = true;
    MaybeRecordLoadLibraryOrigin(
        reinterpret_cast<uintptr_t>(library_name),
        reinterpret_cast<uintptr_t>(_ReturnAddress()),
        reinterpret_cast<uintptr_t>(_AddressOfReturnAddress()),
        rdx_value,
        r8_value,
        r9_value);
    HMODULE result = g_original_load_library_a(library_name);
    g_inside_load_library_hook = false;
    return result;
}

static HMODULE WINAPI HookedLoadLibraryW(LPCWSTR library_name, uintptr_t rdx_value, uintptr_t r8_value, uintptr_t r9_value) {
    if (g_inside_load_library_hook || !g_original_load_library_w) {
        return g_original_load_library_w ? g_original_load_library_w(library_name) : nullptr;
    }

    g_inside_load_library_hook = true;
    MaybeRecordLoadLibraryOrigin(
        reinterpret_cast<uintptr_t>(library_name),
        reinterpret_cast<uintptr_t>(_ReturnAddress()),
        reinterpret_cast<uintptr_t>(_AddressOfReturnAddress()),
        rdx_value,
        r8_value,
        r9_value);
    HMODULE result = g_original_load_library_w(library_name);
    g_inside_load_library_hook = false;
    return result;
}

static HMODULE WINAPI HookedLoadLibraryExA(LPCSTR library_name, HANDLE file, DWORD flags, uintptr_t r9_value) {
    if (g_inside_load_library_hook || !g_original_load_library_ex_a) {
        return g_original_load_library_ex_a ? g_original_load_library_ex_a(library_name, file, flags) : nullptr;
    }

    g_inside_load_library_hook = true;
    MaybeRecordLoadLibraryOrigin(
        reinterpret_cast<uintptr_t>(library_name),
        reinterpret_cast<uintptr_t>(_ReturnAddress()),
        reinterpret_cast<uintptr_t>(_AddressOfReturnAddress()),
        reinterpret_cast<uintptr_t>(file),
        static_cast<uintptr_t>(flags),
        r9_value);
    HMODULE result = g_original_load_library_ex_a(library_name, file, flags);
    g_inside_load_library_hook = false;
    return result;
}

static HMODULE WINAPI HookedLoadLibraryExW(LPCWSTR library_name, HANDLE file, DWORD flags, uintptr_t r9_value) {
    if (g_inside_load_library_hook || !g_original_load_library_ex_w) {
        return g_original_load_library_ex_w ? g_original_load_library_ex_w(library_name, file, flags) : nullptr;
    }

    g_inside_load_library_hook = true;
    MaybeRecordLoadLibraryOrigin(
        reinterpret_cast<uintptr_t>(library_name),
        reinterpret_cast<uintptr_t>(_ReturnAddress()),
        reinterpret_cast<uintptr_t>(_AddressOfReturnAddress()),
        reinterpret_cast<uintptr_t>(file),
        static_cast<uintptr_t>(flags),
        r9_value);
    HMODULE result = g_original_load_library_ex_w(library_name, file, flags);
    g_inside_load_library_hook = false;
    return result;
}

static void BuildSocketIoTarget(wchar_t* output, size_t output_cch, SOCKET socket, int length) {
    if (!output || output_cch == 0) {
        return;
    }
    swprintf_s(
        output,
        output_cch,
        L"socket=0x%llX bytes=%d",
        static_cast<unsigned long long>(socket),
        length);
}

static int WSAAPI HookedConnect(SOCKET socket, const sockaddr* name, int namelen) {
    if (!g_inside_hook && g_original_connect) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        FormatSockaddrTarget(name, namelen, target, _countof(target));
        SendNetworkUseEvent(L"ws2_32.dll!connect", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_connect(socket, name, namelen);
        g_inside_hook = false;
        return result;
    }
    return g_original_connect ? g_original_connect(socket, name, namelen) : SOCKET_ERROR;
}

static int WSAAPI HookedWSAConnect(SOCKET socket, const sockaddr* name, int namelen,
    LPWSABUF caller_data, LPWSABUF callee_data, LPQOS sqos, LPQOS gqos) {
    if (!g_inside_hook && g_original_wsa_connect) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        FormatSockaddrTarget(name, namelen, target, _countof(target));
        SendNetworkUseEvent(L"ws2_32.dll!WSAConnect", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_wsa_connect(socket, name, namelen, caller_data, callee_data, sqos, gqos);
        g_inside_hook = false;
        return result;
    }
    return g_original_wsa_connect
        ? g_original_wsa_connect(socket, name, namelen, caller_data, callee_data, sqos, gqos)
        : SOCKET_ERROR;
}

static int WSAAPI HookedSend(SOCKET socket, const char* buffer, int length, int flags) {
    if (!g_inside_hook && g_original_send) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildSocketIoTarget(target, _countof(target), socket, length);
        SendNetworkUseEvent(L"ws2_32.dll!send", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_send(socket, buffer, length, flags);
        g_inside_hook = false;
        return result;
    }
    return g_original_send ? g_original_send(socket, buffer, length, flags) : SOCKET_ERROR;
}

static int WSAAPI HookedRecv(SOCKET socket, char* buffer, int length, int flags) {
    if (!g_inside_hook && g_original_recv) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildSocketIoTarget(target, _countof(target), socket, length);
        SendNetworkUseEvent(L"ws2_32.dll!recv", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_recv(socket, buffer, length, flags);
        g_inside_hook = false;
        return result;
    }
    return g_original_recv ? g_original_recv(socket, buffer, length, flags) : SOCKET_ERROR;
}

static int WSAAPI HookedWSASend(SOCKET socket, LPWSABUF buffers, DWORD buffer_count,
    LPDWORD bytes_sent, DWORD flags, LPWSAOVERLAPPED overlapped,
    LPWSAOVERLAPPED_COMPLETION_ROUTINE completion_routine) {
    if (!g_inside_hook && g_original_wsa_send) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildSocketIoTarget(target, _countof(target), socket,
            buffers && buffer_count ? static_cast<int>(buffers[0].len) : 0);
        SendNetworkUseEvent(L"ws2_32.dll!WSASend", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_wsa_send(
            socket, buffers, buffer_count, bytes_sent, flags, overlapped, completion_routine);
        g_inside_hook = false;
        return result;
    }
    return g_original_wsa_send
        ? g_original_wsa_send(socket, buffers, buffer_count, bytes_sent, flags, overlapped, completion_routine)
        : SOCKET_ERROR;
}

static int WSAAPI HookedWSARecv(SOCKET socket, LPWSABUF buffers, DWORD buffer_count,
    LPDWORD bytes_received, LPDWORD flags, LPWSAOVERLAPPED overlapped,
    LPWSAOVERLAPPED_COMPLETION_ROUTINE completion_routine) {
    if (!g_inside_hook && g_original_wsa_recv) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildSocketIoTarget(target, _countof(target), socket,
            buffers && buffer_count ? static_cast<int>(buffers[0].len) : 0);
        SendNetworkUseEvent(L"ws2_32.dll!WSARecv", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_wsa_recv(
            socket, buffers, buffer_count, bytes_received, flags, overlapped, completion_routine);
        g_inside_hook = false;
        return result;
    }
    return g_original_wsa_recv
        ? g_original_wsa_recv(socket, buffers, buffer_count, bytes_received, flags, overlapped, completion_routine)
        : SOCKET_ERROR;
}

static int WSAAPI HookedGetAddrInfoA(PCSTR node, PCSTR service, const ADDRINFOA* hints, ADDRINFOA** result_ptr) {
    if (!g_inside_hook && g_original_getaddrinfo) {
        g_inside_hook = true;
        wchar_t host[kMonitorTargetNameChars]{};
        CopyAnsiToWide(host, _countof(host), node);
        SendNetworkUseEvent(L"ws2_32.dll!getaddrinfo", host, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_getaddrinfo(node, service, hints, result_ptr);
        g_inside_hook = false;
        return result;
    }
    return g_original_getaddrinfo ? g_original_getaddrinfo(node, service, hints, result_ptr) : EAI_FAIL;
}

static int WSAAPI HookedGetAddrInfoW(PCWSTR node, PCWSTR service, const ADDRINFOW* hints, ADDRINFOW** result_ptr) {
    if (!g_inside_hook && g_original_getaddrinfow) {
        g_inside_hook = true;
        wchar_t host[kMonitorTargetNameChars]{};
        CopyWideString(host, _countof(host), node ? node : L"");
        SendNetworkUseEvent(L"ws2_32.dll!GetAddrInfoW", host, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const int result = g_original_getaddrinfow(node, service, hints, result_ptr);
        g_inside_hook = false;
        return result;
    }
    return g_original_getaddrinfow ? g_original_getaddrinfow(node, service, hints, result_ptr) : EAI_FAIL;
}

static HINTERNET WINAPI HookedInternetConnectA(HINTERNET internet, LPCSTR server_name, INTERNET_PORT port,
    LPCSTR user_name, LPCSTR password, DWORD service, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_internet_connect_a) {
        g_inside_hook = true;
        wchar_t host[kMonitorTargetNameChars]{};
        wchar_t target[kMonitorTargetNameChars]{};
        CopyAnsiToWide(host, _countof(host), server_name);
        BuildHostPortTarget(target, _countof(target), host, port);
        SendNetworkUseEvent(L"wininet.dll!InternetConnectA", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_internet_connect_a(
            internet, server_name, port, user_name, password, service, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_connect_a
        ? g_original_internet_connect_a(internet, server_name, port, user_name, password, service, flags, context)
        : nullptr;
}

static HINTERNET WINAPI HookedInternetConnectW(HINTERNET internet, LPCWSTR server_name, INTERNET_PORT port,
    LPCWSTR user_name, LPCWSTR password, DWORD service, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_internet_connect_w) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildHostPortTarget(target, _countof(target), server_name, port);
        SendNetworkUseEvent(L"wininet.dll!InternetConnectW", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_internet_connect_w(
            internet, server_name, port, user_name, password, service, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_connect_w
        ? g_original_internet_connect_w(internet, server_name, port, user_name, password, service, flags, context)
        : nullptr;
}

static HINTERNET WINAPI HookedInternetOpenUrlA(HINTERNET internet, LPCSTR url, LPCSTR headers,
    DWORD headers_length, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_internet_open_url_a) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        CopyAnsiToWide(target, _countof(target), url);
        SendNetworkUseEvent(L"wininet.dll!InternetOpenUrlA", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_internet_open_url_a(internet, url, headers, headers_length, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_open_url_a
        ? g_original_internet_open_url_a(internet, url, headers, headers_length, flags, context)
        : nullptr;
}

static HINTERNET WINAPI HookedInternetOpenUrlW(HINTERNET internet, LPCWSTR url, LPCWSTR headers,
    DWORD headers_length, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_internet_open_url_w) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!InternetOpenUrlW", url ? url : L"",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_internet_open_url_w(internet, url, headers, headers_length, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_open_url_w
        ? g_original_internet_open_url_w(internet, url, headers, headers_length, flags, context)
        : nullptr;
}

static HINTERNET WINAPI HookedHttpOpenRequestA(HINTERNET connect, LPCSTR verb, LPCSTR object_name,
    LPCSTR version, LPCSTR referrer, LPCSTR* accept_types, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_http_open_request_a) {
        g_inside_hook = true;
        wchar_t object[kMonitorTargetNameChars]{};
        CopyAnsiToWide(object, _countof(object), object_name);
        SendNetworkUseEvent(L"wininet.dll!HttpOpenRequestA", object[0] ? object : L"http-open-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_http_open_request_a(
            connect, verb, object_name, version, referrer, accept_types, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_http_open_request_a
        ? g_original_http_open_request_a(connect, verb, object_name, version, referrer, accept_types, flags, context)
        : nullptr;
}

static HINTERNET WINAPI HookedHttpOpenRequestW(HINTERNET connect, LPCWSTR verb, LPCWSTR object_name,
    LPCWSTR version, LPCWSTR referrer, LPCWSTR* accept_types, DWORD flags, DWORD_PTR context) {
    if (!g_inside_hook && g_original_http_open_request_w) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!HttpOpenRequestW",
            object_name && object_name[0] ? object_name : L"http-open-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_http_open_request_w(
            connect, verb, object_name, version, referrer, accept_types, flags, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_http_open_request_w
        ? g_original_http_open_request_w(connect, verb, object_name, version, referrer, accept_types, flags, context)
        : nullptr;
}

static BOOL WINAPI HookedHttpSendRequestA(HINTERNET request, LPCSTR headers, DWORD headers_length,
    LPVOID optional, DWORD optional_length) {
    if (!g_inside_hook && g_original_http_send_request_a) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!HttpSendRequestA", L"http-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_http_send_request_a(request, headers, headers_length, optional, optional_length);
        g_inside_hook = false;
        return result;
    }
    return g_original_http_send_request_a
        ? g_original_http_send_request_a(request, headers, headers_length, optional, optional_length)
        : FALSE;
}

static BOOL WINAPI HookedHttpSendRequestW(HINTERNET request, LPCWSTR headers, DWORD headers_length,
    LPVOID optional, DWORD optional_length) {
    if (!g_inside_hook && g_original_http_send_request_w) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!HttpSendRequestW", L"http-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_http_send_request_w(request, headers, headers_length, optional, optional_length);
        g_inside_hook = false;
        return result;
    }
    return g_original_http_send_request_w
        ? g_original_http_send_request_w(request, headers, headers_length, optional, optional_length)
        : FALSE;
}

static BOOL WINAPI HookedInternetReadFile(HINTERNET file, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read) {
    if (!g_inside_hook && g_original_internet_read_file) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!InternetReadFile", L"internet-read",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_internet_read_file(file, buffer, bytes_to_read, bytes_read);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_read_file
        ? g_original_internet_read_file(file, buffer, bytes_to_read, bytes_read)
        : FALSE;
}

static BOOL WINAPI HookedInternetWriteFile(HINTERNET file, LPCVOID buffer, DWORD bytes_to_write, LPDWORD bytes_written) {
    if (!g_inside_hook && g_original_internet_write_file) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"wininet.dll!InternetWriteFile", L"internet-write",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_internet_write_file(file, buffer, bytes_to_write, bytes_written);
        g_inside_hook = false;
        return result;
    }
    return g_original_internet_write_file
        ? g_original_internet_write_file(file, buffer, bytes_to_write, bytes_written)
        : FALSE;
}

static HINTERNET WINAPI HookedWinHttpOpen(LPCWSTR user_agent, DWORD access_type,
    LPCWSTR proxy_name, LPCWSTR proxy_bypass, DWORD flags) {
    if (!g_inside_hook && g_original_winhttp_open) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpOpen",
            user_agent && user_agent[0] ? user_agent : L"winhttp-open",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_winhttp_open(user_agent, access_type, proxy_name, proxy_bypass, flags);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_open
        ? g_original_winhttp_open(user_agent, access_type, proxy_name, proxy_bypass, flags)
        : nullptr;
}

static HINTERNET WINAPI HookedWinHttpConnect(HINTERNET session, LPCWSTR server_name, INTERNET_PORT port, DWORD reserved) {
    if (!g_inside_hook && g_original_winhttp_connect) {
        g_inside_hook = true;
        wchar_t target[kMonitorTargetNameChars]{};
        BuildHostPortTarget(target, _countof(target), server_name, port);
        SendNetworkUseEvent(L"winhttp.dll!WinHttpConnect", target, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_winhttp_connect(session, server_name, port, reserved);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_connect ? g_original_winhttp_connect(session, server_name, port, reserved) : nullptr;
}

static HINTERNET WINAPI HookedWinHttpOpenRequest(HINTERNET connect, LPCWSTR verb, LPCWSTR object_name,
    LPCWSTR version, LPCWSTR referrer, LPCWSTR* accept_types, DWORD flags) {
    if (!g_inside_hook && g_original_winhttp_open_request) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpOpenRequest",
            object_name && object_name[0] ? object_name : L"winhttp-open-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        HINTERNET result = g_original_winhttp_open_request(
            connect, verb, object_name, version, referrer, accept_types, flags);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_open_request
        ? g_original_winhttp_open_request(connect, verb, object_name, version, referrer, accept_types, flags)
        : nullptr;
}

static BOOL WINAPI HookedWinHttpSendRequest(HINTERNET request, LPCWSTR headers, DWORD headers_length,
    LPVOID optional, DWORD optional_length, DWORD total_length, DWORD_PTR context) {
    if (!g_inside_hook && g_original_winhttp_send_request) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpSendRequest", L"winhttp-request",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_winhttp_send_request(
            request, headers, headers_length, optional, optional_length, total_length, context);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_send_request
        ? g_original_winhttp_send_request(request, headers, headers_length, optional, optional_length, total_length, context)
        : FALSE;
}

static BOOL WINAPI HookedWinHttpReceiveResponse(HINTERNET request, LPVOID reserved) {
    if (!g_inside_hook && g_original_winhttp_receive_response) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpReceiveResponse", L"winhttp-response",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_winhttp_receive_response(request, reserved);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_receive_response ? g_original_winhttp_receive_response(request, reserved) : FALSE;
}

static BOOL WINAPI HookedWinHttpReadData(HINTERNET request, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read) {
    if (!g_inside_hook && g_original_winhttp_read_data) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpReadData", L"winhttp-read",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_winhttp_read_data(request, buffer, bytes_to_read, bytes_read);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_read_data
        ? g_original_winhttp_read_data(request, buffer, bytes_to_read, bytes_read)
        : FALSE;
}

static BOOL WINAPI HookedWinHttpWriteData(HINTERNET request, LPCVOID buffer, DWORD bytes_to_write, LPDWORD bytes_written) {
    if (!g_inside_hook && g_original_winhttp_write_data) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"winhttp.dll!WinHttpWriteData", L"winhttp-write",
            reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        const BOOL result = g_original_winhttp_write_data(request, buffer, bytes_to_write, bytes_written);
        g_inside_hook = false;
        return result;
    }
    return g_original_winhttp_write_data
        ? g_original_winhttp_write_data(request, buffer, bytes_to_write, bytes_written)
        : FALSE;
}

static DNS_STATUS WINAPI HookedDnsQueryA(PCSTR name, WORD type, DWORD options, PVOID extra,
    PDNS_RECORDA* query_results, PVOID* reserved) {
    if (!g_inside_hook && g_original_dns_query_a) {
        g_inside_hook = true;
        wchar_t host[kMonitorTargetNameChars]{};
        CopyAnsiToWide(host, _countof(host), name);
        SendNetworkUseEvent(L"dnsapi.dll!DnsQuery_A", host, reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        DNS_STATUS result = g_original_dns_query_a(name, type, options, extra, query_results, reserved);
        g_inside_hook = false;
        return result;
    }
    return g_original_dns_query_a ? g_original_dns_query_a(name, type, options, extra, query_results, reserved) : DNS_ERROR_RCODE_NAME_ERROR;
}

static DNS_STATUS WINAPI HookedDnsQueryW(PCWSTR name, WORD type, DWORD options, PVOID extra,
    PDNS_RECORDW* query_results, PVOID* reserved) {
    if (!g_inside_hook && g_original_dns_query_w) {
        g_inside_hook = true;
        SendNetworkUseEvent(L"dnsapi.dll!DnsQuery_W", name ? name : L"", reinterpret_cast<uintptr_t>(_ReturnAddress()), 0);
        DNS_STATUS result = g_original_dns_query_w(name, type, options, extra, query_results, reserved);
        g_inside_hook = false;
        return result;
    }
    return g_original_dns_query_w ? g_original_dns_query_w(name, type, options, extra, query_results, reserved) : DNS_ERROR_RCODE_NAME_ERROR;
}

static void HookNetworkExport(const wchar_t* module_name, const char* function_name, void* hook, void** original) {
    if (!NetworkUseTraceEnabled() || !original || *original) {
        return;
    }

    HMODULE module = GetModuleHandleW(module_name);
    if (!module) {
        return;
    }
    void* target = reinterpret_cast<void*>(GetProcAddress(module, function_name));
    if (!target) {
        return;
    }

    const bool was_inside_hook = g_inside_hook;
    g_inside_hook = true;
    const MH_STATUS create_status = MH_CreateHook(target, hook, original);
    if (create_status == MH_OK) {
        if (MH_EnableHook(target) != MH_OK) {
            *original = nullptr;
        }
    }
    g_inside_hook = was_inside_hook;
}

static void InstallNetworkUseHooks() {
    if (!NetworkUseTraceEnabled()) {
        return;
    }

    HookNetworkExport(L"ws2_32.dll", "connect", reinterpret_cast<void*>(&HookedConnect), reinterpret_cast<void**>(&g_original_connect));
    HookNetworkExport(L"ws2_32.dll", "WSAConnect", reinterpret_cast<void*>(&HookedWSAConnect), reinterpret_cast<void**>(&g_original_wsa_connect));
    HookNetworkExport(L"ws2_32.dll", "send", reinterpret_cast<void*>(&HookedSend), reinterpret_cast<void**>(&g_original_send));
    HookNetworkExport(L"ws2_32.dll", "recv", reinterpret_cast<void*>(&HookedRecv), reinterpret_cast<void**>(&g_original_recv));
    HookNetworkExport(L"ws2_32.dll", "WSASend", reinterpret_cast<void*>(&HookedWSASend), reinterpret_cast<void**>(&g_original_wsa_send));
    HookNetworkExport(L"ws2_32.dll", "WSARecv", reinterpret_cast<void*>(&HookedWSARecv), reinterpret_cast<void**>(&g_original_wsa_recv));
    HookNetworkExport(L"ws2_32.dll", "getaddrinfo", reinterpret_cast<void*>(&HookedGetAddrInfoA), reinterpret_cast<void**>(&g_original_getaddrinfo));
    HookNetworkExport(L"ws2_32.dll", "GetAddrInfoW", reinterpret_cast<void*>(&HookedGetAddrInfoW), reinterpret_cast<void**>(&g_original_getaddrinfow));

    HookNetworkExport(L"wininet.dll", "InternetConnectA", reinterpret_cast<void*>(&HookedInternetConnectA), reinterpret_cast<void**>(&g_original_internet_connect_a));
    HookNetworkExport(L"wininet.dll", "InternetConnectW", reinterpret_cast<void*>(&HookedInternetConnectW), reinterpret_cast<void**>(&g_original_internet_connect_w));
    HookNetworkExport(L"wininet.dll", "InternetOpenUrlA", reinterpret_cast<void*>(&HookedInternetOpenUrlA), reinterpret_cast<void**>(&g_original_internet_open_url_a));
    HookNetworkExport(L"wininet.dll", "InternetOpenUrlW", reinterpret_cast<void*>(&HookedInternetOpenUrlW), reinterpret_cast<void**>(&g_original_internet_open_url_w));
    HookNetworkExport(L"wininet.dll", "HttpOpenRequestA", reinterpret_cast<void*>(&HookedHttpOpenRequestA), reinterpret_cast<void**>(&g_original_http_open_request_a));
    HookNetworkExport(L"wininet.dll", "HttpOpenRequestW", reinterpret_cast<void*>(&HookedHttpOpenRequestW), reinterpret_cast<void**>(&g_original_http_open_request_w));
    HookNetworkExport(L"wininet.dll", "HttpSendRequestA", reinterpret_cast<void*>(&HookedHttpSendRequestA), reinterpret_cast<void**>(&g_original_http_send_request_a));
    HookNetworkExport(L"wininet.dll", "HttpSendRequestW", reinterpret_cast<void*>(&HookedHttpSendRequestW), reinterpret_cast<void**>(&g_original_http_send_request_w));
    HookNetworkExport(L"wininet.dll", "InternetReadFile", reinterpret_cast<void*>(&HookedInternetReadFile), reinterpret_cast<void**>(&g_original_internet_read_file));
    HookNetworkExport(L"wininet.dll", "InternetWriteFile", reinterpret_cast<void*>(&HookedInternetWriteFile), reinterpret_cast<void**>(&g_original_internet_write_file));

    HookNetworkExport(L"winhttp.dll", "WinHttpOpen", reinterpret_cast<void*>(&HookedWinHttpOpen), reinterpret_cast<void**>(&g_original_winhttp_open));
    HookNetworkExport(L"winhttp.dll", "WinHttpConnect", reinterpret_cast<void*>(&HookedWinHttpConnect), reinterpret_cast<void**>(&g_original_winhttp_connect));
    HookNetworkExport(L"winhttp.dll", "WinHttpOpenRequest", reinterpret_cast<void*>(&HookedWinHttpOpenRequest), reinterpret_cast<void**>(&g_original_winhttp_open_request));
    HookNetworkExport(L"winhttp.dll", "WinHttpSendRequest", reinterpret_cast<void*>(&HookedWinHttpSendRequest), reinterpret_cast<void**>(&g_original_winhttp_send_request));
    HookNetworkExport(L"winhttp.dll", "WinHttpReceiveResponse", reinterpret_cast<void*>(&HookedWinHttpReceiveResponse), reinterpret_cast<void**>(&g_original_winhttp_receive_response));
    HookNetworkExport(L"winhttp.dll", "WinHttpReadData", reinterpret_cast<void*>(&HookedWinHttpReadData), reinterpret_cast<void**>(&g_original_winhttp_read_data));
    HookNetworkExport(L"winhttp.dll", "WinHttpWriteData", reinterpret_cast<void*>(&HookedWinHttpWriteData), reinterpret_cast<void**>(&g_original_winhttp_write_data));

    HookNetworkExport(L"dnsapi.dll", "DnsQuery_A", reinterpret_cast<void*>(&HookedDnsQueryA), reinterpret_cast<void**>(&g_original_dns_query_a));
    HookNetworkExport(L"dnsapi.dll", "DnsQuery_W", reinterpret_cast<void*>(&HookedDnsQueryW), reinterpret_cast<void**>(&g_original_dns_query_w));
}

static volatile LONG g_temporal_image_hooks_disabled_for_managed_runtime = 0;

static void DisableTemporalImageHooksForManagedRuntime() {
    if (!TemporalImageTraceEnabled() ||
        (g_config.hook_flags & kMonitorHookMemoryApis) != 0 ||
        InterlockedCompareExchange(&g_temporal_image_hooks_disabled_for_managed_runtime, 1, 0) != 0) {
        return;
    }

    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    if (!ntdll) {
        return;
    }

    const bool was_inside_hook = g_inside_hook;
    g_inside_hook = true;
    if (void* target = reinterpret_cast<void*>(GetProcAddress(ntdll, "NtProtectVirtualMemory"))) {
        MH_DisableHook(target);
    }
    if (void* target = reinterpret_cast<void*>(GetProcAddress(ntdll, "NtMapViewOfSection"))) {
        MH_DisableHook(target);
    }
    if (void* target = reinterpret_cast<void*>(GetProcAddress(ntdll, "NtUnmapViewOfSection"))) {
        MH_DisableHook(target);
    }
    g_inside_hook = was_inside_hook;
}

static HANDLE WINAPI HookedOpenProcess(DWORD desired_access, BOOL inherit_handle, DWORD process_id) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        HANDLE result = g_original_open_process(desired_access, inherit_handle, process_id);
        if (result && process_id && process_id != GetCurrentProcessId()) {
            SendRemoteFollowEvent(L"OpenProcess", process_id, desired_access, 0);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_open_process(desired_access, inherit_handle, process_id);
}

static NTSTATUS NTAPI HookedNtOpenProcess(
    PHANDLE process_handle,
    ACCESS_MASK desired_access,
    POBJECT_ATTRIBUTES object_attributes,
    CLIENT_ID* client_id) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const NTSTATUS status = g_original_nt_open_process(
            process_handle,
            desired_access,
            object_attributes,
            client_id);
        const DWORD pid = client_id
            ? static_cast<DWORD>(reinterpret_cast<uintptr_t>(client_id->UniqueProcess))
            : 0;
        if (NT_SUCCESS(status) && process_handle && *process_handle && pid && pid != GetCurrentProcessId()) {
            SendRemoteFollowEvent(L"NtOpenProcess", pid, desired_access, static_cast<int32_t>(status));
        }
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_open_process(process_handle, desired_access, object_attributes, client_id);
}

static NTSTATUS NTAPI HookedLdrLoadDll(
    PWSTR search_path,
    PULONG dll_characteristics,
    PUNICODE_STRING module_file_name,
    PVOID* module_handle) {
    if (g_inside_hook || !g_original_ldr_load_dll) {
        return g_original_ldr_load_dll(search_path, dll_characteristics, module_file_name, module_handle);
    }

    g_inside_hook = true;

    wchar_t lower_dll_name[kMonitorTargetNameChars]{};
    CopyLowerBasenameFromUnicodeString(module_file_name, lower_dll_name, _countof(lower_dll_name));
    MaybeRecordLdrLoadDllOrigin(
        module_file_name,
        reinterpret_cast<uintptr_t>(_ReturnAddress()),
        reinterpret_cast<uintptr_t>(_AddressOfReturnAddress()),
        reinterpret_cast<uintptr_t>(search_path),
        reinterpret_cast<uintptr_t>(dll_characteristics),
        reinterpret_cast<uintptr_t>(module_file_name),
        reinterpret_cast<uintptr_t>(module_handle));

    void* frames[kMonitorMaxFrames]{};
    const USHORT captured = CaptureFrames(frames);
    uint8_t frame_context[kMonitorMaxFrames][kMonitorFrameContextBytes]{};
    uint8_t frame_context_size[kMonitorMaxFrames]{};
    CaptureFrameContexts(frames, captured, frame_context, frame_context_size);
    if (ByoudTraceEnabled() && IsWatchedDll(lower_dll_name)) {
        EmitByoudDiffsForCapturedModules(frames, captured, frame_context, frame_context_size);
    }

    const NTSTATUS status = g_original_ldr_load_dll(
        search_path,
        dll_characteristics,
        module_file_name,
        module_handle);

    if (NT_SUCCESS(status) && IsClrLikeModuleName(lower_dll_name)) {
        MarkManagedRuntimeLoaded();
    }

    if (NT_SUCCESS(status) && module_handle && *module_handle) {
        AddTraceRangesForModule(reinterpret_cast<HMODULE>(*module_handle), false);
        InstallNetworkUseHooks();
    }

    if (NT_SUCCESS(status) && IsWatchedDll(lower_dll_name)) {
        const uint64_t loaded_base = module_handle && *module_handle
            ? reinterpret_cast<uint64_t>(*module_handle)
            : 0;
        SendEvent(
            kMonitorEventDllLoad,
            L"LdrLoadDll",
            lower_dll_name,
            static_cast<int32_t>(status),
            loaded_base,
            0,
            0,
            frames,
            captured,
            frame_context,
            frame_context_size);
        if (NetResetEnabled() && module_handle && *module_handle && IsNetworkResetTarget(lower_dll_name)) {
            TryUnloadNetworkModule(reinterpret_cast<HMODULE>(*module_handle), lower_dll_name, L"net_reset_loaded");
        }
    }

    g_inside_hook = false;
    if (NT_SUCCESS(status) && IsClrLikeModuleName(lower_dll_name)) {
        DisableTemporalImageHooksForManagedRuntime();
    }
    return status;
}

static VOID WINAPI HookedSleep(DWORD milliseconds) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        SendTimedEvent(L"Sleep", milliseconds, false);
        g_original_sleep(milliseconds);
        g_inside_hook = false;
        return;
    }
    g_original_sleep(milliseconds);
}

static DWORD WINAPI HookedSleepEx(DWORD milliseconds, BOOL alertable) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        SendTimedEvent(L"SleepEx", milliseconds, false);
        const DWORD result = g_original_sleep_ex(milliseconds, alertable);
        g_inside_hook = false;
        return result;
    }
    return g_original_sleep_ex(milliseconds, alertable);
}

static NTSTATUS NTAPI HookedNtDelayExecution(BOOLEAN alertable, PLARGE_INTEGER delay_interval) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        bool infinite = false;
        const uint64_t timeout_ms = NtDelayIntervalToMs(delay_interval, &infinite);
        SendTimedEvent(L"NtDelayExecution", timeout_ms, infinite);
        const NTSTATUS status = g_original_nt_delay_execution(alertable, delay_interval);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_delay_execution(alertable, delay_interval);
}

static DWORD WINAPI HookedWaitForSingleObject(HANDLE handle, DWORD milliseconds) {
    if (DispatchTraceEnabled() && (g_config.hook_flags & kMonitorHookWaitObjects) == 0) {
        MarkDispatchWaitForHandle(handle);
        return g_original_wait_for_single_object(handle, milliseconds);
    }
    if (!g_inside_hook) {
        g_inside_hook = true;
        MarkDispatchWaitForHandle(handle);
        SendTimedEvent(L"WaitForSingleObject", milliseconds, milliseconds == INFINITE);
        const DWORD result = g_original_wait_for_single_object(handle, milliseconds);
        g_inside_hook = false;
        return result;
    }
    return g_original_wait_for_single_object(handle, milliseconds);
}

static DWORD WINAPI HookedWaitForMultipleObjects(DWORD count, const HANDLE* handles, BOOL wait_all, DWORD milliseconds) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        SendTimedEvent(L"WaitForMultipleObjects", milliseconds, milliseconds == INFINITE);
        const DWORD result = g_original_wait_for_multiple_objects(count, handles, wait_all, milliseconds);
        g_inside_hook = false;
        return result;
    }
    return g_original_wait_for_multiple_objects(count, handles, wait_all, milliseconds);
}

static DWORD WINAPI HookedMsgWaitForMultipleObjectsEx(DWORD count, const HANDLE* handles, DWORD milliseconds, DWORD wake_mask, DWORD flags) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        SendTimedEvent(L"MsgWaitForMultipleObjectsEx", milliseconds, milliseconds == INFINITE);
        const DWORD result = g_original_msg_wait_for_multiple_objects_ex(count, handles, milliseconds, wake_mask, flags);
        g_inside_hook = false;
        return result;
    }
    return g_original_msg_wait_for_multiple_objects_ex(count, handles, milliseconds, wake_mask, flags);
}

static HANDLE WINAPI HookedCreateThread(
    LPSECURITY_ATTRIBUTES thread_attributes,
    SIZE_T stack_size,
    LPTHREAD_START_ROUTINE start_address,
    LPVOID parameter,
    DWORD creation_flags,
    LPDWORD thread_id) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        ScanLdrIntegrity(L"CreateThread");
        bool trace_thread = ShouldWrapThreadStartForRegisterTrace(reinterpret_cast<void*>(start_address)) &&
            ShouldRegisterTraceAddress(reinterpret_cast<void*>(start_address));
        ThreadStartTraceRecord* trace_record = nullptr;
        LPTHREAD_START_ROUTINE effective_start = start_address;
        void* effective_parameter = parameter;
        if (trace_thread) {
            trace_record = CreateThreadStartTraceRecord(start_address, parameter);
            if (trace_record) {
                effective_start = RegTraceThreadStartThunk;
                effective_parameter = trace_record;
            } else {
                trace_thread = false;
            }
        }
        SendCallbackEvent(L"CreateThread", reinterpret_cast<void*>(start_address), 0, 0);
        const HANDLE thread = g_original_create_thread(
            thread_attributes,
            stack_size,
            effective_start,
            effective_parameter,
            creation_flags,
            thread_id);
        if (!thread && trace_record) {
            HeapFree(GetProcessHeap(), 0, trace_record);
        }
        g_inside_hook = false;
        return thread;
    }
    return g_original_create_thread(thread_attributes, stack_size, start_address, parameter, creation_flags, thread_id);
}

static DWORD WINAPI HookedQueueUserAPC(PAPCFUNC apc_routine, HANDLE thread, ULONG_PTR data) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        ArmTraceGuardForAddress(reinterpret_cast<uintptr_t>(apc_routine));
        SendCallbackEvent(L"QueueUserAPC", reinterpret_cast<void*>(apc_routine), reinterpret_cast<uint64_t>(thread), 0);
        const DWORD result = g_original_queue_user_apc(apc_routine, thread, data);
        g_inside_hook = false;
        return result;
    }
    return g_original_queue_user_apc(apc_routine, thread, data);
}

static VOID CALLBACK ThreadpoolChainCallbackThunk(PTP_CALLBACK_INSTANCE instance, PVOID context, PTP_WORK work) {
    auto* record = static_cast<ThreadpoolChainRecord*>(context);
    if (!record || !record->callback) {
        return;
    }

    ThreadpoolChainRecord* previous = g_active_threadpool_chain_record;
    g_active_threadpool_chain_record = record;
    record->callback(instance, record->context, work);
    g_active_threadpool_chain_record = previous;
}

static PTP_WORK WINAPI HookedCreateThreadpoolWork(
    PTP_WORK_CALLBACK callback,
    PVOID context,
    PTP_CALLBACK_ENVIRON callback_environment) {
    if (g_inside_hook || !g_original_create_threadpool_work) {
        return g_original_create_threadpool_work
            ? g_original_create_threadpool_work(callback, context, callback_environment)
            : nullptr;
    }

    if (!ThreadpoolChainTraceEnabled() || !callback) {
        return g_original_create_threadpool_work(callback, context, callback_environment);
    }

    g_inside_hook = true;
    ThreadpoolChainRecord* record = AllocateThreadpoolChainRecord(callback, context);
    PTP_WORK work = nullptr;
    if (record) {
        work = g_original_create_threadpool_work(ThreadpoolChainCallbackThunk, record, callback_environment);
        if (work) {
            StoreThreadpoolChainRecord(record, work);
            StoreWorkCallback(work, reinterpret_cast<void*>(callback));
            ArmTraceGuardForAddress(reinterpret_cast<uintptr_t>(callback));
            SendCallbackEvent(L"CreateThreadpoolWork", reinterpret_cast<void*>(callback), reinterpret_cast<uint64_t>(work), 0);
        } else {
            HeapFree(GetProcessHeap(), 0, record);
        }
    } else {
        work = g_original_create_threadpool_work(callback, context, callback_environment);
    }
    g_inside_hook = false;
    return work;
}

static VOID WINAPI HookedSubmitThreadpoolWork(PTP_WORK work) {
    if (!g_inside_hook && g_original_submit_threadpool_work) {
        g_inside_hook = true;
        ThreadpoolChainRecord* record = LookupThreadpoolChainRecord(work);
        if (record && record->callback) {
            SendCallbackEvent(L"SubmitThreadpoolWork", reinterpret_cast<void*>(record->callback), reinterpret_cast<uint64_t>(work), 0);
        }
        g_original_submit_threadpool_work(work);
        g_inside_hook = false;
        return;
    }
    if (g_original_submit_threadpool_work) {
        g_original_submit_threadpool_work(work);
    }
}

static VOID WINAPI HookedWaitForThreadpoolWorkCallbacks(PTP_WORK work, BOOL cancel_pending_callbacks) {
    if (!g_inside_hook && g_original_wait_for_threadpool_work_callbacks) {
        g_inside_hook = true;
        ThreadpoolChainRecord* record = LookupThreadpoolChainRecord(work);
        if (record && record->callback) {
            SendCallbackEvent(L"WaitForThreadpoolWorkCallbacks", reinterpret_cast<void*>(record->callback),
                reinterpret_cast<uint64_t>(work), 0);
        }
        g_original_wait_for_threadpool_work_callbacks(work, cancel_pending_callbacks);
        g_inside_hook = false;
        return;
    }
    if (g_original_wait_for_threadpool_work_callbacks) {
        g_original_wait_for_threadpool_work_callbacks(work, cancel_pending_callbacks);
    }
}

static VOID WINAPI HookedCloseThreadpoolWork(PTP_WORK work) {
    ThreadpoolChainRecord* record = RemoveThreadpoolChainRecord(work);
    RemoveWorkCallback(work);
    if (g_original_close_threadpool_work) {
        g_original_close_threadpool_work(work);
    }
    if (record) {
        HeapFree(GetProcessHeap(), 0, record);
    }
}

static NTSTATUS NTAPI HookedTpAllocWork(PTP_WORK* work_return, PTP_WORK_CALLBACK callback, PVOID context, PTP_CALLBACK_ENVIRON callback_environment) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        ArmTraceGuardForAddress(reinterpret_cast<uintptr_t>(callback));
        const NTSTATUS status = g_original_tp_alloc_work(work_return, callback, context, callback_environment);
        if (NT_SUCCESS(status) && work_return && *work_return) {
            StoreWorkCallback(*work_return, reinterpret_cast<void*>(callback));
        }
        SendCallbackEvent(L"TpAllocWork", reinterpret_cast<void*>(callback), work_return ? reinterpret_cast<uint64_t>(*work_return) : 0, static_cast<int32_t>(status));
        g_inside_hook = false;
        return status;
    }
    return g_original_tp_alloc_work(work_return, callback, context, callback_environment);
}

static VOID NTAPI HookedTpPostWork(PTP_WORK work) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        void* callback = LookupWorkCallback(work);
        SendCallbackEvent(L"TpPostWork", callback, reinterpret_cast<uint64_t>(work), 0);
        g_original_tp_post_work(work);
        g_inside_hook = false;
        return;
    }
    g_original_tp_post_work(work);
}

static VOID NTAPI HookedTpReleaseWork(PTP_WORK work) {
    RemoveWorkCallback(work);
    g_original_tp_release_work(work);
}

static NTSTATUS NTAPI HookedNtAllocateVirtualMemory(
    HANDLE process,
    PVOID* base_address,
    ULONG_PTR zero_bits,
    PSIZE_T region_size,
    ULONG allocation_type,
    ULONG protect) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const NTSTATUS status = g_original_nt_allocate_virtual_memory(
            process, base_address, zero_bits, region_size, allocation_type, protect);
        const DWORD original_last_error = GetLastError();
        if (NT_SUCCESS(status) && IsSelfProcessHandle(process) && base_address && *base_address) {
            if (IsExecutableMemoryProtect(protect)) {
                AddTraceRangesForExecutableRegion(
                    *base_address,
                    region_size ? *region_size : 0,
                    L"private-exec");
            }
            if (MemoryApiEventsEnabled()) {
                SendAddressEvent(
                    kMonitorEventMemoryApi,
                    L"NtAllocateVirtualMemory",
                    reinterpret_cast<uint64_t>(*base_address),
                    protect,
                    0,
                    static_cast<int32_t>(status));
            }
        }
        SetLastError(original_last_error);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_allocate_virtual_memory(process, base_address, zero_bits, region_size, allocation_type, protect);
}

static NTSTATUS NTAPI HookedNtProtectVirtualMemory(
    HANDLE process,
    PVOID* base_address,
    PSIZE_T region_size,
    ULONG new_protect,
    PULONG old_protect) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const bool managed_runtime_stack = ManagedRuntimeLoaded() || CurrentStackHasClrLikeFrame();
        const NTSTATUS status = g_original_nt_protect_virtual_memory(
            process, base_address, region_size, new_protect, old_protect);
        const DWORD original_last_error = GetLastError();
        if (NT_SUCCESS(status) && !managed_runtime_stack && IsSelfProcessHandle(process) && base_address && *base_address) {
            if (IsExecutableMemoryProtect(new_protect)) {
                AddTraceRangesForExecutableRegion(
                    *base_address,
                    region_size ? *region_size : 0,
                    L"private-exec");
            }
            ProbeTemporalImageForAddress(
                reinterpret_cast<uintptr_t>(*base_address),
                region_size ? *region_size : 0,
                static_cast<int32_t>(status));
            if (MemoryApiEventsEnabled()) {
                SendAddressEvent(
                    kMonitorEventMemoryApi,
                    L"NtProtectVirtualMemory",
                    reinterpret_cast<uint64_t>(*base_address),
                    new_protect,
                    0,
                    static_cast<int32_t>(status));
            }
        }
        SetLastError(original_last_error);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_protect_virtual_memory(process, base_address, region_size, new_protect, old_protect);
}

static NTSTATUS NTAPI HookedNtMapViewOfSection(
    HANDLE section,
    HANDLE process,
    PVOID* base_address,
    ULONG_PTR zero_bits,
    SIZE_T commit_size,
    PLARGE_INTEGER section_offset,
    PSIZE_T view_size,
    DWORD inherit_disposition,
    ULONG allocation_type,
    ULONG win32_protect) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const bool managed_runtime_stack = ManagedRuntimeLoaded() || CurrentStackHasClrLikeFrame();
        const NTSTATUS status = g_original_nt_map_view_of_section(
            section,
            process,
            base_address,
            zero_bits,
            commit_size,
            section_offset,
            view_size,
            inherit_disposition,
            allocation_type,
            win32_protect);
        const DWORD original_last_error = GetLastError();
        if (NT_SUCCESS(status) && !managed_runtime_stack && IsSelfProcessHandle(process) && base_address && *base_address) {
            AddTraceRangesForExecutableRegion(
                *base_address,
                view_size ? *view_size : 0,
                L"mapped-exec");
            ProbeTemporalImageForAddress(
                reinterpret_cast<uintptr_t>(*base_address),
                view_size ? *view_size : 0,
                static_cast<int32_t>(status));
            if (MemoryApiEventsEnabled()) {
                SendAddressEvent(
                    kMonitorEventMemoryApi,
                    L"NtMapViewOfSection",
                    reinterpret_cast<uint64_t>(*base_address),
                    win32_protect,
                    0,
                    static_cast<int32_t>(status));
            }
        }
        SetLastError(original_last_error);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_map_view_of_section(section, process, base_address, zero_bits, commit_size,
        section_offset, view_size, inherit_disposition, allocation_type, win32_protect);
}

static NTSTATUS NTAPI HookedNtUnmapViewOfSection(HANDLE process, PVOID base_address) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const bool managed_runtime_stack = ManagedRuntimeLoaded() || CurrentStackHasClrLikeFrame();
        if (!managed_runtime_stack && MemoryApiEventsEnabled() && IsSelfProcessHandle(process) && base_address) {
            ProbeTemporalImageBeforeUnmap(reinterpret_cast<uintptr_t>(base_address));
            SendAddressEvent(
                kMonitorEventMemoryApi,
                L"NtUnmapViewOfSection",
                reinterpret_cast<uint64_t>(base_address),
                0,
                0,
                0);
        }
        const NTSTATUS status = g_original_nt_unmap_view_of_section(process, base_address);
        const DWORD original_last_error = GetLastError();
        SetLastError(original_last_error);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_unmap_view_of_section(process, base_address);
}

static NTSTATUS NTAPI HookedNtWriteVirtualMemory(
    HANDLE process,
    PVOID base_address,
    PVOID buffer,
    SIZE_T bytes_to_write,
    PSIZE_T bytes_written) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const NTSTATUS status = g_original_nt_write_virtual_memory(
            process, base_address, buffer, bytes_to_write, bytes_written);
        const DWORD original_last_error = GetLastError();
        if (NT_SUCCESS(status) && MemoryApiEventsEnabled() && IsSelfProcessHandle(process) && base_address) {
            SendAddressEvent(
                kMonitorEventMemoryApi,
                L"NtWriteVirtualMemory",
                reinterpret_cast<uint64_t>(base_address),
                0,
                0,
                static_cast<int32_t>(status));
        }
        SetLastError(original_last_error);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_write_virtual_memory(process, base_address, buffer, bytes_to_write, bytes_written);
}

static NTSTATUS NTAPI HookedNtCreateThreadEx(
    PHANDLE thread,
    ACCESS_MASK desired_access,
    PVOID object_attributes,
    HANDLE process,
    PVOID start_routine,
    PVOID argument,
    ULONG create_flags,
    SIZE_T zero_bits,
    SIZE_T stack_size,
    SIZE_T maximum_stack_size,
    PVOID attribute_list) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        if (IsSelfProcessHandle(process)) {
            ScanLdrIntegrity(L"NtCreateThreadEx");
        }
        if (!IsSelfProcessHandle(process)) {
            InjectMonitorIntoRemoteProcess(process, L"NtCreateThreadEx");
        }
        bool trace_thread = IsSelfProcessHandle(process) &&
            ShouldWrapThreadStartForRegisterTrace(start_routine) &&
            ShouldRegisterTraceAddress(start_routine);
        ThreadStartTraceRecord* trace_record = nullptr;
        PVOID effective_start = start_routine;
        PVOID effective_argument = argument;
        if (trace_thread) {
            trace_record = CreateThreadStartTraceRecord(reinterpret_cast<LPTHREAD_START_ROUTINE>(start_routine), argument);
            if (trace_record) {
                effective_start = reinterpret_cast<PVOID>(&RegTraceThreadStartThunk);
                effective_argument = trace_record;
            } else {
                trace_thread = false;
            }
        }
        const NTSTATUS status = g_original_nt_create_thread_ex(
            thread,
            desired_access,
            object_attributes,
            process,
            effective_start,
            effective_argument,
            create_flags,
            zero_bits,
            stack_size,
            maximum_stack_size,
            attribute_list);
        if (!NT_SUCCESS(status) && trace_record) {
            HeapFree(GetProcessHeap(), 0, trace_record);
        }
        if (NT_SUCCESS(status) && IsSelfProcessHandle(process)) {
            SendCallbackEvent(
                L"NtCreateThreadEx",
                start_routine,
                thread ? reinterpret_cast<uint64_t>(*thread) : 0,
                static_cast<int32_t>(status));
        }
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_create_thread_ex(thread, desired_access, object_attributes, process, start_routine,
        argument, create_flags, zero_bits, stack_size, maximum_stack_size, attribute_list);
}

static NTSTATUS NTAPI HookedNtQueueApcThread(
    HANDLE thread,
    PVOID apc_routine,
    PVOID apc_argument1,
    PVOID apc_argument2,
    PVOID apc_argument3) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        InjectMonitorIntoThreadProcess(thread, L"NtQueueApcThread");
        ArmTraceGuardForAddress(reinterpret_cast<uintptr_t>(apc_routine));
        const NTSTATUS status = g_original_nt_queue_apc_thread(
            thread, apc_routine, apc_argument1, apc_argument2, apc_argument3);
        if (NT_SUCCESS(status)) {
            SendCallbackEvent(
                L"NtQueueApcThread",
                apc_routine,
                reinterpret_cast<uint64_t>(thread),
                static_cast<int32_t>(status));
        }
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_queue_apc_thread(thread, apc_routine, apc_argument1, apc_argument2, apc_argument3);
}

static uintptr_t TraceableRipFromContext(const CONTEXT* context) {
    if (!context || context->Rip == 0) {
        return 0;
    }
    if ((context->ContextFlags & CONTEXT_CONTROL) != CONTEXT_CONTROL &&
        (context->ContextFlags & CONTEXT_FULL) != CONTEXT_FULL) {
        return 0;
    }
    return static_cast<uintptr_t>(context->Rip);
}

static NTSTATUS NTAPI HookedNtSetContextThread(HANDLE thread, PCONTEXT context) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        InjectMonitorIntoThreadProcess(thread, L"NtSetContextThread");
        const uintptr_t rip = TraceableRipFromContext(context);
        if (rip && ShouldRegisterTraceAddress(reinterpret_cast<void*>(rip))) {
            ArmTraceGuardForAddress(rip);
        }
        const NTSTATUS status = g_original_nt_set_context_thread(thread, context);
        if (NT_SUCCESS(status) && rip) {
            SendCallbackEvent(L"NtSetContextThread", reinterpret_cast<void*>(rip), reinterpret_cast<uint64_t>(thread), static_cast<int32_t>(status));
        }
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_set_context_thread(thread, context);
}

static BOOL WINAPI HookedSetThreadContext(HANDLE thread, const CONTEXT* context) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        InjectMonitorIntoThreadProcess(thread, L"SetThreadContext");
        const uintptr_t rip = TraceableRipFromContext(context);
        if (rip && ShouldRegisterTraceAddress(reinterpret_cast<void*>(rip))) {
            ArmTraceGuardForAddress(rip);
        }
        const BOOL result = g_original_set_thread_context(thread, context);
        if (result && rip) {
            SendCallbackEvent(L"SetThreadContext", reinterpret_cast<void*>(rip), reinterpret_cast<uint64_t>(thread), 0);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_set_thread_context(thread, context);
}

static DWORD WINAPI HookedResumeThread(HANDLE thread) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        InjectMonitorIntoThreadProcess(thread, L"ResumeThread");
        const DWORD result = g_original_resume_thread(thread);
        g_inside_hook = false;
        return result;
    }
    return g_original_resume_thread(thread);
}

static NTSTATUS NTAPI HookedNtResumeThread(HANDLE thread, PULONG suspend_count) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        InjectMonitorIntoThreadProcess(thread, L"NtResumeThread");
        const NTSTATUS status = g_original_nt_resume_thread(thread, suspend_count);
        g_inside_hook = false;
        return status;
    }
    return g_original_nt_resume_thread(thread, suspend_count);
}

static PVOID WINAPI HookedAddVectoredExceptionHandler(ULONG first, PVECTORED_EXCEPTION_HANDLER handler) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        PVECTORED_EXCEPTION_HANDLER effective_handler = WrapVectoredExceptionHandler(handler);
        PVOID result = g_original_add_vectored_exception_handler(first, effective_handler);
        if (result && handler) {
            SendCallbackEvent(L"AddVectoredExceptionHandler", reinterpret_cast<void*>(handler), reinterpret_cast<uint64_t>(result), 0);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_add_vectored_exception_handler(first, handler);
}

static PVOID WINAPI HookedRtlAddVectoredExceptionHandler(ULONG first, PVECTORED_EXCEPTION_HANDLER handler) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        PVECTORED_EXCEPTION_HANDLER effective_handler = WrapVectoredExceptionHandler(handler);
        PVOID result = g_original_rtl_add_vectored_exception_handler(first, effective_handler);
        if (result && handler) {
            SendCallbackEvent(L"RtlAddVectoredExceptionHandler", reinterpret_cast<void*>(handler), reinterpret_cast<uint64_t>(result), 0);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_rtl_add_vectored_exception_handler(first, handler);
}

static BOOLEAN NTAPI HookedRtlAddFunctionTable(PRUNTIME_FUNCTION function_table, DWORD entry_count, DWORD64 base_address) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const BOOLEAN result = g_original_rtl_add_function_table(function_table, entry_count, base_address);
        if (result) {
            SendAddressEvent(
                kMonitorEventUnwindTable,
                L"RtlAddFunctionTable",
                reinterpret_cast<uint64_t>(function_table),
                entry_count,
                base_address,
                result ? 0 : 1);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_rtl_add_function_table(function_table, entry_count, base_address);
}

static BOOLEAN NTAPI HookedRtlDeleteFunctionTable(PRUNTIME_FUNCTION function_table) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        SendAddressEvent(
            kMonitorEventUnwindTable,
            L"RtlDeleteFunctionTable",
            reinterpret_cast<uint64_t>(function_table),
            0,
            0,
            0);
        const BOOLEAN result = g_original_rtl_delete_function_table(function_table);
        g_inside_hook = false;
        return result;
    }
    return g_original_rtl_delete_function_table(function_table);
}

static BOOLEAN NTAPI HookedRtlInstallFunctionTableCallback(
    DWORD64 table_identifier,
    DWORD64 base_address,
    DWORD length,
    PVOID callback,
    PVOID context,
    PCWSTR out_of_process_callback_dll) {
    if (!g_inside_hook) {
        g_inside_hook = true;
        const BOOLEAN result = g_original_rtl_install_function_table_callback(
            table_identifier,
            base_address,
            length,
            callback,
            context,
            out_of_process_callback_dll);
        if (result) {
            SendAddressEvent(
                kMonitorEventUnwindTable,
                L"RtlInstallFunctionTableCallback",
                base_address,
                length,
                reinterpret_cast<uint64_t>(callback),
                result ? 0 : 1);
        }
        g_inside_hook = false;
        return result;
    }
    return g_original_rtl_install_function_table_callback(
        table_identifier, base_address, length, callback, context, out_of_process_callback_dll);
}
