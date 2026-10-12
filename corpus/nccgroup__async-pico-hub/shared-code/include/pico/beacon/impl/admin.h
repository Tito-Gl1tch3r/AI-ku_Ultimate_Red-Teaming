#pragma once
#include <Windows.h>
#include <pico/utils.h>

extern "C" {
	DFR(ADVAPI32, OpenThreadToken);
	DFR(ADVAPI32, OpenProcessToken);
	DFR(ADVAPI32, GetTokenInformation);
	DFR(ADVAPI32, CreateWellKnownSid);
	DFR(ADVAPI32, CheckTokenMembership);
	DFR(ADVAPI32, EqualSid);
    DFR(ADVAPI32, GetSidSubAuthority);
    DFR(ADVAPI32, GetSidSubAuthorityCount);
    DFR(ADVAPI32, SetThreadToken);
    DFR(ADVAPI32, RevertToSelf);

	DFR(KERNEL32, GetCurrentThread);
	DFR(KERNEL32, GetCurrentProcess);
	DFR(KERNEL32, GetLastError);
	DFR(KERNEL32, CloseHandle);

    DFR(KERNELBASE, OutputDebugStringA);

    DFR(MSVCRT, malloc);
    DFR(MSVCRT, free);
}

namespace pic::winsec {
    bool OpenEffectiveToken(HANDLE& token)
    {
        // Try thread impersonation token first
        if (ADVAPI32$OpenThreadToken(
            KERNEL32$GetCurrentThread(),
            TOKEN_QUERY,
            TRUE,
            &token))
        {
            return true;
        }

        if (KERNEL32$GetLastError() == ERROR_NO_TOKEN)
        {
            return ADVAPI32$OpenProcessToken(
                KERNEL32$GetCurrentProcess(),
                TOKEN_QUERY,
                &token);
        }

        return false;
    }

    DWORD GetIntegrityLevelRid(HANDLE token)
    {

        DWORD needed = 0;

        ADVAPI32$GetTokenInformation(
            token,
            TokenIntegrityLevel,
            nullptr,
            0,
            &needed);

        if (KERNEL32$GetLastError() != ERROR_INSUFFICIENT_BUFFER)
            return 0;

        BYTE* buffer =
            (BYTE*)MSVCRT$malloc(needed);

        TOKEN_MANDATORY_LABEL* til =
            reinterpret_cast<TOKEN_MANDATORY_LABEL*>(buffer);

        DWORD rid = 0;

        if (ADVAPI32$GetTokenInformation(
            token,
            TokenIntegrityLevel,
            til,
            needed,
            &needed))
        {
            PSID sid = til->Label.Sid;

            DWORD subAuthCount =
                *ADVAPI32$GetSidSubAuthorityCount(sid);

            rid =
                *ADVAPI32$GetSidSubAuthority(
                    sid,
                    subAuthCount - 1);
        }

        MSVCRT$free(buffer);
        return rid;
    }
}

extern "C" {
    BOOL BeaconIsAdmin()
    {
        HANDLE token = nullptr;
        pic::winsec::OpenEffectiveToken(token);
        bool result = pic::winsec::GetIntegrityLevelRid(token)
            >= SECURITY_MANDATORY_HIGH_RID;
        KERNEL32$CloseHandle(token);
        return result;
    }

    BOOL BeaconUseToken(HANDLE token) {
        return ADVAPI32$SetThreadToken(NULL, token);
    }

    void BeaconRevertToken() {
        ADVAPI32$RevertToSelf();
    }
}