#pragma once
#include <pico/core/vector.h>
#include <pico/core/string.h>
#include <pico/core/atomic.h>
#include <pico/beacon/arguments.h>
namespace pic {
	struct OutputMessage {
		int type; // BeaconPrintf types (CALLBACK_OUTPUT, CALLBACK_ERROR, etc)
		pic::string<char> text;
	};

	struct AsyncContext {
		CRITICAL_SECTION mutex;
		CONDITION_VARIABLE cv;
		pic::vector<OutputMessage>* output;
	};

	struct OutputData {
		pic::vector<void*> data;
	};

	enum class ThreadState : long {
		Uninitialized,
		Running,
		Stopping,
		Stopped,
		Failed
	};

	struct ThreadContext
	{
		DWORD id;
		HANDLE handle; // handle to the Thread itself from CreateThread
		pic::string<char> name;
		void* location;
		size_t size;
		pic::atomic<ThreadState> state{ ThreadState::Uninitialized };
		pic::vector<Argument> args;
		OutputData output;
		HANDLE impersonationToken;
		AsyncContext* async;
		HANDLE stop_event;
	};

	struct ThreadRegistry
	{
		static constexpr size_t max_threads = 10;
		pic::ThreadContext threads[max_threads];
	};

}

#define _PRINT 1
#if !defined(BUILD_OBJECTS_ONLY) || defined(_PRINT)
#define DBG_PRINT(msg) OutputDebugStringA(msg)
#else
#define DBG_PRINT(msg) ((void)0)
#endif