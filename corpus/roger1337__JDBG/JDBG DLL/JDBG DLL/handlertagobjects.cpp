#define exprtk_disable_caseinsensitivity
#include <exprtk.hpp>


#include "handler.h"
#include "handlertagobjects.h"
#include "jdbgpipeline.h"
#include <string>
#include <map>
#include <sstream>
#include <jni.h>
#include "util.h"
#include <cmath>

// tags are inclusive of the bottom and exclusive of the top.
// subsequent calls will overwrite the tags, so add like a refresh button or something in the gui.

HandlerTagObjects::HandlerTagObjects(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : ObjectHandler { GET_OBJECT_TAGS, jvmti, jni, pipeline } {

}


// TODO add support for arrays
jobject getParentObject(jobject& obj, std::string& variable, JNIEnv* jni, jvmtiEnv* jvmti, std::function<void(const std::string&)> msgLog) {
	std::stringstream stream { variable };

	//ignore obj
	std::string _;
	std::getline(stream, _, '.');

	std::string token;

	jobject theObj = obj;
	while (std::getline(stream, token, '.')) {	

		// means its the last one which is the actual field
		if (stream.eof()) {
			continue;
		}

		jclass klass = jni->GetObjectClass(theObj);

		if (klass == NULL) {
			msgLog("No class for token: " + token);
			return NULL;
		}

		jobject obj = getObjectField(klass, theObj, token, jvmti, jni);

		if (obj == NULL) {
			msgLog("Parent class field was null: " + token);
			return NULL;
		}

		msgLog("Success for token: " + token);


		jni->DeleteLocalRef(theObj);
		jni->DeleteLocalRef(klass);

		theObj = obj;

	}

	return theObj;

}


std::string getLastVariable(std::string& var) {
	std::stringstream stream{ var };
	std::string token;
	while (std::getline(stream, token, '.')) {};
	return std::move(token);
}

bool filter(
	std::vector<std::string>& variableList, 
	jobject& obj, 
	char* objClass,
	JNIEnv* jni,
	jvmtiEnv* jvmti,
	std::function<void(const std::string& message)> msgLog,
	const std::function<void(std::string& var, double a)> addOrUpdate,
	const std::function<void(std::string& var, const std::string& str)> addOrUpdateString
) {

	for (std::string& var : variableList) {
		const auto& handleObject{ [&](jobject& object, std::string& sig) {
			if (sig == "Ljava/lang/String;") {
				const char* ptr{ jni->GetStringUTFChars((jstring)object, NULL) };

				if (ptr != nullptr) {
					std::string strVal{ ptr };
					addOrUpdateString(var, std::move(strVal));
					jni->ReleaseStringUTFChars((jstring)object, ptr);
				}
			}
		} };


		if (var != "obj") {
			jobject parentObject = getParentObject(obj, var, jni, jvmti, msgLog);
			jclass klass = jni->GetObjectClass(parentObject);

			if (parentObject == NULL || klass == NULL) {
				return false;
			}

			std::string token{ getLastVariable(var) };

			char* sig;

			// TODO here, can get fields from parent classes as well.
			jfieldID field = getField(klass, parentObject, token, jvmti, jni);

			if (field == NULL) {
				msgLog("The value you wanted did not exist in the parent class");
				return false;
			}

			jvmti->GetFieldName(klass, field, NULL, &sig, NULL);
			std::string signature{ sig };

			jvmti->Deallocate((unsigned char*)sig);



			if (signature.starts_with("L")) {
				jobject o{ jni->GetObjectField(parentObject, field) };
				handleObject(o, signature);
				jni->DeleteLocalRef(o);
				continue;
			}

			const auto& func{ [&]() {
				if (signature == "B") return (double)jni->GetByteField(parentObject, field); else
				if (signature == "C") return (double)jni->GetCharField(parentObject, field); else
				if (signature == "D") return (double)floor(jni->GetDoubleField(parentObject, field)); else
				if (signature == "F") return (double)floor(jni->GetFloatField(parentObject, field)); else
				if (signature == "I") return (double)jni->GetIntField(parentObject, field); else
				if (signature == "J") return (double)jni->GetLongField(parentObject, field); else
				if (signature == "S") return (double)jni->GetShortField(parentObject, field); else
				if (signature == "Z") return (double)jni->GetBooleanField(parentObject, field); else return 0.0;
			 } };


			double value = func();
			addOrUpdate(var, value);

			jni->DeleteLocalRef(klass);
			// dont delete parent obj as it can be equal to the obj
		} else {
			
			std::string signature{ "L" + std::string{objClass} + ";" };

			// dont release obj, as it is the one stored in the map. 
			handleObject(obj, signature);
		}
	}
	
	return false;

}




void collectVariables(std::string& expressionString, std::vector<std::string>& variables) {

	if (expressionString.length() > 2) {
		std::string var;
		bool building = false;
		for (int i = 2; i < expressionString.length(); i++) {
			if (expressionString[i - 2] == 'o' && expressionString[i - 1] == 'b' && expressionString[i] == 'j' && !building) {
				building = true;
				var += "obj";
				continue;
			}

			if (building && (isalnum(expressionString[i]) || expressionString[i]=='.')) {
				var += expressionString[i];
				continue;
			}

			if (building) {
				variables.push_back(var);
				var.clear();
			}


			building = false;
		}

		if (building) {
			variables.push_back(var);
		}
	}
}



int HandlerTagObjects::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {
	char* filterString = data;
	while (*(filterString++) != '\0') {}

	std::map<std::string, jclass>::const_iterator pos = klassMap.find(data);
	if (pos == klassMap.end()) {
		msgLog("Class was not found");
		return 0;
	}
	jclass klass = pos->second;

	if (!instanceMapInit[data]) {
		if (instanceMap[data].size() > 0) {
			msgLog("Something already existed.");
		}

		populateMap(klass, data);
		instanceMapInit[data] = true;
	}
	msgLog("check1");


	std::vector<long> filteredObjKeys;

	std::string expressionString { filterString };
	std::vector<std::string> variableList;

	exprtk::symbol_table<double> symbolTable;
	exprtk::expression<double> expression;
	exprtk::parser<double> parser;

	std::map<std::string, double> variableMap;
	std::map<std::string, std::string> stringVariableMap;


	const auto& addOrUpdate{ std::function{ [&](std::string& var,double value) {
		if (variableMap.find(var) == variableMap.end()) {
			variableMap[var] = value;
			symbolTable.add_variable(var, variableMap[var], false);
			return;
		}
		variableMap[var] = value;
	} } };

	const auto& addOrUpdateString{ std::function { [&](std::string& var, const std::string& str) {
		if (variableMap.find(var) == variableMap.end()) {
			stringVariableMap[var] = str;
			symbolTable.add_stringvar(var, stringVariableMap[var], false);
			return;
		}
		stringVariableMap[var] = str;
	} } };

	msgLog("Im here!");
	expression.register_symbol_table(symbolTable);
	bool compiled = false;




	if (!expressionString.empty()) {
		collectVariables(expressionString, variableList);
	}

	for (std::string& s : variableList) {
		msgLog("Variable: " + s);
	}


	for (const auto& entry : instanceMap[data]) {

		jweak obj{ entry.second };

		// check if ref died
		if (jni->IsSameObject(obj, NULL)) {
			continue;
		}

		filter(variableList, obj, data, jni, jvmti, std::bind(&Handler::msgLog, this, std::placeholders::_1), addOrUpdate, addOrUpdateString);

		if (!expressionString.empty() && !compiled) {
			if (parser.compile(expressionString, expression)) {
				compiled = true;
			}
			else {
				for (int i = 0; i < parser.error_count(); i++) {
					exprtk::parser_error::type error{ parser.get_error(i) };

					msgLog("diagnostic: " + error.diagnostic);
					msgLog("error_line: " + error.error_line);
					msgLog("----");

				}
				return 0;
			}
		}



		double value{ expression.value() };

		if (expressionString.empty() || value > 0) {
			filteredObjKeys.push_back(entry.first);
		}

	}


	for (int i = 0; i < filteredObjKeys.size(); i++) {
		*((long*)responseBuffer + i) = filteredObjKeys[i];
	}

	return sizeof(long) * filteredObjKeys.size();
}