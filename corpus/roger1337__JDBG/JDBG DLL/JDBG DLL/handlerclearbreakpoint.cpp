#include "handlerclearbreakpoint.h"
#include "json.hpp"
#include "util.h"



HandlerClearBreakpoint::HandlerClearBreakpoint(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : ObjectHandler{ CLEAR_BREAKPOINT, jvmti, jni, pipeline } {

}



int HandlerClearBreakpoint::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {
    int methodIdx = *((int*)data);
    int offset = *((int*)data + 1);
    char* klassName = data + 2 * sizeof(int);

    std::map<std::string, jclass>::const_iterator pos = klassMap.find(klassName);

    if (pos == klassMap.end()) {
        msgLog("Class not found for breakpoint");
        status = 1;
        return 0;
    }

    jclass klass{ pos->second };

    jvmtiJlocationFormat format;
    jvmti->GetJLocationFormat(&format);
    if (format != JVMTI_JLOCATION_JVMBCI) {
        msgLog("Format in this JVM is not matching - cannot set breakpoint");
        status = 1;
        return 0;
    }
    jlocation loc = static_cast<long>(offset);


    jmethodID method{ getMethod(klass, methodIdx, jvmti, jni) };
    if (method == NULL) {
        msgLog("Failed to get method ID from idx");
        status = 1;
        return 0;
    }


    jvmtiError error{ jvmti->ClearBreakpoint(method, loc) };


    if (error != JVMTI_ERROR_NONE) {
        msgLog("There was an error when clearing breakpoint: " + std::to_string(error));
        status = 1;
        return 0;
    }

    return 0;
}