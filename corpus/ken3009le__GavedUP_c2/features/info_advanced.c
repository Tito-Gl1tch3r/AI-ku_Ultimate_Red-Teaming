#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <Lmcons.h>
#include <iphlpapi.h>
#include "info_advanced.h"

#pragma comment(lib, "iphlpapi.lib")

char* get_advanced_info() {
    char buffer[4096];
    memset(buffer, 0, sizeof(buffer));

    char computerName[UNCLEN + 1];
    DWORD size = UNCLEN + 1;
    GetComputerNameA(computerName, &size);
    strcat(buffer, "Computer Name: ");
    strcat(buffer, computerName);
    strcat(buffer, "\n");

    char username[UNLEN + 1];
    DWORD uname_len = UNLEN + 1;
    GetUserNameA(username, &uname_len);
    strcat(buffer, "User: ");
    strcat(buffer, username);
    strcat(buffer, "\n");

    OSVERSIONINFOEX osvi = {0};
    osvi.dwOSVersionInfoSize = sizeof(osvi);
    GetVersionEx((LPOSVERSIONINFO)&osvi);
    char os[128];
    sprintf(os, "OS Version: %lu.%lu Build %lu\n", osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber);
    strcat(buffer, os);

    SYSTEM_INFO si;
    GetSystemInfo(&si);
    char arch[64];
    sprintf(arch, "CPU Arch: %u\n", si.wProcessorArchitecture);
    strcat(buffer, arch);

    // Network interfaces
    IP_ADAPTER_INFO AdapterInfo[16];
    DWORD buflen = sizeof(AdapterInfo);
    if (GetAdaptersInfo(AdapterInfo, &buflen) == NO_ERROR) {
        PIP_ADAPTER_INFO pAdapter = AdapterInfo;
        while (pAdapter) {
            char netinfo[256];
            sprintf(netinfo, "Adapter: %s, IP: %s\n", pAdapter->Description, pAdapter->IpAddressList.IpAddress.String);
            strcat(buffer, netinfo);
            pAdapter = pAdapter->Next;
        }
    }

    return _strdup(buffer);
}
