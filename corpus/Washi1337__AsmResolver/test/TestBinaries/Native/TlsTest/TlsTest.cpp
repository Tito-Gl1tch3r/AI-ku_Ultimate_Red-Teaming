#include <iostream>
#include <Windows.h>
#include <time.h>

__declspec(thread) int _threadLocalInt = 0x12345678;
__declspec(thread) char _threadLocalArray[14] = "Hello World!\n";

VOID WINAPI tls_callback1(
    PVOID DllHandle,
    DWORD Reason,
    PVOID Reserved)
{
    printf("[%d]: TLS callback 1 (Reason: %d)\n", GetCurrentThreadId(), Reason);
}

#ifdef _WIN64
#pragma comment (linker, "/INCLUDE:_tls_used")
#pragma comment (linker, "/INCLUDE:tls_callback_func1")
#else
#pragma comment (linker, "/INCLUDE:__tls_used")
#pragma comment (linker, "/INCLUDE:_tls_callback_func1")
#endif

#ifdef _WIN64
#pragma const_seg(".CRT$XLF")
EXTERN_C const
#else
#pragma data_seg(".CRT$XLF")
EXTERN_C
#endif

PIMAGE_TLS_CALLBACK tls_callback_func1 = tls_callback1;
PIMAGE_TLS_CALLBACK tls_callback_end = NULL;
#ifdef _WIN64
#pragma const_seg()
#else
#pragma data_seg()
#endif //_WIN64

DWORD WINAPI thread_main(LPVOID arg)
{
    int threadId = GetCurrentThreadId();
    printf("[%d]: _threadLocalInt = %d\n", threadId, _threadLocalInt);
    _threadLocalInt++;
    printf("[%d]: _threadLocalInt = %d\n", threadId, _threadLocalInt);
    printf("[%d]: _threadLocalArray = %s\n", threadId, _threadLocalArray);
    return (DWORD) arg;
}

int main(int argc, char** argv)
{
    int threadCount = 1;

    if (argc == 2) {
        threadCount = atoi(argv[1]);
    }

    auto* handles = new HANDLE[threadCount];
    for (int i = 0; i < threadCount; i++) {
        handles[i] = CreateThread(NULL, NULL, thread_main, (LPVOID) i, 0, NULL);
    }

    WaitForMultipleObjects(threadCount, handles, TRUE, INFINITE);

    printf("[%d]: Done\n", GetCurrentThreadId());
    delete[] handles;
}
