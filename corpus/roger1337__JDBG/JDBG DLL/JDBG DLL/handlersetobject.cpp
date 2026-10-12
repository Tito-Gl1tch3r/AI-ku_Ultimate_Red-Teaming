#include "handlersetobject.h"
#include "json.hpp"

using json = nlohmann::basic_json<>;


HandlerSetObject::HandlerSetObject(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : ObjectHandler{ SET_OBJECT, jvmti, jni, pipeline } {

}



int HandlerSetObject::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {

	json response{ nlohmann::json::parse(data) };

	long tag{ response.at("tag") };
	std::string klass{ response.at("klass") };
		
	auto result{ getObject(tag, klass.c_str(), klassMap)};
	if (!result.has_value()) {
		return 0;
	}

	auto [objClass, obj] = (*result);


	// make this modular once introduce other types, such as Double, Character etc
	if (klass == "java/lang/String") {
		std::string value{ response["value"] };
		jfieldID field{ jni->GetFieldID(objClass, "value", "[C") };


		if (field == NULL) {
			field = jni->GetFieldID(objClass, "value", "[B");

			jbyteArray byteArray{ jni->NewByteArray(value.length()) };

			jni->SetByteArrayRegion(byteArray, 0, value.length(), (const jbyte*)value.c_str());
			jni->SetObjectField(obj, field, byteArray);
			msgLog("Set string");
			return 0;
		}

		jcharArray arr{ jni->NewCharArray(value.length()) };


		jchar* buf{ new jchar[value.length()] };
		for (int i = 0; i < value.length(); i++) {
			buf[i] = static_cast<jchar>(value[i]);
		}

		jni->SetCharArrayRegion(arr, 0, value.length(), buf);

		jni->SetObjectField(obj, field, arr);
		msgLog("Set string");

		delete[] buf;
	}

	return 0;
}
