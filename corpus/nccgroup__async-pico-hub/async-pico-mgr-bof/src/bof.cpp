#include <Windows.h>
#include <type_traits>

#ifndef BUILD_OBJECTS_ONLY
#include "base\mock.h"
//#undef DECLSPEC_IMPORT
//#define DECLSPEC_IMPORT
#endif

#include <pico/utils.h>
#include <pico/pico.h>
#include "commands/handle_async.h"
#include "commands/handle_print.h"
#include "commands/handle_stop.h"
#include "beacon.h"

extern "C" {

	static pic::ThreadRegistry* get_or_create_registry();
	static const char* extract_action(datap& parser);
	static void dispatch_action(pic::ThreadRegistry& registry, datap& parser, const char* action);

#pragma code_seg(".text$A")
	void go(char* args, int len) {
		auto registry = get_or_create_registry();
		if (!registry) {
			return;
		}

		datap parser{ args, args, len, len };

		const auto action = extract_action(parser);
		if (!action) {
			return;
		}

		dispatch_action(*registry, parser, action);
	}
#pragma code_seg()

	static pic::ThreadRegistry* get_or_create_registry()
	{
		DFR_LOCAL(KERNEL32, VirtualAlloc);

		auto* buffer = BeaconGetValue("picthreadstore");

		if (!buffer) {
			buffer = VirtualAlloc(
				nullptr,
				sizeof(pic::ThreadRegistry),
				MEM_COMMIT | MEM_RESERVE,
				PAGE_READWRITE);

			if (!buffer) {
				BeaconPrintf(
					CALLBACK_ERROR,
					"Failed to allocate thread registry.");
				return nullptr;
			}

			BeaconAddValue("picthreadstore", buffer);
		}

		return static_cast<pic::ThreadRegistry*>(buffer);
	}

	static const char* extract_action(datap& parser)
	{
		auto* action =
			static_cast<const char*>(BeaconDataExtract(&parser, nullptr));

		if (!action) {
			BeaconPrintf(
				CALLBACK_ERROR,
				"Missing action parameter.");
			return nullptr;
		}

		return action;
	}

	static void dispatch_action(
		pic::ThreadRegistry& registry,
		datap& parser,
		const char* action)
	{
		DFR_LOCAL(MSVCRT, strcmp);

		if (strcmp(action, "async") == 0) {
			handle_async(registry, parser);
			return;
		}

		if (strcmp(action, "print") == 0) {
			handle_print(registry);
			return;
		}

		if (strcmp(action, "stop") == 0) {
			handle_stop(registry, parser);
			return;
		}

		if (strcmp(action, "stop-name") == 0) {
			handle_stop_name(registry, parser);
			return;
		}

		BeaconPrintf(
			CALLBACK_ERROR,
			"Unknown action: %s",
			action);
	}

	void free_impl(void* ptr) {
		DFR_LOCAL(msvcrt, free);
		free(ptr);
	}

}



// Define a main function for the bebug build
#ifndef BUILD_OBJECTS_ONLY

#include <fstream>
#include <iostream>

std::vector<char> SimpleReadToByteArray(const std::string& filePath) {
	std::ifstream file(filePath, std::ios::binary);
	if (!file.is_open()) {
		throw std::runtime_error("Error: Unable to open the file.");
	}
	return { std::istreambuf_iterator<char>(file), {} };
}


int main(int argc, char* argv[]) {
	// Run BOF's entrypoint
	const char* pic = R"(C:\Users\USER\PATH\TO\YOUR\PICO.obj)";
	std::vector<char> picData = SimpleReadToByteArray(pic);
	bof::runMocked<>(go, "async", picData, "noname", "z", "wombat");
	std::cin.get();
	bof::runMocked<>(go, "dump");
	std::cin.clear();
	std::cin.get();
	return 0;
}
#endif