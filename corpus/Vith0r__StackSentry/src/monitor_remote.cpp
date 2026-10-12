static bool IsSelfProcessHandle(HANDLE process) {
    return process == GetCurrentProcess() ||
        process == reinterpret_cast<HANDLE>(static_cast<intptr_t>(-1));
}

static void RemoteTargetName(DWORD pid, wchar_t* output, size_t output_cch) {
    if (!output || output_cch == 0) {
        return;
    }

    SafeCopyWideString(output, output_cch, L"pid:");
    wchar_t digits[16]{};
    size_t digit_count = 0;
    DWORD value = pid;
    do {
        digits[digit_count++] = static_cast<wchar_t>(L'0' + (value % 10));
        value /= 10;
    } while (value && digit_count < _countof(digits));

    wchar_t ordered[16]{};
    for (size_t i = 0; i < digit_count; ++i) {
        ordered[i] = digits[digit_count - 1 - i];
    }
    SafeAppendWideString(output, output_cch, ordered);
}

static void SendRemoteFollowEvent(const wchar_t* api_name, DWORD pid, uint64_t value, int32_t status) {
    if (!FollowRemoteEnabled()) {
        return;
    }
    wchar_t target[kMonitorTargetNameChars]{};
    RemoteTargetName(pid, target, _countof(target));
    SendNamedEvent(kMonitorEventRemoteFollow, api_name, target, value, 0, status);
}

static bool HasInstrumentedRemotePid(DWORD pid) {
    bool found = false;
    AcquireSRWLockShared(&g_remote_follow_lock);
    for (DWORD item : g_remote_follow_pids) {
        if (item == pid) {
            found = true;
            break;
        }
    }
    ReleaseSRWLockShared(&g_remote_follow_lock);
    return found;
}

static void RememberInstrumentedRemotePid(DWORD pid) {
    if (!pid) {
        return;
    }
    AcquireSRWLockExclusive(&g_remote_follow_lock);
    for (DWORD& item : g_remote_follow_pids) {
        if (item == pid) {
            ReleaseSRWLockExclusive(&g_remote_follow_lock);
            return;
        }
        if (item == 0) {
            item = pid;
            ReleaseSRWLockExclusive(&g_remote_follow_lock);
            return;
        }
    }
    g_remote_follow_pids[0] = pid;
    ReleaseSRWLockExclusive(&g_remote_follow_lock);
}

static DWORD ProcessIdFromProcessHandle(HANDLE process) {
    if (!process || process == INVALID_HANDLE_VALUE) {
        return 0;
    }
    if (IsSelfProcessHandle(process)) {
        return GetCurrentProcessId();
    }
    return GetProcessId(process);
}

static DWORD ProcessIdFromThreadHandle(HANDLE thread) {
    if (!thread || thread == INVALID_HANDLE_VALUE) {
        return 0;
    }
    return GetProcessIdOfThread(thread);
}

static bool WriteRemoteMemoryBlock(HANDLE process, const void* data, size_t size, void** remote) {
    if (!remote) {
        return false;
    }
    *remote = VirtualAllocEx(process, nullptr, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!*remote) {
        return false;
    }
    SIZE_T written = 0;
    if (!WriteProcessMemory(process, *remote, data, size, &written) || written != size) {
        VirtualFreeEx(process, *remote, 0, MEM_RELEASE);
        *remote = nullptr;
        return false;
    }
    return true;
}

static bool RunRemoteThreadAndWait(HANDLE process, LPTHREAD_START_ROUTINE start, void* parameter, DWORD& exit_code) {
    HANDLE thread = CreateRemoteThread(process, nullptr, 0, start, parameter, 0, nullptr);
    if (!thread) {
        return false;
    }
    WaitForSingleObject(thread, 5000);
    exit_code = 0;
    GetExitCodeThread(thread, &exit_code);
    CloseHandle(thread);
    return true;
}

static uint64_t FindRemoteModuleBaseLocal(DWORD pid, const wchar_t* module_basename) {
    if (!pid || !module_basename || !module_basename[0]) {
        return 0;
    }
    wchar_t expected[kMonitorEventNameChars]{};
    CopyWideString(expected, _countof(expected), module_basename);
    LowerInPlace(expected);

    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return 0;
    }
    MODULEENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    uint64_t result = 0;
    if (Module32FirstW(snapshot, &entry)) {
        do {
            wchar_t name[kMonitorEventNameChars]{};
            CopyWideString(name, _countof(name), entry.szModule);
            LowerInPlace(name);
            if (wcscmp(name, expected) == 0) {
                result = reinterpret_cast<uint64_t>(entry.modBaseAddr);
                break;
            }
        } while (Module32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return result;
}

static bool InjectMonitorIntoRemoteProcess(HANDLE process, const wchar_t* reason) {
    if (!FollowRemoteEnabled() ||
        g_remote_follow_in_progress ||
        !process ||
        process == INVALID_HANDLE_VALUE ||
        g_config.monitor_path[0] == L'\0') {
        return false;
    }

    const DWORD pid = ProcessIdFromProcessHandle(process);
    if (!pid || pid == GetCurrentProcessId()) {
        return false;
    }
    if (HasInstrumentedRemotePid(pid)) {
        SendRemoteFollowEvent(reason ? reason : L"remote", pid, 0, 1);
        return true;
    }

    g_remote_follow_in_progress = true;
    const bool was_inside_hook = g_inside_hook;
    g_inside_hook = true;

    bool ok = false;
    void* remote_path = nullptr;
    if (WriteRemoteMemoryBlock(process, g_config.monitor_path,
        (wcslen(g_config.monitor_path) + 1) * sizeof(wchar_t), &remote_path)) {
        auto load_library = reinterpret_cast<LPTHREAD_START_ROUTINE>(
            GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW"));
        DWORD load_exit = 0;
        if (load_library && RunRemoteThreadAndWait(process, load_library, remote_path, load_exit)) {
            const uint64_t remote_base = FindRemoteModuleBaseLocal(pid, L"CallstackMonitor.dll");
            HMODULE local_monitor = g_module;
            void* local_init = reinterpret_cast<void*>(GetProcAddress(local_monitor, "InitializeMonitor"));
            if (remote_base && local_init) {
                const uint64_t init_rva = reinterpret_cast<uint64_t>(local_init) - reinterpret_cast<uint64_t>(local_monitor);
                void* remote_config = nullptr;
                MonitorConfig child_config = g_config;
                if (WriteRemoteMemoryBlock(process, &child_config, sizeof(child_config), &remote_config)) {
                    DWORD init_exit = 0;
                    ok = RunRemoteThreadAndWait(
                        process,
                        reinterpret_cast<LPTHREAD_START_ROUTINE>(remote_base + init_rva),
                        remote_config,
                        init_exit) && init_exit == kMonitorInitOk;
                    VirtualFreeEx(process, remote_config, 0, MEM_RELEASE);
                }
            }
        }
        VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);
    }

    if (ok) {
        RememberInstrumentedRemotePid(pid);
    }
    SendRemoteFollowEvent(reason ? reason : L"remote", pid, 0, ok ? 0 : static_cast<int32_t>(GetLastError()));

    g_inside_hook = was_inside_hook;
    g_remote_follow_in_progress = false;
    return ok;
}

static bool InjectMonitorIntoThreadProcess(HANDLE thread, const wchar_t* reason) {
    const DWORD pid = ProcessIdFromThreadHandle(thread);
    if (!pid || pid == GetCurrentProcessId()) {
        return false;
    }
    HANDLE process = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE,
        pid);
    if (!process) {
        SendRemoteFollowEvent(reason ? reason : L"remote-thread", pid, 0, static_cast<int32_t>(GetLastError()));
        return false;
    }
    const bool ok = InjectMonitorIntoRemoteProcess(process, reason);
    CloseHandle(process);
    return ok;
}

static bool IsNetworkResetTarget(const wchar_t* lower_basename) {
    if (!lower_basename || !lower_basename[0]) {
        return false;
    }
    wchar_t canonical[kMonitorWatchedDllNameChars]{};
    CopyWideString(canonical, _countof(canonical), lower_basename);
    if (!HasExtension(canonical)) {
        SafeAppendWideString(canonical, _countof(canonical), L".dll");
    }
    return wcscmp(canonical, L"wininet.dll") == 0 ||
        wcscmp(canonical, L"winhttp.dll") == 0 ||
        wcscmp(canonical, L"ws2_32.dll") == 0 ||
        wcscmp(canonical, L"dnsapi.dll") == 0 ||
        wcscmp(canonical, L"iphlpapi.dll") == 0;
}

static void SendNetResetEvent(const wchar_t* event_name, const wchar_t* dll_name, HMODULE module, int32_t status) {
    if (!NetResetEnabled()) {
        return;
    }
    SendNamedEvent(
        kMonitorEventNetReset,
        event_name,
        dll_name,
        reinterpret_cast<uint64_t>(module),
        0,
        status);
}

static void TryUnloadNetworkModule(HMODULE module, const wchar_t* lower_name, const wchar_t* reason) {
    if (!NetResetEnabled() || !module || !lower_name || !IsNetworkResetTarget(lower_name)) {
        return;
    }
    SendNetResetEvent(reason, lower_name, module, 1);
    const BOOL ok = FreeLibrary(module);
    SendNetResetEvent(ok ? L"net_reset_succeeded" : L"net_reset_failed",
        lower_name,
        module,
        ok ? 0 : static_cast<int32_t>(GetLastError()));
}

static void AttemptStartupNetReset() {
    if (!NetResetEnabled()) {
        return;
    }
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId());
    if (snapshot == INVALID_HANDLE_VALUE) {
        SendNetResetEvent(L"net_reset_failed", L"snapshot", nullptr, static_cast<int32_t>(GetLastError()));
        return;
    }
    MODULEENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    if (Module32FirstW(snapshot, &entry)) {
        do {
            wchar_t lower_name[kMonitorWatchedDllNameChars]{};
            CopyWideString(lower_name, _countof(lower_name), entry.szModule);
            LowerInPlace(lower_name);
            if (!IsNetworkResetTarget(lower_name)) {
                continue;
            }
            HMODULE module = GetModuleHandleW(entry.szModule);
            TryUnloadNetworkModule(module, lower_name, L"net_reset_preloaded");
        } while (Module32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
}
