#pragma once
#include <Windows.h>
#include <pico/utils.h>
#include <pico/pico.h>
#include "beacon.h"

extern "C" {
	static bool stop_thread(pic::ThreadContext& thread)
	{
		DFR_LOCAL(KERNEL32, WaitForSingleObject);
		DFR_LOCAL(KERNEL32, SetEvent);
		DFR_LOCAL(KERNEL32, VirtualFree);
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);

		DBG_PRINT("Stopping PIC thread.");

		thread.state = pic::ThreadState::Stopping;
		SetEvent(thread.stop_event);

		constexpr DWORD k_thread_shutdown_timeout_ms = 30000;

		const auto result =
			WaitForSingleObject(thread.handle, k_thread_shutdown_timeout_ms);

		if (result == WAIT_TIMEOUT) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"Thread shutdown timed out.");

			thread.state = pic::ThreadState::Failed;
			return false;
		}

		thread.state = pic::ThreadState::Stopped;

		if (!VirtualFree(thread.location, 0, MEM_RELEASE)) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"VirtualFree failed.");
			return false;
		}

		BeaconPrintf(
			CALLBACK_OUTPUT,
			"Successfully stopped PIC thread.");

		return true;
	}

	static void handle_stop(
		pic::ThreadRegistry& registry,
		datap& parser)
	{
		const auto id = BeaconDataInt(&parser);

		if (id < 0 ||
			static_cast<size_t>(id) >= registry.max_threads) {

			BeaconPrintf(
				CALLBACK_ERROR,
				"Invalid thread id.");
			return;
		}

		auto& thread = registry.threads[id];

		if (thread.state != pic::ThreadState::Running) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"Thread is not running.");
			return;
		}

		stop_thread(thread);
	}

	static void handle_stop_name(
		pic::ThreadRegistry& registry,
		datap& parser)
	{
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);

		const auto* pico_name =
			reinterpret_cast<const char*>(
				BeaconDataExtract(
					&parser,
					nullptr));

		if (!pico_name) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"Missing PIC name.");
			return;
		}

		pic::ThreadContext* target_thread =
			nullptr;

		for (auto& thread : registry.threads) {

			if (thread.name == pic::string<char>(pico_name))
			{
				target_thread = &thread;
				break;
			}

		}

		if (!target_thread) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"PIC not found.");
			return;
		}

		if (target_thread->state.load() != pic::ThreadState::Running)
		{
			BeaconPrintf(
				CALLBACK_ERROR,
				"PIC is not running.");
			return;
		}

		DBG_PRINT(
			"[stop-name] Signaling PIC thread.");

		stop_thread(*target_thread);
	}
}