static bool ParseUiModeValue(const std::wstring& value, UiMode& mode) {
    const std::wstring lower = ToLower(value);
    if (lower == L"auto") {
        mode = UiMode::Auto;
    } else if (lower == L"live") {
        mode = UiMode::Live;
    } else if (lower == L"plain") {
        mode = UiMode::Plain;
    } else if (lower == L"quiet") {
        mode = UiMode::Quiet;
    } else {
        return false;
    }
    return true;
}

static bool ParseUiThemeValue(const std::wstring& value, UiTheme& theme) {
    const std::wstring lower = ToLower(value);
    if (lower == L"dark") {
        theme = UiTheme::Dark;
    } else if (lower == L"mono") {
        theme = UiTheme::Mono;
    } else {
        return false;
    }
    return true;
}

static bool ParseProfileValue(const std::wstring& value, AnalysisProfile& profile) {
    const std::wstring lower = ToLower(value);
    if (lower == L"default" || lower == L"custom") {
        profile = AnalysisProfile::Default;
    } else if (lower == L"quick") {
        profile = AnalysisProfile::Quick;
    } else if (lower == L"deep") {
        profile = AnalysisProfile::Deep;
    } else if (lower == L"max" || lower == L"lab") {
        profile = AnalysisProfile::Max;
    } else {
        return false;
    }
    return true;
}

static bool IsArg(const std::wstring& arg, std::initializer_list<const wchar_t*> names) {
    const std::wstring lower = ToLower(arg);
    for (const wchar_t* name : names) {
        if (lower == name) {
            return true;
        }
    }
    return false;
}

static bool LooksLikeOption(const std::wstring& arg) {
    return !arg.empty() && (arg[0] == L'-' || arg[0] == L'/');
}

static bool HelpColorEnabled() {
    static bool initialized = false;
    static bool enabled = false;
    if (!initialized) {
        initialized = true;
        const HANDLE output = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD mode = 0;
        enabled = output != INVALID_HANDLE_VALUE &&
            GetFileType(output) == FILE_TYPE_CHAR &&
            GetConsoleMode(output, &mode);
        if (enabled) {
            SetConsoleMode(output, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
        }
    }
    return enabled;
}

static std::wstring HelpPaint(const std::wstring& text, const wchar_t* code) {
    if (!HelpColorEnabled()) {
        return text;
    }
    return std::wstring(L"\x1b[") + code + L"m" + text + L"\x1b[0m";
}

static std::wstring HelpOption(const wchar_t* text) {
    return HelpPaint(text, L"32;1");
}

static std::wstring HelpSection(const wchar_t* text) {
    return HelpPaint(text, L"36;1");
}

static void PrintBanner(bool ascii_art = true) {
    if (ascii_art) {
        std::wcout
            << HelpPaint(L"   _____ _             _     _____            _              \n", L"36;1")
            << HelpPaint(L"  / ____| |           | |   / ____|          | |             \n", L"36;1")
            << HelpPaint(L" | (___ | |_ __ _  ___| | _| (___   ___ _ __ | |_ _ __ _   _ \n", L"36;1")
            << HelpPaint(L"  \\___ \\| __/ _` |/ __| |/ /\\___ \\ / _ \\ '_ \\| __| '__| | | |\n", L"36;1")
            << HelpPaint(L"  ____) | || (_| | (__|   < ____) |  __/ | | | |_| |  | |_| |\n", L"36;1")
            << HelpPaint(L" |_____/ \\__\\__,_|\\___|_|\\_\\_____/ \\___|_| |_|\\__|_|   \\__, |\n", L"36;1")
            << HelpPaint(L"                                                        __/ |\n", L"36;1")
            << HelpPaint(L"                                                       |___/ \n\n", L"36;1");
    }

    std::wcout
        << HelpPaint(L"StackSentry v0.8 (x64)\n", L"37;1")
        << HelpPaint(L"Author: Vithor Schirmer\n", L"90")
        << L"Memory triage and call-stack based malware research tool.\n\n";
}

static void PrintVersion() {
    PrintBanner();
}

static void PrintRequiredUsage() {
    std::wcout
        << HelpSection(L"REQUIRED") << L"\n\n"
        << HelpOption(L"/run <target.exe>") << L"\n"
        << L"         : Start the target suspended, inject the monitor, then resume it.\n\n";
}

static void PrintMasterProfilesUsage() {
    std::wcout
        << HelpSection(L"MASTER PROFILES") << L"\n\n"
        << HelpOption(L"/quick") << L"\n"
        << L"         : Low-noise DLL-load triage profile. Good first run for new users.\n"
        << HelpOption(L"/deep") << L"\n"
        << L"         : DLL-load hunting profile with callback, unwind, and LDR integrity telemetry. Memory API hooks stay opt-in.\n"
        << HelpOption(L"/max") << L"\n"
        << L"         : Strongest DLL-load profile. Enables deep telemetry, stack audit, and auto-enter, not /mem.\n"
        << HelpOption(L"/profile <quick|deep|max>") << L"\n"
        << L"         : Select a master profile by name.\n\n";
}

static void PrintExamplesUsage() {
    std::wcout
        << HelpSection(L"EXAMPLES") << L"\n\n"
        << L"StackSentry64.exe /run target.exe /quick /out out\\target /timeout 5000\n"
        << L"StackSentry64.exe /run samples\\sample_00_pic_runner.exe /max /hunt /no-target-output /out out\\byoud /timeout 15000 -- samples\\payload_12_byoud_rdi.bin\n"
        << L"StackSentry64.exe /run target.exe /max /timeout 10000 /keep-alive\n"
        << L"StackSentry64.exe /run samples\\sample_03_text_section_proxy.exe /max /hunt /no-target-output /timeout 9000\n\n";
}

static void PrintRecommendedStartUsage() {
    std::wcout
        << HelpSection(L"RECOMMENDED START") << L"\n\n"
        << L"First safe pass:\n"
        << L"  StackSentry64.exe /run sample.exe /quick /no-target-output /timeout 5000\n\n"
        << L"Strong default for suspicious loaders:\n"
        << L"  StackSentry64.exe /run sample.exe /max /no-target-output /timeout 10000\n\n"
        << L"Advanced anti-evasion hunt:\n"
        << L"  StackSentry64.exe /run sample.exe /max /hunt /no-target-output /timeout 15000\n\n"
        << L"Hidden proxy/gadget origin:\n"
        << L"  StackSentry64.exe /run sample.exe /max /regtrace /no-target-output /timeout 10000\n\n"
        << L"Loader that injects into another process:\n"
        << L"  StackSentry64.exe /run loader.exe /max /follow-remote /regtrace /timeout 15000\n\n"
        << L"Memory-state audit for hollowing/artifacts:\n"
        << L"  StackSentry64.exe /run sample.exe /max /memory-audit /no-target-output /timeout 10000\n\n";
}

static void PrintQuickUsage() {
    PrintBanner();
    PrintRequiredUsage();
    PrintMasterProfilesUsage();
    PrintExamplesUsage();
    std::wcout
        << HelpSection(L"INFO") << L"\n\n"
        << HelpOption(L"/help, /?, -h") << L"\n"
        << L"         : Show full help.\n"
        << HelpOption(L"/features") << L"\n"
        << L"         : Show all optional hooks and advanced features.\n"
        << HelpOption(L"/version") << L"\n"
        << L"         : Show version and credits.\n";
}

static void PrintFullHelp() {
    PrintBanner();
    PrintRequiredUsage();
    PrintMasterProfilesUsage();
    PrintExamplesUsage();
    PrintRecommendedStartUsage();
    std::wcout
        << HelpSection(L"COMMON OPTIONS") << L"\n\n"
        << HelpOption(L"/out <dir>") << L"\n"
        << L"         : Output directory. Default: out\\run\n"
        << HelpOption(L"/timeout <ms>") << L"\n"
        << L"         : Terminate the target after N ms. Useful for samples waiting for Enter.\n"
        << HelpOption(L"/keep-alive") << L"\n"
        << L"         : On timeout, stop collecting and leave the target process running for inspection.\n"
        << HelpOption(L"/auto-enter") << L"\n"
        << L"         : Feed Enter to the target console/stdin periodically. Enabled by default in /max.\n"
        << HelpOption(L"/auto-enter-ms <ms>") << L"\n"
        << L"         : Interval for /auto-enter. Default: 1000 ms.\n"
        << HelpOption(L"/no-auto-enter") << L"\n"
        << L"         : Disable automatic stdin Enter feeding, even in /max.\n"
        << HelpOption(L"/verbose") << L"\n"
        << L"         : Print non-alerted events and disable console aggregation.\n\n"
        << HelpSection(L"OUTPUT STYLE") << L"\n\n"
        << HelpOption(L"/no-target-output") << L"\n"
        << L"         : Suppress stdout/stderr from the target process in the StackSentry console.\n"
        << HelpOption(L"/full-stack") << L"\n"
        << L"         : Print stack frames one per line with module offsets; disables stack-frame compression.\n"
        << HelpOption(L"/inline-stack") << L"\n"
        << L"         : Print the full stack in one line without repeated-frame compression.\n"
        << HelpOption(L"/quiet") << L"\n"
        << L"         : Suppress console UI; write artifacts only.\n"
        << HelpOption(L"/plain") << L"\n"
        << L"         : Simple non-animated output.\n"
        << HelpOption(L"/live") << L"\n"
        << L"         : Colored/animated output when the terminal supports it.\n"
        << HelpOption(L"/no-color") << L"\n"
        << L"         : Disable ANSI colors.\n\n"
        << HelpSection(L"HUNT PRESET") << L"\n\n"
        << HelpOption(L"/hunt") << L"\n"
        << L"         : Advanced anti-evasion bundle: /regtrace, /stack-audit, /memory-audit,\n"
        << L"           /byoud-trace, and /ldr-integrity. Network API tracing stays explicit.\n\n"
        << HelpSection(L"ORIGIN / PROXY ANALYSIS") << L"\n\n"
        << HelpOption(L"/origin-trace") << L"\n"
        << L"         : Correlate DLL loads with recent callback/thread/APC context.\n"
        << HelpOption(L"/regtrace") << L"\n"
        << L"         : Find hidden caller/origin behind clean proxy/gadget DLL loads. Implies /origin-trace.\n"
        << HelpOption(L"/proxy-trace") << L"\n"
        << L"         : Alias for /origin-trace /regtrace.\n"
        << HelpOption(L"/dispatch-trace") << L"\n"
        << L"         : Detect function-proxy dispatch patterns such as MassDriver.\n"
        << HelpOption(L"/threadpool-chain-trace") << L"\n"
        << L"         : Detect threadpool callback-chain proxy loading.\n\n"
        << HelpSection(L"NETWORK USE ANALYSIS") << L"\n\n"
        << HelpOption(L"/network-use-trace") << L"\n"
        << L"         : Trace network DLL API use and attribute suspicious callers. Not included in /hunt.\n"
        << HelpOption(L"/net-use-trace") << L"\n"
        << L"         : Alias for /network-use-trace.\n\n"
        << HelpSection(L"REMOTE / MULTI-PROCESS") << L"\n\n"
        << HelpOption(L"/follow-remote") << L"\n"
        << L"         : Follow loaders that inject payloads into another process.\n"
        << HelpOption(L"/net-reset") << L"\n"
        << L"         : Try to unload watched network DLLs and observe suspicious reloads.\n\n"
        << HelpSection(L"EXTRA TELEMETRY / INTEGRITY") << L"\n\n"
        << HelpOption(L"/etw") << L"\n"
        << L"         : Collect kernel process/thread/image-load timeline for target and children.\n"
        << HelpOption(L"/ldr-integrity") << L"\n"
        << L"         : Validate PEB loader EntryPoint/OriginalBase metadata for EntryPoint hijacking.\n"
        << HelpOption(L"/unwind") << L"\n"
        << L"         : Enable Rtl*FunctionTable hooks and unwind metadata integrity checks.\n"
        << HelpOption(L"/stack-audit") << L"\n"
        << L"         : Strict stack spoofing audit for DLL-load return frames and synthetic stacks. Enabled by /max.\n\n"
        << HelpOption(L"/memory-audit") << L"\n"
        << L"         : Moneta-inspired memory-state and temporal image audit for hollowing, stomping, and orphan executable regions.\n\n"
        << HelpOption(L"/byoud-trace") << L"\n"
        << L"         : Lab mode: detect BYOUD/unwind metadata spoofing around sensitive DLL loads.\n\n"
        << HelpOption(L"/shadow-stack") << L"\n"
        << L"         : Research-only CET/HSP sequence comparison. Experimental; not validated; not included in /hunt.\n\n"
        << HelpSection(L"AGGRESSIVE / LOW-LEVEL HOOKS") << L"\n\n"
        << HelpOption(L"/mem") << L"\n"
        << L"         : Very noisy memory/API telemetry. Use only when needed.\n"
        << HelpOption(L"/tp") << L"\n"
        << L"         : Enable TpAllocWork/TpPostWork hooks. Aggressive; may destabilize some targets.\n"
        << HelpOption(L"/wait") << L"\n"
        << L"         : Enable WaitFor* hooks. Aggressive; may destabilize some targets.\n"
        << HelpOption(L"/xhooks") << L"\n"
        << L"         : Enable stable callback/thread-start hooks directly.\n\n"
        << HelpSection(L"ADVANCED CONFIG") << L"\n\n"
        << HelpOption(L"/rules <rules.json>") << L"\n"
        << L"         : Use a custom rules/config file. Default: built-in rules.\n\n"
        << HelpSection(L"INFO") << L"\n\n"
        << HelpOption(L"/help, /?, -h") << L"\n"
        << L"         : Show full help.\n"
        << HelpOption(L"/features") << L"\n"
        << L"         : Show all optional hooks and advanced features.\n"
        << HelpOption(L"/version") << L"\n"
        << L"         : Show version and credits.\n\n";
    std::wcout << HelpPaint(L"Compatibility:", L"90")
        << L" -e, --out, --rules, --timeout-ms, and --experimental-hooks still work.\n";
}

static bool ParseOptions(int argc, wchar_t** argv, Options& options) {
    if (argc <= 1) {
        PrintQuickUsage();
        options.exit_after_parse = true;
        options.parse_exit_code = 0;
        return true;
    }

    bool after_separator = false;
    for (int i = 1; i < argc; ++i) {
        std::wstring arg = argv[i];
        if (after_separator) {
            options.target_args.push_back(arg);
            continue;
        }

        if (arg == L"--") {
            after_separator = true;
        } else if (IsArg(arg, { L"-h", L"--help", L"/help", L"/?", L"--features", L"/features" })) {
            PrintFullHelp();
            options.exit_after_parse = true;
            options.parse_exit_code = 0;
            return true;
        } else if (IsArg(arg, { L"/version", L"--version" })) {
            PrintVersion();
            options.exit_after_parse = true;
            options.parse_exit_code = 0;
            return true;
        } else if (IsArg(arg, { L"-e", L"/e", L"/run", L"/target" }) && i + 1 < argc) {
            options.target = argv[++i];
        } else if (IsArg(arg, { L"--rules", L"/rules" }) && i + 1 < argc) {
            options.rules_path = argv[++i];
        } else if (IsArg(arg, { L"--out", L"/out", L"/dir" }) && i + 1 < argc) {
            options.out_dir = argv[++i];
        } else if (IsArg(arg, { L"--timeout-ms", L"/timeout", L"/timeout-ms" }) && i + 1 < argc) {
            options.timeout_ms = static_cast<uint32_t>(wcstoul(argv[++i], nullptr, 10));
        } else if (IsArg(arg, { L"--keep-alive", L"/keep-alive", L"/leave-running", L"/no-kill" })) {
            options.keep_alive = true;
        } else if (IsArg(arg, { L"--auto-enter", L"/auto-enter", L"/enter" })) {
            options.auto_enter = true;
            options.auto_enter_configured = true;
        } else if (IsArg(arg, { L"--no-auto-enter", L"/no-auto-enter", L"/no-enter" })) {
            options.auto_enter = false;
            options.auto_enter_configured = true;
        } else if (IsArg(arg, { L"--auto-enter-ms", L"/auto-enter-ms", L"/enter-ms" }) && i + 1 < argc) {
            options.auto_enter_interval_ms = static_cast<uint32_t>(wcstoul(argv[++i], nullptr, 10));
            options.auto_enter = true;
            options.auto_enter_configured = true;
        } else if (IsArg(arg, { L"--profile", L"/profile" }) && i + 1 < argc) {
            if (!ParseProfileValue(argv[++i], options.profile)) {
                std::wcerr << L"[!] Invalid /profile value\n";
                PrintFullHelp();
                return false;
            }
        } else if (IsArg(arg, { L"--quick", L"/quick" })) {
            options.profile = AnalysisProfile::Quick;
        } else if (IsArg(arg, { L"--deep", L"/deep" })) {
            options.profile = AnalysisProfile::Deep;
        } else if (IsArg(arg, { L"--max", L"/max", L"/lab" })) {
            options.profile = AnalysisProfile::Max;
        } else if (IsArg(arg, { L"--hunt", L"/hunt" })) {
            options.hunt = true;
        } else if (IsArg(arg, { L"--ui", L"/ui" }) && i + 1 < argc) {
            if (!ParseUiModeValue(argv[++i], options.ui_mode)) {
                std::wcerr << L"[!] Invalid --ui value\n";
                PrintFullHelp();
                return false;
            }
        } else if (IsArg(arg, { L"--theme", L"/theme" }) && i + 1 < argc) {
            if (!ParseUiThemeValue(argv[++i], options.ui_theme)) {
                std::wcerr << L"[!] Invalid --theme value\n";
                PrintFullHelp();
                return false;
            }
        } else if (IsArg(arg, { L"--quiet", L"/quiet", L"/q" })) {
            options.ui_mode = UiMode::Quiet;
        } else if (IsArg(arg, { L"/plain" })) {
            options.ui_mode = UiMode::Plain;
        } else if (IsArg(arg, { L"/live" })) {
            options.ui_mode = UiMode::Live;
        } else if (IsArg(arg, { L"--no-color", L"/no-color" })) {
            options.no_color = true;
        } else if (IsArg(arg, { L"--no-animate", L"/no-animate" })) {
            options.no_animate = true;
        } else if (IsArg(arg, { L"--verbose", L"/verbose", L"/v" })) {
            options.verbose = true;
        } else if (IsArg(arg, { L"--full-stack", L"/full-stack" })) {
            options.full_stack = true;
        } else if (IsArg(arg, { L"--inline-stack", L"/inline-stack", L"/flat-stack", L"/raw-stack", L"/no-stack-compact" })) {
            options.inline_stack = true;
        } else if (IsArg(arg, { L"--no-target-output", L"/no-target-output", L"/mute-target", L"/target-quiet" })) {
            options.suppress_target_output = true;
        } else if (IsArg(arg, { L"--experimental-hooks", L"/xhooks", L"/experimental" })) {
            options.experimental_hooks = true;
        } else if (IsArg(arg, { L"--memory-hooks", L"/mem", L"/memory" })) {
            options.memory_hooks = true;
        } else if (IsArg(arg, { L"--unwind-hooks", L"/unwind" })) {
            options.unwind_hooks = true;
        } else if (IsArg(arg, { L"--thread-start-hooks", L"/thread" })) {
            options.thread_start_hooks = true;
        } else if (IsArg(arg, { L"--threadpool-hooks", L"/tp", L"/threadpool" })) {
            options.threadpool_hooks = true;
        } else if (IsArg(arg, { L"--wait-hooks", L"/wait" })) {
            options.wait_hooks = true;
        } else if (IsArg(arg, { L"--origin-trace", L"/origin-trace", L"/origin" })) {
            options.origin_trace = true;
        } else if (IsArg(arg, { L"--regtrace", L"/regtrace", L"/register-trace" })) {
            options.origin_trace = true;
            options.register_trace = true;
        } else if (IsArg(arg, { L"--proxy-trace", L"/proxy-trace" })) {
            options.origin_trace = true;
            options.register_trace = true;
        } else if (IsArg(arg, { L"--dispatch-trace", L"/dispatch-trace", L"/dispatch" })) {
            options.dispatch_trace = true;
        } else if (IsArg(arg, { L"--threadpool-chain-trace", L"/threadpool-chain-trace", L"/tp-chain" })) {
            options.threadpool_chain_trace = true;
        } else if (IsArg(arg, { L"--stack-audit", L"/stack-audit", L"/audit-stack" })) {
            options.stack_audit = true;
        } else if (IsArg(arg, { L"--memory-audit", L"/memory-audit", L"/image-audit", L"/audit-memory" })) {
            options.memory_audit = true;
        } else if (IsArg(arg, { L"--byoud-trace", L"/byoud-trace", L"/byoud" })) {
            options.byoud_trace = true;
        } else if (IsArg(arg, { L"--shadow-stack", L"/shadow-stack", L"/shadow" })) {
            options.shadow_stack = true;
        } else if (IsArg(arg, { L"--network-use-trace", L"/network-use-trace", L"/net-use-trace", L"/net-use" })) {
            options.network_use_trace = true;
        } else if (IsArg(arg, { L"--follow-remote", L"/follow-remote", L"/remote-follow" })) {
            options.follow_remote = true;
        } else if (IsArg(arg, { L"--net-reset", L"/net-reset" })) {
            options.net_reset = true;
        } else if (IsArg(arg, { L"--etw", L"/etw", L"/etw-timeline" })) {
            options.etw_telemetry = true;
        } else if (IsArg(arg, { L"--ldr-integrity", L"/ldr-integrity", L"/ldr" })) {
            options.ldr_integrity = true;
        } else if (IsArg(arg, { L"/args" })) {
            after_separator = true;
        } else if (options.target.empty() && !LooksLikeOption(arg)) {
            options.target = arg;
        } else {
            std::wcerr << L"[!] Unknown or incomplete argument: " << arg << L"\n";
            PrintFullHelp();
            return false;
        }
    }

    if (options.target.empty()) {
        std::wcerr << L"[!] Missing /run <target.exe>\n";
        PrintFullHelp();
        return false;
    }
    if (options.profile == AnalysisProfile::Max && !options.auto_enter_configured) {
        options.auto_enter = true;
    }
    options.auto_enter_interval_ms = std::clamp<uint32_t>(options.auto_enter_interval_ms, 50, 60000);

    return true;
}

static void ApplyAnalysisProfile(AnalysisProfile profile, Rules& rules) {
    switch (profile) {
    case AnalysisProfile::Quick:
        rules.enable_sleep_hooks = true;
        rules.enable_msgwait_hook = true;
        rules.enable_wait_object_hooks = false;
        rules.enable_thread_start_hooks = false;
        rules.enable_threadpool_hooks = false;
        rules.experimental_hooks = false;
        rules.memory_api_hooks = false;
        rules.unwind_integrity = true;
        rules.unwind_table_hooks = false;
        rules.callsite_validation = true;
        rules.dump_suspicious_regions = true;
        rules.analyze_dumps = true;
        rules.carve_embedded_pe = true;
        rules.long_sleep_ms = std::min<uint32_t>(rules.long_sleep_ms, 1000);
        rules.correlation_window_ms = std::max<uint32_t>(rules.correlation_window_ms, 5000);
        break;
    case AnalysisProfile::Deep:
        rules.enable_sleep_hooks = true;
        rules.enable_msgwait_hook = true;
        rules.enable_wait_object_hooks = false;
        rules.enable_thread_start_hooks = true;
        rules.enable_threadpool_hooks = false;
        rules.experimental_hooks = true;
        rules.memory_api_hooks = false;
        rules.unwind_integrity = true;
        rules.unwind_table_hooks = true;
        rules.ldr_integrity = true;
        rules.callsite_validation = true;
        rules.dump_suspicious_regions = true;
        rules.analyze_dumps = true;
        rules.carve_embedded_pe = true;
        rules.correlation_window_ms = std::max<uint32_t>(rules.correlation_window_ms, 10000);
        break;
    case AnalysisProfile::Max:
        rules.enable_sleep_hooks = true;
        rules.enable_msgwait_hook = true;
        rules.enable_wait_object_hooks = false;
        rules.enable_thread_start_hooks = true;
        rules.enable_threadpool_hooks = false;
        rules.experimental_hooks = true;
        rules.memory_api_hooks = false;
        rules.unwind_integrity = true;
        rules.unwind_table_hooks = true;
        rules.ldr_integrity = true;
        rules.stack_audit = true;
        rules.callsite_validation = true;
        rules.dump_suspicious_regions = true;
        rules.analyze_dumps = true;
        rules.carve_embedded_pe = true;
        rules.correlation_window_ms = std::max<uint32_t>(rules.correlation_window_ms, 15000);
        rules.max_dump_bytes = std::max<uint64_t>(rules.max_dump_bytes, 32ull * 1024ull * 1024ull);
        break;
    default:
        break;
    }
}

static bool ReadTextFile(const fs::path& path, std::string& text) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return false;
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    text = buffer.str();
    return true;
}

static std::string Trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

static bool ExtractStringArray(const std::string& text, const std::string& key, std::vector<std::wstring>& output) {
    const std::string quoted_key = "\"" + key + "\"";
    const size_t key_pos = text.find(quoted_key);
    if (key_pos == std::string::npos) {
        return true;
    }
    const size_t colon = text.find(':', key_pos + quoted_key.size());
    const size_t open = text.find('[', colon);
    const size_t close = text.find(']', open);
    if (colon == std::string::npos || open == std::string::npos || close == std::string::npos) {
        return false;
    }

    std::vector<std::wstring> parsed;
    size_t pos = open + 1;
    while (pos < close) {
        while (pos < close && isspace(static_cast<unsigned char>(text[pos]))) {
            ++pos;
        }
        if (pos < close && text[pos] == ',') {
            ++pos;
            continue;
        }
        if (pos >= close) {
            break;
        }
        if (text[pos] != '"') {
            return false;
        }
        ++pos;
        std::string item;
        while (pos < close) {
            const char ch = text[pos++];
            if (ch == '\\' && pos < close) {
                item.push_back(text[pos++]);
            } else if (ch == '"') {
                break;
            } else {
                item.push_back(ch);
            }
        }
        if (!item.empty()) {
            const int needed = MultiByteToWideChar(CP_UTF8, 0, item.data(), static_cast<int>(item.size()), nullptr, 0);
            std::wstring wide(static_cast<size_t>(needed), L'\0');
            MultiByteToWideChar(CP_UTF8, 0, item.data(), static_cast<int>(item.size()), wide.data(), needed);
            parsed.push_back(ToLower(BasenameOf(wide)));
        }
    }

    output = parsed;
    return true;
}

static bool ExtractBool(const std::string& text, const std::string& key, bool& value) {
    const std::string quoted_key = "\"" + key + "\"";
    const size_t key_pos = text.find(quoted_key);
    if (key_pos == std::string::npos) {
        return true;
    }
    const size_t colon = text.find(':', key_pos + quoted_key.size());
    if (colon == std::string::npos) {
        return false;
    }
    const std::string tail = Trim(text.substr(colon + 1, 8));
    if (tail.rfind("true", 0) == 0) {
        value = true;
        return true;
    }
    if (tail.rfind("false", 0) == 0) {
        value = false;
        return true;
    }
    return false;
}

static bool ExtractUInt64(const std::string& text, const std::string& key, uint64_t& value) {
    const std::string quoted_key = "\"" + key + "\"";
    const size_t key_pos = text.find(quoted_key);
    if (key_pos == std::string::npos) {
        return true;
    }
    const size_t colon = text.find(':', key_pos + quoted_key.size());
    if (colon == std::string::npos) {
        return false;
    }
    size_t pos = colon + 1;
    while (pos < text.size() && isspace(static_cast<unsigned char>(text[pos]))) {
        ++pos;
    }
    size_t end = pos;
    while (end < text.size() && isdigit(static_cast<unsigned char>(text[end]))) {
        ++end;
    }
    if (end == pos) {
        return false;
    }
    value = _strtoui64(text.substr(pos, end - pos).c_str(), nullptr, 10);
    return true;
}

static bool LoadRules(const fs::path& path, Rules& rules, std::wstring& error) {
    if (path.empty()) {
        NormalizeModuleList(rules.network_modules);
        NormalizeModuleList(rules.dotnet_modules);
        NormalizeModuleList(rules.sensitive_modules);
        NormalizeModuleList(rules.module_integrity_allowlist);
        NormalizeModuleList(rules.environment_callback_allowlist);
        MergeModuleList(rules.sensitive_modules, rules.network_modules);
        MergeModuleList(rules.sensitive_modules, rules.dotnet_modules);
        rules.watch_dlls = rules.sensitive_modules;
        return true;
    }

    std::string text;
    if (!ReadTextFile(path, text)) {
        error = L"could not read rules file";
        return false;
    }

    const std::string trimmed = Trim(text);
    if (trimmed.empty() || trimmed.front() != '{' || trimmed.back() != '}') {
        error = L"rules file is not a JSON object";
        return false;
    }

    std::vector<std::wstring> legacy_watch_dlls;
    uint64_t long_sleep_ms = rules.long_sleep_ms;
    uint64_t correlation_window_ms = rules.correlation_window_ms;
    if (!ExtractStringArray(text, "network_modules", rules.network_modules) ||
        !ExtractStringArray(text, "dotnet_modules", rules.dotnet_modules) ||
        !ExtractStringArray(text, "sensitive_modules", rules.sensitive_modules) ||
        !ExtractStringArray(text, "module_integrity_allowlist", rules.module_integrity_allowlist) ||
        !ExtractStringArray(text, "environment_callback_allowlist", rules.environment_callback_allowlist) ||
        !ExtractStringArray(text, "watch_dlls", legacy_watch_dlls) ||
        !ExtractBool(text, "alert_on_unbacked_executable", rules.alert_on_unbacked_executable) ||
        !ExtractBool(text, "alert_on_backed_modified", rules.alert_on_backed_modified) ||
        !ExtractBool(text, "dump_suspicious_regions", rules.dump_suspicious_regions) ||
        !ExtractBool(text, "analyze_dumps", rules.analyze_dumps) ||
        !ExtractBool(text, "carve_embedded_pe", rules.carve_embedded_pe) ||
        !ExtractBool(text, "module_integrity_enabled", rules.module_integrity_enabled) ||
        !ExtractBool(text, "enable_sleep_hooks", rules.enable_sleep_hooks) ||
        !ExtractBool(text, "enable_msgwait_hook", rules.enable_msgwait_hook) ||
        !ExtractBool(text, "enable_wait_object_hooks", rules.enable_wait_object_hooks) ||
        !ExtractBool(text, "enable_thread_start_hooks", rules.enable_thread_start_hooks) ||
        !ExtractBool(text, "enable_threadpool_hooks", rules.enable_threadpool_hooks) ||
        !ExtractBool(text, "experimental_hooks", rules.experimental_hooks) ||
        !ExtractBool(text, "memory_api_hooks", rules.memory_api_hooks) ||
        !ExtractBool(text, "unwind_integrity", rules.unwind_integrity) ||
        !ExtractBool(text, "unwind_table_hooks", rules.unwind_table_hooks) ||
        !ExtractBool(text, "origin_trace", rules.origin_trace) ||
        !ExtractBool(text, "register_trace", rules.register_trace) ||
        !ExtractBool(text, "follow_remote", rules.follow_remote) ||
        !ExtractBool(text, "net_reset", rules.net_reset) ||
        !ExtractBool(text, "etw_telemetry", rules.etw_telemetry) ||
        !ExtractBool(text, "ldr_integrity", rules.ldr_integrity) ||
        !ExtractBool(text, "dispatch_trace", rules.dispatch_trace) ||
        !ExtractBool(text, "threadpool_chain_trace", rules.threadpool_chain_trace) ||
        !ExtractBool(text, "stack_audit", rules.stack_audit) ||
        !ExtractBool(text, "memory_audit", rules.memory_audit) ||
        !ExtractBool(text, "byoud_trace", rules.byoud_trace) ||
        !ExtractBool(text, "shadow_stack", rules.shadow_stack) ||
        !ExtractBool(text, "network_use_trace", rules.network_use_trace) ||
        !ExtractBool(text, "callsite_validation", rules.callsite_validation) ||
        !ExtractBool(text, "alert_on_unwind_tamper", rules.alert_on_unwind_tamper) ||
        !ExtractUInt64(text, "max_dump_bytes", rules.max_dump_bytes) ||
        !ExtractUInt64(text, "long_sleep_ms", long_sleep_ms) ||
        !ExtractUInt64(text, "correlation_window_ms", correlation_window_ms)) {
        error = L"rules file contains an invalid supported field";
        return false;
    }

    rules.long_sleep_ms = static_cast<uint32_t>(std::min<uint64_t>(long_sleep_ms, 24ull * 60ull * 60ull * 1000ull));
    rules.correlation_window_ms = static_cast<uint32_t>(std::min<uint64_t>(correlation_window_ms, 60ull * 60ull * 1000ull));
    NormalizeModuleList(rules.network_modules);
    NormalizeModuleList(rules.dotnet_modules);
    NormalizeModuleList(rules.sensitive_modules);
    NormalizeModuleList(rules.module_integrity_allowlist);
    NormalizeModuleList(rules.environment_callback_allowlist);
    NormalizeModuleList(legacy_watch_dlls);
    MergeModuleList(rules.sensitive_modules, rules.network_modules);
    MergeModuleList(rules.sensitive_modules, rules.dotnet_modules);
    MergeModuleList(rules.sensitive_modules, legacy_watch_dlls);
    rules.watch_dlls = rules.sensitive_modules;

    if (rules.sensitive_modules.empty()) {
        error = L"rules sensitive_modules/watch_dlls cannot be empty";
        return false;
    }
    return true;
}

static bool IsWatchedByRules(const Rules& rules, const std::wstring& dll_name) {
    return ContainsInsensitive(rules.sensitive_modules, dll_name);
}

static bool IsNetworkModule(const Rules& rules, const std::wstring& dll_name) {
    return ContainsInsensitive(rules.network_modules, dll_name);
}

static bool IsDotnetModule(const Rules& rules, const std::wstring& dll_name) {
    return ContainsInsensitive(rules.dotnet_modules, dll_name);
}

static bool IsModuleIntegrityAllowed(const Rules& rules, const std::wstring& module_name) {
    return ContainsInsensitive(rules.module_integrity_allowlist, module_name);
}

static bool IsManagedModuleName(const std::wstring& module_name) {
    const std::wstring lower = ToLower(BasenameOf(module_name));
    return lower == L"clr.dll" ||
        lower == L"clrjit.dll" ||
        lower == L"coreclr.dll" ||
        lower == L"mscoree.dll" ||
        lower == L"system.ni.dll" ||
        lower == L"mscorlib.ni.dll" ||
        lower.find(L".ni.dll") != std::wstring::npos;
}

static std::wstring EventTypeToString(uint32_t event_type) {
    switch (event_type) {
    case kMonitorEventDllLoad: return L"dll_load";
    case kMonitorEventSleepWait: return L"sleep_wait";
    case kMonitorEventCallback: return L"callback";
    case kMonitorEventMemoryApi: return L"memory_api";
    case kMonitorEventUnwindTable: return L"unwind_table";
    case kMonitorEventRemoteFollow: return L"remote_follow";
    case kMonitorEventNetReset: return L"net_reset";
    case kMonitorEventLdrIntegrity: return L"ldr_integrity";
    case kMonitorEventNetworkApi: return L"network_api";
    default: return L"unknown";
    }
}


