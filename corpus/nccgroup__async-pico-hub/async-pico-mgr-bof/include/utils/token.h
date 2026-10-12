#pragma once
#include <Windows.h>
#include <pico/utils.h>

extern "C" {
	bool acquire_thread_impersonation_token(HANDLE& outToken)
	{
		DFR_LOCAL(Advapi32, OpenThreadToken);
		DFR_LOCAL(Advapi32, DuplicateTokenEx);
		DFR_LOCAL(KERNEL32, GetCurrentThread);
		DFR_LOCAL(KERNEL32, CloseHandle);
		DFR_LOCAL(KERNELBASE, OutputDebugStringA);
		HANDLE hThreadToken = NULL;

		// Try to open the current thread's impersonation token
		if (!OpenThreadToken(
			GetCurrentThread(),
			TOKEN_DUPLICATE | TOKEN_QUERY,
			TRUE, // OpenAsSelf (important!)
			&hThreadToken))
		{
			//BeaconPrintf(CALLBACK_ERROR, "Could not open thread token! Error %d", GetLastError());
			return false;
		}

		// Duplicate it into a usable impersonation token
		HANDLE hDupToken = NULL;
		if (!DuplicateTokenEx(
			hThreadToken,
			TOKEN_IMPERSONATE | TOKEN_QUERY | TOKEN_DUPLICATE,
			NULL,
			SecurityImpersonation,
			TokenImpersonation,
			&hDupToken))
		{
			//BeaconPrintf(CALLBACK_ERROR, "Could not duplicate token ex!");
			CloseHandle(hThreadToken);
			return false;
		}

		CloseHandle(hThreadToken);
		outToken = hDupToken;
		return true;
	}
}