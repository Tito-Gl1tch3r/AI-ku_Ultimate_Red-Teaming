#include "pipeline.h"
#include "jdbgpipeline.h"
#include "handlerclassnames.h"
#include <jni.h>
#include <jvmti.h>
#include <vector>
#include <memory>
#include "handlerclassdata.h"
#include "handlerclassnames.h"
#include "handlertagobjects.h"
#include "handlergetreferences.h"
#include "handlerobjectfields.h"
#include "handlersetobject.h"
#include "handlersetbreakpoint.h"
#include "handlerclearbreakpoint.h"

#include <map>
#include <string>
#include "logpipeline.h"
#include "breakpointpipeline.h"


std::map<std::string, jclass> klassMap;

JdbgPipeline::JdbgPipeline(const wchar_t* p) : ClientPipeline{ p } {

};


void JdbgPipeline::sendStatus(char status) {
	sendData(&status, 1);
}

void populateKlassMap(jvmtiEnv* jvmti) {
	jint classCount;
	jclass* classesPtr;

	jvmti->GetLoadedClasses(&classCount, &classesPtr);


	int cur = 0;
	for (int i = 0; i < classCount; i++) {
		jclass klass = *(classesPtr + i);

		char* name;
		jvmti->GetClassSignature(klass, &name, NULL);

		if (sizeof(name) > 2 && name[0] != '[') {

			std::string n{ name };
			std::string cleanedName{ n.substr(1, n.size() - 2) };

			//MessageBoxA(nullptr, cleanedName.c_str(), "JDBG", MB_ICONERROR);


			
			klassMap.insert({cleanedName, klass });

		}

	}
}


void JdbgPipeline::startListen(jvmtiEnv* jvmti, JNIEnv* jni) {

	LogPipeline log{ L"\\\\.\\pipe\\jdbg_log" };
	populateKlassMap(jvmti);

	BreakpointPipeline::getInstance().setKlassMap(&klassMap);
	


	std::vector<std::unique_ptr<Handler>> handlers;
	handlers.push_back(std::make_unique<HandlerClassNames>(HandlerClassNames{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerClassData>(HandlerClassData{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerTagObjects>(HandlerTagObjects{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerGetReferences>(HandlerGetReferences{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerObjectFields>(HandlerObjectFields{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerSetObject>(HandlerSetObject{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerSetBreakpoint>(HandlerSetBreakpoint{ jvmti, jni, this }));
	handlers.push_back(std::make_unique<HandlerClearBreakpoint>(HandlerClearBreakpoint{ jvmti, jni, this }));

	for (std::unique_ptr<Handler>& h : handlers) {
		h->setLogPipeline(&log);
	}



	DWORD threadID{ GetThreadId(GetCurrentThread()) };
	log.addMessage("Thread id: " + std::to_string(threadID));
	log.flush();

	constexpr int BUFFER_SIZE = 500;
	constexpr int RESPONSE_BUFFER_SIZE = 50000000;

	char* responseBuffer = new char[RESPONSE_BUFFER_SIZE];

	while(true) {
		char* buffer = new char[BUFFER_SIZE];

		DWORD bytesRead{ 0 };

		if (!ReadFile(handle, buffer, BUFFER_SIZE, &bytesRead, NULL)) {
			CloseHandle(handle);
			break;
		}
		if (bytesRead == 0) {
			MessageBoxA(nullptr, "Failed to read message", "JDBG @ startListen", MB_ICONERROR);
			continue;
		}

		
		jint threadCount;
		jthread* threads;
		jvmti->GetAllThreads(&threadCount, &threads);

		jthread currentThread;
		if (jvmti->GetCurrentThread(&currentThread) != JVMTI_ERROR_NONE) {
			MessageBoxA(nullptr, "Failed to get current thread", "JDBG @ startListen", MB_ICONERROR);
		}

		for (int i = 0; i < threadCount; i++) {
			jthread thread{ *(threads + i) };

			if (!jni->IsSameObject(currentThread, thread)) {
				if (jvmti->SuspendThread(thread) != JVMTI_ERROR_NONE) {
					MessageBoxA(nullptr, "Failed to suspend thread", "JDBG @ startListen", MB_ICONERROR);

				}

			}
		}
		

		ServerCommand command = static_cast<ServerCommand>(buffer[0]);

		for (std::unique_ptr<Handler>& h : handlers) {
			if (h->getCommand() == command) {

				// make space for the code byte
				int status = 0;
				int len = h->handle(buffer + 1, bytesRead - 1, responseBuffer+1, status, klassMap);
				responseBuffer[0] = status;
				sendData(responseBuffer, len + 1);

			}
		}

		log.flush();

		
		for (int i = 0; i < threadCount; i++) {
			jthread thread{ *(threads + i) };

			if (!jni->IsSameObject(currentThread, thread)) {
				if (jvmti->ResumeThread(thread) != JVMTI_ERROR_NONE) {
					MessageBoxA(nullptr, "Failed to resume thread", "JDBG @ startListen", MB_ICONERROR);

				}
			}

		}
		


		delete[] buffer;
	}

	delete[] responseBuffer;
}

