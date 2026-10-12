#ifndef BUILD_OBJECTS_ONLY
#include <assert.h>
#include "..\sleepmask-vs.h"
#include "..\debug.h"

// Test function to ensure that asm harnesses correctly pass up to 10 arguments.
void __stdcall TestArgumentsArePassedCorrectly(int a, int b, int c, int d, int e, int f, int g, int h, int i, int j) {
    assert(a == 0);
    assert(b == 1);
    assert(c == 2);
    assert(d == 3);
    assert(e == 4);
    assert(f == 5);
    assert(g == 6);
    assert(h == 7);
    assert(i == 8);
    assert(j == 9);
}

// Test function wrapper to ensure that asm harnesses correctly pass up to 10 arguments.
void TestArgumentsArePassedCorrectlyWrapper() {
    FUNCTION_CALL test_args_fc;
    _memset(&test_args_fc, 0, sizeof(FUNCTION_CALL));
    test_args_fc.functionPtr = (PVOID)&TestArgumentsArePassedCorrectly;
    test_args_fc.numOfArgs = 10;
    test_args_fc.args[0] = 0;
    test_args_fc.args[1] = 1;
    test_args_fc.args[2] = 2;
    test_args_fc.args[3] = 3;
    test_args_fc.args[4] = 4;
    test_args_fc.args[5] = 5;
    test_args_fc.args[6] = 6;
    test_args_fc.args[7] = 7;
    test_args_fc.args[8] = 8;
    test_args_fc.args[9] = 9;
    bof::runMockedBeaconGate(sleep_mask, &test_args_fc, {});
}

/**
* This warning is generated as we cast variadic DWORDS to PVOIDs via GateArg().
* Surpress as it is generated for every sleepmask BOF and so gets noisy.
* */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-to-void-pointer-cast"

/**
* Unit test runner which will ensure that all sys calls
* are behaving as expected with whatever technique is
* implemented in *-sleepmask.cpp.
*/
void TestSysCallApi() {
    // Test 1. Memory Management APIs.
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Running Memory Management API tests...");

    // VirtualAlloc.
    // [1.1] Allocate some memory.
    FUNCTION_CALL vaFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualAlloc, // Function Pointer
        WinApi::VIRTUALALLOC, // Human Readable WinApi Enum
        TRUE, // Mask Beacon
        4, // Number of Arguments
        GateArg(NULL),  // VirtualAlloc Arg1
        GateArg(0x1000), // VirtualAlloc Arg2
        GateArg(MEM_RESERVE | MEM_COMMIT), // VirtualAlloc Arg3
        GateArg(PAGE_EXECUTE_READWRITE) // VirtualAlloc Arg4
    );
    bof::runMockedBeaconGate(sleep_mask, &vaFunctionCall, {});
    assert(vaFunctionCall.retValue != NULL);
    PVOID pBuffer = (PVOID)vaFunctionCall.retValue;

    // VirtualQuery.
    // [1.2] Query the newly allocated memory.
    MEMORY_BASIC_INFORMATION mbi = { 0 };
    FUNCTION_CALL vqFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualQuery,
        WinApi::VIRTUALQUERY,
        TRUE,
        3,
        GateArg(pBuffer),
        GateArg(&mbi),
        GateArg(sizeof(MEMORY_BASIC_INFORMATION))
    );
    bof::runMockedBeaconGate(sleep_mask, &vqFunctionCall, {});
    assert(vqFunctionCall.retValue != 0);
    assert(vqFunctionCall.retValue == sizeof(MEMORY_BASIC_INFORMATION));
    assert(mbi.AllocationBase == (PVOID)pBuffer);

    // VirtualProtect.
    // [1.3] Change the protections.
    DWORD oldProtection = 0;
    FUNCTION_CALL vpFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualProtect,
        WinApi::VIRTUALPROTECT,
        TRUE,
        4,
        GateArg(pBuffer),
        GateArg(0x1000),
        GateArg(PAGE_READONLY),
        GateArg(&oldProtection)
    );
    bof::runMockedBeaconGate(sleep_mask, &vpFunctionCall, {});
    assert(vpFunctionCall.retValue != 0);
    assert(oldProtection == PAGE_EXECUTE_READWRITE);

    // VirtualQuery.
    // [1.4] Re-query the protections.
    vqFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualQuery,
        WinApi::VIRTUALQUERY,
        TRUE,
        3,
        GateArg(pBuffer),
        GateArg(&mbi),
        GateArg(sizeof(MEMORY_BASIC_INFORMATION))
    );
    bof::runMockedBeaconGate(sleep_mask, &vqFunctionCall, {});
    assert(vqFunctionCall.retValue != 0);
    assert(vqFunctionCall.retValue == sizeof(MEMORY_BASIC_INFORMATION));
    assert(mbi.Protect == PAGE_READONLY);

    // VirtualFree.
    // [1.5] Free the memory.
    FUNCTION_CALL vfFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualFree,
        WinApi::VIRTUALFREE,
        TRUE,
        3,
        GateArg(pBuffer),
        GateArg(0),
        GateArg(MEM_RELEASE)
    );
    bof::runMockedBeaconGate(sleep_mask, &vfFunctionCall, {});
    assert(vfFunctionCall.retValue != 0);
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Memory management API tests passed.");


    // Test 2. Process/Thread APIs.
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Running Process/Thread API tests...");
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Spawning a dummy process...");

    // [2.1] Create a new process.
    BOOL retValue = 0;
    STARTUPINFOA si = { 0 };
    PROCESS_INFORMATION pi = { 0 };
    retValue = CreateProcessA(NULL,   // No module name (use command line)
        (LPSTR)"cmd.exe",        // Command line
        NULL,           // Process handle not inheritable
        NULL,           // Thread handle not inheritable
        FALSE,          // Set handle inheritance to FALSE
        0,              // No creation flags
        NULL,           // Use parent's environment block
        NULL,           // Use parent's starting directory
        &si,            // Pointer to STARTUPINFO structure
        &pi);         // Pointer to PROCESS_INFORMATION structure
    assert(retValue != 0);

    // DuplicateHandle.
    // [2.2] Duplicate a handle into new process.
    HANDLE hMutex = CreateMutex(NULL, FALSE, NULL);
    HANDLE hOut;
    FUNCTION_CALL dhFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)DuplicateHandle,
        WinApi::DUPLICATEHANDLE,
        TRUE,
        7,
        GateArg(GetCurrentProcess()),
        GateArg(hMutex),
        GateArg(pi.hProcess),
        GateArg(&hOut),
        GateArg(0),
        GateArg(FALSE),
        GateArg(DUPLICATE_SAME_ACCESS)
    );
    bof::runMockedBeaconGate(sleep_mask, &dhFunctionCall, {});
    assert(vfFunctionCall.retValue != 0);

    // CloseHandle.
    // [2.3] Close handle in PROCESS_INFO.
    FUNCTION_CALL chFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)CloseHandle,
        WinApi::CLOSEHANDLE,
        TRUE,
        1,
        GateArg(pi.hProcess)
    );
    bof::runMockedBeaconGate(sleep_mask, &chFunctionCall, {});
    assert(chFunctionCall.retValue != 0);

    // OpenProcess.
    // [2.4] Re-open a handle.
    HANDLE hProcess = INVALID_HANDLE_VALUE;
    FUNCTION_CALL opFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)OpenProcess,
        WinApi::OPENPROCESS,
        TRUE,
        3,
        GateArg(PROCESS_ALL_ACCESS),
        GateArg(FALSE),
        GateArg(pi.dwProcessId)
    );
    bof::runMockedBeaconGate(sleep_mask, &opFunctionCall, {});
    assert(opFunctionCall.retValue != 0);
    assert((HANDLE)opFunctionCall.retValue != INVALID_HANDLE_VALUE);
    hProcess = (HANDLE)opFunctionCall.retValue;

    // VirtualAllocEx.
    // [2.5] Allocate remote memory.
    pBuffer = NULL;
    FUNCTION_CALL vaeFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualAllocEx, // Function Pointer
        WinApi::VIRTUALALLOCEX,
        TRUE,
        5,
        GateArg(hProcess),
        GateArg(NULL),
        GateArg(0x1000),
        GateArg(MEM_COMMIT),
        GateArg(PAGE_READWRITE)
    );
    bof::runMockedBeaconGate(sleep_mask, &vaeFunctionCall, {});
    assert(vaeFunctionCall.retValue != NULL);
    pBuffer = (PVOID)vaeFunctionCall.retValue;

    // WriteProcessMemory.
    // [2.6] Write memory to remote buffer.
    char writeBuffer[] = "BeaconTest";
    size_t size = strlen(writeBuffer);
    FUNCTION_CALL wpmFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)WriteProcessMemory,
        WinApi::WRITEPROCESSMEMORY,
        TRUE,
        5,
        GateArg(hProcess),
        GateArg(pBuffer),
        GateArg(&writeBuffer),
        GateArg(size),
        GateArg(NULL)
    );
    bof::runMockedBeaconGate(sleep_mask, &wpmFunctionCall, {});
    assert(wpmFunctionCall.retValue != NULL);

    // ReadProcessMemory.
    // [2.7] Read remote memory.
    char readBuffer[20] = { 0 };
    FUNCTION_CALL rpmFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)ReadProcessMemory,
        WinApi::READPROCESSMEMORY,
        TRUE,
        5,
        GateArg(hProcess),
        GateArg(pBuffer),
        GateArg(&readBuffer),
        GateArg(size),
        GateArg(NULL)
    );
    bof::runMockedBeaconGate(sleep_mask, &rpmFunctionCall, {});
    assert(rpmFunctionCall.retValue != NULL);
    assert(0 == strcmp(readBuffer, writeBuffer));

    // VirtualProtectEx.
    // [2.8] Change perms for remote memory.
    oldProtection = 0;
    FUNCTION_CALL vpeFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)VirtualProtectEx,
        WinApi::VIRTUALPROTECTEX,
        TRUE,
        5,
        GateArg(hProcess),
        GateArg(pBuffer),
        GateArg(0x1000),
        GateArg(PAGE_READONLY),
        GateArg(&oldProtection)
    );
    bof::runMockedBeaconGate(sleep_mask, &vpeFunctionCall, {});
    assert(vpeFunctionCall.retValue != 0);
    assert(oldProtection == PAGE_READWRITE);

    // CreateRemoteThread.
    // [2.9] Create Remote Thread to terminate process.
    PVOID exitProcPtr = (LPVOID)GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitProcess");
    DWORD threadId = 0;
    HANDLE hThread = INVALID_HANDLE_VALUE;
    FUNCTION_CALL crtFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)CreateRemoteThread,
        WinApi::CREATEREMOTETHREAD,
        TRUE,
        7,
        GateArg(hProcess),
        GateArg(NULL),
        GateArg(0),
        GateArg(exitProcPtr),
        GateArg(NULL),
        GateArg(0),
        GateArg(&threadId)
    );
    bof::runMockedBeaconGate(sleep_mask, &crtFunctionCall, {});
    assert(crtFunctionCall.retValue != NULL);
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Process/Thread API tests passed");

    // Test 3. Local thread tests
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Running local thread API tests...");

    // CreateThread.
    // [3.1] Create new thread (local).
    PVOID loadLib = (LPVOID)GetProcAddress(GetModuleHandleA("kernel32.dll"), "LoadLibraryA");
    hThread = INVALID_HANDLE_VALUE;
    threadId = 0;
    FUNCTION_CALL ctFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)CreateThread,
        WinApi::CREATETHREAD,
        TRUE,
        6,
        GateArg(NULL),
        GateArg(0),
        GateArg(loadLib),
        GateArg(NULL),
        GateArg(CREATE_SUSPENDED),
        GateArg(&threadId)
    );
    bof::runMockedBeaconGate(sleep_mask, &ctFunctionCall, {});
    assert(ctFunctionCall.retValue != NULL);
    assert((HANDLE)ctFunctionCall.retValue != INVALID_HANDLE_VALUE);
    hThread = (HANDLE)ctFunctionCall.retValue;
    threadId = GetThreadId(hThread);

    // CloseHandle.
    chFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)CloseHandle,
        WinApi::CLOSEHANDLE,
        TRUE,
        1,
        GateArg(hThread)
    );
    bof::runMockedBeaconGate(sleep_mask, &chFunctionCall, {});
    assert(chFunctionCall.retValue != 0);

    // OpenThread.
    // [3.2] Open handle to new thread.
    hThread = INVALID_HANDLE_VALUE;
    FUNCTION_CALL otFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)OpenThread,
        WinApi::OPENTHREAD,
        TRUE,
        3,
        GateArg(THREAD_ALL_ACCESS),
        GateArg(FALSE),
        GateArg(threadId)
    );
    bof::runMockedBeaconGate(sleep_mask, &otFunctionCall, {});
    assert(otFunctionCall.retValue != NULL);
    hThread = (HANDLE)otFunctionCall.retValue;

    // GetThreadContext.
    // [3.3] Get thread context.
    CONTEXT ctx = { 0 };
    ctx.ContextFlags = CONTEXT_CONTROL;
    PVOID rtlUserThread = (LPVOID)GetProcAddress(GetModuleHandleA("ntdll.dll"), "RtlUserThreadStart");
    FUNCTION_CALL gtcFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)GetThreadContext,
        WinApi::GETTHREADCONTEXT,
        TRUE,
        2,
        GateArg(hThread),
        GateArg(&ctx)
    );
    bof::runMockedBeaconGate(sleep_mask, &gtcFunctionCall, {});
    assert(gtcFunctionCall.retValue != NULL);
#ifdef _WIN64
    assert(ctx.Rip == (DWORD64)rtlUserThread);
#elif _WIN32
    assert(ctx.Eip == (DWORD32)rtlUserThread);
#endif

    // SetThreadContext.
    // [3.4] Set ctx.Rip to point at ExitThread.
    PVOID exitThreadPtr = (LPVOID)GetProcAddress(GetModuleHandleA("kernel32.dll"), "ExitThread");
#ifdef _WIN64
    ctx.Rip = (DWORD64)exitThreadPtr;
    ctx.Rcx = 0;
    ctx.ContextFlags = CONTEXT_CONTROL;
#elif _WIN32
    ctx.Eip = (DWORD32)exitThreadPtr;
    ctx.Ecx = 0;
    ctx.ContextFlags = CONTEXT_CONTROL;
#endif
    FUNCTION_CALL stcFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)SetThreadContext,
        WinApi::SETTHREADCONTEXT,
        TRUE,
        2,
        GateArg(hThread),
        GateArg(&ctx)
    );
    bof::runMockedBeaconGate(sleep_mask, &stcFunctionCall, {});
    assert(stcFunctionCall.retValue != 0);

    // ResumeThread.
    // [3.5] Resume thread so it terminates.
    FUNCTION_CALL rtFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)ResumeThread,
        WinApi::RESUMETHREAD,
        TRUE,
        1,
        GateArg(hThread)
    );
    bof::runMockedBeaconGate(sleep_mask, &rtFunctionCall, {});
    assert(rtFunctionCall.retValue != -1);
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Local thread API tests passsed.");

    // Test 4: File mapping tests.
    BeaconPrintf(CALLBACK_OUTPUT, "[+] Running file mapping API tests...");
 
    // [4.1] CreateFileMapping.
    HANDLE hFile = INVALID_HANDLE_VALUE;
    FUNCTION_CALL cfmFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)CreateFileMappingA,
        WinApi::CREATEFILEMAPPING,
        TRUE,
        6,
        GateArg(INVALID_HANDLE_VALUE),
        GateArg(NULL),
        GateArg(PAGE_EXECUTE_READWRITE),
        GateArg(0),
        GateArg(1000),
        GateArg(NULL)
    );
    bof::runMockedBeaconGate(sleep_mask, &cfmFunctionCall, {});
    assert(cfmFunctionCall.retValue != NULL);
    hFile = (HANDLE)cfmFunctionCall.retValue;

    // [4.2] MapViewOfFile.
    FUNCTION_CALL mvofFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)MapViewOfFile,
        WinApi::MAPVIEWOFFILE,
        TRUE,
        5,
        GateArg(hFile),
        GateArg(FILE_MAP_ALL_ACCESS | FILE_MAP_EXECUTE),
        GateArg(0),
        GateArg(0),
        GateArg(0)
    );
    bof::runMockedBeaconGate(sleep_mask, &mvofFunctionCall, {});
    assert(mvofFunctionCall.retValue != NULL);

    // [4.3] UnmapViewOfFile.
    FUNCTION_CALL uvofFunctionCall = bof::mock::createFunctionCallStructure(
        (PVOID)UnmapViewOfFile,
        WinApi::UNMAPVIEWOFFILE,
        TRUE,
        1,
        GateArg(mvofFunctionCall.retValue)
    );
    bof::runMockedBeaconGate(sleep_mask, &uvofFunctionCall, {});
    assert(uvofFunctionCall.retValue != NULL);
    BeaconPrintf(CALLBACK_OUTPUT, "[+] File mapping API tests passed.");
    BeaconPrintf(CALLBACK_OUTPUT, "[+] All tests passed.");
#pragma GCC diagnostic pop
}
#endif
