enum class UiMode {
    Auto,
    Live,
    Plain,
    Quiet
};

enum class UiTheme {
    Dark,
    Mono
};

enum class AnalysisProfile {
    Default,
    Quick,
    Deep,
    Max
};

static const wchar_t* AnalysisProfileName(AnalysisProfile profile) {
    switch (profile) {
    case AnalysisProfile::Quick: return L"quick";
    case AnalysisProfile::Deep: return L"deep";
    case AnalysisProfile::Max: return L"max";
    default: return L"default";
    }
}

struct Rules {
    uint32_t schema_version = 3;
    std::vector<std::wstring> network_modules{L"ws2_32.dll", L"wininet.dll", L"winhttp.dll", L"dnsapi.dll", L"iphlpapi.dll"};
    std::vector<std::wstring> dotnet_modules{L"clr.dll", L"coreclr.dll", L"mscoree.dll", L"system.management.automation.dll"};
    std::vector<std::wstring> sensitive_modules{
        L"ws2_32.dll", L"wininet.dll", L"winhttp.dll", L"dnsapi.dll", L"iphlpapi.dll",
        L"clr.dll", L"coreclr.dll", L"mscoree.dll", L"system.management.automation.dll"
    };
    std::vector<std::wstring> module_integrity_allowlist{
        L"ntdll.dll", L"kernel32.dll", L"kernelbase.dll", L"clr.dll", L"clrjit.dll",
        L"system.ni.dll", L"mscorlib.ni.dll", L"callstackmonitor.dll"
    };
    std::vector<std::wstring> environment_callback_allowlist{L"windhawk.dll"};
    std::vector<std::wstring> watch_dlls;
    bool alert_on_unbacked_executable = true;
    bool alert_on_backed_modified = true;
    bool dump_suspicious_regions = true;
    bool analyze_dumps = true;
    bool carve_embedded_pe = true;
    bool module_integrity_enabled = true;
    bool enable_sleep_hooks = true;
    bool enable_msgwait_hook = true;
    bool enable_wait_object_hooks = false;
    bool enable_thread_start_hooks = false;
    bool enable_threadpool_hooks = false;
    bool experimental_hooks = false;
    bool memory_api_hooks = false;
    bool unwind_integrity = true;
    bool unwind_table_hooks = false;
    bool origin_trace = false;
    bool register_trace = false;
    bool follow_remote = false;
    bool net_reset = false;
    bool etw_telemetry = false;
    bool ldr_integrity = false;
    bool dispatch_trace = false;
    bool threadpool_chain_trace = false;
    bool stack_audit = false;
    bool memory_audit = false;
    bool byoud_trace = false;
    bool shadow_stack = false;
    bool network_use_trace = false;
    bool callsite_validation = true;
    bool alert_on_unwind_tamper = true;
    uint64_t max_dump_bytes = 16ull * 1024ull * 1024ull;
    uint32_t long_sleep_ms = 1000;
    uint32_t correlation_window_ms = 5000;
};

struct Options {
    fs::path target;
    std::vector<std::wstring> target_args;
    fs::path rules_path;
    fs::path out_dir = L"out\\run";
    uint32_t timeout_ms = 0;
    bool keep_alive = false;
    UiMode ui_mode = UiMode::Auto;
    UiTheme ui_theme = UiTheme::Dark;
    bool no_color = false;
    bool no_animate = false;
    bool verbose = false;
    bool full_stack = false;
    bool inline_stack = false;
    bool suppress_target_output = false;
    bool experimental_hooks = false;
    bool memory_hooks = false;
    bool unwind_hooks = false;
    bool thread_start_hooks = false;
    bool threadpool_hooks = false;
    bool wait_hooks = false;
    bool origin_trace = false;
    bool register_trace = false;
    bool follow_remote = false;
    bool net_reset = false;
    bool etw_telemetry = false;
    bool ldr_integrity = false;
    bool dispatch_trace = false;
    bool threadpool_chain_trace = false;
    bool stack_audit = false;
    bool memory_audit = false;
    bool byoud_trace = false;
    bool shadow_stack = false;
    bool network_use_trace = false;
    bool hunt = false;
    AnalysisProfile profile = AnalysisProfile::Default;
    bool auto_enter = false;
    bool auto_enter_configured = false;
    uint32_t auto_enter_interval_ms = 1000;
    bool exit_after_parse = false;
    int parse_exit_code = 0;
};

struct ModuleInfo {
    uint64_t base = 0;
    uint64_t size = 0;
    std::wstring name;
    std::wstring path;
};

struct FrameInfo {
    uint64_t address = 0;
    uint64_t module_base = 0;
    uint64_t module_offset = 0;
    uint64_t allocation_base = 0;
    uint64_t allocation_size = 0;
    uint64_t region_base = 0;
    uint64_t region_size = 0;
    DWORD state = 0;
    DWORD protect = 0;
    DWORD allocation_protect = 0;
    DWORD type = 0;
    bool executable = false;
    bool suspicious = false;
    bool unbacked_executable = false;
    bool backed_modified = false;
    bool module_modified = false;
    bool jit_managed = false;
    bool suspicious_gadget_frame = false;
    bool return_address_without_call = false;
    bool tail_call_proxy = false;
    bool forward_proxy_frame = false;
    bool unwind_metadata_tampered = false;
    bool captured_context_modified = false;
    bool monitor_frame = false;
    uint64_t module_modified_bytes = 0;
    uint64_t unwind_modified_bytes = 0;
    uint64_t captured_context_modified_bytes = 0;
    std::wstring module_name;
    std::wstring module_path;
    std::wstring summary_name;
    std::wstring symbol_label;
};

struct EmbeddedPeRecord {
    uint64_t offset = 0;
    uint64_t carved_size = 0;
    std::wstring path;
};

struct DumpAnalysis {
    bool analyzed = false;
    double entropy = 0.0;
    std::wstring sha256;
    std::vector<EmbeddedPeRecord> embedded_pes;
    std::vector<std::wstring> strings;
};

struct DumpRecord {
    std::wstring path;
    uint64_t base = 0;
    uint64_t requested_size = 0;
    uint64_t dumped_size = 0;
    uint64_t trigger_address = 0;
    uint64_t trigger_region_base = 0;
    bool truncated = false;
    DumpAnalysis analysis;
};

struct OriginRegionDumpRecord {
    std::wstring path;
    uint64_t dump_base = 0;
    uint64_t dump_size = 0;
    uint64_t origin_address = 0;
    uint64_t origin_rva = 0;
    uint64_t module_base = 0;
    std::wstring module_name;
    std::wstring module_path;
    uint64_t visible_caller_address = 0;
    std::wstring visible_caller_label;
    std::wstring evidence;
    DumpAnalysis analysis;
};

struct ModulePatchRecord {
    uint64_t rva = 0;
    uint8_t memory_byte = 0;
    uint8_t disk_byte = 0;
    bool unwind_metadata = false;
};

struct ModuleIntegrityInfo {
    bool scanned = false;
    bool modified = false;
    bool executable_modified = false;
    bool unwind_modified = false;
    bool scan_error = false;
    uint64_t module_base = 0;
    uint64_t modified_bytes = 0;
    uint64_t executable_modified_bytes = 0;
    uint64_t unwind_modified_bytes = 0;
    std::wstring module_name;
    std::wstring module_path;
    std::wstring dump_path;
    std::vector<ModulePatchRecord> patches;
};

struct CallbackObservation {
    uint64_t callback_address = 0;
    uint32_t tid = 0;
    uint64_t event_index = 0;
    uint64_t tick_ms = 0;
    bool suspicious = false;
    bool origin_candidate = false;
    std::wstring api_name;
    std::wstring label;
};

struct LdrTamperObservation {
    uint64_t event_index = 0;
    uint64_t tick_ms = 0;
    uint64_t entrypoint = 0;
    std::wstring module_name;
};

struct MemoryAuditFinding {
    uint64_t event_index = 0;
    uint32_t pid = 0;
    bool alert = false;
    int score = 0;
    std::wstring rule;
    std::wstring confidence;
    std::wstring module_name;
    std::wstring module_path;
    std::wstring mapped_path;
    std::wstring detail;
    uint64_t address = 0;
    uint64_t region_base = 0;
    uint64_t region_size = 0;
    uint64_t allocation_base = 0;
    uint64_t allocation_size = 0;
    uint64_t private_pages = 0;
    uint64_t executable_private_pages = 0;
    DWORD state = 0;
    DWORD protect = 0;
    DWORD type = 0;
    bool dumped = false;
    std::wstring dump_path;
};

struct TemporalImageState {
    uint64_t module_base = 0;
    uint64_t module_size = 0;
    uint64_t dirty_event_index = 0;
    uint64_t restored_event_index = 0;
    bool dirty_seen = false;
    bool restored_seen = false;
    bool unmap_seen = false;
    uint64_t dirty_address = 0;
    uint64_t dirty_modified_bytes = 0;
    std::wstring module_name;
    std::wstring module_path;
    std::wstring dirty_dump_path;
};

struct ByoudTraceRecord {
    uint64_t event_index = 0;
    uint32_t pid = 0;
    uint32_t tid = 0;
    bool alert = false;
    int score = 0;
    std::wstring rule;
    std::wstring confidence;
    std::wstring technique;
    std::wstring module_name;
    std::wstring module_path;
    std::wstring section_name;
    std::wstring api_name;
    std::wstring dll_name;
    std::wstring caller_label;
    std::wstring detail;
    uint64_t module_base = 0;
    uint64_t address = 0;
    uint64_t rva = 0;
    uint64_t size = 0;
    uint64_t old_value = 0;
    uint64_t new_value = 0;
};

struct ShadowStackTraceRecord {
    uint64_t event_index = 0;
    uint32_t pid = 0;
    uint32_t tid = 0;
    bool alert = false;
    int score = 0;
    std::wstring rule;
    std::wstring confidence;
    std::wstring api_name;
    std::wstring dll_name;
    std::wstring classic_stack;
    std::wstring shadow_stack;
    std::wstring hidden_frame_label;
    std::wstring hidden_frame_module;
    std::wstring hidden_frame_path;
    std::wstring detail;
    uint64_t hidden_frame_address = 0;
    uint32_t classic_frame_count = 0;
    uint32_t shadow_frame_count = 0;
    uint32_t matched_shadow_frames = 0;
    uint32_t missing_or_out_of_order_frames = 0;
};

struct DllLoadMemoryObservation {
    uint64_t event_index = 0;
    uint32_t pid = 0;
    uint32_t tid = 0;
    bool alert = false;
    int score = 0;
    std::wstring dll_name;
    uint64_t loaded_base = 0;
    uint64_t loaded_size = 0;
    std::wstring loaded_path;
    uint64_t caller_address = 0;
    uint64_t caller_region_base = 0;
    uint64_t caller_region_size = 0;
    uint64_t caller_allocation_base = 0;
    uint64_t caller_allocation_size = 0;
    std::wstring caller_label;
    std::wstring caller_summary_name;
    std::wstring caller_module_name;
    std::wstring caller_module_path;
    bool caller_module_modified = false;
    std::wstring caller_modified_module_dump_path;
    std::wstring caller_state;
    std::wstring caller_protect;
    std::wstring caller_type;
    std::wstring stack_summary;
    bool origin_trace = false;
    std::wstring origin_confidence;
    std::wstring origin_source;
    std::wstring origin_kind;
    std::wstring origin_register;
    std::wstring origin_label;
    std::wstring origin_evidence;
    uint64_t origin_address = 0;
    uint64_t origin_value = 0;
    uint64_t origin_target = 0;
    bool origin_region_dumped = false;
    std::wstring origin_region_dump_path;
    uint64_t origin_region_dump_base = 0;
    uint64_t origin_region_dump_size = 0;
    uint64_t origin_region_rva = 0;
    bool dispatch_trace = false;
    bool dispatch_wait_observed = false;
    uint32_t dispatch_source_tid = 0;
    uint32_t dispatch_target_tid = 0;
    uint32_t dispatch_message = 0;
    uint64_t dispatch_wparam = 0;
    uint64_t dispatch_lparam = 0;
    std::wstring dispatch_api;
    std::wstring dispatch_function;
    std::wstring dispatch_argument;
    std::wstring dispatch_requester;
    std::wstring dispatch_worker;
};

struct NetworkUseObservation {
    uint64_t event_index = 0;
    uint32_t pid = 0;
    uint32_t tid = 0;
    bool alert = false;
    int score = 0;
    std::wstring api_name;
    std::wstring target_name;
    std::wstring network_module;
    uint64_t caller_address = 0;
    uint64_t caller_region_base = 0;
    uint64_t caller_region_size = 0;
    uint64_t caller_allocation_base = 0;
    uint64_t caller_allocation_size = 0;
    std::wstring caller_label;
    std::wstring caller_module_name;
    std::wstring caller_module_path;
    std::wstring caller_protect;
    std::wstring caller_type;
    bool caller_module_imports_network = false;
    bool import_checked = false;
    std::wstring stack_summary;
    std::vector<std::wstring> rules;
};

struct ProcessState {
    DWORD pid = 0;
    HANDLE handle = nullptr;
    std::wstring name;
    std::wstring main_module_name;
    fs::path out_dir;
    uint64_t events_total = 0;
    uint64_t alerts_total = 0;
    uint64_t dumps_total = 0;
    uint64_t origin_regions_total = 0;
    uint64_t memory_audit_findings_total = 0;
    uint64_t memory_audit_alerts_total = 0;
    uint64_t byoud_trace_total = 0;
    uint64_t byoud_alerts_total = 0;
    uint64_t shadow_stack_sensitive_events = 0;
    uint64_t shadow_stack_frame_records = 0;
    uint64_t shadow_stack_total = 0;
    uint64_t shadow_stack_alerts_total = 0;
    uint64_t network_use_total = 0;
    uint64_t network_use_alerts_total = 0;
    bool memory_audit_completed = false;
    std::vector<std::wstring> preloaded_network_modules;
    std::vector<DumpRecord> dumps;
    std::vector<OriginRegionDumpRecord> origin_region_dumps;
    std::vector<MemoryAuditFinding> memory_audit_findings;
    std::vector<ByoudTraceRecord> byoud_trace_records;
    std::vector<ShadowStackTraceRecord> shadow_stack_records;
    std::vector<DllLoadMemoryObservation> dll_load_memory;
    std::vector<NetworkUseObservation> network_use_records;
    std::vector<CallbackObservation> callback_observations;
    std::vector<LdrTamperObservation> ldr_tamper_observations;
    std::map<std::wstring, uint64_t> decision_counts;
    std::set<std::wstring> byoud_trace_keys;
    std::set<std::wstring> shadow_stack_keys;
    std::set<std::wstring> temporal_image_keys;
    std::set<uint64_t> dumped_allocation_bases;
    std::set<uint64_t> dumped_origin_region_keys;
    std::map<uint64_t, ModuleIntegrityInfo> module_integrity_cache;
    std::map<uint64_t, TemporalImageState> temporal_image_states;
};

struct EtwTimelineEvent {
    uint64_t tick_ms = 0;
    std::wstring kind;
    DWORD pid = 0;
    DWORD tid = 0;
    DWORD parent_pid = 0;
    uint64_t image_base = 0;
    uint64_t image_size = 0;
    std::wstring image_name;
    std::wstring process_name;
    std::wstring opcode;
    std::wstring provider;
};

static std::wstring ProtectToString(DWORD protect);
static std::wstring TypeToString(DWORD type);

class ConsoleUi {
public:
    ConsoleUi(UiMode mode, UiTheme theme, bool no_color, bool no_animate, bool verbose,
        bool full_stack, bool inline_stack)
        : requested_mode_(mode), theme_(theme), no_color_(no_color), no_animate_(no_animate),
        verbose_(verbose), full_stack_(full_stack), inline_stack_(inline_stack) {
        InitializeConsole();
    }

    bool Quiet() const {
        return effective_mode_ == UiMode::Quiet;
    }

    bool Verbose() const {
        return verbose_;
    }

    void Banner(const fs::path& target, const fs::path& out_dir, AnalysisProfile profile,
        bool auto_enter, uint32_t auto_enter_interval_ms, bool keep_alive,
        bool origin_trace, bool register_trace, bool dispatch_trace,
        bool threadpool_chain_trace, bool stack_audit, bool memory_audit, bool byoud_trace,
        bool shadow_stack, bool network_use_trace, bool etw_telemetry,
        bool suppress_target_output) {
        if (Quiet()) {
            return;
        }
        std::lock_guard<std::mutex> lock(output_mutex_);
        std::wcout << Paint(L"== StackSentry x64 ==", L"36;1") << L"\n";
        KeyValue(L"target", target.wstring());
        KeyValue(L"out", out_dir.wstring());
        KeyValue(L"profile", AnalysisProfileName(profile));
        if (auto_enter) {
            std::wostringstream value;
            value << L"auto-enter every " << auto_enter_interval_ms << L" ms";
            KeyValue(L"stdin", value.str());
        }
        if (keep_alive) {
            KeyValue(L"process", L"leave running after timeout");
        }
        if (suppress_target_output) {
            KeyValue(L"target output", L"suppressed");
        }
        if (origin_trace || register_trace) {
            KeyValue(L"origin", register_trace ? L"register trace + callback correlation" : L"callback correlation");
        }
        if (dispatch_trace) {
            KeyValue(L"dispatch", L"function proxy trace");
        }
        if (threadpool_chain_trace) {
            KeyValue(L"threadpool", L"callback chain trace");
        }
        if (stack_audit) {
            KeyValue(L"stack audit", L"strict return-frame validation");
        }
        if (memory_audit) {
            KeyValue(L"memory audit", L"Moneta-inspired image/state scan");
        }
        if (byoud_trace) {
            KeyValue(L"byoud trace", L"temporal unwind metadata audit");
        }
        if (shadow_stack) {
            KeyValue(L"shadow stack", L"research-only CET/HSP experiment");
        }
        if (network_use_trace) {
            KeyValue(L"network use", L"network API caller trace");
        }
        if (etw_telemetry) {
            KeyValue(L"etw", L"kernel process/thread/image-load timeline");
        }
        std::wcout << L"\n";
        printed_output_block_ = true;
    }

    void FeatureStatus(bool follow_remote, bool net_reset, bool dispatch_trace,
        bool threadpool_chain_trace, bool stack_audit, bool memory_audit, bool byoud_trace,
        bool shadow_stack, bool network_use_trace, bool etw_telemetry) {
        if (Quiet() || (!follow_remote && !net_reset && !dispatch_trace &&
            !threadpool_chain_trace && !stack_audit && !memory_audit && !byoud_trace && !shadow_stack &&
            !network_use_trace && !etw_telemetry)) {
            return;
        }
        std::lock_guard<std::mutex> lock(output_mutex_);
        if (follow_remote) {
            KeyValue(L"remote follow", L"enabled");
        }
        if (net_reset) {
            KeyValue(L"net reset", L"enabled");
        }
        if (dispatch_trace) {
            KeyValue(L"dispatch trace", L"enabled");
        }
        if (threadpool_chain_trace) {
            KeyValue(L"threadpool chain", L"enabled");
        }
        if (stack_audit) {
            KeyValue(L"stack audit", L"enabled");
        }
        if (memory_audit) {
            KeyValue(L"memory audit", L"enabled");
        }
        if (byoud_trace) {
            KeyValue(L"byoud trace", L"enabled");
        }
        if (shadow_stack) {
            KeyValue(L"shadow stack", L"research-only, unvalidated");
        }
        if (network_use_trace) {
            KeyValue(L"network use", L"enabled");
        }
        if (etw_telemetry) {
            KeyValue(L"etw telemetry", L"enabled");
        }
        std::wcout << L"\n";
        printed_output_block_ = true;
    }

    void Info(const std::wstring& message) {
        Line(L"info", message, L"36");
    }

    void Warn(const std::wstring& message) {
        Line(L"warn", message, L"33;1");
    }

    void Error(const std::wstring& message) {
        if (Quiet()) {
            return;
        }
        std::lock_guard<std::mutex> lock(output_mutex_);
        std::wcerr << L"[error] " << message << L"\n";
    }

    void Ready(DWORD pid, bool experimental_hooks) {
        if (Quiet()) {
            return;
        }
        std::wostringstream message;
        message << L"monitor ready; resuming pid=" << pid;
        if (experimental_hooks) {
            message << L" experimental-hooks=on";
        }
        Line(L"ready", message.str(), experimental_hooks ? L"33;1" : L"32;1");
    }

    void EventCard(const std::wstring& event_type, const std::wstring& target, bool alert, int score,
        const std::wstring& summary, const std::vector<std::wstring>& rule_hits,
        const std::vector<std::pair<std::wstring, std::wstring>>& details,
        uint64_t events_total, uint64_t alerts_total, uint64_t dumps_total) {
        if (Quiet()) {
            return;
        }
        const bool always_show =
            event_type == L"remote_follow" ||
            event_type == L"net_reset";
        if (!alert && !verbose_ && !always_show) {
            return;
        }

        std::lock_guard<std::mutex> lock(output_mutex_);
        if (alert && ShouldSuppressLiveAlertLocked(event_type, target, summary, rule_hits, events_total)) {
            return;
        }

        if (!printed_live_events_header_) {
            SectionHeader(L"Live Events", L"36;1");
            printed_live_events_header_ = true;
        }

        const wchar_t spin = NextSpinner();
        EventHeader(event_type, target, alert, score, events_total, alerts_total, dumps_total, spin);

        if (alert) {
            PrintRules(rule_hits, score);
            PrintDetails(details);
            PrintStack(summary);
        }
    }

    void Final(uint64_t events_total, uint64_t alerts_total, uint64_t dumps_total,
        uint64_t origin_regions_total,
        uint64_t modified_total, uint64_t embedded_pe_total,
        bool memory_audit_enabled, uint64_t memory_audit_findings_total,
        uint64_t memory_audit_alerts_total,
        const std::vector<MemoryAuditFinding>& memory_audit_findings,
        bool byoud_trace_enabled, uint64_t byoud_trace_total,
        uint64_t byoud_alerts_total,
        const std::vector<ByoudTraceRecord>& byoud_records,
        bool shadow_stack_enabled, uint64_t shadow_stack_sensitive_events,
        uint64_t shadow_stack_frame_records,
        uint64_t shadow_stack_total,
        uint64_t shadow_stack_alerts_total,
        const std::vector<ShadowStackTraceRecord>& shadow_stack_records,
        bool network_use_trace_enabled,
        uint64_t network_use_total,
        uint64_t network_use_alerts_total,
        const std::vector<NetworkUseObservation>& network_use_records,
        const std::vector<DllLoadMemoryObservation>& dll_memory,
        bool etw_enabled, const std::wstring& etw_status,
        uint64_t etw_events_total, uint64_t etw_process_events,
        uint64_t etw_thread_events, uint64_t etw_image_loads,
        const std::vector<EtwTimelineEvent>& etw_timeline,
        const fs::path& out_dir) {
        if (Quiet()) {
            return;
        }
        std::lock_guard<std::mutex> lock(output_mutex_);
        const bool has_printable_memory =
            std::any_of(dll_memory.begin(), dll_memory.end(),
                [&](const DllLoadMemoryObservation& item) { return item.alert || verbose_; });
        if (has_printable_memory) {
            SectionHeader(L"Memory", L"36;1");
            for (const auto& item : dll_memory) {
                if (!item.alert && !verbose_) {
                    continue;
                }
                PrintMemoryItem(item);
            }
        }

        const bool has_printable_audit =
            std::any_of(memory_audit_findings.begin(), memory_audit_findings.end(),
                [&](const MemoryAuditFinding& item) { return item.alert || verbose_; });
        if (has_printable_audit) {
            SectionHeader(L"Memory Audit", memory_audit_alerts_total ? L"31;1" : L"36;1");
            for (const auto& item : memory_audit_findings) {
                if (!item.alert && !verbose_) {
                    continue;
                }
                PrintMemoryAuditItem(item);
            }
        }

        const bool has_printable_byoud =
            std::any_of(byoud_records.begin(), byoud_records.end(),
                [&](const ByoudTraceRecord& item) { return item.alert || verbose_; });
        if (has_printable_byoud) {
            SectionHeader(L"BYOUD Trace", byoud_alerts_total ? L"31;1" : L"35;1");
            for (const auto& item : byoud_records) {
                if (!item.alert && !verbose_) {
                    continue;
                }
                PrintByoudTraceItem(item);
            }
        }

        const bool has_printable_shadow =
            std::any_of(shadow_stack_records.begin(), shadow_stack_records.end(),
                [&](const ShadowStackTraceRecord& item) { return item.alert || verbose_; });
        if (has_printable_shadow) {
            SectionHeader(L"Shadow Stack Trace", shadow_stack_alerts_total ? L"31;1" : L"35;1");
            for (const auto& item : shadow_stack_records) {
                if (!item.alert && !verbose_) {
                    continue;
                }
                PrintShadowStackTraceItem(item);
            }
        }

        const bool has_printable_network_use =
            std::any_of(network_use_records.begin(), network_use_records.end(),
                [&](const NetworkUseObservation& item) { return item.alert || verbose_; });
        if (has_printable_network_use) {
            SectionHeader(L"Network Use Details", network_use_alerts_total ? L"31;1" : L"36;1");
            PrintNetworkUseItems(network_use_records);
        }

        bool printed_origin_header = false;
        for (const auto& item : dll_memory) {
            if (!item.origin_trace || (!item.alert && !verbose_)) {
                continue;
            }
            if (!printed_origin_header) {
                SectionHeader(L"Origin Trace", L"35;1");
                printed_origin_header = true;
            }
            PrintOriginItem(item);
        }

        bool printed_dispatch_header = false;
        for (const auto& item : dll_memory) {
            if (!item.dispatch_trace || (!item.alert && !verbose_)) {
                continue;
            }
            if (!printed_dispatch_header) {
                SectionHeader(L"Dispatch Trace", L"35;1");
                printed_dispatch_header = true;
            }
            PrintDispatchItem(item);
        }

        if (etw_enabled || etw_events_total > 0) {
            SectionHeader(L"ETW Timeline", L"36;1");
            KeyValue(L"status", etw_status.empty() ? L"not started" : etw_status);
            KeyValue(L"process events", std::to_wstring(etw_process_events));
            KeyValue(L"thread events", std::to_wstring(etw_thread_events));
            KeyValue(L"image loads", std::to_wstring(etw_image_loads));
            PrintEtwPreview(etw_timeline);
        }

        SectionHeader(L"Summary", alerts_total ? L"31;1" : L"32;1");
        KeyValue(L"events", std::to_wstring(events_total));
        KeyValue(L"alerts", std::to_wstring(alerts_total));
        KeyValue(L"dumps", std::to_wstring(dumps_total));
        KeyValue(L"origin regions", std::to_wstring(origin_regions_total));
        KeyValue(L"modified images", std::to_wstring(modified_total));
        KeyValue(L"embedded PE", std::to_wstring(embedded_pe_total));
        if (memory_audit_enabled || memory_audit_findings_total > 0) {
            KeyValue(L"memory audit", memory_audit_enabled ? L"enabled" : L"not enabled");
            KeyValue(L"audit findings", std::to_wstring(memory_audit_findings_total));
            KeyValue(L"audit alerts", std::to_wstring(memory_audit_alerts_total));
        }
        if (byoud_trace_enabled || byoud_trace_total > 0) {
            KeyValue(L"byoud trace", byoud_trace_enabled ? L"enabled" : L"not enabled");
            KeyValue(L"byoud findings", std::to_wstring(byoud_trace_total));
            KeyValue(L"byoud alerts", std::to_wstring(byoud_alerts_total));
        }
        if (shadow_stack_enabled || shadow_stack_total > 0) {
            KeyValue(L"shadow stack", shadow_stack_enabled ? L"research-only enabled" : L"not enabled");
            KeyValue(L"shadow events", std::to_wstring(shadow_stack_sensitive_events));
            KeyValue(L"shadow frames", std::to_wstring(shadow_stack_frame_records));
            if (shadow_stack_enabled && shadow_stack_sensitive_events > 0 && shadow_stack_frame_records == 0) {
                KeyValue(L"shadow status", L"no CET/HSP frames captured; target likely did not run with user-mode shadow stack");
            }
            KeyValue(L"shadow findings", std::to_wstring(shadow_stack_total));
            KeyValue(L"shadow alerts", std::to_wstring(shadow_stack_alerts_total));
        }
        if (network_use_trace_enabled || network_use_total > 0) {
            KeyValue(L"network use", network_use_trace_enabled ? L"enabled" : L"not enabled");
            KeyValue(L"network events", std::to_wstring(network_use_total));
            KeyValue(L"network alerts", std::to_wstring(network_use_alerts_total));
        }
        PrintSuppressedLiveSummary();
        if (etw_enabled || etw_events_total > 0 || !etw_status.empty()) {
            KeyValue(L"etw", etw_status.empty() ? L"not started" : etw_status);
            KeyValue(L"etw events", std::to_wstring(etw_events_total));
        }

        std::wcout << L"\n";
        std::wcout << Paint(L"out", L"90") << L": " << out_dir.wstring() << L"\n";
    }

private:
    void SectionHeader(const std::wstring& title, const wchar_t* color) {
        if (printed_output_block_) {
            std::wcout << L"\n";
        }
        std::wcout << Paint(L"== " + title + L" ==", color) << L"\n";
        printed_output_block_ = true;
    }

    std::wstring Label(const wchar_t* text) const {
        std::wostringstream out;
        out << std::left << std::setw(16) << std::setfill(L' ') << text;
        return Paint(out.str(), L"90");
    }

    void KeyValue(const wchar_t* key, const std::wstring& value) {
        std::wcout << L"  " << Label(key) << L": " << value << L"\n";
    }

    void DetailValue(const wchar_t* key, const std::wstring& value) {
        std::wcout << L"  " << Label(key) << L": " << value << L"\n";
    }

    void EventHeader(const std::wstring& event_type, const std::wstring& target, bool alert, int score,
        uint64_t events_total, uint64_t alerts_total, uint64_t dumps_total, wchar_t spinner) {
        const wchar_t* color = alert ? (score >= 85 ? L"31;1" : L"33;1") : L"36";
        std::wcout << Paint(alert ? L"[ALERT]" : L"[event]", color)
            << L" " << event_type << L":" << target;
        if (effective_mode_ == UiMode::Live && !no_animate_) {
            std::wcout << L" " << spinner;
        }
        std::wcout << L"\n"
            << L"  " << Label(L"score") << L": " << score
            << L"  " << Paint(L"events", L"90") << L": " << events_total
            << L"  " << Paint(L"alerts", L"90") << L": " << alerts_total
            << L"  " << Paint(L"dumps", L"90") << L": " << dumps_total
            << L"\n";
    }

    void PrintRules(const std::vector<std::wstring>& rule_hits, int score) {
        if (rule_hits.empty()) {
            return;
        }
        std::wcout << L"  " << Label(L"rules") << L": ";
        for (size_t i = 0; i < rule_hits.size(); ++i) {
            if (i) {
                std::wcout << L", ";
            }
            std::wcout << Paint(rule_hits[i], score >= 85 ? L"31;1" : L"33;1");
        }
        std::wcout << L"\n";
    }

    void PrintStack(const std::wstring& summary) {
        if (summary.empty()) {
            return;
        }
        if (!full_stack_) {
            DetailValue(L"stack", Paint(inline_stack_ ? summary : CompactStackSummary(summary), L"90"));
            return;
        }

        const auto frames = SplitStackSummary(summary);
        if (frames.empty()) {
            return;
        }

        std::wcout << L"  " << Label(L"stack") << L":\n";
        for (size_t i = 0; i < frames.size(); ++i) {
            std::wostringstream index;
            index << L"#" << std::setw(2) << std::setfill(L'0') << i;
            std::wcout << L"    " << Paint(index.str(), L"90") << L" "
                << Paint(frames[i], L"90") << L"\n";
        }
    }

    void PrintDetails(const std::vector<std::pair<std::wstring, std::wstring>>& details) {
        for (const auto& item : details) {
            DetailValue(item.first.c_str(), item.second);
        }
    }

    struct LiveSuppressionGroup {
        std::wstring label;
        std::wstring rule;
        std::wstring stack;
        uint64_t first_event = 0;
        uint64_t last_event = 0;
        uint64_t repeats = 0;
    };

    static std::wstring LowerConsoleText(std::wstring value) {
        for (auto& ch : value) {
            if (ch >= L'A' && ch <= L'Z') {
                ch = static_cast<wchar_t>(ch - L'A' + L'a');
            }
        }
        return value;
    }

    static bool StartsWithInsensitive(const std::wstring& text, const std::wstring& prefix) {
        if (text.size() < prefix.size()) {
            return false;
        }
        return LowerConsoleText(text.substr(0, prefix.size())) == LowerConsoleText(prefix);
    }

    static std::wstring FirstRule(const std::vector<std::wstring>& rules) {
        return rules.empty() ? L"none" : rules.front();
    }

    static std::wstring JoinRulesForKey(const std::vector<std::wstring>& rules) {
        std::wstring joined;
        for (const auto& rule : rules) {
            if (!joined.empty()) {
                joined += L",";
            }
            joined += LowerConsoleText(rule);
        }
        return joined;
    }

    static std::wstring SocketTargetKey(const std::wstring& target) {
        if (!StartsWithInsensitive(target, L"socket=")) {
            return {};
        }
        const size_t bytes_pos = LowerConsoleText(target).find(L" bytes=");
        if (bytes_pos == std::wstring::npos) {
            return LowerConsoleText(target);
        }
        return LowerConsoleText(target.substr(0, bytes_pos));
    }

    static uint64_t SocketByteCount(const std::wstring& target) {
        const std::wstring lower = LowerConsoleText(target);
        const size_t bytes_pos = lower.find(L" bytes=");
        if (bytes_pos == std::wstring::npos) {
            return 0;
        }
        const wchar_t* cursor = target.c_str() + bytes_pos + 7;
        return _wcstoui64(cursor, nullptr, 10);
    }

    static std::vector<std::wstring> SplitStackSummary(const std::wstring& summary) {
        std::vector<std::wstring> frames;
        size_t start = 0;
        while (start <= summary.size()) {
            const size_t split = summary.find(L'|', start);
            const size_t end = split == std::wstring::npos ? summary.size() : split;
            if (end > start) {
                frames.push_back(summary.substr(start, end - start));
            }
            if (split == std::wstring::npos) {
                break;
            }
            start = split + 1;
        }
        return frames;
    }

    static std::wstring CompactStackSummary(const std::wstring& summary) {
        const std::vector<std::wstring> frames = SplitStackSummary(summary);
        std::wstring compact;
        for (size_t i = 0; i < frames.size();) {
            size_t count = 1;
            while (i + count < frames.size() && frames[i + count] == frames[i]) {
                ++count;
            }
            if (!compact.empty()) {
                compact += L"|";
            }
            if (count > 1) {
                compact += L"[" + frames[i] + L" x" + std::to_wstring(count) + L"]";
            } else {
                compact += frames[i];
            }
            i += count;
        }
        return compact;
    }

    bool ShouldSuppressLiveAlertLocked(const std::wstring& event_type, const std::wstring& target,
        const std::wstring& summary, const std::vector<std::wstring>& rules, uint64_t event_index) {
        if (verbose_) {
            return false;
        }

        std::wstring label;
        std::wstring key;
        const std::wstring compact_stack = CompactStackSummary(summary);
        const std::wstring primary_rule = FirstRule(rules);
        if (event_type == L"sleep_wait") {
            label = L"sleep_wait:" + target;
            key = event_type + L"|" + LowerConsoleText(target) + L"|" + JoinRulesForKey(rules);
        } else if (event_type == L"network_api") {
            const std::wstring socket_key = SocketTargetKey(target);
            if (socket_key.empty()) {
                return false;
            }
            label = L"network_api:" + socket_key;
            key = event_type + L"|" + socket_key;
        } else if (event_type == L"callback" &&
            (LowerConsoleText(target) == L"createthread" ||
                LowerConsoleText(target) == L"ntqueueapcthread" ||
                LowerConsoleText(target) == L"queueuserapc")) {
            label = L"callback:" + target;
            key = event_type + L"|" + LowerConsoleText(target) + L"|" + JoinRulesForKey(rules) + L"|" + compact_stack;
        } else {
            return false;
        }

        auto [it, inserted] = suppressed_live_groups_.try_emplace(key);
        auto& group = it->second;
        if (inserted) {
            group.label = label;
            group.rule = primary_rule;
            group.stack = compact_stack;
            group.first_event = event_index;
            group.last_event = event_index;
            return false;
        }

        ++group.repeats;
        ++suppressed_live_repeats_;
        group.last_event = event_index;
        return true;
    }

    void PrintSuppressedLiveSummary() {
        if (suppressed_live_repeats_ == 0) {
            return;
        }

        KeyValue(L"console compact", std::to_wstring(suppressed_live_repeats_) + L" repeated live alerts suppressed");
        std::vector<const LiveSuppressionGroup*> groups;
        groups.reserve(suppressed_live_groups_.size());
        for (const auto& item : suppressed_live_groups_) {
            if (item.second.repeats > 0) {
                groups.push_back(&item.second);
            }
        }
        std::sort(groups.begin(), groups.end(),
            [](const LiveSuppressionGroup* left, const LiveSuppressionGroup* right) {
                return left->repeats > right->repeats;
            });

        const size_t shown = std::min<size_t>(groups.size(), 6);
        for (size_t i = 0; i < shown; ++i) {
            const auto& group = *groups[i];
            std::wostringstream value;
            value << group.label
                << L" repeats=" << group.repeats
                << L" events=" << group.first_event << L".." << group.last_event
                << L" rule=" << group.rule;
            DetailValue(L"compact group", value.str());
        }
        if (groups.size() > shown) {
            KeyValue(L"compact groups", std::to_wstring(groups.size() - shown) + L" additional repeated groups");
        }
    }

    void PrintMemoryItem(const DllLoadMemoryObservation& item) {
        std::wcout << Paint(L"[dll]", item.alert ? L"31;1" : L"36")
            << L" " << item.dll_name
            << L" event=" << item.event_index
            << L" score=" << item.score << L"\n";

        std::wostringstream loaded;
        loaded << L"base=" << FormatHex64(item.loaded_base)
            << L" size=" << FormatHex64(item.loaded_size);
        if (!item.loaded_path.empty()) {
            loaded << L" path=" << item.loaded_path;
        }
        DetailValue(L"loaded", loaded.str());

        std::wostringstream caller;
        caller << L"address=" << FormatHex64(item.caller_address)
            << L" region=" << FormatHex64(item.caller_region_base)
            << L" allocation=" << FormatHex64(item.caller_allocation_base);
        DetailValue(L"caller", caller.str());

        std::wostringstream memory;
        memory << item.caller_protect << L" " << item.caller_type;
        if (!item.caller_label.empty()) {
            memory << L" label=" << item.caller_label;
        }
        DetailValue(L"memory", memory.str());
        if (item.caller_module_modified && !item.caller_modified_module_dump_path.empty()) {
            DetailValue(L"modified dump", item.caller_modified_module_dump_path);
            DetailValue(L"modified bytes", item.caller_modified_module_dump_path + L".tag (byte diff map)");
        }
        PrintStack(item.stack_summary);
    }

    void PrintOriginItem(const DllLoadMemoryObservation& item) {
        std::wcout << Paint(L"[dll]", item.alert ? L"31;1" : L"36")
            << L" " << item.dll_name
            << L" event=" << item.event_index;
        if (!item.origin_confidence.empty()) {
            std::wcout << L" confidence=" << item.origin_confidence;
        }
        std::wcout << L"\n";

        DetailValue(L"visible caller", item.caller_label);
        DetailValue(L"probable origin", item.origin_label + L" address=" + FormatHex64(item.origin_address));
        if (!item.origin_source.empty()) {
            std::wstring source = item.origin_source;
            if (!item.origin_kind.empty()) {
                source += L" kind=" + item.origin_kind;
            }
            if (!item.origin_register.empty()) {
                source += L" reg=" + item.origin_register;
            }
            DetailValue(L"source", source);
        }
        if (!item.origin_evidence.empty()) {
            DetailValue(L"evidence", item.origin_evidence);
        }
        if (item.origin_region_dumped) {
            std::wostringstream dump;
            dump << L"base=" << FormatHex64(item.origin_region_dump_base)
                << L" size=" << FormatHex64(item.origin_region_dump_size)
                << L" rva=" << FormatHex64(item.origin_region_rva)
                << L" path=" << item.origin_region_dump_path;
            DetailValue(L"origin dump", dump.str());
        }
    }

    void PrintDispatchItem(const DllLoadMemoryObservation& item) {
        std::wcout << Paint(L"[dll]", item.alert ? L"31;1" : L"36")
            << L" " << item.dll_name
            << L" event=" << item.event_index;
        if (!item.origin_confidence.empty()) {
            std::wcout << L" confidence=" << item.origin_confidence;
        }
        std::wcout << L"\n";

        DetailValue(L"requester tid", std::to_wstring(item.dispatch_source_tid));
        DetailValue(L"worker tid", std::to_wstring(item.dispatch_target_tid));
        DetailValue(L"dispatch API", item.dispatch_api.empty() ? L"PostThreadMessage" : item.dispatch_api);
        DetailValue(L"function", item.dispatch_function.empty() ? FormatHex64(item.origin_value) : item.dispatch_function);
        DetailValue(L"argument", item.dispatch_argument.empty() ? item.dll_name : item.dispatch_argument);
        if (!item.dispatch_requester.empty()) {
            DetailValue(L"requester", item.dispatch_requester);
        }
        if (!item.dispatch_worker.empty()) {
            DetailValue(L"worker caller", item.dispatch_worker);
        }
        std::wostringstream msg;
        msg << L"msg=0x" << std::hex << std::uppercase << item.dispatch_message
            << L" lParam=" << FormatHex64(item.dispatch_lparam);
        if (item.dispatch_wait_observed) {
            msg << L" wait=observed";
        }
        DetailValue(L"message", msg.str());
        if (!item.origin_evidence.empty()) {
            DetailValue(L"evidence", item.origin_evidence);
        }
    }

    void PrintMemoryAuditItem(const MemoryAuditFinding& item) {
        std::wcout << Paint(item.alert ? L"[ALERT]" : L"[audit]", item.alert ? L"31;1" : L"36")
            << L" " << item.rule
            << L" score=" << item.score
            << L" pid=" << item.pid;
        if (item.event_index) {
            std::wcout << L" event=" << item.event_index;
        }
        std::wcout << L"\n";
        if (!item.confidence.empty()) {
            DetailValue(L"confidence", item.confidence);
        }
        std::wostringstream region;
        region << L"address=" << FormatHex64(item.address)
            << L" region=" << FormatHex64(item.region_base)
            << L" size=" << FormatHex64(item.region_size)
            << L" allocation=" << FormatHex64(item.allocation_base);
        DetailValue(L"region", region.str());

        std::wostringstream memory;
        memory << ProtectToString(item.protect) << L" " << TypeToString(item.type);
        if (item.private_pages || item.executable_private_pages) {
            memory << L" private_pages=" << item.private_pages
                << L" exec_private_pages=" << item.executable_private_pages;
        }
        DetailValue(L"memory", memory.str());

        if (!item.module_name.empty()) {
            DetailValue(L"module", item.module_name);
        }
        if (!item.module_path.empty()) {
            DetailValue(L"peb path", item.module_path);
        }
        if (!item.mapped_path.empty()) {
            DetailValue(L"mapped path", item.mapped_path);
        }
        if (!item.detail.empty()) {
            DetailValue(L"detail", item.detail);
        }
        if (item.dumped && !item.dump_path.empty()) {
            DetailValue(L"audit dump", item.dump_path);
        }
    }

    void PrintByoudTraceItem(const ByoudTraceRecord& item) {
        std::wcout << Paint(item.alert ? L"[ALERT]" : L"[byoud]", item.alert ? L"31;1" : L"35")
            << L" " << item.rule
            << L" score=" << item.score
            << L" pid=" << item.pid;
        if (item.event_index) {
            std::wcout << L" event=" << item.event_index;
        }
        std::wcout << L"\n";
        if (!item.confidence.empty()) {
            DetailValue(L"confidence", item.confidence);
        }
        if (!item.technique.empty()) {
            DetailValue(L"technique", item.technique);
        }
        if (!item.dll_name.empty() || !item.api_name.empty()) {
            std::wstring api = item.api_name;
            if (!item.dll_name.empty()) {
                api += api.empty() ? item.dll_name : L" -> " + item.dll_name;
            }
            DetailValue(L"sensitive API", api);
        }
        if (!item.caller_label.empty()) {
            DetailValue(L"visible caller", item.caller_label);
        }
        if (!item.module_name.empty()) {
            DetailValue(L"module", item.module_name);
        }
        if (!item.section_name.empty()) {
            std::wostringstream location;
            location << item.section_name
                << L" rva=" << FormatHex64(item.rva)
                << L" address=" << FormatHex64(item.address)
                << L" size=" << FormatHex64(item.size);
            DetailValue(L"location", location.str());
        }
        if (item.old_value || item.new_value) {
            std::wostringstream values;
            values << L"disk/original=" << FormatHex64(item.old_value)
                << L" memory/current=" << FormatHex64(item.new_value);
            DetailValue(L"entry diff", values.str());
        }
        if (!item.detail.empty()) {
            DetailValue(L"evidence", item.detail);
        }
    }

    void PrintShadowStackTraceItem(const ShadowStackTraceRecord& item) {
        std::wcout << Paint(item.alert ? L"[ALERT]" : L"[shadow]", item.alert ? L"31;1" : L"35")
            << L" " << item.rule
            << L" score=" << item.score
            << L" pid=" << item.pid;
        if (item.event_index) {
            std::wcout << L" event=" << item.event_index;
        }
        std::wcout << L"\n";
        if (!item.confidence.empty()) {
            DetailValue(L"confidence", item.confidence);
        }
        if (!item.dll_name.empty() || !item.api_name.empty()) {
            std::wstring api = item.api_name;
            if (!item.dll_name.empty()) {
                api += api.empty() ? item.dll_name : L" -> " + item.dll_name;
            }
            DetailValue(L"sensitive API", api);
        }
        if (!item.hidden_frame_label.empty()) {
            DetailValue(L"hidden frame", item.hidden_frame_label + L" address=" + FormatHex64(item.hidden_frame_address));
        }
        if (!item.hidden_frame_module.empty()) {
            DetailValue(L"module", item.hidden_frame_module);
        }
        if (!item.hidden_frame_path.empty()) {
            DetailValue(L"path", item.hidden_frame_path);
        }
        if (item.classic_frame_count || item.shadow_frame_count) {
            std::wostringstream frames;
            frames << L"classic=" << item.classic_frame_count
                << L" shadow=" << item.shadow_frame_count
                << L" matched=" << item.matched_shadow_frames
                << L" missing_or_order=" << item.missing_or_out_of_order_frames;
            DetailValue(L"frame match", frames.str());
        }
        if (!item.classic_stack.empty()) {
            DetailValue(L"classic stack", item.classic_stack);
        }
        if (!item.shadow_stack.empty()) {
            DetailValue(L"shadow stack", item.shadow_stack);
        }
        if (!item.detail.empty()) {
            DetailValue(L"evidence", item.detail);
        }
    }

    struct NetworkUseConsoleGroup {
        NetworkUseObservation first;
        uint64_t count = 0;
        uint64_t first_event = 0;
        uint64_t last_event = 0;
        uint64_t total_socket_bytes = 0;
    };

    static std::wstring NetworkUseGroupKey(const NetworkUseObservation& item) {
        std::wstring target_key = SocketTargetKey(item.target_name);
        if (target_key.empty()) {
            target_key = LowerConsoleText(item.target_name);
        }
        return LowerConsoleText(item.api_name) + L"|" +
            target_key + L"|" +
            LowerConsoleText(item.caller_label);
    }

    void PrintNetworkUseItems(const std::vector<NetworkUseObservation>& items) {
        if (verbose_) {
            for (const auto& item : items) {
                if (item.alert || verbose_) {
                    PrintNetworkUseItem(item);
                }
            }
            return;
        }

        std::vector<NetworkUseConsoleGroup> groups;
        std::map<std::wstring, size_t> group_index;
        for (const auto& item : items) {
            if (!item.alert) {
                continue;
            }
            const std::wstring key = NetworkUseGroupKey(item);
            auto it = group_index.find(key);
            if (it == group_index.end()) {
                NetworkUseConsoleGroup group;
                group.first = item;
                group.count = 1;
                group.first_event = item.event_index;
                group.last_event = item.event_index;
                group.total_socket_bytes = SocketByteCount(item.target_name);
                group_index.emplace(key, groups.size());
                groups.push_back(std::move(group));
            } else {
                auto& group = groups[it->second];
                ++group.count;
                group.last_event = item.event_index;
                group.total_socket_bytes += SocketByteCount(item.target_name);
                for (const auto& rule : item.rules) {
                    if (std::find(group.first.rules.begin(), group.first.rules.end(), rule) == group.first.rules.end()) {
                        group.first.rules.push_back(rule);
                    }
                }
            }
        }

        for (const auto& group : groups) {
            PrintNetworkUseItem(group.first, group.count, group.first_event, group.last_event, group.total_socket_bytes);
        }
    }

    void PrintNetworkUseItem(const NetworkUseObservation& item, uint64_t count = 1,
        uint64_t first_event = 0, uint64_t last_event = 0, uint64_t total_socket_bytes = 0) {
        std::wcout << Paint(item.alert ? L"[ALERT]" : L"[net]", item.alert ? L"31;1" : L"36")
            << L" " << item.api_name
            << L" event=" << (first_event ? first_event : item.event_index);
        if (count > 1) {
            std::wcout << L".." << last_event << L" count=" << count;
        }
        std::wcout
            << L" score=" << item.score << L"\n";
        if (!item.network_module.empty()) {
            DetailValue(L"module", item.network_module);
        }
        if (!item.target_name.empty()) {
            DetailValue(L"target", item.target_name);
        }
        if (count > 1) {
            std::wostringstream observed;
            observed << count << L" calls aggregated";
            if (total_socket_bytes > 0) {
                observed << L"; total socket bytes=" << total_socket_bytes;
            }
            DetailValue(L"observed", observed.str());
        }
        if (!item.rules.empty()) {
            std::wstring joined;
            for (size_t i = 0; i < item.rules.size(); ++i) {
                if (i) {
                    joined += L", ";
                }
                joined += item.rules[i];
            }
            DetailValue(L"rules", joined);
        }
        DetailValue(L"caller", item.caller_label + L" address=" + FormatHex64(item.caller_address));
        const bool has_memory_class =
            !item.caller_protect.empty() &&
            !item.caller_type.empty() &&
            !(item.caller_protect == L"UNKNOWN" && item.caller_type == L"UNKNOWN");
        if (has_memory_class || !item.caller_module_name.empty()) {
            std::wostringstream memory;
            if (has_memory_class) {
                memory << item.caller_protect << L" " << item.caller_type;
                if (!item.caller_module_name.empty()) {
                    memory << L" ";
                }
            }
            if (!item.caller_module_name.empty()) {
                memory << L"module=" << item.caller_module_name;
            }
            DetailValue(L"memory", memory.str());
        }
        if (item.import_checked) {
            DetailValue(L"static import", item.caller_module_imports_network ? L"caller imports this network module" : L"caller does not import this network module");
        }
        PrintStack(item.stack_summary);
    }

    void PrintEtwPreview(const std::vector<EtwTimelineEvent>& events) {
        if (events.empty()) {
            DetailValue(L"timeline", L"no matching target/child events captured");
            return;
        }

        const size_t start = events.size() > 8 ? events.size() - 8 : 0;
        for (size_t i = start; i < events.size(); ++i) {
            const auto& item = events[i];
            std::wostringstream line;
            line << L"+" << item.tick_ms << L"ms " << item.kind
                << L" pid=" << item.pid;
            if (item.tid) {
                line << L" tid=" << item.tid;
            }
            if (item.parent_pid) {
                line << L" ppid=" << item.parent_pid;
            }
            if (!item.process_name.empty()) {
                line << L" process=" << item.process_name;
            }
            if (!item.image_name.empty()) {
                line << L" image=" << item.image_name;
            }
            if (item.image_base) {
                line << L" base=" << FormatHex64(item.image_base);
            }
            DetailValue(L"event", line.str());
        }
    }

    void InitializeConsole() {
        const HANDLE output = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD mode = 0;
        const bool console = output != INVALID_HANDLE_VALUE &&
            GetFileType(output) == FILE_TYPE_CHAR &&
            GetConsoleMode(output, &mode);

        if (requested_mode_ == UiMode::Auto) {
            effective_mode_ = console ? UiMode::Live : UiMode::Plain;
        } else {
            effective_mode_ = requested_mode_;
        }

        use_color_ = !no_color_ && theme_ != UiTheme::Mono && console && effective_mode_ != UiMode::Quiet;
        if (use_color_) {
            SetConsoleMode(output, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
        }
        if (effective_mode_ == UiMode::Live && !console) {
            effective_mode_ = UiMode::Plain;
        }
    }

    std::wstring Paint(const std::wstring& text, const wchar_t* code) const {
        if (!use_color_) {
            return text;
        }
        return std::wstring(L"\x1b[") + code + L"m" + text + L"\x1b[0m";
    }

    std::wstring FormatHex64(uint64_t value) const {
        std::wostringstream out;
        out << L"0x" << std::hex << std::uppercase << std::setw(16) << std::setfill(L'0') << value;
        return out.str();
    }

    void Line(const std::wstring& label, const std::wstring& message, const wchar_t* color) {
        if (Quiet()) {
            return;
        }
        std::lock_guard<std::mutex> lock(output_mutex_);
        std::wcout << Paint(L"[" + label + L"]", color) << L" " << message << L"\n";
    }

    wchar_t NextSpinner() {
        static constexpr wchar_t frames[] = { L'|', L'/', L'-', L'\\' };
        const wchar_t result = frames[spinner_index_ % _countof(frames)];
        ++spinner_index_;
        return result;
    }

    UiMode requested_mode_ = UiMode::Auto;
    UiMode effective_mode_ = UiMode::Plain;
    UiTheme theme_ = UiTheme::Dark;
    bool no_color_ = false;
    bool no_animate_ = false;
    bool verbose_ = false;
    bool full_stack_ = false;
    bool inline_stack_ = false;
    bool use_color_ = false;
    bool printed_output_block_ = false;
    bool printed_live_events_header_ = false;
    size_t spinner_index_ = 0;
    uint64_t suppressed_live_repeats_ = 0;
    std::map<std::wstring, LiveSuppressionGroup> suppressed_live_groups_;
    std::mutex output_mutex_;
};

struct RunState {
    HANDLE process = nullptr;
    DWORD pid = 0;
    std::wstring main_module_name;
    DWORD active_event_pid = 0;
    ProcessState* active_process_state = nullptr;
    fs::path active_out_dir;
    std::wstring active_main_module_name;
    bool follow_remote = false;
    bool net_reset = false;
    bool etw_telemetry = false;
    bool dispatch_trace = false;
    bool threadpool_chain_trace = false;
    bool stack_audit = false;
    bool memory_audit = false;
    bool byoud_trace = false;
    bool shadow_stack = false;
    bool network_use_trace = false;
    AnalysisProfile profile = AnalysisProfile::Default;
    bool auto_enter = false;
    uint32_t auto_enter_interval_ms = 0;
    bool keep_alive = false;
    bool detached = false;
    Rules rules;
    fs::path out_dir;
    ConsoleUi* ui = nullptr;
    std::ofstream events;
    uint64_t events_total = 0;
    uint64_t alerts_total = 0;
    uint64_t dumps_total = 0;
    uint64_t origin_regions_total = 0;
    uint64_t unbacked_total = 0;
    uint64_t modified_image_total = 0;
    uint64_t unwind_tamper_total = 0;
    uint64_t callsite_anomaly_total = 0;
    uint64_t memory_api_alert_total = 0;
    uint64_t unwind_alert_total = 0;
    uint64_t embedded_pe_total = 0;
    uint64_t sleep_alert_total = 0;
    uint64_t callback_alert_total = 0;
    uint64_t ldr_tamper_total = 0;
    uint64_t memory_audit_findings_total = 0;
    uint64_t memory_audit_alerts_total = 0;
    uint64_t byoud_trace_total = 0;
    uint64_t byoud_alerts_total = 0;
    uint64_t shadow_stack_sensitive_events = 0;
    uint64_t shadow_stack_frame_records = 0;
    uint64_t shadow_stack_total = 0;
    uint64_t shadow_stack_alerts_total = 0;
    uint64_t network_use_total = 0;
    uint64_t network_use_alerts_total = 0;
    uint64_t etw_events_total = 0;
    uint64_t etw_process_events = 0;
    uint64_t etw_thread_events = 0;
    uint64_t etw_image_loads = 0;
    std::wstring etw_status;
    std::wstring etw_error;
    std::vector<EtwTimelineEvent> etw_timeline;
    std::set<DWORD> etw_interesting_pids;
    std::vector<DumpRecord> dumps;
    std::vector<OriginRegionDumpRecord> origin_region_dumps;
    std::vector<MemoryAuditFinding> memory_audit_findings;
    std::vector<ByoudTraceRecord> byoud_trace_records;
    std::vector<ShadowStackTraceRecord> shadow_stack_records;
    std::vector<DllLoadMemoryObservation> dll_load_memory;
    std::vector<NetworkUseObservation> network_use_records;
    std::vector<CallbackObservation> callback_observations;
    std::vector<LdrTamperObservation> ldr_tamper_observations;
    std::map<std::wstring, uint64_t> decision_counts;
    std::set<std::wstring> byoud_trace_keys;
    std::set<std::wstring> shadow_stack_keys;
    std::map<DWORD, HANDLE> process_handles;
    std::map<DWORD, ProcessState> processes;
    std::set<uint64_t> dumped_allocation_bases;
    std::set<uint64_t> dumped_origin_region_keys;
    std::map<uint64_t, ModuleIntegrityInfo> module_integrity_cache;
    bool full_stack_output = false;
    std::atomic<bool> stop_collection{ false };
    std::mutex write_mutex;
    std::mutex event_mutex;
    std::mutex etw_mutex;
};

static const fs::path& CurrentOutputDirectory(const RunState& state) {
    if (state.active_process_state && !state.active_process_state->out_dir.empty()) {
        return state.active_process_state->out_dir;
    }
    return state.active_out_dir.empty() ? state.out_dir : state.active_out_dir;
}

static std::wstring CurrentMainModuleName(const RunState& state) {
    if (state.active_process_state && !state.active_process_state->main_module_name.empty()) {
        return state.active_process_state->main_module_name;
    }
    return state.active_main_module_name.empty() ? state.main_module_name : state.active_main_module_name;
}

static ProcessState* CurrentProcessState(RunState& state) {
    if (state.active_process_state) {
        return state.active_process_state;
    }
    auto found = state.processes.find(state.pid);
    return found == state.processes.end() ? nullptr : &found->second;
}

static const ProcessState* CurrentProcessState(const RunState& state) {
    if (state.active_process_state) {
        return state.active_process_state;
    }
    auto found = state.processes.find(state.pid);
    return found == state.processes.end() ? nullptr : &found->second;
}

static std::wstring ToLower(std::wstring value) {
    std::transform(value.begin(), value.end(), value.begin(), [](wchar_t ch) {
        return static_cast<wchar_t>(towlower(ch));
    });
    return value;
}

static std::wstring BasenameOf(const std::wstring& value) {
    const size_t pos = value.find_last_of(L"\\/:");
    if (pos == std::wstring::npos) {
        return value;
    }
    return value.substr(pos + 1);
}

static bool EqualsInsensitive(const std::wstring& a, const std::wstring& b) {
    return ToLower(a) == ToLower(b);
}

static bool ContainsInsensitive(const std::vector<std::wstring>& values, const std::wstring& candidate) {
    std::wstring lower = ToLower(BasenameOf(candidate));
    if (std::find(values.begin(), values.end(), lower) != values.end()) {
        return true;
    }
    const size_t last_sep = lower.find_last_of(L"\\/:");
    const std::wstring basename = last_sep == std::wstring::npos ? lower : lower.substr(last_sep + 1);
    if (basename.find(L'.') == std::wstring::npos) {
        lower += L".dll";
        return std::find(values.begin(), values.end(), lower) != values.end();
    }
    return false;
}

static void NormalizeModuleList(std::vector<std::wstring>& values) {
    std::set<std::wstring> unique;
    for (auto& value : values) {
        const std::wstring normalized = ToLower(BasenameOf(value));
        if (!normalized.empty()) {
            unique.insert(normalized);
        }
    }
    values.assign(unique.begin(), unique.end());
}

static void MergeModuleList(std::vector<std::wstring>& destination, const std::vector<std::wstring>& source) {
    destination.insert(destination.end(), source.begin(), source.end());
    NormalizeModuleList(destination);
}

static std::string WideToUtf8(const std::wstring& value) {
    if (value.empty()) {
        return {};
    }
    const int needed = WideCharToMultiByte(CP_UTF8, 0, value.data(), static_cast<int>(value.size()),
        nullptr, 0, nullptr, nullptr);
    if (needed <= 0) {
        return {};
    }
    std::string output(static_cast<size_t>(needed), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), static_cast<int>(value.size()),
        output.data(), needed, nullptr, nullptr);
    return output;
}

static std::string JsonEscape(const std::string& value) {
    std::ostringstream out;
    for (const unsigned char ch : value) {
        switch (ch) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20) {
                out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(ch);
            } else {
                out << ch;
            }
        }
    }
    return out.str();
}

static std::string JsonString(const std::wstring& value) {
    return "\"" + JsonEscape(WideToUtf8(value)) + "\"";
}

static std::string JsonStringArray(const std::vector<std::wstring>& values) {
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) {
            out << ",";
        }
        out << JsonString(values[i]);
    }
    out << "]";
    return out.str();
}

static std::string Hex64(uint64_t value) {
    std::ostringstream out;
    out << "0x" << std::hex << std::uppercase << std::setw(16) << std::setfill('0') << value;
    return out.str();
}

static std::wstring Hex64Wide(uint64_t value) {
    std::wostringstream out;
    out << L"0x" << std::hex << std::uppercase << std::setw(16) << std::setfill(L'0') << value;
    return out.str();
}

static std::wstring HexRvaWide(uint64_t value) {
    std::wostringstream out;
    out << L"0x" << std::hex << std::uppercase << std::setw(8) << std::setfill(L'0')
        << static_cast<uint32_t>(value & 0xFFFFFFFFull);
    return out.str();
}

static bool ReadFileBytes(const fs::path& path, std::vector<uint8_t>& bytes) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return false;
    }
    input.seekg(0, std::ios::end);
    const std::streamoff size = input.tellg();
    if (size < 0) {
        return false;
    }
    input.seekg(0, std::ios::beg);
    bytes.resize(static_cast<size_t>(size));
    if (!bytes.empty()) {
        input.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    }
    return true;
}

static double CalculateEntropy(const std::vector<uint8_t>& bytes) {
    if (bytes.empty()) {
        return 0.0;
    }
    std::array<uint64_t, 256> counts{};
    for (uint8_t byte : bytes) {
        ++counts[byte];
    }
    double entropy = 0.0;
    const double total = static_cast<double>(bytes.size());
    for (uint64_t count : counts) {
        if (!count) {
            continue;
        }
        const double p = static_cast<double>(count) / total;
        entropy -= p * std::log2(p);
    }
    return entropy;
}

static std::wstring Sha256Hex(const std::vector<uint8_t>& bytes) {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    std::wstring result;

    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) != 0) {
        return result;
    }

    DWORD object_length = 0;
    DWORD returned = 0;
    if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&object_length),
        sizeof(object_length), &returned, 0) != 0) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
        return result;
    }

    std::vector<uint8_t> object_buffer(object_length);
    std::array<uint8_t, 32> hash_buffer{};
    if (BCryptCreateHash(algorithm, &hash, object_buffer.data(), object_length, nullptr, 0, 0) == 0 &&
        BCryptHashData(hash, const_cast<PUCHAR>(bytes.data()), static_cast<ULONG>(bytes.size()), 0) == 0 &&
        BCryptFinishHash(hash, hash_buffer.data(), static_cast<ULONG>(hash_buffer.size()), 0) == 0) {
        std::wostringstream out;
        out << std::hex << std::nouppercase << std::setfill(L'0');
        for (uint8_t byte : hash_buffer) {
            out << std::setw(2) << static_cast<unsigned int>(byte);
        }
        result = out.str();
    }

    if (hash) {
        BCryptDestroyHash(hash);
    }
    BCryptCloseAlgorithmProvider(algorithm, 0);
    return result;
}

static bool IsExecutableProtect(DWORD protect) {
    const DWORD clean = protect & ~(PAGE_GUARD | PAGE_NOCACHE | PAGE_WRITECOMBINE);
    return clean == PAGE_EXECUTE ||
        clean == PAGE_EXECUTE_READ ||
        clean == PAGE_EXECUTE_READWRITE ||
        clean == PAGE_EXECUTE_WRITECOPY;
}

static std::wstring ProtectToString(DWORD protect) {
    const DWORD clean = protect & ~(PAGE_GUARD | PAGE_NOCACHE | PAGE_WRITECOMBINE);
    switch (clean) {
    case PAGE_NOACCESS: return L"NOACCESS";
    case PAGE_READONLY: return L"R--";
    case PAGE_READWRITE: return L"RW-";
    case PAGE_WRITECOPY: return L"WC-";
    case PAGE_EXECUTE: return L"--X";
    case PAGE_EXECUTE_READ: return L"R-X";
    case PAGE_EXECUTE_READWRITE: return L"RWX";
    case PAGE_EXECUTE_WRITECOPY: return L"WCX";
    default: return L"UNKNOWN";
    }
}

static std::wstring TypeToString(DWORD type) {
    switch (type) {
    case MEM_IMAGE: return L"MEM_IMAGE";
    case MEM_MAPPED: return L"MEM_MAPPED";
    case MEM_PRIVATE: return L"MEM_PRIVATE";
    default: return L"UNKNOWN";
    }
}

static std::wstring StateToString(DWORD state) {
    switch (state) {
    case MEM_COMMIT: return L"MEM_COMMIT";
    case MEM_RESERVE: return L"MEM_RESERVE";
    case MEM_FREE: return L"MEM_FREE";
    default: return L"UNKNOWN";
    }
}

static std::wstring QuoteArg(const std::wstring& arg) {
    std::wstring result = L"\"";
    size_t backslashes = 0;
    for (wchar_t ch : arg) {
        if (ch == L'\\') {
            ++backslashes;
        } else if (ch == L'"') {
            result.append(backslashes * 2 + 1, L'\\');
            result.push_back(ch);
            backslashes = 0;
        } else {
            result.append(backslashes, L'\\');
            backslashes = 0;
            result.push_back(ch);
        }
    }
    result.append(backslashes * 2, L'\\');
    result.push_back(L'"');
    return result;
}

static std::wstring BuildCommandLine(const fs::path& target, const std::vector<std::wstring>& args) {
    std::wstring command = QuoteArg(target.wstring());
    for (const auto& arg : args) {
        command.push_back(L' ');
        command += QuoteArg(arg);
    }
    return command;
}

