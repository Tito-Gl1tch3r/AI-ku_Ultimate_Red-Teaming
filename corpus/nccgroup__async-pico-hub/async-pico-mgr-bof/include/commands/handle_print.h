#pragma once
#include <Windows.h>
#include <pico/utils.h>
#include <pico/pico.h>
#include "beacon.h"

static void handle_print(
	pic::ThreadRegistry& registry)
{
	formatp output_buffer;

	constexpr int output_buffer_size =
		256 * 256;

	BeaconFormatAlloc(
		&output_buffer,
		output_buffer_size);

	unsigned active_thread_count = 0;
	unsigned thread_index = 0;

	for (auto& thread : registry.threads) {

		if (thread.state.load() ==
			pic::ThreadState::Uninitialized)
		{
			++thread_index;
			continue;
		}

		BeaconFormatPrintf(
			&output_buffer,
			const_cast<char*>(
				"PICO ID ([%d]) :: PICO NAME [%s]\n"),
			thread_index,
			thread.name.c_str());

		unsigned message_index = 0;

		for (const auto* message :
			thread.output.data)
		{
			if (!message) {
				continue;
			}

			BeaconFormatPrintf(
				&output_buffer,
				const_cast<char*>(
					"\t\tMessage %d: %s\n"),
				message_index,
				message);

			++message_index;
		}

		++active_thread_count;
		++thread_index;
	}

	if (active_thread_count > 0) {

		BeaconPrintf(
			CALLBACK_OUTPUT,
			"%s\n",
			BeaconFormatToString(
				&output_buffer,
				nullptr));
	}
	else {

		BeaconPrintf(
			CALLBACK_OUTPUT,
			"No running picos.");
	}

	BeaconFormatFree(&output_buffer);
}