static std::wstring OriginKindToString(uint32_t kind) {
    switch (kind) {
    case kMonitorOriginLoaderApiPointer: return L"loader_api_pointer";
    case kMonitorOriginDllStringPointer: return L"dll_string_pointer";
    case kMonitorOriginGadgetPointer: return L"gadget_pointer";
    case kMonitorOriginProxyTransfer: return L"proxy_transfer";
    case kMonitorOriginShadowStackFrame: return L"shadow_stack_frame";
    default: return L"none";
    }
}

static std::wstring OriginRegisterToString(uint32_t reg) {
    switch (reg) {
    case kMonitorRegRax: return L"RAX";
    case kMonitorRegRbx: return L"RBX";
    case kMonitorRegRcx: return L"RCX";
    case kMonitorRegRdx: return L"RDX";
    case kMonitorRegRsi: return L"RSI";
    case kMonitorRegRdi: return L"RDI";
    case kMonitorRegRbp: return L"RBP";
    case kMonitorRegRsp: return L"RSP";
    case kMonitorRegR8: return L"R8";
    case kMonitorRegR9: return L"R9";
    case kMonitorRegR10: return L"R10";
    case kMonitorRegR11: return L"R11";
    case kMonitorRegR12: return L"R12";
    case kMonitorRegR13: return L"R13";
    case kMonitorRegR14: return L"R14";
    case kMonitorRegR15: return L"R15";
    case kMonitorRegRip: return L"RIP";
    default: return L"";
    }
}

static void WriteOriginRecordJson(std::ofstream& output, const MonitorOriginRecord& record) {
    output
        << "{"
        << "\"kind\":" << JsonString(OriginKindToString(record.kind)) << ","
        << "\"register\":" << JsonString(OriginRegisterToString(record.reg)) << ","
        << "\"writer_rip\":\"" << Hex64(record.writer_rip) << "\","
        << "\"value\":\"" << Hex64(record.value) << "\","
        << "\"target_rip\":\"" << Hex64(record.target_rip) << "\","
        << "\"tick_ms\":" << record.tick_ms << ","
        << "\"source_tid\":" << record.source_tid << ","
        << "\"target_tid\":" << record.target_tid << ","
        << "\"message\":" << record.message << ","
        << "\"origin_flags\":" << record.origin_flags << ","
        << "\"dispatch_wparam\":\"" << Hex64(record.dispatch_wparam) << "\","
        << "\"dispatch_lparam\":\"" << Hex64(record.dispatch_lparam) << "\","
        << "\"name\":" << JsonString(record.name) << ","
        << "\"value_name\":" << JsonString(record.value_name)
        << "}";
}

struct OriginTraceResult {
    bool present = false;
    bool from_register_trace = false;
    bool from_callback_context = false;
    bool from_dispatch_trace = false;
    bool from_function_proxy_trace = false;
    bool hidden_from_stack = false;
    int confidence_score = 0;
    uint64_t address = 0;
    uint64_t value = 0;
    uint64_t target = 0;
    std::wstring confidence;
    std::wstring source;
    std::wstring kind;
    std::wstring reg;
    std::wstring label;
    std::wstring evidence;
    bool dispatch_wait_observed = false;
    uint32_t dispatch_source_tid = 0;
    uint32_t dispatch_target_tid = 0;
    uint32_t dispatch_message = 0;
    uint64_t dispatch_wparam = 0;
    uint64_t dispatch_lparam = 0;
    std::wstring dispatch_api;
    std::wstring dispatch_function;
    std::wstring dispatch_argument;
};

static void WriteOriginTraceResultJson(std::ofstream& output, const OriginTraceResult& origin) {
    output
        << "{"
        << "\"present\":" << (origin.present ? "true" : "false") << ","
        << "\"confidence\":" << JsonString(origin.confidence) << ","
        << "\"source\":" << JsonString(origin.source) << ","
        << "\"kind\":" << JsonString(origin.kind) << ","
        << "\"register\":" << JsonString(origin.reg) << ","
        << "\"hidden_from_stack\":" << (origin.hidden_from_stack ? "true" : "false") << ","
        << "\"address\":\"" << Hex64(origin.address) << "\","
        << "\"value\":\"" << Hex64(origin.value) << "\","
        << "\"target\":\"" << Hex64(origin.target) << "\","
        << "\"label\":" << JsonString(origin.label) << ","
        << "\"evidence\":" << JsonString(origin.evidence) << ","
        << "\"function_proxy_trace\":" << (origin.from_function_proxy_trace ? "true" : "false") << ","
        << "\"dispatch_trace\":{"
        << "\"present\":" << (origin.from_dispatch_trace ? "true" : "false") << ","
        << "\"requester_tid\":" << origin.dispatch_source_tid << ","
        << "\"worker_tid\":" << origin.dispatch_target_tid << ","
        << "\"message\":" << origin.dispatch_message << ","
        << "\"wparam\":\"" << Hex64(origin.dispatch_wparam) << "\","
        << "\"lparam\":\"" << Hex64(origin.dispatch_lparam) << "\","
        << "\"wait_observed\":" << (origin.dispatch_wait_observed ? "true" : "false") << ","
        << "\"api\":" << JsonString(origin.dispatch_api) << ","
        << "\"function\":" << JsonString(origin.dispatch_function) << ","
        << "\"argument\":" << JsonString(origin.dispatch_argument)
        << "}"
        << "}";
}

static void WriteOriginRegionDumpJson(std::ofstream& output, const OriginRegionDumpRecord* record) {
    if (!record) {
        output << "{\"present\":false}";
        return;
    }
    output
        << "{"
        << "\"present\":true,"
        << "\"path\":" << JsonString(record->path) << ","
        << "\"dump_base\":\"" << Hex64(record->dump_base) << "\","
        << "\"dump_size\":" << record->dump_size << ","
        << "\"origin_address\":\"" << Hex64(record->origin_address) << "\","
        << "\"origin_rva\":\"" << Hex64(record->origin_rva) << "\","
        << "\"module_base\":\"" << Hex64(record->module_base) << "\","
        << "\"module_name\":" << JsonString(record->module_name) << ","
        << "\"module_path\":" << JsonString(record->module_path) << ","
        << "\"visible_caller_address\":\"" << Hex64(record->visible_caller_address) << "\","
        << "\"visible_caller_label\":" << JsonString(record->visible_caller_label) << ","
        << "\"evidence\":" << JsonString(record->evidence) << ","
        << "\"analysis\":{"
        << "\"analyzed\":" << (record->analysis.analyzed ? "true" : "false") << ","
        << "\"sha256\":" << JsonString(record->analysis.sha256) << ","
        << "\"entropy\":" << std::fixed << std::setprecision(4) << record->analysis.entropy << ","
        << "\"strings\":" << JsonStringArray(record->analysis.strings)
        << "}"
        << "}";
}

struct DetectionDecision {
    std::wstring confidence = L"telemetry_only";
    bool has_stack_evidence = false;
    bool has_memory_evidence = false;
    bool has_module_integrity_evidence = false;
    bool has_origin_trace_evidence = false;
    bool has_callback_correlation = false;
    bool has_gadget_suspicion = false;
    bool proof = false;
};

static void WriteDetectionDecisionJson(std::ofstream& output, const DetectionDecision& decision) {
    output
        << "{"
        << "\"confidence\":" << JsonString(decision.confidence) << ","
        << "\"proof\":" << (decision.proof ? "true" : "false") << ","
        << "\"evidence\":{"
        << "\"stack\":" << (decision.has_stack_evidence ? "true" : "false") << ","
        << "\"memory\":" << (decision.has_memory_evidence ? "true" : "false") << ","
        << "\"module_integrity\":" << (decision.has_module_integrity_evidence ? "true" : "false") << ","
        << "\"origin_trace\":" << (decision.has_origin_trace_evidence ? "true" : "false") << ","
        << "\"callback_correlation\":" << (decision.has_callback_correlation ? "true" : "false") << ","
        << "\"gadget_suspicion\":" << (decision.has_gadget_suspicion ? "true" : "false")
        << "}"
        << "}";
}

static void WriteLdrIntegrityJson(std::ofstream& output, const MonitorEvent& event) {
    output
        << "{"
        << "\"present\":" << (event.event_type == kMonitorEventLdrIntegrity ? "true" : "false") << ","
        << "\"table_entry\":\"" << Hex64(event.ldr_table_entry) << "\","
        << "\"dll_base\":\"" << Hex64(event.ldr_dll_base) << "\","
        << "\"size_of_image\":" << event.ldr_size_of_image << ","
        << "\"entrypoint\":\"" << Hex64(event.ldr_entrypoint) << "\","
        << "\"expected_entrypoint\":\"" << Hex64(event.ldr_expected_entrypoint) << "\","
        << "\"original_base\":\"" << Hex64(event.ldr_original_base) << "\","
        << "\"entrypoint_region\":{"
        << "\"base\":\"" << Hex64(event.ldr_entrypoint_region_base) << "\","
        << "\"size\":" << event.ldr_entrypoint_region_size << ","
        << "\"protect\":" << JsonString(ProtectToString(event.ldr_entrypoint_protect)) << ","
        << "\"type\":" << JsonString(TypeToString(event.ldr_entrypoint_type))
        << "},"
        << "\"original_base_region\":{"
        << "\"base\":\"" << Hex64(event.ldr_original_base_region_base) << "\","
        << "\"size\":" << event.ldr_original_base_region_size << ","
        << "\"protect\":" << JsonString(ProtectToString(event.ldr_original_base_protect)) << ","
        << "\"type\":" << JsonString(TypeToString(event.ldr_original_base_type))
        << "}"
        << "}";
}

static void WriteEventJson(RunState& state, const MonitorEvent& event, const std::vector<FrameInfo>& frames,
    const FrameInfo* callback_frame, const FrameInfo* event_value_frame, const std::wstring& summary, bool alert, int score,
    const std::vector<std::wstring>& rule_hits, const std::vector<DumpRecord>& event_dumps,
    const std::vector<ByoudTraceRecord>& event_byoud_records,
    const std::vector<ShadowStackTraceRecord>& event_shadow_stack_records,
    const OriginTraceResult& origin_trace, const OriginRegionDumpRecord* origin_region_dump,
    const DetectionDecision& decision) {
    std::lock_guard<std::mutex> lock(state.write_mutex);
    state.events
        << "{"
        << "\"pid\":" << event.pid << ","
        << "\"tid\":" << event.tid << ","
        << "\"event_type\":" << JsonString(EventTypeToString(event.event_type)) << ","
        << "\"event_name\":" << JsonString(event.event_name) << ","
        << "\"target\":" << JsonString(event.target_name) << ","
        << "\"status\":" << event.status << ","
        << "\"event_value\":" << event.event_value << ","
        << "\"event_value_hex\":\"" << Hex64(event.event_value) << "\","
        << "\"event_flags\":" << event.event_flags << ","
        << "\"alert\":" << (alert ? "true" : "false") << ","
        << "\"score\":" << score << ","
        << "\"stack_summary\":" << JsonString(summary) << ",";

    state.events << "\"rule_hits\":[";
    for (size_t i = 0; i < rule_hits.size(); ++i) {
        if (i) {
            state.events << ",";
        }
        state.events << JsonString(rule_hits[i]);
    }
    state.events << "],";

    if (callback_frame) {
        state.events << "\"callback_address\":\"" << Hex64(event.callback_address) << "\",";
        state.events << "\"callback_frame\":";
        WriteFrameJson(state.events, *callback_frame);
        state.events << ",";
    }

    if (event.event_type == kMonitorEventDllLoad && event.event_value != 0) {
        state.events << "\"loaded_module_base\":\"" << Hex64(event.event_value) << "\",";
    }

    state.events << "\"registers\":{"
        << "\"rip\":\"" << Hex64(event.registers.rip) << "\","
        << "\"rsp\":\"" << Hex64(event.registers.rsp) << "\","
        << "\"rax\":\"" << Hex64(event.registers.rax) << "\","
        << "\"rcx\":\"" << Hex64(event.registers.rcx) << "\","
        << "\"rdx\":\"" << Hex64(event.registers.rdx) << "\","
        << "\"r8\":\"" << Hex64(event.registers.r8) << "\","
        << "\"r9\":\"" << Hex64(event.registers.r9) << "\","
        << "\"r10\":\"" << Hex64(event.registers.r10) << "\","
        << "\"r11\":\"" << Hex64(event.registers.r11) << "\""
        << "},";
    state.events << "\"ldr_integrity\":";
    WriteLdrIntegrityJson(state.events, event);
    state.events << ",";

    state.events << "\"origin_trace_records\":[";
    for (uint32_t i = 0; i < std::min<uint32_t>(event.origin_record_count, kMonitorMaxOriginRecords); ++i) {
        if (i) {
            state.events << ",";
        }
        WriteOriginRecordJson(state.events, event.origin_records[i]);
    }
    state.events << "],";
    state.events << "\"origin_trace\":";
    WriteOriginTraceResultJson(state.events, origin_trace);
    state.events << ",";
    state.events << "\"decision\":";
    WriteDetectionDecisionJson(state.events, decision);
    state.events << ",";
    state.events << "\"byoud_trace\":[";
    for (size_t i = 0; i < event_byoud_records.size(); ++i) {
        if (i) {
            state.events << ",";
        }
        const auto& record = event_byoud_records[i];
        state.events
            << "{"
            << "\"rule\":" << JsonString(record.rule) << ","
            << "\"score\":" << record.score << ","
            << "\"confidence\":" << JsonString(record.confidence) << ","
            << "\"technique\":" << JsonString(record.technique) << ","
            << "\"module_name\":" << JsonString(record.module_name) << ","
            << "\"module_path\":" << JsonString(record.module_path) << ","
            << "\"section\":" << JsonString(record.section_name) << ","
            << "\"rva\":\"" << Hex64(record.rva) << "\","
            << "\"address\":\"" << Hex64(record.address) << "\","
            << "\"size\":" << record.size << ","
            << "\"old_value\":\"" << Hex64(record.old_value) << "\","
            << "\"new_value\":\"" << Hex64(record.new_value) << "\","
            << "\"detail\":" << JsonString(record.detail)
            << "}";
    }
    state.events << "]";
    if (!event_shadow_stack_records.empty()) {
        state.events << ",\"shadow_stack_trace\":[";
        for (size_t i = 0; i < event_shadow_stack_records.size(); ++i) {
            if (i) {
                state.events << ",";
            }
            const auto& record = event_shadow_stack_records[i];
            state.events
                << "{"
                << "\"rule\":" << JsonString(record.rule) << ","
                << "\"score\":" << record.score << ","
                << "\"confidence\":" << JsonString(record.confidence) << ","
                << "\"api_name\":" << JsonString(record.api_name) << ","
                << "\"dll_name\":" << JsonString(record.dll_name) << ","
                << "\"classic_stack\":" << JsonString(record.classic_stack) << ","
                << "\"shadow_stack\":" << JsonString(record.shadow_stack) << ","
                << "\"classic_frame_count\":" << record.classic_frame_count << ","
                << "\"shadow_frame_count\":" << record.shadow_frame_count << ","
                << "\"matched_shadow_frames\":" << record.matched_shadow_frames << ","
                << "\"missing_or_out_of_order_frames\":" << record.missing_or_out_of_order_frames << ","
                << "\"hidden_frame\":{"
                << "\"address\":\"" << Hex64(record.hidden_frame_address) << "\","
                << "\"label\":" << JsonString(record.hidden_frame_label) << ","
                << "\"module\":" << JsonString(record.hidden_frame_module) << ","
                << "\"path\":" << JsonString(record.hidden_frame_path)
                << "},"
                << "\"detail\":" << JsonString(record.detail)
                << "}";
        }
        state.events << "]";
    }
    state.events << ",";
    state.events << "\"origin_region_dump\":";
    WriteOriginRegionDumpJson(state.events, origin_region_dump);
    state.events << ",";

    if (event_value_frame) {
        state.events << "\"event_value_frame\":";
        WriteFrameJson(state.events, *event_value_frame);
        state.events << ",";
    }

    state.events << "\"frames\":[";
    bool first = true;
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        if (!first) {
            state.events << ",";
        }
        first = false;
        WriteFrameJson(state.events, frame);
    }
    state.events << "],";

    state.events << "\"dumps\":[";
    for (size_t i = 0; i < event_dumps.size(); ++i) {
        if (i) {
            state.events << ",";
        }
        state.events
            << "{"
            << "\"path\":" << JsonString(event_dumps[i].path) << ","
            << "\"allocation_base\":\"" << Hex64(event_dumps[i].base) << "\","
            << "\"requested_size\":" << event_dumps[i].requested_size << ","
            << "\"dumped_size\":" << event_dumps[i].dumped_size << ","
            << "\"trigger_address\":\"" << Hex64(event_dumps[i].trigger_address) << "\","
            << "\"trigger_region_base\":\"" << Hex64(event_dumps[i].trigger_region_base) << "\","
            << "\"analysis\":{"
            << "\"sha256\":" << JsonString(event_dumps[i].analysis.sha256) << ","
            << "\"entropy\":" << std::fixed << std::setprecision(4) << event_dumps[i].analysis.entropy << ","
            << "\"embedded_pe_count\":" << event_dumps[i].analysis.embedded_pes.size() << ","
            << "\"embedded_pes\":[";
        for (size_t j = 0; j < event_dumps[i].analysis.embedded_pes.size(); ++j) {
            if (j) {
                state.events << ",";
            }
            const auto& pe = event_dumps[i].analysis.embedded_pes[j];
            state.events << "{"
                << "\"offset\":\"" << Hex64(pe.offset) << "\","
                << "\"carved_size\":" << pe.carved_size << ","
                << "\"path\":" << JsonString(pe.path)
                << "}";
        }
        state.events << "]}"
            << "}";
    }
    state.events << "]";
    state.events << "}\n";
    state.events.flush();
}

static bool IsThreadOrApcCallbackApi(const std::wstring& api_name) {
    const std::wstring lower = ToLower(api_name);
    return lower == L"createthread" ||
        lower == L"queueuserapc" ||
        lower == L"ntcreatethreadex" ||
        lower == L"ntqueueapcthread" ||
        lower == L"tpallocwork" ||
        lower == L"tppostwork" ||
        lower == L"ntsetcontextthread" ||
        lower == L"setthreadcontext" ||
        lower == L"ntcontinue" ||
        lower == L"rtlrestorecontext" ||
        lower == L"vehripredirect" ||
        lower == L"addvectoredexceptionhandler" ||
        lower == L"rtladdvectoredexceptionhandler";
}

static bool IsSystemLikeModulePath(const std::wstring& path);

static bool IsCreateThreadpoolWorkApi(const std::wstring& api_name) {
    return EqualsInsensitive(api_name, L"CreateThreadpoolWork");
}

static bool IsLowSignalSystemBackedModifiedFrame(const FrameInfo& frame) {
    return frame.backed_modified &&
        !frame.captured_context_modified &&
        !frame.unbacked_executable &&
        !frame.unwind_metadata_tampered &&
        frame.type == MEM_IMAGE &&
        frame.module_modified_bytes > 0 &&
        frame.module_modified_bytes <= 64 &&
        IsSystemLikeModulePath(frame.module_path);
}

static bool IsSuspiciousFrame(const FrameInfo& frame) {
    return frame.unbacked_executable ||
        (frame.backed_modified && !IsLowSignalSystemBackedModifiedFrame(frame)) ||
        frame.unwind_metadata_tampered;
}

static bool HasStrongCallbackSuspiciousFrame(const std::wstring& api_name, const std::vector<FrameInfo>& frames) {
    static_cast<void>(api_name);
    for (const auto& frame : frames) {
        if (frame.monitor_frame) {
            continue;
        }
        if (frame.unbacked_executable || frame.unwind_metadata_tampered) {
            return true;
        }
        if (frame.backed_modified) {
            if (IsLowSignalSystemBackedModifiedFrame(frame)) {
                continue;
            }
            return true;
        }
    }
    return false;
}

static bool IsVehCallbackApi(const std::wstring& api_name) {
    const std::wstring lower = ToLower(api_name);
    return lower == L"vehripredirect" ||
        lower == L"addvectoredexceptionhandler" ||
        lower == L"rtladdvectoredexceptionhandler";
}

static bool IsContextRedirectApi(const std::wstring& api_name) {
    const std::wstring lower = ToLower(api_name);
    return lower == L"ntsetcontextthread" ||
        lower == L"setthreadcontext" ||
        lower == L"ntcontinue" ||
        lower == L"rtlrestorecontext";
}

static std::wstring FrameDisplayLabel(const FrameInfo& frame) {
    if (!frame.symbol_label.empty()) {
        return frame.symbol_label;
    }
    if (!frame.module_name.empty()) {
        return frame.module_name + L"+" + HexRvaWide(frame.module_offset);
    }
    if (!frame.summary_name.empty()) {
        return frame.summary_name + L"!" + Hex64Wide(frame.address);
    }
    return Hex64Wide(frame.address);
}

static std::wstring BuildStackDisplaySummary(const std::vector<FrameInfo>& frames) {
    std::wstring summary;
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        if (!summary.empty()) {
            summary += L"|";
        }
        summary += FrameDisplayLabel(frame);
    }
    return summary;
}

static bool IsMainModuleFrame(const RunState& state, const FrameInfo& frame) {
    return !frame.module_name.empty() && EqualsInsensitive(frame.module_name, CurrentMainModuleName(state));
}

static bool TextContainsInsensitive(const std::wstring& text, const std::wstring& needle) {
    return ToLower(text).find(ToLower(needle)) != std::wstring::npos;
}

static bool IsSystemLikeModulePath(const std::wstring& path) {
    if (path.empty()) {
        return true;
    }
    return TextContainsInsensitive(path, L"\\windows\\") ||
        TextContainsInsensitive(path, L"\\program files\\") ||
        TextContainsInsensitive(path, L"\\program files (x86)\\");
}

static bool IsTraceableUserCodeFrame(const RunState& state, const FrameInfo& frame) {
    if (frame.address == 0 || frame.monitor_frame || !frame.executable) {
        return false;
    }
    if (IsMainModuleFrame(state, frame)) {
        return true;
    }
    if (frame.unbacked_executable ||
        (frame.backed_modified && !IsLowSignalSystemBackedModifiedFrame(frame)) ||
        frame.unwind_metadata_tampered) {
        return true;
    }
    if (frame.type != MEM_IMAGE || frame.module_name.empty()) {
        return false;
    }
    if (ContainsInsensitive(state.rules.sensitive_modules, frame.module_name) ||
        ContainsInsensitive(state.rules.module_integrity_allowlist, frame.module_name)) {
        return false;
    }
    return !IsSystemLikeModulePath(frame.module_path);
}

static bool StackContainsAddressNear(const std::vector<FrameInfo>& frames, uint64_t address) {
    if (!address) {
        return false;
    }
    for (const auto& frame : frames) {
        if (!frame.address || frame.monitor_frame) {
            continue;
        }
        const uint64_t lower = frame.address > 0x20 ? frame.address - 0x20 : 0;
        const uint64_t upper = frame.address + 0x20;
        if (address >= lower && address <= upper) {
            return true;
        }
    }
    return false;
}

static bool AddressNear(uint64_t left, uint64_t right) {
    if (!left || !right) {
        return false;
    }
    const uint64_t lower = left > 0x20 ? left - 0x20 : 0;
    const uint64_t upper = left + 0x20;
    return right >= lower && right <= upper;
}

static bool StackContainsModuleName(const std::vector<FrameInfo>& frames, const std::wstring& module_name) {
    if (module_name.empty()) {
        return false;
    }
    for (const auto& frame : frames) {
        if (frame.monitor_frame || frame.module_name.empty()) {
            continue;
        }
        if (EqualsInsensitive(frame.module_name, module_name)) {
            return true;
        }
    }
    return false;
}

static bool StackContainsAnyModuleName(const std::vector<FrameInfo>& frames, const std::vector<std::wstring>& module_names) {
    for (const auto& module_name : module_names) {
        if (StackContainsModuleName(frames, module_name)) {
            return true;
        }
    }
    return false;
}

static void RecordCallbackObservation(RunState& state, const MonitorEvent& event, bool suspicious,
    bool origin_candidate, const std::wstring& label) {
    ProcessState* process_state = CurrentProcessState(state);
    auto& observations = process_state ? process_state->callback_observations : state.callback_observations;

    CallbackObservation observation;
    observation.callback_address = event.callback_address;
    observation.tid = event.tid;
    observation.event_index = state.events_total;
    observation.tick_ms = GetTickCount64();
    observation.suspicious = suspicious;
    observation.origin_candidate = origin_candidate;
    observation.api_name = event.event_name;
    observation.label = label;
    observations.push_back(std::move(observation));

    const uint64_t now = GetTickCount64();
    const uint64_t window = state.rules.correlation_window_ms;
    observations.erase(
        std::remove_if(observations.begin(), observations.end(),
            [&](const CallbackObservation& item) {
                return now > item.tick_ms && now - item.tick_ms > window;
            }),
        observations.end());
    if (observations.size() > 256) {
        observations.erase(observations.begin(),
            observations.begin() + (observations.size() - 256));
    }
}

static bool HasRecentSuspiciousCallback(const RunState& state, const MonitorEvent& event) {
    const uint64_t now = GetTickCount64();
    const uint64_t window = state.rules.correlation_window_ms;
    const ProcessState* process_state = CurrentProcessState(state);
    const auto& observations = process_state ? process_state->callback_observations : state.callback_observations;
    for (const auto& observation : observations) {
        if (!observation.suspicious) {
            continue;
        }
        if (now >= observation.tick_ms && now - observation.tick_ms <= window) {
            if (observation.tid == event.tid || event.event_type == kMonitorEventDllLoad || event.event_type == kMonitorEventMemoryApi) {
                return true;
            }
        }
    }
    return false;
}

static const CallbackObservation* FindRecentOriginCallback(const RunState& state, const MonitorEvent& event) {
    if (!state.rules.origin_trace ||
        (event.event_type != kMonitorEventDllLoad && event.event_type != kMonitorEventMemoryApi)) {
        return nullptr;
    }

    const uint64_t now = GetTickCount64();
    const uint64_t window = state.rules.correlation_window_ms;
    const CallbackObservation* best = nullptr;
    const ProcessState* process_state = CurrentProcessState(state);
    const auto& observations = process_state ? process_state->callback_observations : state.callback_observations;
    for (const auto& observation : observations) {
        if (!observation.origin_candidate) {
            continue;
        }
        if (now >= observation.tick_ms && now - observation.tick_ms <= window) {
            best = &observation;
        }
    }
    return best;
}

static void RecordLdrTamperObservation(RunState& state, const MonitorEvent& event) {
    ProcessState* process_state = CurrentProcessState(state);
    auto& observations = process_state ? process_state->ldr_tamper_observations : state.ldr_tamper_observations;

    LdrTamperObservation observation;
    observation.event_index = state.events_total;
    observation.tick_ms = GetTickCount64();
    observation.entrypoint = event.ldr_entrypoint;
    observation.module_name = event.target_name;
    observations.push_back(std::move(observation));

    const uint64_t now = GetTickCount64();
    const uint64_t window = std::max<uint32_t>(state.rules.correlation_window_ms, 15000);
    observations.erase(
        std::remove_if(observations.begin(), observations.end(),
            [&](const LdrTamperObservation& item) {
                return now > item.tick_ms && now - item.tick_ms > window;
            }),
        observations.end());
    if (observations.size() > 128) {
        observations.erase(observations.begin(),
            observations.begin() + (observations.size() - 128));
    }
}

static bool HasRecentLdrTamper(const RunState& state) {
    const ProcessState* process_state = CurrentProcessState(state);
    const auto& observations = process_state ? process_state->ldr_tamper_observations : state.ldr_tamper_observations;
    const uint64_t now = GetTickCount64();
    const uint64_t window = std::max<uint32_t>(state.rules.correlation_window_ms, 15000);
    for (const auto& observation : observations) {
        if (now >= observation.tick_ms && now - observation.tick_ms <= window) {
            return true;
        }
    }
    return false;
}

static std::wstring NormalizeModuleBasenameWithExtension(const std::wstring& name) {
    std::wstring normalized = ToLower(BasenameOf(name));
    if (!normalized.empty() && normalized.find(L'.') == std::wstring::npos) {
        normalized += L".dll";
    }
    return normalized;
}

static const ModuleInfo* FindLoadedModuleForDllEvent(const std::vector<ModuleInfo>& modules, const MonitorEvent& event) {
    if (event.event_value != 0) {
        if (const ModuleInfo* by_address = FindModuleForAddress(modules, event.event_value)) {
            return by_address;
        }
    }

    const std::wstring expected = NormalizeModuleBasenameWithExtension(event.target_name);
    for (const auto& module : modules) {
        if (NormalizeModuleBasenameWithExtension(module.name) == expected ||
            NormalizeModuleBasenameWithExtension(module.path) == expected) {
            return &module;
        }
    }
    return nullptr;
}

static bool HasMonitorFrameSnapshot(const MonitorEvent& event, uint32_t index) {
    return index < kMonitorMaxFrames &&
        (event.frame_region_base[index] != 0 ||
            event.frame_allocation_base[index] != 0 ||
            event.frame_module_base[index] != 0 ||
            event.frame_state[index] != 0 ||
            event.frame_module_name[index][0] != L'\0');
}

static void ApplyMonitorFrameSnapshot(const MonitorEvent& event, uint32_t index, FrameInfo& frame) {
    if (!HasMonitorFrameSnapshot(event, index)) {
        return;
    }

    const bool classification_missing =
        frame.state == 0 ||
        frame.summary_name.empty() ||
        frame.summary_name == L"Unknown" ||
        (frame.module_base == 0 && event.frame_module_base[index] != 0);
    if (!classification_missing) {
        return;
    }

    if (event.frame_allocation_base[index] != 0) {
        frame.allocation_base = event.frame_allocation_base[index];
    }
    if (event.frame_allocation_size[index] != 0) {
        frame.allocation_size = event.frame_allocation_size[index];
    }
    if (event.frame_region_base[index] != 0) {
        frame.region_base = event.frame_region_base[index];
    }
    if (event.frame_region_size[index] != 0) {
        frame.region_size = event.frame_region_size[index];
    }
    if (event.frame_state[index] != 0) {
        frame.state = event.frame_state[index];
    }
    if (event.frame_protect[index] != 0) {
        frame.protect = event.frame_protect[index];
    }
    if (event.frame_allocation_protect[index] != 0) {
        frame.allocation_protect = event.frame_allocation_protect[index];
    }
    if (event.frame_type[index] != 0) {
        frame.type = event.frame_type[index];
    }

    frame.executable = frame.state == MEM_COMMIT && IsExecutableProtect(frame.protect);

    if (event.frame_module_base[index] != 0) {
        frame.module_base = event.frame_module_base[index];
        frame.module_offset = frame.address >= frame.module_base ? frame.address - frame.module_base : 0;
        if (event.frame_module_name[index][0] != L'\0') {
            frame.module_name = event.frame_module_name[index];
            frame.summary_name = ToLower(frame.module_name);
            frame.symbol_label = frame.module_name + L"+" + HexRvaWide(frame.module_offset);
            frame.monitor_frame = EqualsInsensitive(frame.module_name, L"CallstackMonitor.dll");
            frame.jit_managed = IsManagedModuleName(frame.module_name);
        }
    } else if (frame.type == MEM_IMAGE) {
        frame.summary_name = L"Image";
    } else if (frame.type == MEM_MAPPED) {
        frame.summary_name = L"Mapped";
    }

    if (frame.executable &&
        (frame.type == MEM_PRIVATE ||
            (frame.type == MEM_MAPPED && frame.module_name.empty() && frame.module_path.empty()))) {
        frame.suspicious = true;
        frame.unbacked_executable = true;
        frame.summary_name = L"Unbacked";
        frame.symbol_label = L"Unbacked!" + Hex64Wide(frame.address);
    } else if (frame.symbol_label.empty() || frame.symbol_label == Hex64Wide(frame.address)) {
        frame.symbol_label = frame.summary_name == L"Unknown" ? Hex64Wide(frame.address) : frame.summary_name + L"!" + Hex64Wide(frame.address);
    }
}

static bool IsLoaderStackFrameName(const std::wstring& name) {
    const std::wstring lower = ToLower(BasenameOf(name));
    return lower == L"ntdll.dll" ||
        lower == L"kernelbase.dll" ||
        lower == L"kernel32.dll" ||
        lower == L"wow64.dll" ||
        lower == L"wow64cpu.dll";
}

struct StackAuditResult {
    bool enabled = false;
    bool system_only_sensitive_stack = false;
    bool terminal_frame_not_last = false;
    bool thread_start_frame_too_high = false;
    bool callsite_anomaly = false;
    uint32_t suspicious_frame_count = 0;
};

static bool IsCoreLoaderFrame(const FrameInfo& frame) {
    if (frame.monitor_frame || frame.address == 0) {
        return true;
    }
    return IsLoaderStackFrameName(!frame.module_name.empty() ? frame.module_name : frame.summary_name);
}

static bool IsRtlUserThreadStartLikeFrame(const FrameInfo& frame) {
    const std::wstring name = ToLower(!frame.module_name.empty() ? frame.module_name : frame.summary_name);
    if (name != L"ntdll.dll") {
        return false;
    }

    const uint64_t offset = frame.module_offset;
    HMODULE local = GetModuleHandleW(L"ntdll.dll");
    void* proc = local ? reinterpret_cast<void*>(GetProcAddress(local, "RtlUserThreadStart")) : nullptr;
    if (proc) {
        const uint64_t rva = reinterpret_cast<uint64_t>(proc) - reinterpret_cast<uint64_t>(local);
        return offset >= rva && offset < rva + 0x200;
    }
    return false;
}

static bool IsBaseThreadInitThunkLikeFrame(const FrameInfo& frame) {
    const std::wstring name = ToLower(!frame.module_name.empty() ? frame.module_name : frame.summary_name);
    if (name != L"kernel32.dll") {
        return false;
    }

    const uint64_t offset = frame.module_offset;
    HMODULE local = GetModuleHandleW(L"kernel32.dll");
    void* proc = local ? reinterpret_cast<void*>(GetProcAddress(local, "BaseThreadInitThunk")) : nullptr;
    if (proc) {
        const uint64_t rva = reinterpret_cast<uint64_t>(proc) - reinterpret_cast<uint64_t>(local);
        return offset >= rva && offset < rva + 0x200;
    }
    return false;
}

static StackAuditResult RunStackAudit(const RunState& state, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames, bool has_callsite_anomaly) {
    StackAuditResult result;
    result.enabled = state.rules.stack_audit;
    if (!result.enabled ||
        event.event_type != kMonitorEventDllLoad ||
        !IsNetworkModule(state.rules, event.target_name)) {
        return result;
    }

    bool has_user_or_nonloader_frame = false;
    size_t visible_count = 0;
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        ++visible_count;
    }

    size_t visible_index = 0;
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        if (frame.return_address_without_call || frame.tail_call_proxy) {
            result.callsite_anomaly = true;
            ++result.suspicious_frame_count;
        }
        if (IsRtlUserThreadStartLikeFrame(frame)) {
            if (visible_index + 1 != visible_count) {
                result.terminal_frame_not_last = true;
            }
            if (visible_index < 2) {
                result.thread_start_frame_too_high = true;
            }
        } else if (IsBaseThreadInitThunkLikeFrame(frame)) {
            if (visible_index + 2 < visible_count) {
                result.thread_start_frame_too_high = true;
            }
        }
        if (!IsCoreLoaderFrame(frame)) {
            has_user_or_nonloader_frame = true;
        }
        ++visible_index;
    }

    result.callsite_anomaly = result.callsite_anomaly || has_callsite_anomaly;
    result.system_only_sensitive_stack = visible_count >= 2 && !has_user_or_nonloader_frame;
    return result;
}

struct ShadowStackEvidenceSummary {
    bool present = false;
    bool alert = false;
    int score = 0;
    std::vector<std::wstring> rules;
    std::vector<FrameInfo> frames;
    std::vector<ShadowStackTraceRecord> event_records;
};

static bool IsShadowStackSensitiveEvent(const RunState& state, const MonitorEvent& event) {
    if (event.event_type == kMonitorEventDllLoad) {
        return IsWatchedByRules(state.rules, event.target_name);
    }
    return event.event_type == kMonitorEventMemoryApi ||
        event.event_type == kMonitorEventSleepWait;
}

static std::vector<FrameInfo> ExtractShadowStackFrames(RunState& state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event) {
    std::vector<FrameInfo> shadow_frames;
    if (!state.rules.shadow_stack || event.origin_record_count == 0) {
        return shadow_frames;
    }

    const uint32_t count = std::min<uint32_t>(event.origin_record_count, kMonitorMaxOriginRecords);
    for (uint32_t i = 0; i < count; ++i) {
        const MonitorOriginRecord& record = event.origin_records[i];
        if (record.kind != kMonitorOriginShadowStackFrame || record.writer_rip == 0) {
            continue;
        }
        shadow_frames.push_back(ClassifyFrame(state.process, modules, record.writer_rip));
    }
    if (!shadow_frames.empty()) {
        ApplyModuleIntegrity(state, modules, shadow_frames);
        ApplyCallsiteValidation(state, shadow_frames);
    }
    return shadow_frames;
}

static bool ShadowFrameIsInterestingOrigin(const RunState& state, const FrameInfo& frame) {
    if (frame.address == 0 || frame.monitor_frame || IsCoreLoaderFrame(frame)) {
        return false;
    }
    return IsSuspiciousFrame(frame) ||
        frame.return_address_without_call ||
        frame.tail_call_proxy ||
        frame.suspicious_gadget_frame ||
        IsTraceableUserCodeFrame(state, frame);
}

struct ShadowStackSequenceComparison {
    uint32_t classic_count = 0;
    uint32_t shadow_count = 0;
    uint32_t matched = 0;
    uint32_t missing_or_out_of_order = 0;
    const FrameInfo* first_missing = nullptr;
    const FrameInfo* first_interesting_missing = nullptr;
};

static bool IsComparableShadowStackFrame(const FrameInfo& frame) {
    return frame.address != 0 && !frame.monitor_frame;
}

static ShadowStackSequenceComparison CompareShadowStackSequences(const RunState& state,
    const std::vector<FrameInfo>& classic_frames, const std::vector<FrameInfo>& shadow_frames) {
    ShadowStackSequenceComparison result;
    for (const auto& frame : classic_frames) {
        if (IsComparableShadowStackFrame(frame)) {
            ++result.classic_count;
        }
    }

    size_t classic_cursor = 0;
    for (const auto& shadow : shadow_frames) {
        if (!IsComparableShadowStackFrame(shadow)) {
            continue;
        }
        ++result.shadow_count;

        bool matched = false;
        while (classic_cursor < classic_frames.size()) {
            const FrameInfo& classic = classic_frames[classic_cursor++];
            if (!IsComparableShadowStackFrame(classic)) {
                continue;
            }
            if (AddressNear(classic.address, shadow.address)) {
                matched = true;
                ++result.matched;
                break;
            }
        }

        if (!matched) {
            ++result.missing_or_out_of_order;
            if (!result.first_missing) {
                result.first_missing = &shadow;
            }
            if (!result.first_interesting_missing && ShadowFrameIsInterestingOrigin(state, shadow)) {
                result.first_interesting_missing = &shadow;
            }
        }
    }
    return result;
}

static void AddShadowStackRule(ShadowStackEvidenceSummary& summary, const std::wstring& rule, int score) {
    summary.present = true;
    summary.score = std::max(summary.score, score);
    if (std::find(summary.rules.begin(), summary.rules.end(), rule) == summary.rules.end()) {
        summary.rules.push_back(rule);
    }
}

static bool AddShadowStackTraceRecord(RunState& state, ProcessState& process_state,
    const ShadowStackTraceRecord& record) {
    std::wostringstream key;
    key << record.event_index << L":" << record.pid << L":" << record.tid << L":"
        << record.rule << L":" << Hex64Wide(record.hidden_frame_address);
    if (!state.shadow_stack_keys.insert(key.str()).second ||
        !process_state.shadow_stack_keys.insert(key.str()).second) {
        return false;
    }

    ++state.shadow_stack_total;
    ++process_state.shadow_stack_total;
    if (record.alert) {
        ++state.shadow_stack_alerts_total;
        ++process_state.shadow_stack_alerts_total;
    }
    state.shadow_stack_records.push_back(record);
    process_state.shadow_stack_records.push_back(record);
    return true;
}

static uint32_t CountShadowStackFrameRecords(const MonitorEvent& event) {
    uint32_t count = 0;
    const uint32_t origin_count = std::min<uint32_t>(event.origin_record_count, kMonitorMaxOriginRecords);
    for (uint32_t i = 0; i < origin_count; ++i) {
        if (event.origin_records[i].kind == kMonitorOriginShadowStackFrame &&
            event.origin_records[i].writer_rip != 0) {
            ++count;
        }
    }
    return count;
}

static ShadowStackEvidenceSummary CollectShadowStackEvidence(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& classic_frames, const StackAuditResult& stack_audit) {
    ShadowStackEvidenceSummary summary;
    if (!state.rules.shadow_stack || !IsShadowStackSensitiveEvent(state, event)) {
        return summary;
    }

    summary.frames = ExtractShadowStackFrames(state, modules, event);
    if (summary.frames.empty()) {
        return summary;
    }

    const std::wstring classic_summary = BuildStackSummary(classic_frames);
    const std::wstring shadow_summary = BuildStackSummary(summary.frames);
    const ShadowStackSequenceComparison sequence =
        CompareShadowStackSequences(state, classic_frames, summary.frames);
    const bool sequence_mismatch = sequence.missing_or_out_of_order > 0;

    const FrameInfo* hidden = sequence.first_interesting_missing;
    for (const auto& frame : summary.frames) {
        if (hidden) {
            break;
        }
        if (!ShadowFrameIsInterestingOrigin(state, frame)) {
            continue;
        }
        if (StackContainsAddressNear(classic_frames, frame.address)) {
            continue;
        }
        hidden = &frame;
        break;
    }

    const FrameInfo* evidence_frame = hidden ? hidden : sequence.first_missing;
    if (!evidence_frame) {
        return summary;
    }

    const bool strong_hidden_origin =
        hidden &&
        (IsSuspiciousFrame(*hidden) ||
            hidden->unbacked_executable ||
            hidden->backed_modified ||
            hidden->unwind_metadata_tampered ||
            IsMainModuleFrame(state, *hidden));

    ShadowStackTraceRecord record;
    record.event_index = state.events_total;
    record.pid = event.pid;
    record.tid = event.tid;
    record.api_name = event.event_name;
    if (event.event_type == kMonitorEventDllLoad) {
        record.dll_name = event.target_name;
    }
    record.classic_stack = classic_summary;
    record.shadow_stack = shadow_summary;
    record.classic_frame_count = sequence.classic_count;
    record.shadow_frame_count = sequence.shadow_count;
    record.matched_shadow_frames = sequence.matched;
    record.missing_or_out_of_order_frames = sequence.missing_or_out_of_order;
    record.hidden_frame_address = evidence_frame->address;
    record.hidden_frame_label = FrameDisplayLabel(*evidence_frame);
    record.hidden_frame_module = evidence_frame->module_name;
    record.hidden_frame_path = evidence_frame->module_path;

    if (strong_hidden_origin) {
        record.rule = L"shadow_stack_reveals_hidden_sensitive_origin";
        record.score = event.event_type == kMonitorEventDllLoad ? 90 : 80;
        record.confidence = L"high";
        record.detail = L"CET/HSP shadow stack retained a user/suspicious return frame that the classic unwind stack did not show";
    } else if (sequence_mismatch) {
        record.rule = L"shadow_stack_frames_missing_or_out_of_order";
        record.score = event.event_type == kMonitorEventDllLoad && stack_audit.system_only_sensitive_stack ? 85 :
            (event.event_type == kMonitorEventDllLoad ? 80 : 65);
        record.confidence = event.event_type == kMonitorEventDllLoad ? L"high" : L"medium";
        record.detail = L"CET/HSP shadow stack return sequence is not preserved as an ordered subsequence of the classic unwind stack";
    } else if (event.event_type == kMonitorEventDllLoad && stack_audit.system_only_sensitive_stack) {
        record.rule = L"shadow_stack_classic_stack_truncated";
        record.score = 75;
        record.confidence = L"medium";
        record.detail = L"classic DLL-load stack was loader-only while the shadow stack still exposed a non-loader caller";
    } else {
        record.rule = L"shadow_stack_stackwalk_disagreement";
        record.score = 40;
        record.confidence = L"medium";
        record.detail = L"classic unwind stack and CET/HSP shadow stack disagree on a non-loader return frame";
    }
    record.alert = record.score >= 75;

    AddShadowStackRule(summary, record.rule, record.score);
    summary.alert = record.alert;
    if (AddShadowStackTraceRecord(state, process_state, record)) {
        summary.event_records.push_back(record);
    }
    return summary;
}

static const FrameInfo* SelectDllLoadCallerFrame(const std::vector<FrameInfo>& frames) {
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        if (frame.unbacked_executable ||
            frame.backed_modified ||
            frame.suspicious_gadget_frame ||
            frame.return_address_without_call ||
            frame.tail_call_proxy ||
            frame.unwind_metadata_tampered ||
            frame.captured_context_modified) {
            return &frame;
        }
    }

    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        const std::wstring name = !frame.module_name.empty() ? frame.module_name : frame.summary_name;
        if (!IsLoaderStackFrameName(name)) {
            return &frame;
        }
    }

    for (const auto& frame : frames) {
        if (frame.address != 0 && !frame.monitor_frame) {
            return &frame;
        }
    }
    return nullptr;
}

static const FrameInfo* SelectNetworkUseCallerFrame(const std::vector<FrameInfo>& frames, const FrameInfo* event_value_frame) {
    if (event_value_frame && event_value_frame->address != 0 && !event_value_frame->monitor_frame) {
        return event_value_frame;
    }
    return SelectDllLoadCallerFrame(frames);
}

static std::wstring NetworkModuleFromApiName(const std::wstring& api_name) {
    const size_t split = api_name.find(L'!');
    if (split == std::wstring::npos) {
        return {};
    }
    return ToLower(BasenameOf(api_name.substr(0, split)));
}

static bool PeImportsDll(const std::wstring& module_path, const std::wstring& dll_name, bool& imports) {
    imports = false;
    if (module_path.empty() || dll_name.empty()) {
        return false;
    }

    std::vector<uint8_t> bytes;
    if (!ReadFileBytes(module_path, bytes) || bytes.size() < sizeof(IMAGE_DOS_HEADER)) {
        return false;
    }
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(bytes.data());
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) {
        return false;
    }
    const size_t nt_offset = static_cast<size_t>(dos->e_lfanew);
    if (nt_offset + sizeof(IMAGE_NT_HEADERS64) > bytes.size()) {
        return false;
    }
    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(bytes.data() + nt_offset);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        return false;
    }

    const auto& import_dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (import_dir.VirtualAddress == 0 || import_dir.Size < sizeof(IMAGE_IMPORT_DESCRIPTOR)) {
        return true;
    }

    std::vector<PeSectionInfo> sections;
    if (!ParsePeSections(bytes, sections)) {
        return false;
    }

    uint64_t import_offset64 = 0;
    if (!RvaToFileOffset(sections, import_dir.VirtualAddress, import_offset64)) {
        return false;
    }
    const size_t import_offset = static_cast<size_t>(import_offset64);
    const size_t max_descriptors = std::min<size_t>(
        import_dir.Size / sizeof(IMAGE_IMPORT_DESCRIPTOR),
        4096);
    for (size_t i = 0; i < max_descriptors; ++i) {
        const size_t descriptor_offset = import_offset + i * sizeof(IMAGE_IMPORT_DESCRIPTOR);
        if (descriptor_offset + sizeof(IMAGE_IMPORT_DESCRIPTOR) > bytes.size()) {
            break;
        }
        const auto* descriptor = reinterpret_cast<const IMAGE_IMPORT_DESCRIPTOR*>(bytes.data() + descriptor_offset);
        if (descriptor->OriginalFirstThunk == 0 && descriptor->FirstThunk == 0 && descriptor->Name == 0) {
            break;
        }
        if (descriptor->Name == 0) {
            continue;
        }
        uint64_t name_offset64 = 0;
        if (!RvaToFileOffset(sections, descriptor->Name, name_offset64)) {
            continue;
        }
        const size_t name_offset = static_cast<size_t>(name_offset64);
        std::string imported;
        for (size_t j = name_offset; j < bytes.size() && bytes[j] != 0 && imported.size() < 260; ++j) {
            imported.push_back(static_cast<char>(bytes[j]));
        }
        if (!imported.empty() && ToLower(BasenameOf(WideFromAscii(imported))) == ToLower(BasenameOf(dll_name))) {
            imports = true;
            return true;
        }
    }
    return true;
}

static std::wstring BuildOriginEvidence(const MonitorOriginRecord& record) {
    const std::wstring reg = OriginRegisterToString(record.reg);
    const std::wstring value_name = record.value_name;
    const std::wstring record_name = record.name;
    if (record_name == L"loadlibrary-proxy-params") {
        return L"LoadLibrary entry preserved a proxy argument block carrying watched DLL, loader API, and gadget state";
    }
    if (record_name == L"loadlibrary-entry-string") {
        return L"LoadLibrary entry received a watched DLL string from executable user-controlled memory";
    }
    if (record_name == L"ldrloaddll-proxy-params") {
        return L"LdrLoadDll entry preserved a proxy argument block carrying watched DLL, loader API, and gadget state";
    }
    if (record_name == L"ldrloaddll-entry-unicode-string") {
        return L"LdrLoadDll entry received a watched DLL UNICODE_STRING from executable user-controlled memory";
    }
    if (record_name == L"ldrloaddll-visible-gadget") {
        return L"LdrLoadDll entry returned through a visible proxy gadget tied to the origin allocation";
    }
    if (record_name == L"thread-message-dispatch") {
        return L"watched DLL loaded by clean worker thread from cross-thread function dispatch";
    }
    if (record_name == L"loadlibrary-function-proxy-stack") {
        return L"LoadLibrary was invoked by a clean worker through a live function-proxy argument block";
    }
    if (record_name == L"ldrloaddll-function-proxy-stack") {
        return L"LdrLoadDll was invoked by a clean worker through a live function-proxy argument block";
    }
    if (record_name == L"function-proxy-indirect-callsite") {
        return L"watched DLL load returned to a worker indirect callsite consistent with a function proxy";
    }
    if (record_name == L"threadpool-chain-proxy-context") {
        return L"threadpool callback chain preserved a proxy context carrying watched DLL, loader API, and return gadget state";
    }
    switch (record.kind) {
    case kMonitorOriginLoaderApiPointer:
        return L"wrote " + value_name + L" pointer into " + reg + L" before proxy DLL load";
    case kMonitorOriginDllStringPointer:
        return L"wrote watched DLL string pointer (" + value_name + L") into " + reg;
    case kMonitorOriginGadgetPointer:
        return L"prepared image gadget pointer (" + value_name + L") in " + reg;
    case kMonitorOriginProxyTransfer:
        if (record_name == L"veh-rip-redirect") {
            return L"VEH handler redirected RIP into guarded user code before the clean gadget DLL load";
        }
        if (record_name == L"execution-guard") {
            return L"execution entered guarded user code before the clean gadget DLL load";
        }
        if (value_name == L"traced-thread-start") {
            return L"register-trace wrapped a thread start inside target .text before the proxy DLL load";
        }
        return L"transferred execution from traced target code to image gadget (" + value_name + L")";
    default:
        return L"captured origin trace record";
    }
}

static OriginTraceResult SelectRegisterTraceOrigin(RunState& state, const MonitorEvent& event,
    const std::vector<ModuleInfo>& modules, const std::vector<FrameInfo>& frames) {
    OriginTraceResult result;
    if ((!state.rules.register_trace && !state.rules.dispatch_trace && !state.rules.threadpool_chain_trace) ||
        event.event_type != kMonitorEventDllLoad ||
        event.origin_record_count == 0) {
        return result;
    }

    const uint64_t now = GetTickCount64();
    const uint64_t window = state.rules.correlation_window_ms;
    int best_score = -1;
    MonitorOriginRecord best_record{};
    FrameInfo best_frame;

    const uint32_t count = std::min<uint32_t>(event.origin_record_count, kMonitorMaxOriginRecords);
    for (uint32_t i = 0; i < count; ++i) {
        const MonitorOriginRecord& record = event.origin_records[i];
        if (record.kind == kMonitorOriginNone || record.writer_rip == 0) {
            continue;
        }
        const std::wstring record_name = record.name;
        const bool dispatch_record = record_name == L"thread-message-dispatch";
        const bool threadpool_chain_record = record_name == L"threadpool-chain-proxy-context";
        const bool function_proxy_record =
            record_name == L"loadlibrary-function-proxy-stack" ||
            record_name == L"ldrloaddll-function-proxy-stack" ||
            record_name == L"function-proxy-indirect-callsite" ||
            threadpool_chain_record;
        if (dispatch_record && !state.rules.dispatch_trace) {
            continue;
        }
        if (function_proxy_record && !state.rules.dispatch_trace && !state.rules.threadpool_chain_trace) {
            continue;
        }
        if (!dispatch_record && !function_proxy_record && !state.rules.register_trace) {
            continue;
        }
        if (record.tick_ms != 0 && now >= record.tick_ms && now - record.tick_ms > window) {
            continue;
        }

        FrameInfo writer = ClassifyFrame(state.process, modules, record.writer_rip);
        std::vector<FrameInfo> writer_frames{writer};
        ApplyModuleIntegrity(state, modules, writer_frames);
        writer = writer_frames.front();

        const bool traceable_user_origin = IsTraceableUserCodeFrame(state, writer);
        const bool main_origin = IsMainModuleFrame(state, writer);
        const bool suspicious_origin = IsSuspiciousFrame(writer);
        const bool generic_function_proxy_record = function_proxy_record &&
            !dispatch_record &&
            !threadpool_chain_record;
        if (generic_function_proxy_record &&
            !suspicious_origin &&
            writer.type == MEM_IMAGE) {
            continue;
        }
        if (!traceable_user_origin && !suspicious_origin && !dispatch_record && !function_proxy_record) {
            continue;
        }

        int candidate_score = (dispatch_record || function_proxy_record) ? 80 : (traceable_user_origin ? 40 : 25);
        if (main_origin) {
            candidate_score += 5;
        }
        if (suspicious_origin) {
            candidate_score += 30;
        }
        switch (record.kind) {
        case kMonitorOriginLoaderApiPointer: candidate_score += 40; break;
        case kMonitorOriginDllStringPointer: candidate_score += 35; break;
        case kMonitorOriginGadgetPointer: candidate_score += 35; break;
        case kMonitorOriginProxyTransfer: candidate_score += 30; break;
        default: break;
        }
        if (record_name == L"thread-start" ||
            record_name == L"veh-rip-redirect" ||
            record_name == L"execution-guard") {
            candidate_score += 25;
        } else if (dispatch_record) {
            candidate_score += 15;
            if (record.origin_flags & kMonitorOriginFlagDispatchWaitObserved) {
                candidate_score += 5;
            }
        } else if (function_proxy_record) {
            candidate_score += record_name == L"function-proxy-indirect-callsite" ? 0 : 15;
        } else if (record_name == L"loadlibrary-proxy-params" ||
            record_name == L"loadlibrary-entry-string" ||
            record_name == L"ldrloaddll-proxy-params" ||
            record_name == L"ldrloaddll-entry-unicode-string") {
            candidate_score -= 15;
        }
        if (record.reg == kMonitorRegRax || record.reg == kMonitorRegR10 ||
            record.reg == kMonitorRegR11 || record.reg == kMonitorRegRcx ||
            record.reg == kMonitorRegRip) {
            candidate_score += 5;
        }
        if (!StackContainsAddressNear(frames, record.writer_rip)) {
            candidate_score += 10;
        }

        if (candidate_score > best_score) {
            best_score = candidate_score;
            best_record = record;
            best_frame = writer;
        }
    }

    if (best_score < 0) {
        return result;
    }

    result.present = true;
    const std::wstring best_name = best_record.name;
    result.from_dispatch_trace = best_name == L"thread-message-dispatch";
    result.from_function_proxy_trace =
        best_name == L"loadlibrary-function-proxy-stack" ||
        best_name == L"ldrloaddll-function-proxy-stack" ||
        best_name == L"function-proxy-indirect-callsite" ||
        best_name == L"threadpool-chain-proxy-context";
    result.from_register_trace = !result.from_dispatch_trace && !result.from_function_proxy_trace;
    const bool same_origin_module_visible =
        best_frame.type == MEM_IMAGE &&
        !best_frame.module_name.empty() &&
        StackContainsModuleName(frames, best_frame.module_name);
    result.hidden_from_stack = !StackContainsAddressNear(frames, best_record.writer_rip) &&
        !same_origin_module_visible;
    result.confidence_score = best_score;
    result.address = best_record.writer_rip;
    result.value = best_record.value;
    result.target = best_record.target_rip;
    if (result.from_dispatch_trace) {
        result.source = L"thread_message_dispatch";
    } else if (result.from_function_proxy_trace) {
        result.source = best_name == L"threadpool-chain-proxy-context"
            ? L"threadpool_chain_context"
            : L"function_proxy_context";
    } else if (best_name == L"veh-rip-redirect") {
        result.source = L"veh_context";
    } else if (best_name == L"execution-guard") {
        result.source = L"execution_guard";
    } else if (best_frame.type == MEM_MAPPED) {
        result.source = L"mapped_register_trace";
    } else if (best_frame.type == MEM_PRIVATE) {
        result.source = L"unbacked_register_trace";
    } else {
        result.source = L"register_trace";
    }
    result.kind = result.from_dispatch_trace
        ? L"function_proxy_dispatch"
        : (result.from_function_proxy_trace
            ? (best_name == L"threadpool-chain-proxy-context" ? L"threadpool_chain_context" : L"function_proxy_context")
            : OriginKindToString(best_record.kind));
    result.reg = OriginRegisterToString(best_record.reg);
    result.label = FrameDisplayLabel(best_frame);
    result.evidence = BuildOriginEvidence(best_record);
    if (result.from_dispatch_trace) {
        result.dispatch_source_tid = best_record.source_tid;
        result.dispatch_target_tid = best_record.target_tid;
        result.dispatch_message = best_record.message;
        result.dispatch_wparam = best_record.dispatch_wparam;
        result.dispatch_lparam = best_record.dispatch_lparam;
        result.dispatch_wait_observed = (best_record.origin_flags & kMonitorOriginFlagDispatchWaitObserved) != 0;
        result.dispatch_api = L"PostThreadMessage";
        result.dispatch_function = best_record.value_name;
        result.dispatch_argument = event.target_name;
    }
    result.confidence = (best_score >= 85 &&
        (result.hidden_from_stack || result.from_dispatch_trace || result.from_function_proxy_trace)) ? L"high" : L"medium";
    return result;
}

static bool IsLoaderProxyParamRecordName(const std::wstring& name) {
    return name == L"loadlibrary-proxy-params" ||
        name == L"ldrloaddll-proxy-params";
}

static bool IsLoaderEntryStringRecordName(const std::wstring& name) {
    return name == L"loadlibrary-entry-string" ||
        name == L"ldrloaddll-entry-unicode-string";
}

static bool OriginDllNameMatchesTarget(const std::wstring& value_name, const std::wstring& target_name) {
    if (value_name.empty() || target_name.empty()) {
        return false;
    }
    const std::wstring value = NormalizeModuleBasenameWithExtension(value_name);
    const std::wstring target = NormalizeModuleBasenameWithExtension(target_name);
    return value == target;
}

static bool IsLoaderApiValueName(const std::wstring& value_name) {
    const std::wstring value = ToLower(value_name);
    return value == L"loadlibrarya" ||
        value == L"loadlibraryw" ||
        value == L"loadlibraryexa" ||
        value == L"loadlibraryexw" ||
        value == L"ldrloaddll";
}

static OriginTraceResult SelectByoudRegisterTraceOrigin(RunState& state, const MonitorEvent& event,
    const std::vector<ModuleInfo>& modules, const std::vector<FrameInfo>& frames) {
    OriginTraceResult result;
    if (!state.rules.register_trace ||
        event.event_type != kMonitorEventDllLoad ||
        event.origin_record_count == 0) {
        return result;
    }

    const uint64_t now = GetTickCount64();
    const uint64_t window = state.rules.correlation_window_ms;
    int best_score = -1;
    MonitorOriginRecord best_record{};
    FrameInfo best_frame;

    const uint32_t count = std::min<uint32_t>(event.origin_record_count, kMonitorMaxOriginRecords);
    for (uint32_t i = 0; i < count; ++i) {
        const MonitorOriginRecord& record = event.origin_records[i];
        if (record.kind == kMonitorOriginNone || record.writer_rip == 0) {
            continue;
        }
        if (record.tick_ms != 0 && now >= record.tick_ms && now - record.tick_ms > window) {
            continue;
        }

        const std::wstring record_name = record.name;
        const bool proxy_params = IsLoaderProxyParamRecordName(record_name);
        const bool entry_string = IsLoaderEntryStringRecordName(record_name);
        const bool dll_match =
            record.kind == kMonitorOriginDllStringPointer &&
            OriginDllNameMatchesTarget(record.value_name, event.target_name);
        const bool loader_api =
            record.kind == kMonitorOriginLoaderApiPointer &&
            IsLoaderApiValueName(record.value_name);
        const bool proxy_transfer = record.kind == kMonitorOriginProxyTransfer;

        if (!dll_match && !loader_api && !proxy_transfer) {
            continue;
        }
        if (proxy_transfer && record_name != L"execution-guard") {
            continue;
        }
        if (loader_api && !proxy_params && record_name != L"register-write") {
            continue;
        }

        FrameInfo writer = ClassifyFrame(state.process, modules, record.writer_rip);
        std::vector<FrameInfo> writer_frames{writer};
        ApplyModuleIntegrity(state, modules, writer_frames);
        writer = writer_frames.front();

        const bool traceable_user_origin = IsTraceableUserCodeFrame(state, writer);
        const bool main_origin = IsMainModuleFrame(state, writer);
        const bool suspicious_origin = IsSuspiciousFrame(writer);
        const bool system_image_origin =
            writer.type == MEM_IMAGE &&
            !writer.module_path.empty() &&
            IsSystemLikeModulePath(writer.module_path);
        if (system_image_origin && !traceable_user_origin && !suspicious_origin &&
            !proxy_params && !entry_string) {
            continue;
        }

        int candidate_score = 55;
        if (proxy_params) {
            candidate_score += 35;
        }
        if (entry_string) {
            candidate_score += 20;
        }
        if (record_name == L"register-write") {
            candidate_score += 60;
        }
        if (dll_match) {
            candidate_score += 40;
        }
        if (loader_api) {
            candidate_score += 25;
        }
        if (proxy_transfer) {
            candidate_score += 20;
        }
        if (!writer.executable) {
            candidate_score -= 45;
        }
        if (traceable_user_origin) {
            candidate_score += 15;
        }
        if (main_origin) {
            candidate_score += 10;
        }
        if (suspicious_origin) {
            candidate_score += 20;
        }
        if (record.reg == kMonitorRegRax || record.reg == kMonitorRegRcx ||
            record.reg == kMonitorRegRdx || record.reg == kMonitorRegRip) {
            candidate_score += 5;
        }
        if (!StackContainsAddressNear(frames, record.writer_rip)) {
            candidate_score += 10;
        }

        if (candidate_score > best_score) {
            best_score = candidate_score;
            best_record = record;
            best_frame = writer;
        }
    }

    if (best_score < 80) {
        return result;
    }

    result.present = true;
    result.from_register_trace = true;
    result.confidence_score = best_score;
    result.address = best_record.writer_rip;
    result.value = best_record.value;
    result.target = best_record.target_rip;
    result.reg = OriginRegisterToString(best_record.reg);
    result.label = FrameDisplayLabel(best_frame);
    const bool same_origin_module_visible =
        best_frame.type == MEM_IMAGE &&
        !best_frame.module_name.empty() &&
        StackContainsModuleName(frames, best_frame.module_name);
    result.hidden_from_stack = !StackContainsAddressNear(frames, best_record.writer_rip) &&
        !same_origin_module_visible;
    if (best_frame.type == MEM_PRIVATE) {
        result.source = L"byoud_unbacked_register_trace";
    } else if (best_frame.type == MEM_MAPPED) {
        result.source = L"byoud_mapped_register_trace";
    } else if (IsMainModuleFrame(state, best_frame)) {
        result.source = L"byoud_main_module_register_trace";
    } else {
        result.source = L"byoud_register_trace";
    }
    result.kind = L"byoud_hidden_loader_origin";
    if (IsLoaderProxyParamRecordName(best_record.name)) {
        result.evidence = L"BYOUD trace correlated proxy parameters carrying the watched DLL and loader API before unwind metadata hid the caller";
    } else if (best_record.kind == kMonitorOriginDllStringPointer) {
        result.evidence = L"BYOUD trace saw code prepare the watched DLL string before unwind metadata hid the caller";
    } else if (best_record.kind == kMonitorOriginLoaderApiPointer) {
        result.evidence = L"BYOUD trace saw code prepare the loader API pointer before unwind metadata hid the caller";
    } else {
        result.evidence = L"BYOUD trace correlated hidden user-code execution before the clean DLL-load stack";
    }
    result.confidence = (best_score >= 90 && result.hidden_from_stack) ? L"high" : L"medium";
    return result;
}

static OriginTraceResult BuildCallbackOriginResult(const CallbackObservation* observation) {
    OriginTraceResult result;
    if (!observation) {
        return result;
    }
    result.present = true;
    result.from_callback_context = true;
    result.confidence_score = observation->suspicious ? 85 : 70;
    result.address = observation->callback_address;
    result.source = L"callback_context";
    result.kind = L"callback_context";
    result.label = observation->label.empty() ? Hex64Wide(observation->callback_address) : observation->label;
    result.evidence = L"recent " + observation->api_name + L" callback/start context points to the probable origin";
    if (IsVehCallbackApi(observation->api_name)) {
        result.source = L"veh_context";
        result.kind = L"veh_handler_origin";
        result.evidence = L"recent VEH handler registration points to user code that later hides behind a clean proxy gadget";
        if (EqualsInsensitive(observation->api_name, L"VehRipRedirect")) {
            result.kind = L"veh_rip_origin";
            result.evidence = L"VEH handler redirected RIP into user code that later hides behind a clean proxy gadget";
        }
    } else if (IsContextRedirectApi(observation->api_name)) {
        result.source = L"context_redirect";
        result.kind = L"context_rip_origin";
        result.evidence = L"recent thread context/RIP redirect points to user code that later hides behind a clean proxy gadget";
    }
    result.confidence = observation->suspicious ? L"high" : L"medium";
    return result;
}

static OriginTraceResult BuildTemporalImageOriginResult(const RunState& state,
    const ProcessState& process_state, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames) {
    OriginTraceResult result;
    if (!state.rules.origin_trace ||
        !state.rules.memory_audit ||
        event.event_type != kMonitorEventDllLoad ||
        !IsNetworkModule(state.rules, event.target_name)) {
        return result;
    }

    constexpr uint64_t kTemporalCorrelationEvents = 24;
    const TemporalImageState* best = nullptr;
    for (const auto& [base, temporal] : process_state.temporal_image_states) {
        (void)base;
        if (!temporal.dirty_seen || temporal.dirty_event_index == 0) {
            continue;
        }
        if (state.events_total < temporal.dirty_event_index ||
            state.events_total - temporal.dirty_event_index > kTemporalCorrelationEvents) {
            continue;
        }
        if (!best || temporal.dirty_event_index > best->dirty_event_index) {
            best = &temporal;
        }
    }
    if (!best) {
        return result;
    }

    const uint64_t origin_address = best->dirty_address ? best->dirty_address : best->module_base;
    if (origin_address == 0) {
        return result;
    }

    result.present = true;
    result.confidence = L"high";
    result.confidence_score = 90;
    result.address = origin_address;
    result.target = event.event_value;
    result.source = L"temporal_image_stomp";
    result.kind = L"image_stomp_origin";
    result.hidden_from_stack = !StackContainsAddressNear(frames, origin_address);

    const uint64_t rva = origin_address >= best->module_base ? origin_address - best->module_base : 0;
    std::wostringstream label;
    if (!best->module_name.empty()) {
        label << best->module_name << L"+0x"
              << std::hex << std::uppercase << std::setw(16) << std::setfill(L'0') << rva;
    } else {
        label << L"Image!" << Hex64Wide(origin_address);
    }
    result.label = label.str();

    std::wostringstream evidence;
    evidence << L"watched DLL load followed live executable image stomp in "
             << (!best->module_name.empty() ? best->module_name : L"an image module");
    if (best->dirty_modified_bytes) {
        evidence << L" with " << std::dec << best->dirty_modified_bytes << L" modified bytes";
    }
    result.evidence = evidence.str();
    return result;
}

static bool IsLoadLibraryEntryOrigin(const OriginTraceResult& origin) {
    return origin.evidence.rfind(L"LoadLibrary entry", 0) == 0 ||
        origin.evidence.rfind(L"LdrLoadDll entry", 0) == 0;
}

static std::wstring SanitizeArtifactName(std::wstring value) {
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
    return value.empty() ? L"module" : value;
}

static uint64_t AlignDown(uint64_t value, uint64_t alignment) {
    return value & ~(alignment - 1);
}

static uint64_t AlignUp(uint64_t value, uint64_t alignment) {
    return AlignDown(value + alignment - 1, alignment);
}

static bool DumpOriginRegion(RunState& state, const std::vector<ModuleInfo>& modules,
    const OriginTraceResult& origin, const FrameInfo* visible_caller, const std::wstring& dll_name,
    OriginRegionDumpRecord& record) {
    if (!state.rules.dump_suspicious_regions ||
        !origin.present ||
        origin.address == 0) {
        return false;
    }

    FrameInfo origin_frame = ClassifyFrame(state.process, modules, origin.address);
    std::vector<FrameInfo> origin_frames{origin_frame};
    ApplyModuleIntegrity(state, modules, origin_frames);
    origin_frame = origin_frames.front();

    if (origin_frame.monitor_frame ||
        !origin_frame.executable) {
        return false;
    }

    const ModuleInfo* origin_module = FindModuleForAddress(modules, origin.address);
    const bool image_origin = origin_frame.type == MEM_IMAGE && origin_module && origin_module->base != 0 && origin_module->size != 0;
    const uint64_t origin_base = image_origin
        ? origin_module->base
        : (origin_frame.allocation_base ? origin_frame.allocation_base : origin_frame.region_base);
    const uint64_t origin_size = image_origin
        ? origin_module->size
        : (origin_frame.allocation_size ? origin_frame.allocation_size : origin_frame.region_size);
    if (origin_base == 0 || origin_size == 0 || origin.address < origin_base) {
        return false;
    }

    const uint64_t origin_rva = origin.address - origin_base;
    ProcessState* process_state = CurrentProcessState(state);
    auto& dumped_keys = process_state ? process_state->dumped_origin_region_keys : state.dumped_origin_region_keys;
    const uint64_t key = origin_base ^ origin_rva;
    if (!dumped_keys.insert(key).second) {
        return false;
    }

    constexpr uint64_t kOriginWindowBefore = 32ull * 1024ull;
    constexpr uint64_t kOriginWindowAfter = 32ull * 1024ull;
    constexpr uint64_t kPageSize = 0x1000;

    const uint64_t module_begin = origin_base;
    const uint64_t module_end = origin_base + origin_size;
    uint64_t dump_begin = origin.address > kOriginWindowBefore
        ? origin.address - kOriginWindowBefore
        : module_begin;
    dump_begin = std::max<uint64_t>(module_begin, AlignDown(dump_begin, kPageSize));
    uint64_t dump_end = std::min<uint64_t>(module_end, AlignUp(origin.address + kOriginWindowAfter, kPageSize));
    if (dump_end <= dump_begin) {
        return false;
    }

    fs::path dump_dir = CurrentOutputDirectory(state) / L"origin_regions";
    fs::create_directories(dump_dir);

    const std::wstring module_name = !origin_frame.module_name.empty()
        ? origin_frame.module_name
        : (!origin_frame.summary_name.empty() ? origin_frame.summary_name : L"origin");
    std::wostringstream name;
    name << L"origin_region_"
        << std::setw(3) << std::setfill(L'0') << state.origin_regions_total << L"_"
        << SanitizeArtifactName(module_name) << L"_rva_"
        << std::hex << std::uppercase << origin_rva << L".bin";
    const fs::path dump_path = dump_dir / name.str();

    std::ofstream output(dump_path, std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }

    uint64_t cursor = dump_begin;
    uint64_t total_written = 0;
    uint64_t bytes_from_process = 0;
    while (cursor < dump_end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (VirtualQueryEx(state.process, reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
            break;
        }

        const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        const uint64_t region_end = std::min<uint64_t>(region_base + static_cast<uint64_t>(mbi.RegionSize), dump_end);
        if (region_end <= cursor) {
            break;
        }

        if (region_base > cursor) {
            const uint64_t gap = std::min<uint64_t>(region_base - cursor, dump_end - cursor);
            WriteZeroPadding(output, gap);
            total_written += gap;
            cursor += gap;
            continue;
        }

        const uint64_t chunk_size = region_end - cursor;
        if (CanAttemptRead(mbi.State, mbi.Protect)) {
            DumpReadableRange(state.process, output, cursor, chunk_size, bytes_from_process);
        } else {
            WriteZeroPadding(output, chunk_size);
        }
        total_written += chunk_size;
        cursor = region_end;
    }

    if (total_written == 0) {
        return false;
    }
    if (bytes_from_process == 0) {
        output.close();
        std::error_code ignored;
        fs::remove(dump_path, ignored);
        return false;
    }

    record.path = dump_path.wstring();
    record.dump_base = dump_begin;
    record.dump_size = total_written;
    record.origin_address = origin.address;
    record.origin_rva = origin_rva;
    record.module_base = origin_base;
    record.module_name = module_name;
    record.module_path = origin_frame.module_path;
    record.visible_caller_address = visible_caller ? visible_caller->address : 0;
    record.visible_caller_label = visible_caller ? FrameDisplayLabel(*visible_caller) : L"";
    record.evidence = origin.evidence;
    if (state.rules.analyze_dumps) {
        record.analysis = AnalyzeDumpFile(dump_path, false);
    }

    const fs::path meta_path = dump_path.wstring() + L".json";
    std::ofstream meta(meta_path, std::ios::out | std::ios::trunc);
    if (meta) {
        meta << "{"
            << "\"dll_name\":" << JsonString(dll_name) << ","
            << "\"origin_address\":\"" << Hex64(record.origin_address) << "\","
            << "\"origin_rva\":\"" << Hex64(record.origin_rva) << "\","
            << "\"dump_base\":\"" << Hex64(record.dump_base) << "\","
            << "\"dump_size\":" << record.dump_size << ","
            << "\"module_base\":\"" << Hex64(record.module_base) << "\","
            << "\"module_name\":" << JsonString(record.module_name) << ","
            << "\"module_path\":" << JsonString(record.module_path) << ","
            << "\"visible_caller_address\":\"" << Hex64(record.visible_caller_address) << "\","
            << "\"visible_caller_label\":" << JsonString(record.visible_caller_label) << ","
            << "\"origin_source\":" << JsonString(origin.source) << ","
            << "\"origin_kind\":" << JsonString(origin.kind) << ","
            << "\"confidence\":" << JsonString(origin.confidence) << ","
            << "\"evidence\":" << JsonString(record.evidence) << ","
            << "\"analysis\":{"
            << "\"sha256\":" << JsonString(record.analysis.sha256) << ","
            << "\"entropy\":" << std::fixed << std::setprecision(4) << record.analysis.entropy << ","
            << "\"strings\":" << JsonStringArray(record.analysis.strings)
            << "}"
            << "}\n";
    }

    return true;
}

static void RecordDllLoadMemoryObservation(RunState& state, const MonitorEvent& event,
    const std::vector<ModuleInfo>& modules, const std::vector<FrameInfo>& frames,
    const std::wstring& summary, bool alert, int score, const OriginTraceResult& origin,
    const OriginRegionDumpRecord* origin_region_dump) {
    if (event.event_type != kMonitorEventDllLoad) {
        return;
    }

    ProcessState* current_process_state = CurrentProcessState(state);
    DllLoadMemoryObservation observation;
    observation.event_index = state.events_total;
    observation.pid = event.pid;
    observation.tid = event.tid;
    observation.alert = alert;
    observation.score = score;
    observation.dll_name = event.target_name;
    observation.stack_summary = summary;
    observation.origin_trace = origin.present;
    observation.origin_confidence = origin.confidence;
    observation.origin_source = origin.source;
    observation.origin_kind = origin.kind;
    observation.origin_register = origin.reg;
    observation.origin_label = origin.label;
    observation.origin_evidence = origin.evidence;
    observation.origin_address = origin.address;
    observation.origin_value = origin.value;
    observation.origin_target = origin.target;
    observation.dispatch_trace = origin.from_dispatch_trace;
    observation.dispatch_wait_observed = origin.dispatch_wait_observed;
    observation.dispatch_source_tid = origin.dispatch_source_tid;
    observation.dispatch_target_tid = origin.dispatch_target_tid;
    observation.dispatch_message = origin.dispatch_message;
    observation.dispatch_wparam = origin.dispatch_wparam;
    observation.dispatch_lparam = origin.dispatch_lparam;
    observation.dispatch_api = origin.dispatch_api;
    observation.dispatch_function = origin.dispatch_function;
    observation.dispatch_argument = origin.dispatch_argument;
    observation.dispatch_requester = origin.label;
    if (origin_region_dump) {
        observation.origin_region_dumped = true;
        observation.origin_region_dump_path = origin_region_dump->path;
        observation.origin_region_dump_base = origin_region_dump->dump_base;
        observation.origin_region_dump_size = origin_region_dump->dump_size;
        observation.origin_region_rva = origin_region_dump->origin_rva;
    }

    if (const ModuleInfo* loaded = FindLoadedModuleForDllEvent(modules, event)) {
        observation.loaded_base = loaded->base;
        observation.loaded_size = loaded->size;
        observation.loaded_path = loaded->path;
    } else {
        observation.loaded_base = event.event_value;
        observation.loaded_size = event.event_value_module_size;
        if (event.event_value_module_path[0] != L'\0') {
            observation.loaded_path = event.event_value_module_path;
        }
    }

    if (const FrameInfo* caller = SelectDllLoadCallerFrame(frames)) {
        observation.caller_address = caller->address;
        observation.caller_region_base = caller->region_base;
        observation.caller_region_size = caller->region_size;
        observation.caller_allocation_base = caller->allocation_base;
        observation.caller_allocation_size = caller->allocation_size;
        observation.caller_label = caller->symbol_label;
        observation.caller_summary_name = caller->summary_name;
        observation.caller_module_name = caller->module_name;
        observation.caller_module_path = caller->module_path;
        if (current_process_state && caller->module_base != 0) {
            auto integrity = current_process_state->module_integrity_cache.find(caller->module_base);
            if (integrity != current_process_state->module_integrity_cache.end() &&
                integrity->second.modified) {
                observation.caller_module_modified = true;
                observation.caller_modified_module_dump_path = integrity->second.dump_path;
            }
        }
        observation.caller_state = StateToString(caller->state);
        observation.caller_protect = ProtectToString(caller->protect);
        observation.caller_type = TypeToString(caller->type);
        observation.dispatch_worker = caller->symbol_label.empty() ? caller->summary_name : caller->symbol_label;
    }

    if (current_process_state) {
        current_process_state->dll_load_memory.push_back(observation);
    }
    state.dll_load_memory.push_back(std::move(observation));
}

static void RecordNetworkUseObservation(RunState& state, ProcessState& process_state,
    const MonitorEvent& event, const std::vector<FrameInfo>& frames, const FrameInfo* event_value_frame,
    const std::wstring& summary, bool alert, int score, const std::vector<std::wstring>& rule_hits) {
    if (event.event_type != kMonitorEventNetworkApi) {
        return;
    }

    NetworkUseObservation observation;
    observation.event_index = state.events_total;
    observation.pid = event.pid;
    observation.tid = event.tid;
    observation.alert = alert;
    observation.score = score;
    observation.api_name = event.event_name;
    observation.target_name = event.target_name;
    observation.network_module = NetworkModuleFromApiName(observation.api_name);
    observation.stack_summary = summary;
    observation.rules = rule_hits;

    if (const FrameInfo* caller = SelectNetworkUseCallerFrame(frames, event_value_frame)) {
        observation.caller_address = caller->address;
        observation.caller_region_base = caller->region_base;
        observation.caller_region_size = caller->region_size;
        observation.caller_allocation_base = caller->allocation_base;
        observation.caller_allocation_size = caller->allocation_size;
        observation.caller_label = FrameDisplayLabel(*caller);
        observation.caller_module_name = caller->module_name;
        observation.caller_module_path = caller->module_path;
        observation.caller_protect = ProtectToString(caller->protect);
        observation.caller_type = TypeToString(caller->type);
        if (!observation.network_module.empty() && !caller->module_path.empty()) {
            bool imports_network = false;
            observation.import_checked = PeImportsDll(caller->module_path, observation.network_module, imports_network);
            observation.caller_module_imports_network = imports_network;
        }
    }

    ++state.network_use_total;
    ++process_state.network_use_total;
    if (alert) {
        ++state.network_use_alerts_total;
        ++process_state.network_use_alerts_total;
    }
    process_state.network_use_records.push_back(observation);
    state.network_use_records.push_back(std::move(observation));
}

static bool ReadRuntimeFunctionEntries(HANDLE process, uint64_t table_address, uint32_t entry_count,
    std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY>& entries) {
    if (!table_address || entry_count == 0) {
        return false;
    }
    const uint32_t bounded_count = std::min<uint32_t>(entry_count, 32);
    entries.resize(bounded_count);
    SIZE_T bytes_read = 0;
    if (!ReadProcessMemory(process, reinterpret_cast<void*>(table_address), entries.data(),
        entries.size() * sizeof(entries[0]), &bytes_read) || bytes_read < sizeof(entries[0])) {
        entries.clear();
        return false;
    }
    entries.resize(bytes_read / sizeof(entries[0]));
    return !entries.empty();
}

static bool RuntimeFunctionTablePointsToSuspiciousMemory(RunState& state, const std::vector<ModuleInfo>& modules,
    const MonitorEvent& event) {
    if (event.event_type != kMonitorEventUnwindTable ||
        !EqualsInsensitive(event.event_name, L"RtlAddFunctionTable") ||
        event.event_value == 0 ||
        event.callback_address == 0 ||
        event.event_flags == 0) {
        return false;
    }

    std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY> entries;
    if (!ReadRuntimeFunctionEntries(state.process, event.event_value, event.event_flags, entries)) {
        return false;
    }

    for (const auto& entry : entries) {
        const uint64_t begin = event.callback_address + entry.BeginAddress;
        FrameInfo begin_frame = ClassifyFrame(state.process, modules, begin);
        std::vector<FrameInfo> integrity_frames{begin_frame};
        ApplyModuleIntegrity(state, modules, integrity_frames);
        begin_frame = integrity_frames.front();
        if (IsSuspiciousFrame(begin_frame)) {
            return true;
        }

        const uint64_t unwind = event.callback_address + entry.UnwindInfoAddress;
        FrameInfo unwind_frame = ClassifyFrame(state.process, modules, unwind);
        if (unwind_frame.unbacked_executable || unwind_frame.type == MEM_PRIVATE) {
            return true;
        }
    }
    return false;
}

static DetectionDecision BuildDetectionDecision(
    uint32_t event_type,
    bool alert,
    bool has_unbacked,
    bool has_backed_modified,
    bool has_unwind_tampered,
    bool has_gadget_candidate,
    bool has_callsite_anomaly,
    bool recent_suspicious_callback,
    const OriginTraceResult& origin_trace) {
    DetectionDecision decision;
    decision.has_stack_evidence = has_unbacked || has_backed_modified || has_unwind_tampered || has_callsite_anomaly;
    decision.has_memory_evidence = has_unbacked;
    decision.has_module_integrity_evidence = has_backed_modified || has_unwind_tampered;
    decision.has_origin_trace_evidence = origin_trace.present;
    decision.has_callback_correlation = recent_suspicious_callback || origin_trace.from_callback_context;
    decision.has_gadget_suspicion = has_gadget_candidate;
    decision.proof = has_unbacked ||
        has_backed_modified ||
        has_unwind_tampered ||
        (origin_trace.present && origin_trace.from_register_trace && origin_trace.confidence == L"high") ||
        (origin_trace.present && origin_trace.from_dispatch_trace && origin_trace.confidence == L"high") ||
        (origin_trace.present && origin_trace.from_function_proxy_trace && origin_trace.confidence == L"high");

    if (event_type == kMonitorEventLdrIntegrity && alert) {
        decision.has_stack_evidence = true;
        decision.has_memory_evidence = true;
        decision.has_module_integrity_evidence = true;
        decision.proof = true;
        decision.confidence = L"proof";
    } else if (!alert) {
        decision.confidence = event_type == kMonitorEventRemoteFollow || event_type == kMonitorEventNetReset
            ? L"telemetry_only"
            : L"none";
    } else if (decision.proof) {
        decision.confidence = L"proof";
    } else if (origin_trace.present || recent_suspicious_callback || has_callsite_anomaly) {
        decision.confidence = L"strong_correlation";
    } else if (has_gadget_candidate) {
        decision.confidence = L"weak_correlation";
    } else {
        decision.confidence = L"strong_correlation";
    }
    return decision;
}

static std::wstring ProcessDisplayNameFromModules(const std::vector<ModuleInfo>& modules, DWORD pid) {
    for (const auto& module : modules) {
        if (!module.name.empty()) {
            return module.name;
        }
    }
    std::wostringstream fallback;
    fallback << L"pid_" << pid;
    return fallback.str();
}

static ProcessState& EnsureProcessState(RunState& state, DWORD pid, HANDLE handle, const std::vector<ModuleInfo>& modules) {
    auto found = state.processes.find(pid);
    if (found != state.processes.end()) {
        if (!found->second.handle && handle) {
            found->second.handle = handle;
        }
        return found->second;
    }

    ProcessState info;
    info.pid = pid;
    info.handle = handle;
    info.name = ProcessDisplayNameFromModules(modules, pid);
    info.main_module_name = ToLower(BasenameOf(info.name));
    if (pid == state.pid) {
        info.out_dir = state.out_dir;
    } else {
        std::wostringstream name;
        name << SanitizeArtifactName(info.name) << L" - " << pid;
        info.out_dir = state.out_dir / L"children" / name.str();
    }

    std::error_code ignored;
    fs::create_directories(info.out_dir / L"dumps", ignored);
    fs::create_directories(info.out_dir / L"origin_regions", ignored);
    fs::create_directories(info.out_dir / L"modified_modules", ignored);
    fs::create_directories(info.out_dir / L"modified_network_modules", ignored);
    return state.processes.emplace(pid, std::move(info)).first->second;
}

static HANDLE OpenProcessForEvent(RunState& state, DWORD pid) {
    if (pid == 0) {
        return nullptr;
    }
    if (pid == state.pid && state.process) {
        return state.process;
    }
    auto found = state.process_handles.find(pid);
    if (found != state.process_handles.end()) {
        return found->second;
    }

    HANDLE process = OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_OPERATION,
        FALSE,
        pid);
    if (!process) {
        process = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    }
    if (process) {
        state.process_handles.emplace(pid, process);
    }
    return process;
}

struct ScopedEventProcessContext {
    RunState& state;
    HANDLE previous_process = nullptr;
    DWORD previous_pid = 0;
    ProcessState* previous_process_state = nullptr;
    fs::path previous_out_dir;
    std::wstring previous_main_module_name;

    ScopedEventProcessContext(RunState& input_state, ProcessState& process_state)
        : state(input_state),
        previous_process(input_state.process),
        previous_pid(input_state.active_event_pid),
        previous_process_state(input_state.active_process_state),
        previous_out_dir(input_state.active_out_dir),
        previous_main_module_name(input_state.active_main_module_name) {
        state.process = process_state.handle;
        state.active_event_pid = process_state.pid;
        state.active_process_state = &process_state;
        state.active_out_dir = process_state.out_dir;
        state.active_main_module_name = process_state.main_module_name;
    }

    ~ScopedEventProcessContext() {
        state.process = previous_process;
        state.active_event_pid = previous_pid;
        state.active_process_state = previous_process_state;
        state.active_out_dir = previous_out_dir;
        state.active_main_module_name = previous_main_module_name;
    }
};

static void ProcessMonitorEvent(RunState& state, const MonitorEvent& event) {
    if (event.magic != kCallstackProtocolMagic || event.version != kCallstackProtocolVersion) {
        return;
    }
    if (event.event_type == kMonitorEventDllLoad && !IsWatchedByRules(state.rules, event.target_name)) {
        return;
    }

    std::lock_guard<std::mutex> process_lock(state.event_mutex);
    HANDLE event_process = OpenProcessForEvent(state, event.pid);
    if (!event_process) {
        return;
    }
    const auto modules = EnumerateModules(event.pid);
    ProcessState& process_state = EnsureProcessState(state, event.pid, event_process, modules);
    ScopedEventProcessContext context(state, process_state);

    ++state.events_total;
    ++process_state.events_total;
    if (event.event_type == kMonitorEventNetReset &&
        EqualsInsensitive(event.event_name, L"net_reset_preloaded") &&
        event.target_name[0] != L'\0') {
        const std::wstring module_name = ToLower(BasenameOf(event.target_name));
        if (!module_name.empty() &&
            std::find(process_state.preloaded_network_modules.begin(),
                process_state.preloaded_network_modules.end(),
                module_name) == process_state.preloaded_network_modules.end()) {
            process_state.preloaded_network_modules.push_back(module_name);
        }
    }

    std::vector<FrameInfo> frames;
    frames.reserve(event.frame_count);

    for (uint32_t i = 0; i < std::min<uint32_t>(event.frame_count, kMonitorMaxFrames); ++i) {
        FrameInfo frame = ClassifyFrame(state.process, modules, event.frames[i]);
        ApplyMonitorFrameSnapshot(event, i, frame);
        frames.push_back(std::move(frame));
    }
    ApplyModuleIntegrity(state, modules, frames);
    ApplyCapturedContextIntegrity(state, event, frames);
    ApplyCallsiteValidation(state, frames);

    FrameInfo callback_frame;
    FrameInfo* callback_frame_ptr = nullptr;
    if (event.callback_address != 0) {
        callback_frame = ClassifyFrame(state.process, modules, event.callback_address);
        std::vector<FrameInfo> callback_frames{callback_frame};
        ApplyModuleIntegrity(state, modules, callback_frames);
        callback_frame = callback_frames.front();
        callback_frame_ptr = &callback_frame;
    }

    FrameInfo event_value_frame;
    FrameInfo* event_value_frame_ptr = nullptr;
    if (event.event_value != 0 &&
        (event.event_type == kMonitorEventMemoryApi ||
            event.event_type == kMonitorEventUnwindTable ||
            event.event_type == kMonitorEventLdrIntegrity ||
            event.event_type == kMonitorEventNetworkApi)) {
        event_value_frame = ClassifyFrame(state.process, modules, event.event_value);
        std::vector<FrameInfo> event_value_frames{event_value_frame};
        ApplyModuleIntegrity(state, modules, event_value_frames);
        event_value_frame = event_value_frames.front();
        event_value_frame_ptr = &event_value_frame;
    }
    CollectTemporalImageIntegrity(state, process_state, modules, event, event_value_frame_ptr);

    bool has_unbacked = false;
    bool has_backed_modified = false;
    bool has_unwind_tampered = false;
    bool has_jit_managed = false;
    bool has_gadget_candidate = false;
    bool has_callsite_anomaly = false;
    for (size_t i = 0; i < frames.size(); ++i) {
        auto& frame = frames[i];
        if (frame.monitor_frame) {
            continue;
        }
        if (frame.unbacked_executable) {
            has_unbacked = true;
        }
        if (frame.backed_modified && !IsLowSignalSystemBackedModifiedFrame(frame)) {
            has_backed_modified = true;
        }
        if (frame.unwind_metadata_tampered) {
            has_unwind_tampered = true;
        }
        if (frame.jit_managed) {
            has_jit_managed = true;
        }
        if (frame.return_address_without_call || frame.tail_call_proxy) {
            has_callsite_anomaly = true;
        }
        if (IsLikelyInsertedGadgetFrame(state, frame, i, event)) {
            frame.suspicious_gadget_frame = true;
            frame.forward_proxy_frame = true;
            has_gadget_candidate = true;
        }
    }

    const StackAuditResult stack_audit = RunStackAudit(state, event, frames, has_callsite_anomaly);
    if (state.rules.shadow_stack && IsShadowStackSensitiveEvent(state, event)) {
        const uint32_t shadow_frame_records = CountShadowStackFrameRecords(event);
        ++state.shadow_stack_sensitive_events;
        ++process_state.shadow_stack_sensitive_events;
        state.shadow_stack_frame_records += shadow_frame_records;
        process_state.shadow_stack_frame_records += shadow_frame_records;
    }
    const ByoudEvidenceSummary byoud_trace = CollectByoudEvidenceForEvent(state, process_state, modules, event, frames);
    const ShadowStackEvidenceSummary shadow_stack_trace =
        CollectShadowStackEvidence(state, process_state, modules, event, frames, stack_audit);
    const bool has_byoud_evidence = byoud_trace.present;
    const bool has_shadow_stack_evidence = shadow_stack_trace.present;

    const bool callback_suspicious = callback_frame_ptr &&
        IsSuspiciousFrame(*callback_frame_ptr);
    const bool callback_environment_allowed =
        event.event_type == kMonitorEventCallback &&
        StackContainsAnyModuleName(frames, state.rules.environment_callback_allowlist);
    const bool callback_origin_candidate = callback_frame_ptr &&
        !callback_environment_allowed &&
        (callback_suspicious || IsTraceableUserCodeFrame(state, *callback_frame_ptr));
    const bool event_value_suspicious = event_value_frame_ptr &&
        IsSuspiciousFrame(*event_value_frame_ptr);
    const bool managed_runtime_unwind_event = event.event_type == kMonitorEventUnwindTable &&
        (has_jit_managed ||
            (callback_frame_ptr && (callback_frame_ptr->jit_managed ||
                IsManagedModuleName(callback_frame_ptr->module_name) ||
                IsManagedModuleName(callback_frame_ptr->summary_name))) ||
            (event_value_frame_ptr && (event_value_frame_ptr->jit_managed ||
                IsManagedModuleName(event_value_frame_ptr->module_name) ||
                IsManagedModuleName(event_value_frame_ptr->summary_name))));
    const bool network_api_event = event.event_type == kMonitorEventNetworkApi;
    const bool network_caller_unbacked = network_api_event && event_value_frame_ptr &&
        event_value_frame_ptr->unbacked_executable;
    const bool network_caller_backed_modified = network_api_event && event_value_frame_ptr &&
        event_value_frame_ptr->backed_modified &&
        !IsLowSignalSystemBackedModifiedFrame(*event_value_frame_ptr);
    const bool network_caller_unwind_tampered = network_api_event && event_value_frame_ptr &&
        event_value_frame_ptr->unwind_metadata_tampered;
    bool network_import_checked = false;
    bool network_import_missing = false;
    if (network_api_event && event_value_frame_ptr && !event_value_frame_ptr->module_path.empty()) {
        const std::wstring network_module = NetworkModuleFromApiName(event.event_name);
        bool imports_network = false;
        network_import_checked = PeImportsDll(event_value_frame_ptr->module_path, network_module, imports_network);
        network_import_missing = network_import_checked && !imports_network &&
            !EqualsInsensitive(event_value_frame_ptr->module_name, network_module) &&
            !IsLoaderStackFrameName(event_value_frame_ptr->module_name);
    }
    const bool recent_suspicious_callback = event.event_type != kMonitorEventCallback &&
        HasRecentSuspiciousCallback(state, event);
    const CallbackObservation* recent_origin_callback = FindRecentOriginCallback(state, event);
    OriginTraceResult origin_trace = SelectRegisterTraceOrigin(state, event, modules, frames);
    if (has_byoud_evidence) {
        OriginTraceResult byoud_origin = SelectByoudRegisterTraceOrigin(state, event, modules, frames);
        if (byoud_origin.present &&
            (!origin_trace.present ||
                IsLoadLibraryEntryOrigin(origin_trace) ||
                origin_trace.source == L"execution_guard" ||
                byoud_origin.confidence_score >= origin_trace.confidence_score)) {
            origin_trace = byoud_origin;
        }
    }
    if ((!origin_trace.present || IsLoadLibraryEntryOrigin(origin_trace)) && has_gadget_candidate && recent_origin_callback) {
        origin_trace = BuildCallbackOriginResult(recent_origin_callback);
        if (state.rules.register_trace) {
            origin_trace.from_register_trace = true;
            origin_trace.hidden_from_stack = !StackContainsAddressNear(frames, origin_trace.address);
            origin_trace.confidence_score = 90;
            origin_trace.confidence = L"high";
            if (IsVehCallbackApi(recent_origin_callback->api_name)) {
                origin_trace.source = L"veh_context";
                origin_trace.kind = L"veh_handler_origin";
                origin_trace.evidence = L"register-trace correlated a VEH handler origin that is absent from the final proxy DLL-load stack";
                if (EqualsInsensitive(recent_origin_callback->api_name, L"VehRipRedirect")) {
                    origin_trace.kind = L"veh_rip_origin";
                    origin_trace.evidence = L"register-trace correlated the VEH redirected RIP that is absent from the final proxy DLL-load stack";
                }
            } else if (IsContextRedirectApi(recent_origin_callback->api_name)) {
                origin_trace.source = L"context_redirect";
                origin_trace.kind = L"context_rip_origin";
                origin_trace.evidence = L"register-trace correlated a context/RIP redirect origin that is absent from the final proxy DLL-load stack";
            } else {
                origin_trace.source = L"register_trace_thread_start";
                origin_trace.kind = L"thread_start_origin";
                origin_trace.evidence = L"register-trace wrapped a target .text thread start that is absent from the final proxy DLL-load stack";
            }
        }
    }
    if (!origin_trace.present || IsLoadLibraryEntryOrigin(origin_trace)) {
        OriginTraceResult temporal_origin = BuildTemporalImageOriginResult(state, process_state, event, frames);
        if (temporal_origin.present &&
            (!origin_trace.present || temporal_origin.confidence_score >= origin_trace.confidence_score)) {
            origin_trace = temporal_origin;
        }
    }

    std::vector<std::wstring> rule_hits;
    int score = 0;
    if (event.event_type == kMonitorEventDllLoad && has_unbacked && state.rules.alert_on_unbacked_executable) {
        if (IsNetworkModule(state.rules, event.target_name)) {
            rule_hits.push_back(L"network_module_loaded_from_unbacked_executable_memory");
        } else if (IsDotnetModule(state.rules, event.target_name)) {
            rule_hits.push_back(L"dotnet_module_loaded_from_suspicious_memory");
        } else {
            rule_hits.push_back(L"sensitive_module_loaded_from_unbacked_executable_memory");
        }
        score = std::max(score, 90);
    }
    if (event.event_type == kMonitorEventDllLoad && has_backed_modified && state.rules.alert_on_backed_modified) {
        rule_hits.push_back(L"sensitive_module_loaded_from_backed_modified_memory");
        score = std::max(score, 80);
    }
    if (has_unwind_tampered && state.rules.alert_on_unwind_tamper) {
        rule_hits.push_back(L"unwind_metadata_tampered_in_stack");
        score = std::max(score, event.event_type == kMonitorEventDllLoad ? 75 : 65);
        ++state.unwind_tamper_total;
    }
    if (event.event_type == kMonitorEventSleepWait && (has_unbacked || has_backed_modified)) {
        rule_hits.push_back(L"sleep_from_suspicious_memory");
        score = std::max(score, 75);
        ++state.sleep_alert_total;
    }
    const bool callback_has_strong_suspicious_stack =
        event.event_type == kMonitorEventCallback &&
        !callback_environment_allowed &&
        HasStrongCallbackSuspiciousFrame(event.event_name, frames);
    const bool low_signal_threadpool_callback =
        event.event_type == kMonitorEventCallback &&
        IsCreateThreadpoolWorkApi(event.event_name) &&
        callback_frame_ptr &&
        IsLowSignalSystemBackedModifiedFrame(*callback_frame_ptr);

    if (event.event_type == kMonitorEventCallback && callback_has_strong_suspicious_stack) {
        rule_hits.push_back(L"callback_registered_from_suspicious_stack");
        score = std::max(score, 85);
        ++state.callback_alert_total;
    }
    if (event.event_type == kMonitorEventCallback && callback_suspicious &&
        !callback_environment_allowed && !low_signal_threadpool_callback) {
        rule_hits.push_back(L"callback_registered_from_suspicious_memory");
        score = std::max(score, 85);
        ++state.callback_alert_total;
    }
    if (event.event_type == kMonitorEventCallback &&
        IsThreadOrApcCallbackApi(event.event_name) &&
        callback_suspicious &&
        !callback_environment_allowed &&
        !low_signal_threadpool_callback) {
        rule_hits.push_back(L"thread_or_apc_callback_points_to_suspicious_memory");
        score = std::max(score, 90);
    }
    if (event.event_type == kMonitorEventCallback && callback_frame_ptr && callback_frame_ptr->jit_managed) {
        rule_hits.push_back(L"callback_registered_to_managed_jit_code");
        score = std::max(score, 45);
    }
    const bool generic_memory_api_scoring =
        event.event_type == kMonitorEventMemoryApi && state.rules.memory_api_hooks;
    if (generic_memory_api_scoring && (has_unbacked || has_backed_modified || has_unwind_tampered)) {
        rule_hits.push_back(L"memory_api_called_from_suspicious_memory");
        const bool touches_executable_memory = event_value_frame_ptr && event_value_frame_ptr->executable;
        const bool requests_executable_memory = IsExecutableProtect(event.event_flags);
        const int memory_api_score =
            (touches_executable_memory || requests_executable_memory || has_backed_modified || has_unwind_tampered) ? 80 : 45;
        score = std::max(score, memory_api_score);
    }
    if (generic_memory_api_scoring && event_value_frame_ptr &&
        event_value_frame_ptr->unbacked_executable && event_value_frame_ptr->executable) {
        rule_hits.push_back(L"memory_api_touched_private_executable_region");
        score = std::max(score, IsExecutableProtect(event.event_flags) ? 70 : 55);
    }
    if (network_api_event && (has_unbacked || network_caller_unbacked)) {
        rule_hits.push_back(L"network_api_called_from_unbacked_executable_memory");
        score = std::max(score, 90);
    }
    if (network_api_event && (has_backed_modified || network_caller_backed_modified)) {
        rule_hits.push_back(L"network_api_called_from_backed_modified_memory");
        score = std::max(score, 90);
    }
    if (network_api_event && (has_unwind_tampered || network_caller_unwind_tampered)) {
        rule_hits.push_back(L"network_api_called_with_tampered_unwind_metadata");
        score = std::max(score, 80);
    }
    if (network_api_event && has_callsite_anomaly && !has_unbacked) {
        rule_hits.push_back(L"network_api_called_from_spoofed_or_unusual_stack");
        score = std::max(score, 75);
    }
    if (network_api_event && network_import_missing) {
        rule_hits.push_back(L"network_api_used_by_module_without_static_network_import");
        score = std::max(score, 45);
    }
    if (event.event_type == kMonitorEventUnwindTable && event_value_suspicious && !managed_runtime_unwind_event) {
        rule_hits.push_back(L"dynamic_unwind_table_from_suspicious_memory");
        score = std::max(score, 80);
        ++state.unwind_alert_total;
    }
    if (event.event_type == kMonitorEventUnwindTable && callback_suspicious && !managed_runtime_unwind_event) {
        rule_hits.push_back(L"dynamic_unwind_base_or_callback_suspicious");
        score = std::max(score, 80);
        ++state.unwind_alert_total;
    }
    if (!managed_runtime_unwind_event && RuntimeFunctionTablePointsToSuspiciousMemory(state, modules, event)) {
        rule_hits.push_back(L"runtime_function_points_to_unbacked_or_modified_memory");
        score = std::max(score, 90);
        ++state.unwind_alert_total;
    }
    if (has_byoud_evidence) {
        for (const auto& byoud_rule : byoud_trace.rules) {
            if (std::find(rule_hits.begin(), rule_hits.end(), byoud_rule) == rule_hits.end()) {
                rule_hits.push_back(byoud_rule);
            }
        }
        score = std::max(score, event.event_type == kMonitorEventDllLoad ? 90 : byoud_trace.score);
        ++state.unwind_alert_total;
    }
    if (has_shadow_stack_evidence) {
        for (const auto& shadow_rule : shadow_stack_trace.rules) {
            if (std::find(rule_hits.begin(), rule_hits.end(), shadow_rule) == rule_hits.end()) {
                rule_hits.push_back(shadow_rule);
            }
        }
        score = std::max(score, shadow_stack_trace.score);
    }
    if (event.event_type == kMonitorEventLdrIntegrity) {
        if (event.event_flags & kMonitorEventFlagLdrEntryPointOutsideImage) {
            rule_hits.push_back(L"ldr_entrypoint_outside_module_image");
            score = std::max(score, 90);
        }
        if (event.event_flags & kMonitorEventFlagLdrEntryPointNotImage) {
            rule_hits.push_back(L"ldr_entrypoint_not_mem_image");
            score = std::max(score, 85);
        }
        if (event.event_flags & kMonitorEventFlagLdrOriginalBaseSuspicious) {
            rule_hits.push_back(L"ldr_originalbase_suspicious_context");
        }
        if ((event.event_flags & kMonitorEventFlagLdrEntryPointMismatch) && score > 0) {
            rule_hits.push_back(L"ldr_entrypoint_mismatch_with_pe_header");
            score = std::max(score, 75);
        }
        if (event_value_frame_ptr && event_value_frame_ptr->unbacked_executable) {
            rule_hits.push_back(L"ldr_entrypoint_points_to_unbacked_executable_memory");
            score = std::max(score, 95);
        }
        if (!rule_hits.empty()) {
            ++state.ldr_tamper_total;
        }
    }
    if (event.event_type == kMonitorEventDllLoad &&
        IsNetworkModule(state.rules, event.target_name) &&
        HasRecentLdrTamper(state)) {
        rule_hits.push_back(L"sensitive_dll_load_after_ldr_entrypoint_tamper");
        score = std::max(score, 85);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        IsNetworkModule(state.rules, event.target_name) &&
        HasRecentTemporalImageEvidence(process_state, state.events_total)) {
        rule_hits.push_back(L"sensitive_dll_load_after_temporal_image_stomp");
        score = std::max(score, 90);
    }
    if (has_gadget_candidate && event.event_type == kMonitorEventDllLoad && !has_unbacked) {
        rule_hits.push_back(L"possible_stack_gadget_or_proxy_loading_frame");
        score = std::max(score, 45);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        origin_trace.present &&
        origin_trace.from_dispatch_trace) {
        rule_hits.push_back(L"sensitive_dll_loaded_via_thread_message_dispatch");
        if (origin_trace.dispatch_wait_observed) {
            rule_hits.push_back(L"agent_waiting_for_dispatch_result");
        }
        score = std::max(score, origin_trace.confidence_score >= 90 ? 90 : 80);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        origin_trace.present &&
        origin_trace.from_function_proxy_trace) {
        if (origin_trace.source == L"threadpool_chain_context") {
            rule_hits.push_back(L"sensitive_dll_loaded_via_threadpool_callback_chain");
        } else {
            rule_hits.push_back(L"sensitive_dll_loaded_via_worker_function_proxy");
        }
        score = std::max(score, origin_trace.confidence_score >= 90 ? 90 : 80);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        origin_trace.present &&
        origin_trace.source == L"temporal_image_stomp") {
        rule_hits.push_back(L"sensitive_dll_load_origin_correlated_to_temporal_image_stomp");
        score = std::max(score, origin_trace.confidence_score >= 90 ? 90 : 80);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        has_gadget_candidate &&
        origin_trace.present &&
        origin_trace.from_register_trace &&
        origin_trace.hidden_from_stack) {
        if (origin_trace.source == L"veh_context" || origin_trace.source == L"context_redirect") {
            rule_hits.push_back(L"proxy_dll_load_origin_via_context_or_exception_dispatch");
        } else if (origin_trace.source == L"execution_guard") {
            rule_hits.push_back(L"proxy_dll_load_origin_hidden_by_execution_tracing");
        } else if (origin_trace.source == L"mapped_register_trace") {
            rule_hits.push_back(L"proxy_dll_load_origin_hidden_by_mapped_register_tracing");
        } else if (origin_trace.source == L"unbacked_register_trace") {
            rule_hits.push_back(L"proxy_dll_load_origin_hidden_by_unbacked_register_tracing");
        } else {
            rule_hits.push_back(L"proxy_dll_load_origin_hidden_by_register_tracing");
        }
        score = std::max(score, 90);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        !has_gadget_candidate &&
        origin_trace.present &&
        origin_trace.from_register_trace &&
        origin_trace.hidden_from_stack &&
        IsNetworkModule(state.rules, event.target_name)) {
        rule_hits.push_back(L"sensitive_dll_load_origin_hidden_by_register_trace");
        score = std::max(score, origin_trace.confidence == L"high" ? 90 : 85);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        origin_trace.present &&
        origin_trace.source == L"execution_guard" &&
        origin_trace.hidden_from_stack &&
        !recent_origin_callback) {
        rule_hits.push_back(L"origin_execution_observed_without_thread_api");
        score = std::max(score, 85);
    }
    if (event.event_type == kMonitorEventDllLoad &&
        has_gadget_candidate &&
        origin_trace.present &&
        origin_trace.from_callback_context) {
        rule_hits.push_back(L"proxy_dll_load_origin_correlated_to_callback_context");
        score = std::max(score, origin_trace.confidence_score >= 85 ? 90 : 80);
    }
    if (has_callsite_anomaly &&
        (event.event_type == kMonitorEventDllLoad || generic_memory_api_scoring || network_api_event) &&
        !has_unbacked) {
        rule_hits.push_back(L"return_address_without_plausible_callsite");
        score = std::max(score, network_api_event ? 70 : (has_gadget_candidate ? 70 : 55));
        ++state.callsite_anomaly_total;
    }
    if (event.event_type == kMonitorEventDllLoad && stack_audit.enabled) {
        if (stack_audit.callsite_anomaly) {
            rule_hits.push_back(L"stack_audit_return_frame_without_matching_call");
            score = std::max(score, 70);
        }
        if (stack_audit.system_only_sensitive_stack && !origin_trace.present) {
            rule_hits.push_back(L"stack_audit_sensitive_dll_load_without_user_origin");
            score = std::max(score, 75);
        }
        if (stack_audit.terminal_frame_not_last || stack_audit.thread_start_frame_too_high) {
            rule_hits.push_back(L"stack_audit_synthetic_thread_start_frame");
            score = std::max(score, 85);
        }
    }
    if (recent_suspicious_callback &&
        (event.event_type == kMonitorEventDllLoad || generic_memory_api_scoring || network_api_event)) {
        rule_hits.push_back(L"sensitive_event_after_suspicious_callback_registration");
        score = std::max(score, 80);
    }
    if (has_jit_managed && event.event_type == kMonitorEventDllLoad && IsDotnetModule(state.rules, event.target_name)) {
        rule_hits.push_back(L"managed_runtime_loaded_in_sensitive_stack");
        score = std::max(score, has_unbacked ? 90 : 35);
    }

    if (has_unbacked || network_caller_unbacked) {
        ++state.unbacked_total;
    }
    if (has_backed_modified || network_caller_backed_modified) {
        ++state.modified_image_total;
    }

    const bool alert = !rule_hits.empty() && score >= 50;
    if (alert) {
        ++state.alerts_total;
        ++process_state.alerts_total;
        if (event.event_type == kMonitorEventMemoryApi) {
            ++state.memory_api_alert_total;
        }
    }
    if (event.event_type == kMonitorEventCallback) {
        RecordCallbackObservation(
            state,
            event,
            !callback_environment_allowed &&
                (callback_suspicious || has_unbacked || has_backed_modified || has_unwind_tampered || score >= 80),
            callback_origin_candidate,
            callback_frame_ptr ? FrameDisplayLabel(*callback_frame_ptr) : Hex64Wide(event.callback_address));
    }
    if (alert && event.event_type == kMonitorEventLdrIntegrity) {
        RecordLdrTamperObservation(state, event);
    }

    std::vector<DumpRecord> event_dumps;
    if (alert && state.rules.dump_suspicious_regions) {
        auto dump_frame = [&](const FrameInfo& frame) {
            if (!frame.unbacked_executable || frame.monitor_frame || frame.allocation_base == 0) {
                return;
            }
            auto& dumped_bases = process_state.dumped_allocation_bases;
            const uint64_t dump_key = frame.allocation_base;
            if (!dumped_bases.insert(dump_key).second) {
                return;
            }
            DumpRecord record;
            if (DumpAllocation(state.process, CurrentOutputDirectory(state) / L"dumps", state.dumps_total, frame,
                state.rules.max_dump_bytes, state.rules.analyze_dumps, state.rules.carve_embedded_pe, record)) {
                ++state.dumps_total;
                ++process_state.dumps_total;
                state.embedded_pe_total += record.analysis.embedded_pes.size();
                event_dumps.push_back(record);
                process_state.dumps.push_back(record);
                state.dumps.push_back(record);
            }
        };

        for (const auto& frame : frames) {
            dump_frame(frame);
        }
        if (callback_frame_ptr) {
            dump_frame(*callback_frame_ptr);
        }
        if (event_value_frame_ptr) {
            dump_frame(*event_value_frame_ptr);
        }
    }

    OriginRegionDumpRecord origin_region_dump;
    OriginRegionDumpRecord* origin_region_dump_ptr = nullptr;
    if (alert && event.event_type == kMonitorEventDllLoad && origin_trace.present) {
        const FrameInfo* visible_caller = SelectDllLoadCallerFrame(frames);
        if (DumpOriginRegion(state, modules, origin_trace, visible_caller, event.target_name, origin_region_dump)) {
            ++state.origin_regions_total;
            ++process_state.origin_regions_total;
            process_state.origin_region_dumps.push_back(origin_region_dump);
            state.origin_region_dumps.push_back(origin_region_dump);
            origin_region_dump_ptr = &origin_region_dump;
        }
    }

    const std::wstring summary = state.full_stack_output ? BuildStackDisplaySummary(frames) : BuildStackSummary(frames);
    RecordDllLoadMemoryObservation(state, event, modules, frames, summary, alert, score,
        origin_trace, origin_region_dump_ptr);
    RecordNetworkUseObservation(state, process_state, event, frames, event_value_frame_ptr,
        summary, alert, score, rule_hits);
    const DetectionDecision decision = BuildDetectionDecision(
        event.event_type,
        alert,
        has_unbacked || network_caller_unbacked,
        has_backed_modified || network_caller_backed_modified,
        has_unwind_tampered || network_caller_unwind_tampered || has_byoud_evidence || has_shadow_stack_evidence,
        has_gadget_candidate,
        has_callsite_anomaly,
        recent_suspicious_callback,
        origin_trace);
    ++state.decision_counts[decision.confidence];
    ++process_state.decision_counts[decision.confidence];
    WriteEventJson(state, event, frames, callback_frame_ptr, event_value_frame_ptr,
        summary, alert, score, rule_hits, event_dumps, byoud_trace.event_records,
        shadow_stack_trace.event_records,
        origin_trace, origin_region_dump_ptr, decision);

    if (state.ui) {
        std::wstring ui_target = event.target_name;
        std::vector<std::pair<std::wstring, std::wstring>> event_details;
        if ((event.event_type == kMonitorEventRemoteFollow || event.event_type == kMonitorEventNetReset) &&
            event.event_name[0] != L'\0') {
            ui_target = std::wstring(event.event_name) + L":" + ui_target;
        }
        if (event.event_type == kMonitorEventLdrIntegrity) {
            ui_target += L" ep=" + Hex64Wide(event.ldr_entrypoint);
            std::wostringstream entry;
            entry << L"table=" << Hex64Wide(event.ldr_table_entry)
                << L" base=" << Hex64Wide(event.ldr_dll_base)
                << L" size=" << Hex64Wide(event.ldr_size_of_image);
            event_details.emplace_back(L"ldr entry", entry.str());

            std::wostringstream entrypoint;
            entrypoint << L"current=" << Hex64Wide(event.ldr_entrypoint)
                << L" expected=" << Hex64Wide(event.ldr_expected_entrypoint);
            if (event_value_frame_ptr) {
                entrypoint << L" label=" << FrameDisplayLabel(*event_value_frame_ptr);
            }
            event_details.emplace_back(L"entrypoint", entrypoint.str());

            std::wostringstream ep_memory;
            ep_memory << L"region=" << Hex64Wide(event.ldr_entrypoint_region_base)
                << L" size=" << Hex64Wide(event.ldr_entrypoint_region_size)
                << L" " << ProtectToString(event.ldr_entrypoint_protect)
                << L" " << TypeToString(event.ldr_entrypoint_type);
            event_details.emplace_back(L"ep memory", ep_memory.str());

            if (event.ldr_original_base || event.ldr_original_base_region_base) {
                std::wostringstream original_base;
                original_base << L"value=" << Hex64Wide(event.ldr_original_base)
                    << L" region=" << Hex64Wide(event.ldr_original_base_region_base)
                    << L" " << ProtectToString(event.ldr_original_base_protect)
                    << L" " << TypeToString(event.ldr_original_base_type);
                event_details.emplace_back(L"original base", original_base.str());
            }
        }
        if (event.event_type == kMonitorEventNetworkApi) {
            if (event_value_frame_ptr) {
                event_details.emplace_back(L"caller", FrameDisplayLabel(*event_value_frame_ptr));
            }
            if (network_import_checked) {
                event_details.emplace_back(
                    L"static import",
                    network_import_missing ? L"not present in caller import table" : L"present in caller import table");
            }
        }
        state.ui->EventCard(
            EventTypeToString(event.event_type),
            ui_target,
            alert,
            score,
            summary,
            rule_hits,
            event_details,
            state.events_total,
            state.alerts_total,
            state.dumps_total);
    }
}

