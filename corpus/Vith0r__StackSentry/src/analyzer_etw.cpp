#include <krabs/krabs/client.hpp>
#include <krabs/krabs/kernel_providers.hpp>
#include <krabs/krabs/parser.hpp>
#include <krabs/krabs/schema.hpp>
#include <krabs/krabs/trace_context.hpp>

static std::wstring NarrowToWide(const std::string& value) {
    if (value.empty()) {
        return {};
    }
    int needed = MultiByteToWideChar(CP_UTF8, 0, value.data(), static_cast<int>(value.size()), nullptr, 0);
    UINT code_page = CP_UTF8;
    if (needed <= 0) {
        code_page = CP_ACP;
        needed = MultiByteToWideChar(code_page, 0, value.data(), static_cast<int>(value.size()), nullptr, 0);
    }
    if (needed <= 0) {
        return {};
    }
    std::wstring output(static_cast<size_t>(needed), L'\0');
    MultiByteToWideChar(code_page, 0, value.data(), static_cast<int>(value.size()), output.data(), needed);
    return output;
}

static std::wstring ExceptionTextToWide(const std::exception& ex) {
    return NarrowToWide(ex.what());
}

static bool EtwTryParseString(krabs::parser& parser, std::initializer_list<const wchar_t*> names, std::wstring& value) {
    for (const wchar_t* name : names) {
        std::wstring wide;
        if (parser.try_parse<std::wstring>(name, wide) && !wide.empty()) {
            value = wide;
            return true;
        }
        std::string narrow;
        if (parser.try_parse<std::string>(name, narrow) && !narrow.empty()) {
            value = NarrowToWide(narrow);
            return !value.empty();
        }
    }
    return false;
}

static bool EtwTryParseUInt32(krabs::parser& parser, std::initializer_list<const wchar_t*> names, DWORD& value) {
    for (const wchar_t* name : names) {
        uint32_t parsed = 0;
        if (parser.try_parse<uint32_t>(name, parsed)) {
            value = static_cast<DWORD>(parsed);
            return true;
        }
        uint64_t parsed64 = 0;
        if (parser.try_parse<uint64_t>(name, parsed64)) {
            value = static_cast<DWORD>(parsed64);
            return true;
        }
    }
    return false;
}

static bool EtwTryParseUInt64(krabs::parser& parser, std::initializer_list<const wchar_t*> names, uint64_t& value) {
    for (const wchar_t* name : names) {
        krabs::pointer pointer{};
        if (parser.try_parse<krabs::pointer>(name, pointer)) {
            value = pointer.address;
            return true;
        }
        uint64_t parsed64 = 0;
        if (parser.try_parse<uint64_t>(name, parsed64)) {
            value = parsed64;
            return true;
        }
        uint32_t parsed32 = 0;
        if (parser.try_parse<uint32_t>(name, parsed32)) {
            value = parsed32;
            return true;
        }
    }
    return false;
}

static bool EtwOpcodeLooksLikeStart(int opcode, const std::wstring& opcode_name) {
    const std::wstring lower = ToLower(opcode_name);
    return opcode == 1 ||
        lower.find(L"start") != std::wstring::npos ||
        lower.find(L"load") != std::wstring::npos ||
        lower.find(L"create") != std::wstring::npos;
}

static bool EtwOpcodeLooksLikeStop(int opcode, const std::wstring& opcode_name) {
    const std::wstring lower = ToLower(opcode_name);
    return opcode == 2 ||
        lower.find(L"stop") != std::wstring::npos ||
        lower.find(L"end") != std::wstring::npos ||
        lower.find(L"unload") != std::wstring::npos ||
        lower.find(L"delete") != std::wstring::npos;
}

static bool EtwIsInterestingPidLocked(const RunState& state, DWORD pid) {
    return pid != 0 && state.etw_interesting_pids.find(pid) != state.etw_interesting_pids.end();
}

static bool EtwShouldRecordProcessEvent(RunState& state, DWORD pid, DWORD parent_pid, bool is_start) {
    if (pid == 0) {
        return false;
    }

    std::lock_guard<std::mutex> lock(state.etw_mutex);
    const bool already_interesting = EtwIsInterestingPidLocked(state, pid);
    const bool parent_interesting = EtwIsInterestingPidLocked(state, parent_pid);
    if (pid == state.pid || already_interesting || (is_start && parent_interesting)) {
        state.etw_interesting_pids.insert(pid);
        return true;
    }
    return false;
}

static bool EtwShouldRecordPid(RunState& state, DWORD pid) {
    std::lock_guard<std::mutex> lock(state.etw_mutex);
    return EtwIsInterestingPidLocked(state, pid);
}

static void EtwRecordTimelineEvent(RunState& state, EtwTimelineEvent event) {
    std::lock_guard<std::mutex> lock(state.etw_mutex);
    ++state.etw_events_total;
    if (event.kind.find(L"process") == 0) {
        ++state.etw_process_events;
    } else if (event.kind.find(L"thread") == 0) {
        ++state.etw_thread_events;
    } else if (event.kind == L"image_load" || event.kind == L"image_unload") {
        ++state.etw_image_loads;
    }
    state.etw_timeline.push_back(std::move(event));
    if (state.etw_timeline.size() > 4096) {
        state.etw_timeline.erase(state.etw_timeline.begin(), state.etw_timeline.begin() + 512);
    }
}

class EtwSupervisor {
public:
    ~EtwSupervisor() {
        Stop();
    }

    bool Start(RunState& state, std::wstring& error) {
        if (running_.load()) {
            return true;
        }

        state_ = &state;
        start_tick_ = GetTickCount64();

        try {
            const std::wstring trace_name =
                L"StackSentryKernel_" + std::to_wstring(state.pid) + L"_" + std::to_wstring(GetTickCount64());
            trace_ = std::make_unique<krabs::kernel_trace>(trace_name);

            process_provider_.add_on_event_callback([this](const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
                OnProcessEvent(record, trace_context);
            });
            thread_provider_.add_on_event_callback([this](const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
                OnThreadEvent(record, trace_context);
            });
            image_provider_.add_on_event_callback([this](const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
                OnImageEvent(record, trace_context);
            });

            trace_->enable(process_provider_);
            trace_->enable(thread_provider_);
            trace_->enable(image_provider_);
            trace_->open();
        } catch (const std::exception& ex) {
            error = ExceptionTextToWide(ex);
            if (error.empty()) {
                error = L"failed to open kernel ETW trace";
            }
            trace_.reset();
            return false;
        } catch (...) {
            error = L"failed to open kernel ETW trace";
            trace_.reset();
            return false;
        }

        running_.store(true);
        state.etw_status = L"running";
        worker_ = std::thread([this]() {
            try {
                if (trace_) {
                    trace_->process();
                }
            } catch (const std::exception& ex) {
                if (state_) {
                    std::lock_guard<std::mutex> lock(state_->etw_mutex);
                    state_->etw_status = L"stopped with error";
                    state_->etw_error = ExceptionTextToWide(ex);
                }
            } catch (...) {
                if (state_) {
                    std::lock_guard<std::mutex> lock(state_->etw_mutex);
                    state_->etw_status = L"stopped with error";
                    state_->etw_error = L"ETW processing failed";
                }
            }
            running_.store(false);
        });
        return true;
    }

    void Stop() {
        if (!trace_ && !worker_.joinable()) {
            return;
        }

        if (trace_) {
            try {
                trace_->stop();
            } catch (...) {
            }
        }
        if (worker_.joinable()) {
            worker_.join();
        }
        if (state_) {
            std::lock_guard<std::mutex> lock(state_->etw_mutex);
            if (state_->etw_status == L"running" || state_->etw_status == L"requested") {
                state_->etw_status = L"stopped";
            }
        }
        trace_.reset();
        running_.store(false);
    }

private:
    void OnProcessEvent(const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
        if (!state_) {
            return;
        }
        try {
            krabs::schema schema(record, trace_context.schema_locator);
            krabs::parser parser(schema);

            DWORD pid = static_cast<DWORD>(schema.process_id());
            DWORD parent_pid = 0;
            EtwTryParseUInt32(parser, { L"ProcessId", L"ProcessID", L"PID" }, pid);
            EtwTryParseUInt32(parser, { L"ParentId", L"ParentID", L"ParentProcessId", L"ParentProcessID" }, parent_pid);

            const std::wstring opcode_name = schema.opcode_name() ? schema.opcode_name() : L"";
            const int opcode = schema.event_opcode();
            const bool start = EtwOpcodeLooksLikeStart(opcode, opcode_name);
            if (!EtwShouldRecordProcessEvent(*state_, pid, parent_pid, start)) {
                return;
            }

            EtwTimelineEvent event;
            event.tick_ms = GetTickCount64() - start_tick_;
            event.kind = start ? L"process_start" : (EtwOpcodeLooksLikeStop(opcode, opcode_name) ? L"process_stop" : L"process");
            event.pid = pid;
            event.tid = static_cast<DWORD>(schema.thread_id());
            event.parent_pid = parent_pid;
            event.opcode = opcode_name;
            event.provider = schema.provider_name() ? schema.provider_name() : L"";
            EtwTryParseString(parser, { L"ImageFileName", L"ImageName", L"ProcessName" }, event.process_name);
            EtwRecordTimelineEvent(*state_, std::move(event));
        } catch (...) {
        }
    }

    void OnThreadEvent(const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
        if (!state_) {
            return;
        }
        try {
            krabs::schema schema(record, trace_context.schema_locator);
            krabs::parser parser(schema);

            DWORD pid = static_cast<DWORD>(schema.process_id());
            DWORD tid = static_cast<DWORD>(schema.thread_id());
            EtwTryParseUInt32(parser, { L"ProcessId", L"ProcessID" }, pid);
            EtwTryParseUInt32(parser, { L"ThreadId", L"ThreadID", L"TThreadId", L"TThreadID" }, tid);
            if (!EtwShouldRecordPid(*state_, pid)) {
                return;
            }

            const std::wstring opcode_name = schema.opcode_name() ? schema.opcode_name() : L"";
            const int opcode = schema.event_opcode();
            EtwTimelineEvent event;
            event.tick_ms = GetTickCount64() - start_tick_;
            event.kind = EtwOpcodeLooksLikeStart(opcode, opcode_name) ? L"thread_start" :
                (EtwOpcodeLooksLikeStop(opcode, opcode_name) ? L"thread_stop" : L"thread");
            event.pid = pid;
            event.tid = tid;
            event.opcode = opcode_name;
            event.provider = schema.provider_name() ? schema.provider_name() : L"";
            EtwRecordTimelineEvent(*state_, std::move(event));
        } catch (...) {
        }
    }

    void OnImageEvent(const EVENT_RECORD& record, const krabs::trace_context& trace_context) {
        if (!state_) {
            return;
        }
        try {
            krabs::schema schema(record, trace_context.schema_locator);
            krabs::parser parser(schema);

            DWORD pid = static_cast<DWORD>(schema.process_id());
            EtwTryParseUInt32(parser, { L"ProcessId", L"ProcessID", L"PID" }, pid);
            if (!EtwShouldRecordPid(*state_, pid)) {
                return;
            }

            uint64_t base = 0;
            uint64_t size = 0;
            EtwTryParseUInt64(parser, { L"ImageBase", L"BaseAddress", L"ImageBaseAddress" }, base);
            EtwTryParseUInt64(parser, { L"ImageSize", L"Size", L"ImageSizeBytes" }, size);

            const std::wstring opcode_name = schema.opcode_name() ? schema.opcode_name() : L"";
            EtwTimelineEvent event;
            event.tick_ms = GetTickCount64() - start_tick_;
            event.kind = EtwOpcodeLooksLikeStop(schema.event_opcode(), opcode_name) ? L"image_unload" : L"image_load";
            event.pid = pid;
            event.tid = static_cast<DWORD>(schema.thread_id());
            event.image_base = base;
            event.image_size = size;
            event.opcode = opcode_name;
            event.provider = schema.provider_name() ? schema.provider_name() : L"";
            EtwTryParseString(parser, { L"FileName", L"ImageName", L"ImageFileName" }, event.image_name);
            EtwRecordTimelineEvent(*state_, std::move(event));
        } catch (...) {
        }
    }

    RunState* state_ = nullptr;
    uint64_t start_tick_ = 0;
    krabs::kernel::process_provider process_provider_;
    krabs::kernel::thread_provider thread_provider_;
    krabs::kernel::image_load_provider image_provider_;
    std::unique_ptr<krabs::kernel_trace> trace_;
    std::thread worker_;
    std::atomic<bool> running_{ false };
};

static void WriteEtwTimeline(RunState& state) {
    if (!state.etw_telemetry && state.etw_timeline.empty()) {
        return;
    }

    std::vector<EtwTimelineEvent> events;
    std::wstring status;
    std::wstring error;
    {
        std::lock_guard<std::mutex> lock(state.etw_mutex);
        events = state.etw_timeline;
        status = state.etw_status;
        error = state.etw_error;
    }

    std::ofstream output(state.out_dir / L"etw_timeline.json", std::ios::out | std::ios::trunc);
    if (!output) {
        return;
    }

    output << "{"
        << "\"enabled\":" << (state.etw_telemetry ? "true" : "false") << ","
        << "\"status\":" << JsonString(status) << ","
        << "\"error\":" << JsonString(error) << ","
        << "\"events_total\":" << state.etw_events_total << ","
        << "\"process_events\":" << state.etw_process_events << ","
        << "\"thread_events\":" << state.etw_thread_events << ","
        << "\"image_loads\":" << state.etw_image_loads << ","
        << "\"events\":[";
    for (size_t i = 0; i < events.size(); ++i) {
        const auto& item = events[i];
        if (i) {
            output << ",";
        }
        output << "{"
            << "\"tick_ms\":" << item.tick_ms << ","
            << "\"kind\":" << JsonString(item.kind) << ","
            << "\"pid\":" << item.pid << ","
            << "\"tid\":" << item.tid << ","
            << "\"parent_pid\":" << item.parent_pid << ","
            << "\"image_base\":\"" << Hex64(item.image_base) << "\","
            << "\"image_size\":" << item.image_size << ","
            << "\"image_name\":" << JsonString(item.image_name) << ","
            << "\"process_name\":" << JsonString(item.process_name) << ","
            << "\"opcode\":" << JsonString(item.opcode) << ","
            << "\"provider\":" << JsonString(item.provider)
            << "}";
    }
    output << "]}";
}
