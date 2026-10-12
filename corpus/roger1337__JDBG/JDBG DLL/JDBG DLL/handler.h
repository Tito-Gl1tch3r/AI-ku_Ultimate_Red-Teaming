#pragma once

#include "logpipeline.h"
#include "jdbgpipeline.h"
#include <jni.h>
#include <jvmti.h>
#include <Windows.h>
#include <map>
#include <string>

class Handler {
protected:
	JdbgPipeline* pipeline;
	LogPipeline* logPipeline = nullptr;
	ServerCommand command;
	jvmtiEnv* jvmti;
	JNIEnv* jni;

public:


	Handler(ServerCommand c, jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : command{ c }, jvmti{ jvmti }, jni{ jni }, pipeline{ pipeline } {

	}

	ServerCommand getCommand() {
		return command;
	}


	virtual int handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) { return 0; };

	void setLogPipeline(LogPipeline* p) {
		logPipeline = p;
	}


	void msg(const std::string& message, bool flush) {
		if (logPipeline != nullptr) {
			logPipeline->addMessage(message, flush);
		}
	}

	void msgLog(const std::string& message) {
		msg(message, false);
	}

	void flushLog() {
		logPipeline->flush();
	}
};