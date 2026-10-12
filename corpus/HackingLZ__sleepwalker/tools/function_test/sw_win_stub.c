/* Minimal Windows console stub for running the bytecode VM in isolation.
 * Links sw_core.c + sw_bytecode.c + sw_lzma.c so a crash here is a VM-logic
 * bug, independent of DLL side-loading into ERAAgent.exe. */
#include <windows.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#include "sw_core.h"
#include "sw_impl.h"

uint32_t sw_random_u32(void) {
    return (uint32_t)((uintptr_t)&sw_random_u32 ^ (uintptr_t)time(NULL) ^ rand());
}

int sw_worker_start(void) { return 0; }

int sw_tcp_send(const char *la, const char *lp, const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)la;(void)lp;(void)rh;(void)rp;(void)dl; return blen ? 0 : -1;
}
int sw_udp_send(const char *la, const char *lp, const char *rh, const char *rp,
                const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)la;(void)lp;(void)rh;(void)rp;(void)dl; return blen ? 0 : -1;
}
int sw_icmp_send(const char *src, const char *dst,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)src;(void)dst;(void)dl; return blen ? 0 : -1;
}
int sw_pipe_send(const char *s, const char *p, const char *u, const char *w,
                 const uint8_t *blob, uint32_t blen, uint16_t dl) {
    (void)s;(void)p;(void)u;(void)w;(void)dl; return blen ? 0 : -1;
}
int sw_tcp_connect_recv(const char *a,const char *b,const char *c,const char *d,
                        uint16_t dl,uint8_t *task,uint32_t cap,uint32_t *tlen) {
    (void)a;(void)b;(void)c;(void)d;(void)dl;(void)task;(void)cap; if(tlen)*tlen=0; return -1;
}
int sw_tcp_listen_recv(const char *a,const char *b,uint16_t dl,
                       uint8_t *task,uint32_t cap,uint32_t *tlen) {
    (void)a;(void)b;(void)dl;(void)task;(void)cap; if(tlen)*tlen=0; return -1;
}
int sw_udp_bind_recv(const char *a,const char *b,uint16_t dl,
                     uint8_t *task,uint32_t cap,uint32_t *tlen) {
    (void)a;(void)b;(void)dl;(void)task;(void)cap; if(tlen)*tlen=0; return -1;
}
int sw_pipe_client_recv(const char *s,const char *p,const char *u,const char *w,
                        uint16_t dl,uint8_t *task,uint32_t cap,uint32_t *tlen) {
    (void)s;(void)p;(void)u;(void)w;(void)dl;(void)task;(void)cap; if(tlen)*tlen=0; return -1;
}
int sw_pipe_server_recv(const char *p,const char *r,uint16_t dl,
                        uint8_t *task,uint32_t cap,uint32_t *tlen) {
    (void)p;(void)r;(void)dl;(void)task;(void)cap; if(tlen)*tlen=0; return -1;
}
int sw_run_shellcode(const uint8_t *c,uint32_t l){(void)c; return l?0:-1;}
int sw_run_file_script(const char *p){(void)p; return -1;}
int sw_sniff_magic(const char *i,uint32_t d,int raw,int dep){(void)i;(void)raw;(void)dep;
    for(volatile int x=0;x<(int)d&&x<24;x++) Sleep(50); return 0;}
void sw_namedpipe_cleanup(void){}
