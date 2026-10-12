static HANDLE CreateMonitorPipeInstance(const std::wstring& pipe_name) {
    return CreateNamedPipeW(
        pipe_name.c_str(),
        PIPE_ACCESS_INBOUND,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_NOWAIT,
        PIPE_UNLIMITED_INSTANCES,
        sizeof(MonitorEvent) * 8,
        sizeof(MonitorEvent) * 8,
        0,
        nullptr);
}

static void PipeReader(HANDLE pipe, RunState* state) {
    for (;;) {
        if (state && state->stop_collection.load()) {
            CloseHandle(pipe);
            return;
        }

        const BOOL connected = ConnectNamedPipe(pipe, nullptr);
        if (connected) {
            break;
        }

        const DWORD error = GetLastError();
        if (error == ERROR_PIPE_CONNECTED) {
            break;
        }
        if (error == ERROR_PIPE_LISTENING || error == ERROR_NO_DATA) {
            Sleep(25);
            continue;
        }
        CloseHandle(pipe);
        return;
    }

    for (;;) {
        if (state && state->stop_collection.load()) {
            break;
        }

        MonitorEvent event{};
        DWORD bytes_read = 0;
        const BOOL ok = ReadFile(pipe, &event, sizeof(event), &bytes_read, nullptr);
        if (!ok) {
            const DWORD error = GetLastError();
            if (error == ERROR_NO_DATA || error == ERROR_PIPE_LISTENING) {
                Sleep(25);
                continue;
            }
            break;
        }
        if (bytes_read == 0) {
            break;
        }
        if (bytes_read == sizeof(event)) {
            ProcessMonitorEvent(*state, event);
        }
    }

    DisconnectNamedPipe(pipe);
    CloseHandle(pipe);
}

static void PipeServer(const std::wstring& pipe_name, RunState* state,
    std::vector<std::thread>* readers, std::mutex* readers_mutex) {
    while (!state || !state->stop_collection.load()) {
        HANDLE pipe = CreateMonitorPipeInstance(pipe_name);
        if (pipe == INVALID_HANDLE_VALUE) {
            Sleep(100);
            continue;
        }

        bool connected = false;
        while (!state || !state->stop_collection.load()) {
            const BOOL ok = ConnectNamedPipe(pipe, nullptr);
            if (ok) {
                connected = true;
                break;
            }
            const DWORD error = GetLastError();
            if (error == ERROR_PIPE_CONNECTED) {
                connected = true;
                break;
            }
            if (error == ERROR_PIPE_LISTENING || error == ERROR_NO_DATA) {
                Sleep(25);
                continue;
            }
            break;
        }

        if (!connected) {
            CloseHandle(pipe);
            continue;
        }

        std::lock_guard<std::mutex> lock(*readers_mutex);
        readers->emplace_back(PipeReader, pipe, state);
    }
}

static void CloseHandleIfValid(HANDLE& handle) {
    if (handle && handle != INVALID_HANDLE_VALUE) {
        CloseHandle(handle);
        handle = nullptr;
    }
}

static bool DuplicateInheritableHandle(HANDLE source, HANDLE& duplicated) {
    duplicated = nullptr;
    if (!source || source == INVALID_HANDLE_VALUE) {
        return false;
    }
    return DuplicateHandle(
        GetCurrentProcess(),
        source,
        GetCurrentProcess(),
        &duplicated,
        0,
        TRUE,
        DUPLICATE_SAME_ACCESS) != FALSE;
}

static bool OpenInheritableNullDevice(HANDLE& handle, DWORD desired_access) {
    SECURITY_ATTRIBUTES security{};
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;
    handle = CreateFileW(
        L"NUL",
        desired_access,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        &security,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        nullptr);
    return handle && handle != INVALID_HANDLE_VALUE;
}

static std::wstring SanitizePathComponent(std::wstring value) {
    for (auto& ch : value) {
        if (ch < 32 ||
            ch == L'<' || ch == L'>' || ch == L':' || ch == L'"' ||
            ch == L'/' || ch == L'\\' || ch == L'|' || ch == L'?' || ch == L'*') {
            ch = L'_';
        }
    }
    while (!value.empty() && (value.back() == L' ' || value.back() == L'.')) {
        value.pop_back();
    }
    return value.empty() ? L"target" : value;
}

static fs::path BuildRunOutputDirectory(const fs::path& base_out_dir, const fs::path& target, DWORD pid) {
    std::wostringstream name;
    name << SanitizePathComponent(target.filename().wstring()) << L" - " << pid;
    fs::path candidate = base_out_dir / name.str();
    if (!fs::exists(candidate)) {
        return candidate;
    }

    for (uint32_t index = 2; index < 1000; ++index) {
        std::wostringstream alternate;
        alternate << name.str() << L" - " << index;
        candidate = base_out_dir / alternate.str();
        if (!fs::exists(candidate)) {
            return candidate;
        }
    }
    return base_out_dir / name.str();
}

static bool PrepareAutoEnterStdio(STARTUPINFOW& startup,
    HANDLE& child_stdin_read,
    HANDLE& stdin_write,
    HANDLE& child_stdout,
    HANDLE& child_stderr,
    std::wstring& error) {
    SECURITY_ATTRIBUTES security{};
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;

    if (!CreatePipe(&child_stdin_read, &stdin_write, &security, 0)) {
        std::wostringstream message;
        message << L"CreatePipe for target stdin failed: " << GetLastError();
        error = message.str();
        return false;
    }
    SetHandleInformation(stdin_write, HANDLE_FLAG_INHERIT, 0);

    if (!DuplicateInheritableHandle(GetStdHandle(STD_OUTPUT_HANDLE), child_stdout)) {
        CloseHandleIfValid(child_stdin_read);
        CloseHandleIfValid(stdin_write);
        error = L"failed to duplicate stdout for target";
        return false;
    }
    if (!DuplicateInheritableHandle(GetStdHandle(STD_ERROR_HANDLE), child_stderr)) {
        CloseHandleIfValid(child_stdin_read);
        CloseHandleIfValid(stdin_write);
        CloseHandleIfValid(child_stdout);
        error = L"failed to duplicate stderr for target";
        return false;
    }

    startup.dwFlags |= STARTF_USESTDHANDLES;
    startup.hStdInput = child_stdin_read;
    startup.hStdOutput = child_stdout;
    startup.hStdError = child_stderr;
    return true;
}

static bool PrepareSuppressedTargetStdio(STARTUPINFOW& startup,
    bool auto_enter,
    HANDLE& child_stdin_read,
    HANDLE& stdin_write,
    HANDLE& child_stdout,
    HANDLE& child_stderr,
    std::wstring& error) {
    SECURITY_ATTRIBUTES security{};
    security.nLength = sizeof(security);
    security.bInheritHandle = TRUE;

    if (auto_enter) {
        if (!CreatePipe(&child_stdin_read, &stdin_write, &security, 0)) {
            std::wostringstream message;
            message << L"CreatePipe for target stdin failed: " << GetLastError();
            error = message.str();
            return false;
        }
        SetHandleInformation(stdin_write, HANDLE_FLAG_INHERIT, 0);
    } else if (!DuplicateInheritableHandle(GetStdHandle(STD_INPUT_HANDLE), child_stdin_read) &&
        !OpenInheritableNullDevice(child_stdin_read, GENERIC_READ)) {
        error = L"failed to prepare stdin for target";
        return false;
    }

    if (!OpenInheritableNullDevice(child_stdout, GENERIC_WRITE)) {
        CloseHandleIfValid(child_stdin_read);
        CloseHandleIfValid(stdin_write);
        error = L"failed to redirect target stdout to NUL";
        return false;
    }
    if (!OpenInheritableNullDevice(child_stderr, GENERIC_WRITE)) {
        CloseHandleIfValid(child_stdin_read);
        CloseHandleIfValid(stdin_write);
        CloseHandleIfValid(child_stdout);
        error = L"failed to redirect target stderr to NUL";
        return false;
    }

    startup.dwFlags |= STARTF_USESTDHANDLES;
    startup.hStdInput = child_stdin_read;
    startup.hStdOutput = child_stdout;
    startup.hStdError = child_stderr;
    return true;
}

static bool CanUseConsoleAutoEnter(HANDLE& console_input) {
    console_input = GetStdHandle(STD_INPUT_HANDLE);
    if (!console_input || console_input == INVALID_HANDLE_VALUE) {
        console_input = nullptr;
        return false;
    }

    DWORD mode = 0;
    if (GetFileType(console_input) != FILE_TYPE_CHAR || !GetConsoleMode(console_input, &mode)) {
        console_input = nullptr;
        return false;
    }

    return true;
}

static void ConsoleEnterFeeder(HANDLE process, HANDLE console_input, uint32_t interval_ms, std::atomic<bool>* stop) {
    const DWORD delay = std::max<DWORD>(interval_ms, 50);

    for (;;) {
        if (stop && stop->load()) {
            break;
        }
        if (WaitForSingleObject(process, delay) != WAIT_TIMEOUT) {
            break;
        }
        if (stop && stop->load()) {
            break;
        }

        INPUT_RECORD input[2]{};
        input[0].EventType = KEY_EVENT;
        input[0].Event.KeyEvent.bKeyDown = TRUE;
        input[0].Event.KeyEvent.wRepeatCount = 1;
        input[0].Event.KeyEvent.wVirtualKeyCode = VK_RETURN;
        input[0].Event.KeyEvent.wVirtualScanCode = 0;
        input[0].Event.KeyEvent.uChar.UnicodeChar = L'\r';

        input[1] = input[0];
        input[1].Event.KeyEvent.bKeyDown = FALSE;

        DWORD written = 0;
        if (!WriteConsoleInputW(console_input, input, _countof(input), &written)) {
            break;
        }
    }
}

static void AutoEnterFeeder(HANDLE process, HANDLE stdin_write, uint32_t interval_ms, std::atomic<bool>* stop) {
    const DWORD delay = std::max<DWORD>(interval_ms, 50);
    static constexpr char kEnter[] = "\r\n";

    for (;;) {
        if (stop && stop->load()) {
            break;
        }
        if (WaitForSingleObject(process, delay) != WAIT_TIMEOUT) {
            break;
        }
        if (stop && stop->load()) {
            break;
        }

        DWORD written = 0;
        if (!WriteFile(stdin_write, kEnter, static_cast<DWORD>(sizeof(kEnter) - 1), &written, nullptr)) {
            break;
        }
    }

    CloseHandle(stdin_write);
}

static bool WriteRemoteMemory(HANDLE process, const void* data, size_t size, void** remote) {
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

static bool RunRemoteThread(HANDLE process, LPTHREAD_START_ROUTINE start, void* param, DWORD& exit_code) {
    HANDLE thread = CreateRemoteThread(process, nullptr, 0, start, param, 0, nullptr);
    if (!thread) {
        return false;
    }
    WaitForSingleObject(thread, INFINITE);
    exit_code = 0;
    GetExitCodeThread(thread, &exit_code);
    CloseHandle(thread);
    return true;
}

static fs::path GetExecutableDirectory() {
    wchar_t path[MAX_PATH * 4]{};
    GetModuleFileNameW(nullptr, path, _countof(path));
    return fs::path(path).parent_path();
}

static bool InjectMonitor(HANDLE process, DWORD pid, const fs::path& monitor_path,
    const MonitorConfig& config, std::wstring& error) {
    const std::wstring monitor_path_str = fs::absolute(monitor_path).wstring();
    void* remote_path = nullptr;
    if (!WriteRemoteMemory(process, monitor_path_str.c_str(),
        (monitor_path_str.size() + 1) * sizeof(wchar_t), &remote_path)) {
        error = L"failed to write monitor path into target";
        return false;
    }

    auto load_library = reinterpret_cast<LPTHREAD_START_ROUTINE>(
        GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW"));
    DWORD load_exit = 0;
    if (!load_library || !RunRemoteThread(process, load_library, remote_path, load_exit)) {
        VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);
        error = L"failed to run remote LoadLibraryW";
        return false;
    }
    VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);

    const uint64_t remote_base = FindRemoteModuleBase(pid, L"CallstackMonitor.dll");
    if (!remote_base) {
        error = L"monitor DLL was not found in target module list after LoadLibraryW";
        return false;
    }

    HMODULE local_monitor = LoadLibraryExW(monitor_path_str.c_str(), nullptr, DONT_RESOLVE_DLL_REFERENCES);
    if (!local_monitor) {
        error = L"failed to map monitor DLL locally for export RVA";
        return false;
    }
    void* local_init = reinterpret_cast<void*>(GetProcAddress(local_monitor, "InitializeMonitor"));
    if (!local_init) {
        FreeLibrary(local_monitor);
        error = L"InitializeMonitor export not found";
        return false;
    }
    const uint64_t init_rva = reinterpret_cast<uint64_t>(local_init) - reinterpret_cast<uint64_t>(local_monitor);
    FreeLibrary(local_monitor);

    void* remote_config = nullptr;
    if (!WriteRemoteMemory(process, &config, sizeof(config), &remote_config)) {
        error = L"failed to write monitor config into target";
        return false;
    }

    const auto remote_init = reinterpret_cast<LPTHREAD_START_ROUTINE>(remote_base + init_rva);
    DWORD init_exit = 0;
    if (!RunRemoteThread(process, remote_init, remote_config, init_exit)) {
        VirtualFreeEx(process, remote_config, 0, MEM_RELEASE);
        error = L"failed to run remote InitializeMonitor";
        return false;
    }
    VirtualFreeEx(process, remote_config, 0, MEM_RELEASE);

    if (init_exit != kMonitorInitOk) {
        std::wostringstream message;
        message << L"InitializeMonitor failed with code " << init_exit;
        error = message.str();
        return false;
    }

    return true;
}

static MonitorConfig BuildMonitorConfig(const std::wstring& pipe_name, const Rules& rules, const fs::path& monitor_path) {
    MonitorConfig config{};
    config.magic = kCallstackProtocolMagic;
    config.version = kCallstackProtocolVersion;
    config.max_frames = kMonitorMaxFrames;
    config.long_sleep_ms = rules.long_sleep_ms;
    if (rules.enable_sleep_hooks) {
        config.hook_flags |= kMonitorHookSleep;
    }
    if (rules.enable_msgwait_hook) {
        config.hook_flags |= kMonitorHookMsgWait;
    }
    if (rules.enable_wait_object_hooks) {
        config.hook_flags |= kMonitorHookWaitObjects;
    }
    if (rules.enable_thread_start_hooks) {
        config.hook_flags |= kMonitorHookThreadStarts;
    }
    if (rules.enable_threadpool_hooks) {
        config.hook_flags |= kMonitorHookThreadPool;
    }
    if (rules.memory_api_hooks) {
        config.hook_flags |= kMonitorHookMemoryApis;
    }
    const bool passive_memory_audit = rules.memory_audit &&
        rules.network_use_trace &&
        !rules.memory_api_hooks;
    if (rules.memory_audit && !passive_memory_audit) {
        config.hook_flags |= kMonitorHookTemporalImageTrace;
    }
    if (rules.unwind_table_hooks) {
        config.hook_flags |= kMonitorHookUnwindTables;
    }
    if (rules.origin_trace) {
        config.hook_flags |= kMonitorHookOriginTrace;
    }
    if (rules.register_trace) {
        config.hook_flags |= kMonitorHookOriginTrace | kMonitorHookRegisterTrace;
    }
    if (rules.follow_remote) {
        config.hook_flags |= kMonitorHookFollowRemote;
    }
    if (rules.net_reset) {
        config.hook_flags |= kMonitorHookNetReset;
    }
    if (rules.ldr_integrity) {
        config.hook_flags |= kMonitorHookLdrIntegrity;
    }
    if (rules.dispatch_trace) {
        config.hook_flags |= kMonitorHookDispatchTrace;
    }
    if (rules.threadpool_chain_trace) {
        config.hook_flags |= kMonitorHookThreadpoolChainTrace;
    }
    if (rules.byoud_trace) {
        config.hook_flags |= kMonitorHookByoudTrace;
    }
    if (rules.shadow_stack) {
        config.hook_flags |= kMonitorHookShadowStack;
    }
    if (rules.network_use_trace) {
        config.hook_flags |= kMonitorHookNetworkUseTrace;
    }
    wcsncpy_s(config.pipe_name, pipe_name.c_str(), _TRUNCATE);
    const std::wstring monitor_path_str = fs::absolute(monitor_path).wstring();
    wcsncpy_s(config.monitor_path, monitor_path_str.c_str(), _TRUNCATE);

    config.watched_dll_count = std::min<uint32_t>(static_cast<uint32_t>(rules.watch_dlls.size()), kMonitorMaxWatchedDlls);
    for (uint32_t i = 0; i < config.watched_dll_count; ++i) {
        wcsncpy_s(config.watched_dlls[i], rules.watch_dlls[i].c_str(), _TRUNCATE);
    }
    return config;
}

static void WriteDllLoadMemoryObservationJson(std::ofstream& output, const DllLoadMemoryObservation& item) {
    output
        << "{"
        << "\"event_index\":" << item.event_index << ","
        << "\"pid\":" << item.pid << ","
        << "\"tid\":" << item.tid << ","
        << "\"alert\":" << (item.alert ? "true" : "false") << ","
        << "\"score\":" << item.score << ","
        << "\"dll_name\":" << JsonString(item.dll_name) << ","
        << "\"loaded_base\":\"" << Hex64(item.loaded_base) << "\","
        << "\"loaded_size\":" << item.loaded_size << ","
        << "\"loaded_path\":" << JsonString(item.loaded_path) << ","
        << "\"caller\":{"
        << "\"address\":\"" << Hex64(item.caller_address) << "\","
        << "\"region_base\":\"" << Hex64(item.caller_region_base) << "\","
        << "\"region_size\":" << item.caller_region_size << ","
        << "\"allocation_base\":\"" << Hex64(item.caller_allocation_base) << "\","
        << "\"allocation_size\":" << item.caller_allocation_size << ","
        << "\"label\":" << JsonString(item.caller_label) << ","
        << "\"summary_name\":" << JsonString(item.caller_summary_name) << ","
        << "\"module_name\":" << JsonString(item.caller_module_name) << ","
        << "\"module_path\":" << JsonString(item.caller_module_path) << ","
        << "\"module_modified\":" << (item.caller_module_modified ? "true" : "false") << ","
        << "\"modified_module_dump_path\":" << JsonString(item.caller_modified_module_dump_path) << ","
        << "\"state\":" << JsonString(item.caller_state) << ","
        << "\"protect\":" << JsonString(item.caller_protect) << ","
        << "\"type\":" << JsonString(item.caller_type)
        << "},"
        << "\"origin_trace\":{"
        << "\"present\":" << (item.origin_trace ? "true" : "false") << ","
        << "\"confidence\":" << JsonString(item.origin_confidence) << ","
        << "\"source\":" << JsonString(item.origin_source) << ","
        << "\"kind\":" << JsonString(item.origin_kind) << ","
        << "\"register\":" << JsonString(item.origin_register) << ","
        << "\"address\":\"" << Hex64(item.origin_address) << "\","
        << "\"value\":\"" << Hex64(item.origin_value) << "\","
        << "\"target\":\"" << Hex64(item.origin_target) << "\","
        << "\"label\":" << JsonString(item.origin_label) << ","
        << "\"evidence\":" << JsonString(item.origin_evidence) << ","
        << "\"region_dump\":{"
        << "\"present\":" << (item.origin_region_dumped ? "true" : "false") << ","
        << "\"path\":" << JsonString(item.origin_region_dump_path) << ","
        << "\"base\":\"" << Hex64(item.origin_region_dump_base) << "\","
        << "\"size\":" << item.origin_region_dump_size << ","
        << "\"rva\":\"" << Hex64(item.origin_region_rva) << "\""
        << "}"
        << "},"
        << "\"dispatch_trace\":{"
        << "\"present\":" << (item.dispatch_trace ? "true" : "false") << ","
        << "\"requester_tid\":" << item.dispatch_source_tid << ","
        << "\"worker_tid\":" << item.dispatch_target_tid << ","
        << "\"message\":" << item.dispatch_message << ","
        << "\"wparam\":\"" << Hex64(item.dispatch_wparam) << "\","
        << "\"lparam\":\"" << Hex64(item.dispatch_lparam) << "\","
        << "\"wait_observed\":" << (item.dispatch_wait_observed ? "true" : "false") << ","
        << "\"api\":" << JsonString(item.dispatch_api) << ","
        << "\"function\":" << JsonString(item.dispatch_function) << ","
        << "\"argument\":" << JsonString(item.dispatch_argument) << ","
        << "\"requester\":" << JsonString(item.dispatch_requester) << ","
        << "\"worker\":" << JsonString(item.dispatch_worker)
        << "},"
        << "\"stack_summary\":" << JsonString(item.stack_summary)
        << "}";
}

static void WriteNetworkUseObservationJson(std::ofstream& output, const NetworkUseObservation& item) {
    output
        << "{"
        << "\"event_index\":" << item.event_index << ","
        << "\"pid\":" << item.pid << ","
        << "\"tid\":" << item.tid << ","
        << "\"alert\":" << (item.alert ? "true" : "false") << ","
        << "\"score\":" << item.score << ","
        << "\"api_name\":" << JsonString(item.api_name) << ","
        << "\"target\":" << JsonString(item.target_name) << ","
        << "\"network_module\":" << JsonString(item.network_module) << ","
        << "\"caller\":{"
        << "\"address\":\"" << Hex64(item.caller_address) << "\","
        << "\"region_base\":\"" << Hex64(item.caller_region_base) << "\","
        << "\"region_size\":" << item.caller_region_size << ","
        << "\"allocation_base\":\"" << Hex64(item.caller_allocation_base) << "\","
        << "\"allocation_size\":" << item.caller_allocation_size << ","
        << "\"label\":" << JsonString(item.caller_label) << ","
        << "\"module_name\":" << JsonString(item.caller_module_name) << ","
        << "\"module_path\":" << JsonString(item.caller_module_path) << ","
        << "\"protect\":" << JsonString(item.caller_protect) << ","
        << "\"type\":" << JsonString(item.caller_type) << ","
        << "\"import_checked\":" << (item.import_checked ? "true" : "false") << ","
        << "\"imports_network_module\":" << (item.caller_module_imports_network ? "true" : "false")
        << "},"
        << "\"rules\":" << JsonStringArray(item.rules) << ","
        << "\"stack_summary\":" << JsonString(item.stack_summary)
        << "}";
}

static void WriteMemoryAuditFindingJson(std::ofstream& output, const MemoryAuditFinding& item) {
    output
        << "{"
        << "\"event_index\":" << item.event_index << ","
        << "\"pid\":" << item.pid << ","
        << "\"alert\":" << (item.alert ? "true" : "false") << ","
        << "\"score\":" << item.score << ","
        << "\"rule\":" << JsonString(item.rule) << ","
        << "\"confidence\":" << JsonString(item.confidence) << ","
        << "\"address\":\"" << Hex64(item.address) << "\","
        << "\"region_base\":\"" << Hex64(item.region_base) << "\","
        << "\"region_size\":" << item.region_size << ","
        << "\"allocation_base\":\"" << Hex64(item.allocation_base) << "\","
        << "\"allocation_size\":" << item.allocation_size << ","
        << "\"state\":" << JsonString(StateToString(item.state)) << ","
        << "\"protect\":" << JsonString(ProtectToString(item.protect)) << ","
        << "\"type\":" << JsonString(TypeToString(item.type)) << ","
        << "\"private_pages\":" << item.private_pages << ","
        << "\"executable_private_pages\":" << item.executable_private_pages << ","
        << "\"module_name\":" << JsonString(item.module_name) << ","
        << "\"module_path\":" << JsonString(item.module_path) << ","
        << "\"mapped_path\":" << JsonString(item.mapped_path) << ","
        << "\"detail\":" << JsonString(item.detail) << ","
        << "\"dump\":{"
        << "\"present\":" << (item.dumped ? "true" : "false") << ","
        << "\"path\":" << JsonString(item.dump_path)
        << "}"
        << "}";
}

static void WriteByoudTraceRecordJson(std::ofstream& output, const ByoudTraceRecord& item) {
    output
        << "{"
        << "\"event_index\":" << item.event_index << ","
        << "\"pid\":" << item.pid << ","
        << "\"tid\":" << item.tid << ","
        << "\"alert\":" << (item.alert ? "true" : "false") << ","
        << "\"score\":" << item.score << ","
        << "\"rule\":" << JsonString(item.rule) << ","
        << "\"confidence\":" << JsonString(item.confidence) << ","
        << "\"technique\":" << JsonString(item.technique) << ","
        << "\"api_name\":" << JsonString(item.api_name) << ","
        << "\"dll_name\":" << JsonString(item.dll_name) << ","
        << "\"caller_label\":" << JsonString(item.caller_label) << ","
        << "\"module_name\":" << JsonString(item.module_name) << ","
        << "\"module_path\":" << JsonString(item.module_path) << ","
        << "\"section\":" << JsonString(item.section_name) << ","
        << "\"module_base\":\"" << Hex64(item.module_base) << "\","
        << "\"address\":\"" << Hex64(item.address) << "\","
        << "\"rva\":\"" << Hex64(item.rva) << "\","
        << "\"size\":" << item.size << ","
        << "\"old_value\":\"" << Hex64(item.old_value) << "\","
        << "\"new_value\":\"" << Hex64(item.new_value) << "\","
        << "\"detail\":" << JsonString(item.detail)
        << "}";
}

static void WriteShadowStackTraceRecordJson(std::ofstream& output, const ShadowStackTraceRecord& item) {
    output
        << "{"
        << "\"event_index\":" << item.event_index << ","
        << "\"pid\":" << item.pid << ","
        << "\"tid\":" << item.tid << ","
        << "\"alert\":" << (item.alert ? "true" : "false") << ","
        << "\"score\":" << item.score << ","
        << "\"rule\":" << JsonString(item.rule) << ","
        << "\"confidence\":" << JsonString(item.confidence) << ","
        << "\"api_name\":" << JsonString(item.api_name) << ","
        << "\"dll_name\":" << JsonString(item.dll_name) << ","
        << "\"classic_stack\":" << JsonString(item.classic_stack) << ","
        << "\"shadow_stack\":" << JsonString(item.shadow_stack) << ","
        << "\"classic_frame_count\":" << item.classic_frame_count << ","
        << "\"shadow_frame_count\":" << item.shadow_frame_count << ","
        << "\"matched_shadow_frames\":" << item.matched_shadow_frames << ","
        << "\"missing_or_out_of_order_frames\":" << item.missing_or_out_of_order_frames << ","
        << "\"hidden_frame\":{"
        << "\"address\":\"" << Hex64(item.hidden_frame_address) << "\","
        << "\"label\":" << JsonString(item.hidden_frame_label) << ","
        << "\"module\":" << JsonString(item.hidden_frame_module) << ","
        << "\"path\":" << JsonString(item.hidden_frame_path)
        << "},"
        << "\"detail\":" << JsonString(item.detail)
        << "}";
}

static uint64_t ModuleIntegrityScanCount(const RunState& state) {
    uint64_t total = state.module_integrity_cache.size();
    for (const auto& item : state.processes) {
        total += item.second.module_integrity_cache.size();
    }
    return total;
}

static void WriteDecisionCountsJson(std::ofstream& output, const std::map<std::wstring, uint64_t>& counts) {
    output << "{";
    bool first = true;
    for (const auto& item : counts) {
        if (!first) {
            output << ",";
        }
        first = false;
        output << JsonString(item.first) << ":" << item.second;
    }
    output << "}";
}

static void WriteByoudTraceReport(const RunState& state) {
    std::ofstream output(state.out_dir / L"byoud_trace.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"enabled\":" << (state.rules.byoud_trace ? "true" : "false") << ","
        << "\"findings_total\":" << state.byoud_trace_total << ","
        << "\"alerts_total\":" << state.byoud_alerts_total << ","
        << "\"findings\":[";
    for (size_t i = 0; i < state.byoud_trace_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteByoudTraceRecordJson(output, state.byoud_trace_records[i]);
    }
    output << "],\"processes\":[";
    bool first_process = true;
    for (const auto& item : state.processes) {
        const ProcessState& process = item.second;
        if (!first_process) {
            output << ",";
        }
        first_process = false;
        output << "{"
            << "\"pid\":" << process.pid << ","
            << "\"name\":" << JsonString(process.name) << ","
            << "\"findings_total\":" << process.byoud_trace_total << ","
            << "\"alerts_total\":" << process.byoud_alerts_total << ","
            << "\"findings\":[";
        for (size_t i = 0; i < process.byoud_trace_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteByoudTraceRecordJson(output, process.byoud_trace_records[i]);
        }
        output << "]}";
    }
    output << "]}";
}

static void WriteShadowStackTraceReport(const RunState& state) {
    std::ofstream output(state.out_dir / L"shadow_stack_trace.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"enabled\":" << (state.rules.shadow_stack ? "true" : "false") << ","
        << "\"sensitive_events\":" << state.shadow_stack_sensitive_events << ","
        << "\"frame_records\":" << state.shadow_stack_frame_records << ","
        << "\"findings_total\":" << state.shadow_stack_total << ","
        << "\"alerts_total\":" << state.shadow_stack_alerts_total << ","
        << "\"findings\":[";
    for (size_t i = 0; i < state.shadow_stack_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteShadowStackTraceRecordJson(output, state.shadow_stack_records[i]);
    }
    output << "],\"processes\":[";
    bool first_process = true;
    for (const auto& item : state.processes) {
        const ProcessState& process = item.second;
        if (!first_process) {
            output << ",";
        }
        first_process = false;
        output << "{"
            << "\"pid\":" << process.pid << ","
            << "\"name\":" << JsonString(process.name) << ","
            << "\"sensitive_events\":" << process.shadow_stack_sensitive_events << ","
            << "\"frame_records\":" << process.shadow_stack_frame_records << ","
            << "\"findings_total\":" << process.shadow_stack_total << ","
            << "\"alerts_total\":" << process.shadow_stack_alerts_total << ","
            << "\"findings\":[";
        for (size_t i = 0; i < process.shadow_stack_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteShadowStackTraceRecordJson(output, process.shadow_stack_records[i]);
        }
        output << "]}";
    }
    output << "]}";
}

static void WriteNetworkTraceReport(const RunState& state) {
    std::ofstream output(state.out_dir / L"network_trace.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"enabled\":" << (state.rules.network_use_trace ? "true" : "false") << ","
        << "\"events_total\":" << state.network_use_total << ","
        << "\"alerts_total\":" << state.network_use_alerts_total << ","
        << "\"events\":[";
    for (size_t i = 0; i < state.network_use_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteNetworkUseObservationJson(output, state.network_use_records[i]);
    }
    output << "],\"processes\":[";
    bool first_process = true;
    for (const auto& item : state.processes) {
        const ProcessState& process = item.second;
        if (!first_process) {
            output << ",";
        }
        first_process = false;
        output << "{"
            << "\"pid\":" << process.pid << ","
            << "\"name\":" << JsonString(process.name) << ","
            << "\"events_total\":" << process.network_use_total << ","
            << "\"alerts_total\":" << process.network_use_alerts_total << ","
            << "\"events\":[";
        for (size_t i = 0; i < process.network_use_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteNetworkUseObservationJson(output, process.network_use_records[i]);
        }
        output << "]}";
    }
    output << "]}";
}

static void WriteMemoryAuditReport(const RunState& state) {
    std::ofstream output(state.out_dir / L"memory_audit.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"enabled\":" << (state.rules.memory_audit ? "true" : "false") << ","
        << "\"findings_total\":" << state.memory_audit_findings_total << ","
        << "\"alerts_total\":" << state.memory_audit_alerts_total << ","
        << "\"findings\":[";
    for (size_t i = 0; i < state.memory_audit_findings.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteMemoryAuditFindingJson(output, state.memory_audit_findings[i]);
    }
    output << "],\"processes\":[";
    bool first_process = true;
    for (const auto& item : state.processes) {
        const ProcessState& process = item.second;
        if (!first_process) {
            output << ",";
        }
        first_process = false;
        output << "{"
            << "\"pid\":" << process.pid << ","
            << "\"name\":" << JsonString(process.name) << ","
            << "\"completed\":" << (process.memory_audit_completed ? "true" : "false") << ","
            << "\"findings_total\":" << process.memory_audit_findings_total << ","
            << "\"alerts_total\":" << process.memory_audit_alerts_total << ","
            << "\"findings\":[";
        for (size_t i = 0; i < process.memory_audit_findings.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteMemoryAuditFindingJson(output, process.memory_audit_findings[i]);
        }
        output << "]}";
    }
    output << "]}";
}

static void WriteMemoryReport(const RunState& state) {
    std::ofstream output(state.out_dir / L"memory.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"pid\":" << state.pid << ","
        << "\"origin_region_total\":" << state.origin_regions_total << ","
        << "\"memory_audit_findings_total\":" << state.memory_audit_findings_total << ","
        << "\"memory_audit_alerts_total\":" << state.memory_audit_alerts_total << ","
        << "\"byoud_trace_total\":" << state.byoud_trace_total << ","
        << "\"byoud_alerts_total\":" << state.byoud_alerts_total << ","
        << "\"shadow_stack_sensitive_events\":" << state.shadow_stack_sensitive_events << ","
        << "\"shadow_stack_frame_records\":" << state.shadow_stack_frame_records << ","
        << "\"shadow_stack_total\":" << state.shadow_stack_total << ","
        << "\"shadow_stack_alerts_total\":" << state.shadow_stack_alerts_total << ","
        << "\"network_use_total\":" << state.network_use_total << ","
        << "\"network_use_alerts_total\":" << state.network_use_alerts_total << ","
        << "\"dll_loads\":[";
    for (size_t i = 0; i < state.dll_load_memory.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteDllLoadMemoryObservationJson(output, state.dll_load_memory[i]);
    }
    output << "],"
        << "\"byoud_trace\":[";
    for (size_t i = 0; i < state.byoud_trace_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteByoudTraceRecordJson(output, state.byoud_trace_records[i]);
    }
    output << "],"
        << "\"network_use\":[";
    for (size_t i = 0; i < state.network_use_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteNetworkUseObservationJson(output, state.network_use_records[i]);
    }
    output << "],"
        << "\"shadow_stack_trace\":[";
    for (size_t i = 0; i < state.shadow_stack_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteShadowStackTraceRecordJson(output, state.shadow_stack_records[i]);
    }
    output << "],"
        << "\"processes\":[";
    bool first_process = true;
    for (const auto& item : state.processes) {
        const ProcessState& process = item.second;
        if (!first_process) {
            output << ",";
        }
        first_process = false;
        output << "{"
            << "\"pid\":" << process.pid << ","
            << "\"name\":" << JsonString(process.name) << ","
            << "\"out_dir\":" << JsonString(process.out_dir.wstring()) << ","
            << "\"events_total\":" << process.events_total << ","
            << "\"alerts_total\":" << process.alerts_total << ","
            << "\"dumps_total\":" << process.dumps_total << ","
            << "\"origin_region_total\":" << process.origin_regions_total << ","
            << "\"memory_audit_findings_total\":" << process.memory_audit_findings_total << ","
            << "\"memory_audit_alerts_total\":" << process.memory_audit_alerts_total << ","
            << "\"byoud_trace_total\":" << process.byoud_trace_total << ","
            << "\"byoud_alerts_total\":" << process.byoud_alerts_total << ","
            << "\"shadow_stack_sensitive_events\":" << process.shadow_stack_sensitive_events << ","
            << "\"shadow_stack_frame_records\":" << process.shadow_stack_frame_records << ","
            << "\"shadow_stack_total\":" << process.shadow_stack_total << ","
            << "\"shadow_stack_alerts_total\":" << process.shadow_stack_alerts_total << ","
            << "\"network_use_total\":" << process.network_use_total << ","
            << "\"network_use_alerts_total\":" << process.network_use_alerts_total << ","
            << "\"dll_loads\":[";
        for (size_t i = 0; i < process.dll_load_memory.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteDllLoadMemoryObservationJson(output, process.dll_load_memory[i]);
        }
        output << "],"
            << "\"network_use\":[";
        for (size_t i = 0; i < process.network_use_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteNetworkUseObservationJson(output, process.network_use_records[i]);
        }
        output << "],"
            << "\"shadow_stack_trace\":[";
        for (size_t i = 0; i < process.shadow_stack_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteShadowStackTraceRecordJson(output, process.shadow_stack_records[i]);
        }
        output << "],"
            << "\"byoud_trace\":[";
        for (size_t i = 0; i < process.byoud_trace_records.size(); ++i) {
            if (i) {
                output << ",";
            }
            WriteByoudTraceRecordJson(output, process.byoud_trace_records[i]);
        }
        output << "]"
            << "}";
    }
    output << "]}";
}

static void WriteSummary(const RunState& state, DWORD exit_code, bool timed_out, bool detached) {
    std::ofstream output(state.out_dir / L"summary.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output
        << "{"
        << "\"pid\":" << state.pid << ","
        << "\"analysis_profile\":" << JsonString(AnalysisProfileName(state.profile)) << ","
        << "\"origin_trace\":" << (state.rules.origin_trace ? "true" : "false") << ","
        << "\"register_trace\":" << (state.rules.register_trace ? "true" : "false") << ","
        << "\"dispatch_trace\":" << (state.rules.dispatch_trace ? "true" : "false") << ","
        << "\"follow_remote\":" << (state.rules.follow_remote ? "true" : "false") << ","
        << "\"net_reset\":" << (state.rules.net_reset ? "true" : "false") << ","
        << "\"etw_telemetry\":" << (state.rules.etw_telemetry ? "true" : "false") << ","
        << "\"memory_audit\":" << (state.rules.memory_audit ? "true" : "false") << ","
        << "\"byoud_trace\":" << (state.rules.byoud_trace ? "true" : "false") << ","
        << "\"shadow_stack\":" << (state.rules.shadow_stack ? "true" : "false") << ","
        << "\"network_use_trace\":" << (state.rules.network_use_trace ? "true" : "false") << ","
        << "\"etw_status\":" << JsonString(state.etw_status) << ","
        << "\"etw_error\":" << JsonString(state.etw_error) << ","
        << "\"etw_events_total\":" << state.etw_events_total << ","
        << "\"etw_process_events\":" << state.etw_process_events << ","
        << "\"etw_thread_events\":" << state.etw_thread_events << ","
        << "\"etw_image_loads\":" << state.etw_image_loads << ","
        << "\"ldr_integrity\":" << (state.rules.ldr_integrity ? "true" : "false") << ","
        << "\"auto_enter\":" << (state.auto_enter ? "true" : "false") << ","
        << "\"auto_enter_interval_ms\":" << state.auto_enter_interval_ms << ","
        << "\"keep_alive\":" << (state.keep_alive ? "true" : "false") << ","
        << "\"detached\":" << (detached ? "true" : "false") << ","
        << "\"exit_code\":" << exit_code << ","
        << "\"timed_out\":" << (timed_out ? "true" : "false") << ","
        << "\"target_crashed\":" << (!timed_out && exit_code >= 0xC0000000 ? "true" : "false") << ","
        << "\"events_total\":" << state.events_total << ","
        << "\"alerts_total\":" << state.alerts_total << ","
        << "\"dumps_total\":" << state.dumps_total << ","
        << "\"origin_region_total\":" << state.origin_regions_total << ","
        << "\"memory_audit_findings_total\":" << state.memory_audit_findings_total << ","
        << "\"memory_audit_alerts_total\":" << state.memory_audit_alerts_total << ","
        << "\"byoud_trace_total\":" << state.byoud_trace_total << ","
        << "\"byoud_alerts_total\":" << state.byoud_alerts_total << ","
        << "\"shadow_stack_total\":" << state.shadow_stack_total << ","
        << "\"shadow_stack_alerts_total\":" << state.shadow_stack_alerts_total << ","
        << "\"network_use_total\":" << state.network_use_total << ","
        << "\"network_use_alerts_total\":" << state.network_use_alerts_total << ","
        << "\"unbacked_total\":" << state.unbacked_total << ","
        << "\"modified_image_total\":" << state.modified_image_total << ","
        << "\"unwind_tamper_total\":" << state.unwind_tamper_total << ","
        << "\"callsite_anomaly_total\":" << state.callsite_anomaly_total << ","
        << "\"memory_api_alert_total\":" << state.memory_api_alert_total << ","
        << "\"unwind_alert_total\":" << state.unwind_alert_total << ","
        << "\"embedded_pe_total\":" << state.embedded_pe_total << ","
        << "\"sleep_alert_total\":" << state.sleep_alert_total << ","
        << "\"callback_alert_total\":" << state.callback_alert_total << ","
        << "\"ldr_tamper_total\":" << state.ldr_tamper_total << ","
        << "\"module_integrity_scanned\":" << ModuleIntegrityScanCount(state) << ","
        << "\"decision_counts\":";
    WriteDecisionCountsJson(output, state.decision_counts);
    output
        << ","
        << "\"sensitive_modules\":" << JsonStringArray(state.rules.sensitive_modules) << ","
        << "\"children\":[";
    bool first_child = true;
    for (const auto& item : state.processes) {
        const ProcessState& child = item.second;
        if (child.pid == state.pid) {
            continue;
        }
        if (!first_child) {
            output << ",";
        }
        first_child = false;
        output << "{"
            << "\"pid\":" << child.pid << ","
            << "\"name\":" << JsonString(child.name) << ","
            << "\"out_dir\":" << JsonString(child.out_dir.wstring()) << ","
            << "\"events_total\":" << child.events_total << ","
            << "\"alerts_total\":" << child.alerts_total << ","
            << "\"dumps_total\":" << child.dumps_total << ","
            << "\"origin_region_total\":" << child.origin_regions_total << ","
            << "\"memory_audit_completed\":" << (child.memory_audit_completed ? "true" : "false") << ","
            << "\"memory_audit_findings_total\":" << child.memory_audit_findings_total << ","
            << "\"memory_audit_alerts_total\":" << child.memory_audit_alerts_total << ","
            << "\"byoud_trace_total\":" << child.byoud_trace_total << ","
            << "\"byoud_alerts_total\":" << child.byoud_alerts_total << ","
            << "\"shadow_stack_sensitive_events\":" << child.shadow_stack_sensitive_events << ","
            << "\"shadow_stack_frame_records\":" << child.shadow_stack_frame_records << ","
            << "\"shadow_stack_total\":" << child.shadow_stack_total << ","
            << "\"shadow_stack_alerts_total\":" << child.shadow_stack_alerts_total << ","
            << "\"network_use_total\":" << child.network_use_total << ","
            << "\"network_use_alerts_total\":" << child.network_use_alerts_total << ","
            << "\"preloaded_network_modules\":" << JsonStringArray(child.preloaded_network_modules) << ","
            << "\"decision_counts\":";
        WriteDecisionCountsJson(output, child.decision_counts);
        output << "}";
    }
    output << "],"
        << "\"dll_load_memory\":[";
    for (size_t i = 0; i < state.dll_load_memory.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteDllLoadMemoryObservationJson(output, state.dll_load_memory[i]);
    }
    output
        << "]"
        << ",\"network_use\":[";
    for (size_t i = 0; i < state.network_use_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteNetworkUseObservationJson(output, state.network_use_records[i]);
    }
    output
        << "]"
        << ",\"byoud_trace\":[";
    for (size_t i = 0; i < state.byoud_trace_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteByoudTraceRecordJson(output, state.byoud_trace_records[i]);
    }
    output
        << "]"
        << ",\"shadow_stack_trace\":[";
    for (size_t i = 0; i < state.shadow_stack_records.size(); ++i) {
        if (i) {
            output << ",";
        }
        WriteShadowStackTraceRecordJson(output, state.shadow_stack_records[i]);
    }
    output
        << "]"
        << "}";
}

