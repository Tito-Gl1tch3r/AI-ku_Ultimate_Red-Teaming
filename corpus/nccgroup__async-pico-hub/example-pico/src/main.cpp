#include <Windows.h>
#include <time.h>
#include <cstdint>
#include <pico/utils.h>
#include <pico/pico.h>
#include <pico/beacon/api.h>


extern "C" {

	void go(pic::ThreadContext* thread);

}

#ifndef BUILD_OBJECTS_ONLY
// This code is compiled only if BUILD_OBJECTS_ONLY is NOT defined
#include <iostream>

#endif


extern "C" {

#pragma code_seg(".text$A")
	void go(pic::ThreadContext* thread) {
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);
		DFR_LOCAL(USER32, MessageBoxA);

		pic::init(thread);

		DBG_PRINT("Before printing thread name");
		DBG_PRINT(thread->name.c_str());
		thread->name = "ExamplePICO";

		pic::vector<pic::string<char>> local;

		MessageBoxA(nullptr, "Example Window!", "Test message", MB_OK);

		if (thread->args.size() > 0 && thread->args[0].type == pic::arg_string) {
			MessageBoxA(nullptr, thread->args[0].string_value.c_str(), "Test message", MB_OK);
		}

		if (thread->args.size() > 1 && thread->args[0].type == pic::arg_string && thread->args[1].type == pic::arg_string) {
			MessageBoxA(nullptr, thread->args[1].string_value.c_str(), thread->args[0].string_value.c_str(), MB_OK);
		}

		BeaconPrintf(CALLBACK_OUTPUT, "Wake up, Wake up!");

		thread->state = pic::ThreadState::Uninitialized;
	}
#pragma code_seg()

}


#ifndef BUILD_OBJECTS_ONLY

int main()
{
	pic::ThreadContext thread;
	thread.state = pic::ThreadState::Failed;
	go(&thread);
	thread.state = pic::ThreadState::Failed;
	go(&thread);
}
#endif
