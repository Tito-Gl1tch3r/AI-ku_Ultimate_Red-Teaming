
#include "handlerclassdata.h"
#include "jdbgpipeline.h"
#include <string>
#include <Windows.h>
#include <mutex>
#include <thread>
#include <map>
#include <string>

// it seems that RetransformClasses is synchronous - wasted time debugging - uncomment code if im wrong yet again

/*
std::condition_variable condition;
std::mutex mutex;
*/

char* buffer;
char* className = nullptr;
int classSize = 0;

void JNICALL
loadHook(jvmtiEnv* jvmti_env,
    JNIEnv* jni_env,
    jclass class_being_redefined,
    jobject loader,
    const char* name,
    jobject protection_domain,
    jint class_data_len,
    const unsigned char* class_data,
    jint* new_class_data_len,
    unsigned char** new_class_data) {


    if (name == nullptr || className == nullptr)
        return;


    if (strcmp(className, name) == 0) {

       // std::lock_guard<std::mutex> l{ mutex };
        classSize = class_data_len;
        memcpy(buffer, class_data, class_data_len);

      //  condition.notify_one();
    }


}

HandlerClassData::HandlerClassData(jvmtiEnv* jvmti, JNIEnv* jni, JdbgPipeline* pipeline) : Handler{ GET_CLASS_DATA, jvmti, jni, pipeline } {

}


int HandlerClassData::handle(char* data, DWORD length, char* responseBuffer, int& status, std::map<std::string, jclass>& klassMap) {
    std::map<std::string, jclass>::const_iterator pos = klassMap.find(data);

    if (pos == klassMap.end()) {
        msgLog("Class was not found");
        return 0;
    }

    jclass klass = pos->second;




    classSize = 0;
    className = data;
    buffer = responseBuffer;



    jvmti->RetransformClasses(1, &klass);

    className = nullptr;

    /*
    std::unique_lock<std::mutex> lock{ mutex };

    MessageBoxA(nullptr, "Waiting Now", "className", MB_ICONERROR);

    condition.wait(lock, []() { return classSize>0; });
    */



    return classSize;
}