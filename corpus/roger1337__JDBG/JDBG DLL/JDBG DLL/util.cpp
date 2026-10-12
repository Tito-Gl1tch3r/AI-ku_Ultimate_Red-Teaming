#pragma once

#include "util.h"
#include <jvmti.h>
#include <jni.h>
#include <string>

jfieldID getField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jint fieldCount;
	jfieldID* fields;
	jvmti->GetClassFields(klass, &fieldCount, &fields);


	for (int i = 0; i < fieldCount; i++) {
		jfieldID field = *(fields + i);

		char* name;
		jvmti->GetFieldName(klass, field, &name, NULL, NULL);

		if (std::string{ name } == fieldName) {
			return field;
		}
	}

	return NULL;

}


jfieldID getField(jclass& klass, int idx, jvmtiEnv* jvmti, JNIEnv* jni) {
	jint fieldCount;
	jfieldID* fields;
	jvmti->GetClassFields(klass, &fieldCount, &fields);


	if (idx >= fieldCount) {
		return NULL;
	}

	jfieldID field = *(fields + idx);
	return field;

}


jmethodID getMethod(jclass& klass, int idx, jvmtiEnv* jvmti, JNIEnv* jni) {
	jint methodCount;
	jmethodID* methods;
	jvmti->GetClassMethods(klass, &methodCount, &methods);


	if (idx >= methodCount) {
		return NULL;
	}

	jmethodID method = *(methods + idx);
	return method;

}



jobject getObjectField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetObjectField(obj, field);

	}
	return NULL;
}


jbyte getByteField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetByteField(obj, field);

	}
	return NULL;
}

jint getIntField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetIntField(obj, field);

	}
	return NULL;
}

jchar getCharField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetCharField(obj, field);

	}
	return NULL;
}


jdouble getDoubleField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetDoubleField(obj, field);

	}
	return NULL;
}



jlong getLongField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetLongField(obj, field);

	}
	return NULL;
}



jshort getShortField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetShortField(obj, field);

	}
	return NULL;
}



jboolean getBoolField(jclass& klass, jobject& obj, std::string& fieldName, jvmtiEnv* jvmti, JNIEnv* jni) {
	jfieldID field = getField(klass, obj, fieldName, jvmti, jni);
	if (field != NULL) {
		return jni->GetBooleanField(obj, field);

	}
	return NULL;
}
