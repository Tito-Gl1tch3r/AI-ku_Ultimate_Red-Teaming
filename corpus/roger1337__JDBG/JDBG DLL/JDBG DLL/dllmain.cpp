// dllmain.cpp : Defines the entry point for the DLL application.
#include <windows.h>
#include "pipeline.h"
#include "jdbgpipeline.h"
#include <jni.h>|
#include <jvmti.h>
#include <string>
#include <sstream>
#include <iomanip>
#include "handlerclassdata.h"
#include "breakpointpipeline.h"

struct EnvResult {
    char code;
    jvmtiEnv* jvmti;
    JNIEnv* jni;
    JavaVM* jvm;
};

typedef jint(JNICALL* JNI_GetCreatedJavaVMs_t)(JavaVM** vm, jsize max_count, jsize* count);

EnvResult getEnv() {
    JavaVM* JVM;
    jvmtiEnv* jvmTI;
    JNIEnv* env;
    jsize nVMs;
    jint res;


    HMODULE hJvm = GetModuleHandle(L"jvm.dll");
    
    if (hJvm == NULL) {
        MessageBoxA(nullptr, "Failed to get jvm.dll handle", "JDBG @ getEnv", MB_ICONERROR);
        return EnvResult{ -1, nullptr,nullptr,nullptr };

    }

    // Get the address of the JNI_GetCreatedJavaVMs function
    JNI_GetCreatedJavaVMs_t JNI_GetCreatedJavaVMs = (JNI_GetCreatedJavaVMs_t)GetProcAddress(hJvm, "JNI_GetCreatedJavaVMs");
    if (JNI_GetCreatedJavaVMs == NULL) {
        MessageBoxA(nullptr, "Failed to find JNI_GetCreatedJavaVMs function in jvm.dll", "JDBG @ getEnv", MB_ICONERROR);
        return EnvResult{ -1, nullptr,nullptr,nullptr };

    }

    try {
        res = JNI_GetCreatedJavaVMs(&JVM, 1, &nVMs);
        if (res != JNI_OK || nVMs < 1) {
            return EnvResult{ 1, nullptr, nullptr, nullptr };
        }
    }
    catch (...) {
        return EnvResult{ 1, nullptr, nullptr, nullptr };
    }
    try {
        res = JVM->AttachCurrentThread((void**)&env, nullptr);
        if (res != JNI_OK) {
            return EnvResult{ 2, nullptr, nullptr, nullptr };

        }

        res = JVM->GetEnv((void**)&jvmTI, JVMTI_VERSION_1_1);
        if (res != JNI_OK || jvmTI == nullptr) {
            return EnvResult{ 2, nullptr, nullptr, nullptr };

        }
    }
    catch (...) {
        return EnvResult{ 2, nullptr, nullptr, nullptr };
    }

    return EnvResult{ 0, jvmTI, env, JVM };
}



DWORD WINAPI start(LPVOID lpParam) {
    JdbgPipeline serverPipe{ L"\\\\.\\pipe\\jdbg" };

    EnvResult env{ getEnv() };

    if (env.code != 0) {
        return 0;
    }

    jvmtiEnv* jvmti = env.jvmti;


    // capabilities acts as a signature which allows us to force write advanced capabilities
    jvmtiCapabilities capabilities{};
    capabilities.can_tag_objects = 1;
    capabilities.can_get_bytecodes = 1;
    capabilities.can_get_synthetic_attribute = 1;


    jvmtiCapabilities withAdvanced = capabilities;
    withAdvanced.can_generate_breakpoint_events = 1;
    withAdvanced.can_retransform_classes = 1;
    withAdvanced.can_retransform_any_class = 1;
    withAdvanced.can_generate_all_class_hook_events = 1;
    withAdvanced.can_redefine_classes = 1;
    withAdvanced.can_redefine_any_class = 1;
    withAdvanced.can_suspend = 1;
    withAdvanced.can_access_local_variables = 1;



    jvmtiError error = jvmti->AddCapabilities(&capabilities);
    if (error != JVMTI_ERROR_NONE) {
        MessageBoxA(nullptr, (std::string{ "Failed to add basic capabilities. Error code: " } + std::to_string(error)).c_str(), "JDBG @ start", MB_ICONERROR);
        serverPipe.sendStatus(2);
        return 0;
    }


    /* Force load capabilities with sig scan */
    bool foundSig = false;
    char curr[16];
    std::memcpy(curr, &capabilities, 0x10);

    constexpr int SIZE_TO_CHECK = 0x200;
    char data[SIZE_TO_CHECK];
    std::memcpy(data, (char*)jvmti, SIZE_TO_CHECK);

    for (int i = 0; i < SIZE_TO_CHECK - 0x10; i++) {
        if (std::memcmp(curr, data + i, 0x10) == 0) {
            foundSig = true;
            *((jvmtiCapabilities*)((char*)jvmti + i)) = withAdvanced;
        }
    }

    if (!foundSig) {
        MessageBoxA(nullptr, "Could not load advanced capabilities", "JDBG @ start", MB_ICONERROR);
        serverPipe.sendStatus(2);
        return 0;

    }


    /* setup callbacks */
    jvmtiEventCallbacks callbacks;
    memset(&callbacks, 0, sizeof(callbacks));
    callbacks.Breakpoint = &breakpoint;
    callbacks.ClassFileLoadHook = &loadHook;

    jvmtiError err = jvmti->SetEventCallbacks(&callbacks, (jint)sizeof(callbacks));
    if (err) {
        MessageBoxA(nullptr, "Failed to set callbacks", "JDBG @ start", MB_ICONERROR);
    }
    jvmtiError breakpoint = jvmti->SetEventNotificationMode(JVMTI_ENABLE, JVMTI_EVENT_BREAKPOINT, NULL);
    jvmtiError loadHook = jvmti->SetEventNotificationMode(JVMTI_ENABLE, JVMTI_EVENT_CLASS_FILE_LOAD_HOOK, NULL);


    if (breakpoint || loadHook) {
        MessageBoxA(nullptr, "Failed to set callbacks", "JDBG @ start", MB_ICONERROR);
    }



    /* start pipeline and listening */
    serverPipe.sendStatus(env.code);
    serverPipe.startListen(env.jvmti, env.jni);

    return 0;
}





BOOL APIENTRY DllMain( HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
                     )
{

    if (ul_reason_for_call == DLL_PROCESS_ATTACH) {
        CreateThread(NULL, 0, start, NULL, 0, NULL);
    }



    return TRUE;
}

