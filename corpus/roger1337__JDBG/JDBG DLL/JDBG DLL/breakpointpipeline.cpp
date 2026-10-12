#include "breakpointpipeline.h"
#include <jni.h>
#include <jvmti.h>
#include <json.hpp>
#include "objecthandler.h"

using json = nlohmann::basic_json<>;





void populateStackTrace(jvmtiEnv* jvmti, jthread& thread, BreakpointResponse& response) {
	constexpr int FRAME_COUNT = 16;
	jvmtiFrameInfo* frames = new jvmtiFrameInfo[FRAME_COUNT];
	jint count;
	jvmti->GetStackTrace(thread, 0, FRAME_COUNT, frames, &count);

	for (int i = 0; i < count; i++) {

		jvmtiFrameInfo& info = frames[i];

		char* frameMethodName;
		char* frameMethodSig;
		jvmti->GetMethodName(info.method, &frameMethodName, &frameMethodSig, NULL);


		jclass frameKlass;
		jvmti->GetMethodDeclaringClass(info.method, &frameKlass);
		char* frameKlassSignature;
		jvmti->GetClassSignature(frameKlass, &frameKlassSignature, NULL);

		StackTraceElement elm;
		elm.klassSignature = frameKlassSignature;
		elm.methodName = frameMethodName;
		elm.methodSignature = frameMethodSig;
		elm.location = info.location;

		response.stackTrace.push_back(elm);
	}
}


// clean up memory if bothered
void populateLocalVars(jvmtiEnv* jvmti,
	JNIEnv* jni,
	jthread thread,
	jmethodID method,
	jlocation location,
	BreakpointResponse& response) {

	jint entriesCount;
	jvmtiLocalVariableEntry* entries;
	if (jvmti->GetLocalVariableTable(method, &entriesCount, &entries) != JVMTI_ERROR_NONE) {
		MessageBoxA(nullptr, "Could not get local variables at breakpoint", "JDBG", MB_ICONERROR);

	}

	const auto& addValue{ [&](char* sig, char* name, const std::string& value) {
		LocalVariableElement elm;
		elm.signature = sig;
		elm.name = name;
		elm.value = value;
		response.localVars.push_back(elm);

	} };

	for (int i = 0; i < entriesCount; i++) {
		jvmtiLocalVariableEntry entry = *(entries + i);

		std::string signature{ entry.signature };

		if (signature.empty()) {
			continue;
		}

		if (signature == "B" || signature == "I" || signature == "C" || signature == "S" || signature == "Z") {
			jint value;
			if (jvmti->GetLocalInt(thread, 0, entry.slot, &value) != JVMTI_ERROR_NONE) {
				MessageBoxA(nullptr, "Failed to get local int", "JDBG", MB_ICONERROR);
			}

			addValue(entry.signature, entry.name, std::to_string(value));

		} else if (signature == "D") {
			jdouble value;
			if (jvmti->GetLocalDouble(thread, 0, entry.slot, &value) != JVMTI_ERROR_NONE) {
				MessageBoxA(nullptr, "Failed to get local double", "JDBG", MB_ICONERROR);
			}
			addValue(entry.signature, entry.name, std::to_string(value));

		} else if (signature == "F") {
			jfloat value;
			if (jvmti->GetLocalFloat(thread, 0, entry.slot, &value) != JVMTI_ERROR_NONE) {
				MessageBoxA(nullptr, "Failed to get local float", "JDBG", MB_ICONERROR);
			}
			addValue(entry.signature, entry.name, std::to_string(value));


		
		}
		else if (signature == "J") {
			jlong value;
			if (jvmti->GetLocalLong(thread, 0, entry.slot, &value) != JVMTI_ERROR_NONE) {
				MessageBoxA(nullptr, "Failed to get local long", "JDBG", MB_ICONERROR);
			}
			addValue(entry.signature, entry.name, std::to_string(value));



		}
		else if(signature.starts_with("L")) {
			std::string cleanedSig{ signature.substr(1, signature.size() - 2) };


			std::map<std::string, jclass>* klassMap{ BreakpointPipeline::getInstance().klassMap };


			// object logic
			// TODO need to define mutexs
		}

	}
}

void JNICALL breakpoint(jvmtiEnv* jvmti,
	JNIEnv* jni,
	jthread thread,
	jmethodID method,
	jlocation location) {


	BreakpointResponse response;

	char* methodName;
	char* methodSig;
	jvmti->GetMethodName(method, &methodName, &methodSig, NULL);


	jclass klass;
	jvmti->GetMethodDeclaringClass(method, &klass);
	char* klassSignature;
	jvmti->GetClassSignature(klass, &klassSignature, NULL);


	response.klassSignature = klassSignature;
	response.methodName = methodName;
	response.methodSignature = methodSig;

	populateStackTrace(jvmti, thread, response);
	populateLocalVars(jvmti, jni, thread, method, location, response);


	BreakpointPipeline::getInstance().sendAndAwait(jvmti, response, method, location);
}

BreakpointPipeline::BreakpointPipeline(const wchar_t* p) : ClientPipeline{ p } {
};

void BreakpointPipeline::sendAndAwait(jvmtiEnv* jvmti, BreakpointResponse& response, jmethodID method, jlocation location) {
	json j = response;
	std::string dump{ j.dump() };

	sendData(dump.c_str(), strlen(dump.c_str()));


	// block until it sends something.
	char buffer[1];
	DWORD bytesRead;
	if (!ReadFile(handle, buffer, 1, &bytesRead, NULL)) {
		CloseHandle(handle);
		// it means the pipe got broken, so we should destroy the breakpoints.
		if (jvmti->ClearBreakpoint(method, location) != JVMTI_ERROR_NONE) {
			MessageBoxA(nullptr, "Failed to clear breakpoint after pipe broke.", "JDBG", MB_ICONERROR);
		}
	}
}