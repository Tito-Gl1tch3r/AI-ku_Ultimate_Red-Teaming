#pragma once
#define _CRT_SECURE_NO_WARNINGS 1
#include <windows.h>
#include <ntsecapi.h>
#include <pico/utils.h>

#ifndef BUILD_OBJECTS_ONLY
#pragma comment(lib, "secur32.lib")
#endif

extern "C" {
    // Macros
#define STATUS_SUCCESS              ((NTSTATUS)0x00000000L)
#define STATUS_MEMORY_NOT_ALLOCATED ((NTSTATUS)0xC00000A0L)
#define NT_SUCCESS(status)          ((NTSTATUS)(status) >= 0)
#define MemAlloc(size) NTDLL$RtlAllocateHeap(KERNEL32$GetProcessHeap(), HEAP_ZERO_MEMORY, (size))
#define MemFree(ptr)   KERNEL32$HeapFree(KERNEL32$GetProcessHeap(), 0, (ptr))

// Structs 
    typedef struct _TIME_FIELDS {
        SHORT Year;
        SHORT Month;
        SHORT Day;
        SHORT Hour;
        SHORT Minute;
        SHORT Second;
        SHORT Milliseconds;
        SHORT Weekday;
    } TIME_FIELDS, * PTIME_FIELDS;

    typedef struct {
        LUID          luid;
        char          spn[256];
        char          clientName[256];
        char          clientRealm[256];
        char          serverRealm[256];
        LARGE_INTEGER startTime;
        LARGE_INTEGER endTime;
        LARGE_INTEGER renewTime;
        ULONG         ticketFlags;
        LONG          encryptionType;
    } TICKET_ENTRY, * PTICKET_ENTRY;

    typedef struct {
        PTICKET_ENTRY tickets;
        int           count;
    } TICKET_CACHE, * PTICKET_CACHE;

    typedef struct {
        ULONG       mask;
        const char* name;
    } FLAG_ENTRY, * PFLAG_ENTRY;

    using RtlAllocateHeap_t =
        LPVOID(NTAPI)(HANDLE, DWORD, SIZE_T);

    using RtlTimeToTimeFields_t =
        VOID(NTAPI)(PLARGE_INTEGER, PTIME_FIELDS);

    using RtlSystemTimeToLocalTime_t =
        VOID(NTAPI)(PLARGE_INTEGER, PLARGE_INTEGER);

    // KERNEL32
    DFR(KERNEL32, GetProcessHeap);
    DFR(KERNEL32, HeapFree);
    DFR(KERNEL32, WaitForSingleObjectEx);
    DFR(KERNEL32, GetLocalTime);
    DFR(KERNEL32, WideCharToMultiByte);

#if !defined(BUILD_OBJECTS_ONLY)
    DFR_VALUE(NTDLL, RtlAllocateHeap, RtlAllocateHeap_t*, HeapAlloc);
    DFR_VALUE(NTDLL, RtlTimeToTimeFields, RtlTimeToTimeFields_t*, nullptr);
    DFR_VALUE(NTDLL, RtlSystemTimeToLocalTime, RtlSystemTimeToLocalTime_t*, nullptr);
#else
    DFR_VALUE(NTDLL, RtlAllocateHeap, RtlAllocateHeap_t, nullptr);
    DFR_VALUE(NTDLL, RtlTimeToTimeFields, RtlTimeToTimeFields_t, nullptr);
    DFR_VALUE(NTDLL, RtlSystemTimeToLocalTime, RtlSystemTimeToLocalTime_t, nullptr);
#endif
    // SECUR32
    DFR(SECUR32, LsaRegisterLogonProcess);
    DFR(SECUR32, LsaLookupAuthenticationPackage);
    DFR(SECUR32, LsaCallAuthenticationPackage);
    DFR(SECUR32, LsaFreeReturnBuffer);
    DFR(SECUR32, LsaEnumerateLogonSessions);
    DFR(SECUR32, LsaGetLogonSessionData);
    DFR(SECUR32, LsaDeregisterLogonProcess);

    // MSVCRT
    DFR(MSVCRT, strcmp);
    DFR(MSVCRT, wcsncmp);
    DFR(MSVCRT, wcslen);
    DFR(MSVCRT, memcpy);
    DFR(MSVCRT, _stricmp);
    DFR(MSVCRT, _snprintf);
    DFR(MSVCRT, strncat);
    DFR(MSVCRT, strlen);
    DFR(MSVCRT, _scprintf);
    DFR(MSVCRT, strcat);

    // Enums 
    enum TICKET_FLAGS : ULONG {
        reserved = 2147483648,
        forwardable = 0x40000000,
        forwarded = 0x20000000,
        proxiable = 0x10000000,
        proxy = 0x08000000,
        may_postdate = 0x04000000,
        postdated = 0x02000000,
        invalid = 0x01000000,
        renewable = 0x00800000,
        initial = 0x00400000,
        pre_authent = 0x00200000,
        hw_authent = 0x00100000,
        ok_as_delegate = 0x00040000,
        anonymous = 0x00020000,
        name_canonicalize = 0x00010000,
        enc_pa_rep = 0x00010000,
        reserved1 = 0x00000001,
    };

    enum KERB_ETYPE {
        des_cbc_crc = 1,
        des_cbc_md4 = 2,
        des_cbc_md5 = 3,
        des3_cbc_md5 = 5,
        des3_cbc_sha1 = 7,
        dsaWithSHA1_CmsOID = 9,
        md5WithRSAEncryption_CmsOID = 10,
        sha1WithRSAEncryption_CmsOID = 11,
        rc2CBC_EnvOID = 12,
        rsaEncryption_EnvOID = 13,
        rsaES_OAEP_ENV_OID = 14,
        des_ede3_cbc_Env_OID = 15,
        des3_cbc_sha1_kd = 16,
        aes128_cts_hmac_sha1 = 17,
        aes256_cts_hmac_sha1 = 18,
        rc4_hmac = 23,
        rc4_hmac_exp = 24,
        subkey_keymaterial = 65,
        old_exp = -135,
    };
}