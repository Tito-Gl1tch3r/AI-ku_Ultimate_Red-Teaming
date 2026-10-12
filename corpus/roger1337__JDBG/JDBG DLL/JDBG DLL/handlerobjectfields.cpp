#include "handlerobjectfields.h"
#include <json.hpp>
#include "jni.h"
#include "util.h"

using json = nlohmann::basic_json<>;


HandlerObjectFields::HandlerObjectFields(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : ObjectHandler{ GET_FIELDS, jvmti, jni, pipeline } {

}




void HandlerObjectFields::buildFields(json& response, jclass& klass, jobject& obj) {
	jint fieldsNum;
	jfieldID* fieldsPtr;
	if (jvmti->GetClassFields(klass, &fieldsNum, &fieldsPtr) != JVMTI_ERROR_NONE) {
		msgLog("Failed to get class fields");
		return;
	}

	const auto& addStringValue{ [&](std::string& signature, std::string& fieldName, jfieldID& field) {
		jobject fieldObject = jni->GetObjectField(obj, field);
		const char* data = jni->GetStringUTFChars((jstring)fieldObject, NULL);
		std::string str{ data };
		response["fields"][fieldName]["value"] = str;
		jni->ReleaseStringUTFChars((jstring)fieldObject, data);


	} };

	const auto& addValue{ [&](std::string& signature, std::string& fieldName, jfieldID& field) {
		if (signature == "B") response["fields"][fieldName]["value"] = std::to_string(jni->GetByteField(obj, field)); else
		if (signature == "C") response["fields"][fieldName]["value"] = std::to_string(jni->GetCharField(obj, field)); else
		if (signature == "D") response["fields"][fieldName]["value"] = std::to_string(jni->GetDoubleField(obj, field)); else
		if (signature == "F") response["fields"][fieldName]["value"] = std::to_string(jni->GetFloatField(obj, field)); else
		if (signature == "I") response["fields"][fieldName]["value"] = std::to_string(jni->GetIntField(obj, field)); else
		if (signature == "J") response["fields"][fieldName]["value"] = std::to_string(jni->GetLongField(obj, field)); else
		if (signature == "S") response["fields"][fieldName]["value"] = std::to_string(jni->GetShortField(obj, field)); else
		if (signature == "Z") response["fields"][fieldName]["value"] = std::to_string(jni->GetBooleanField(obj, field)); else {

			// TODO implement array support
			if (signature.starts_with("[")) {
				response["fields"][fieldName]["value"] = "Not Supported ";
				return;
			}

			if (signature == "Ljava/lang/String;") {
				addStringValue(signature, fieldName, field);
				return;
			}


			// is object
			jobject fieldObject = jni->GetObjectField(obj, field);
			/*
			std::string cleanedSig{ signature.substr(1, signature.size() - 2) };

			int num = ++instanceMapTag[cleanedSig];
			instanceMap[cleanedSig][num] = fieldObject;

			response["fields"][fieldName]["value"] = num;
			*/
			response["fields"][fieldName]["value"] = "Not Supported";


		}
 } };


	for (int i = 0; i < fieldsNum; i++) {
		jfieldID field{ *(fieldsPtr + i) };
		char* sig;
		char* n;
		jvmti->GetFieldName(klass, field, &n, &sig, NULL);
		std::string signature{ sig };
		std::string name{ n };
		jint modifiers;


		jvmti->GetFieldModifiers(klass, field, &modifiers);
		jvmti->Deallocate((unsigned char*)sig);
		jvmti->Deallocate((unsigned char*)n);

		// static flag
		if (modifiers & 0x0008)
			continue;

		response["fields"][name]["signature"] = sig;
		response["fields"][name]["modifiers"] = modifiers;
		addValue(signature, name, field);
	}
}

int HandlerObjectFields::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {
	long tag = *((long*)data);
	char* klass = (data + 4);

	auto result{ getObject(tag, klass, klassMap) };
	if (!result.has_value()) {
		return 0;
	}

	json response;

	auto [objClass, obj] = (*result);

	
	// TODO for now, this is ok. But perhaps build a more modular system for handling types with useful inherent values
	if (std::string{ klass } == "java/lang/String") {
		const char* data = jni->GetStringUTFChars((jstring)obj, NULL);
		std::string str{ data };
		response["value"] = str;
		jni->ReleaseStringUTFChars((jstring)obj, data);
	}

	buildFields(response, objClass, obj);

	std::string dump{ response.dump() };
	std::memcpy((void*)responseBuffer, (void*)dump.c_str(), strlen(dump.c_str()));

	return dump.size();
}