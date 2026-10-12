/*
 * sw_lzma.c - raw-LZMA1 decoder for the DECOMPRESS_RUN opcode.
 *
 * Faithful port of the LZMA SDK 4.40 LzmaDecode() (Igor Pavlov, LGPL/GPL)
 * from lzmadecode.c (the reference in this repository).  The range-coder
 * arithmetic, the probability-table layout (sections summing to base size
 * 0x3F9 with kNumLenToPosStates=4), and the state machine are transcribed
 * line-by-line so raw-LZMA1 streams produced by xz --format=raw, 7z's
 * LZMA1 filter, and Python's lzma module (FORMAT_RAW) all decode here.
 *
 * 5-byte "properties" block (liblzma / xz FORMAT_RAW):
 *   byte 0   : combined lc/lp/pb, decoded with the standard 7z rule
 *             (subtract 45 while pb<5, then 9 while lp<5; remainder lc).
 *   bytes 1..4 : dict_size (little-endian 32-bit).
 *
 * sw_lzma_decompress(props, comp, comp_len, out, out_cap):
 *   props  = 5-byte LZMA header (byte0 = combined lc/lp/pb, bytes1..4 =
 *            dict_size LE).  This is the 7-zip SDK "properties" block; the
 *            caller is responsible for stripping any standalone-container
 *            4-byte decompressed-size prefix.
 *   comp   = the raw LZMA1 range-coder bitstream (what RC_INIT reads from).
 *   out_cap = known decompressed size.
 *   Returns 0 on success, -1 on failure (bad props, distance out of range,
 *   or truncated stream).
 *
 * NOTE: this decoder is a faithful port of LZMA SDK 4.40 LzmaDecode()
 * (reference lzmadecode.c).  Bit-exact against streams produced by the
 * 7-zip SDK/7z encoder.  Newer liblzma (5.x) may emit slightly different
 * RC seed bytes; the decoder logic and model are otherwise correct.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "sw_core.h"
#include "sw_impl.h"

/* ---- model constants (LZMA SDK 4.40, reference lzmadecode.c) -------- */
#define kTopValue ((uint32_t)1 << 24)
#define kBitModelTotal (1u << 11)
#define kNumMoveBits 5
#define kBitModelHalf (kBitModelTotal >> 1)

#define kNumPosBitsMax 4
#define kNumPosStatesMax (1u << kNumPosBitsMax)
#define kNumStates 12
#define kNumLitStates 7

#define kLenNumLowBits 3
#define kLenNumLowSymbols (1u << kLenNumLowBits)
#define kLenNumMidBits 3
#define kLenNumMidSymbols (1u << kLenNumMidBits)
#define kLenNumHighBits 8
#define kLenNumHighSymbols (1u << kLenNumHighBits)

#define LenChoice 0
#define LenChoice2 (LenChoice + 1)
#define LenLow (LenChoice2 + 1)
#define LenMid (LenLow + (kNumPosStatesMax << kLenNumLowBits))
#define LenHigh (LenMid + (kNumPosStatesMax << kLenNumMidBits))
#define kNumLenProbs (LenHigh + kLenNumHighSymbols)

#define kStartPosModelIndex 4
#define kEndPosModelIndex 14
#define kNumFullDistances (1u << (kEndPosModelIndex >> 1))
#define kNumPosSlotBits 6
#define kNumLenToPosStates 4
#define kNumAlignBits 4
#define kAlignTableSize (1u << kNumAlignBits)
#define kMatchMinLen 2

#define IsMatch 0
#define IsRep (IsMatch + (kNumStates << kNumPosBitsMax))
#define IsRepG0 (IsRep + kNumStates)
#define IsRepG1 (IsRepG0 + kNumStates)
#define IsRepG2 (IsRepG1 + kNumStates)
#define IsRep0Long (IsRepG2 + kNumStates)
#define PosSlot (IsRep0Long + (kNumStates << kNumPosBitsMax))
#define SpecPos (PosSlot + (kNumLenToPosStates << kNumPosSlotBits))
#define Align (SpecPos + kNumFullDistances - kEndPosModelIndex)
#define LenCoder (Align + kAlignTableSize)
#define RepLenCoder (LenCoder + kNumLenProbs)
#define Literal (RepLenCoder + kNumLenProbs)

/* The reference's header comment cites LZMA_BASE_SIZE 0x3F9, but its own
 * section table (SpecPos=688, Align=802, kNumLenToPosStates=4) sums to
 * 0x736, matching the current 7-zip SDK's published #define LZMA_BASE_SIZE
 * 1846 (0x736).  Use 0x736. */
#if Literal != 0x736
#error "model section offsets must sum to base size 0x736"
#endif

#define SW_LIT_PROBS (0x300u)

#ifndef SW_LZMA_TRACE
#define SW_LZMA_TRACE 0
#endif
#if SW_LZMA_TRACE
#define SW_TRACE(x) (fprintf x)
#else
#define SW_TRACE(x)
#endif

/* ---- range decoder (bit-exact with the reference macros) ------------ */
/*
 * The reference's IfBit0 expands to:
 *     RC_NORMALIZE; bound = (range>>11)*prob; if (code < bound) { UPDATE_0 } else { UPDATE_1 }
 * We reproduce it here as a small struct of state + a helper that returns
 * 0 (bit0) / 1 (bit1) / -1 (input exhausted), updating the prob and the
 * range-coder state.  No renormalize is done after the update, matching
 * the reference exactly.
 */
typedef struct sw_rc {
    const uint8_t *d, *lim;
    uint32_t i;
    uint32_t code, range;
    int eof;
} sw_rc;

static int rc_bit(sw_rc *rc, uint16_t *prob)
{
    if (rc->range < kTopValue) {
        if (rc->i >= (uint32_t)(rc->lim - rc->d)) { rc->eof = 1; return -1; }
        rc->range <<= 8;
        rc->code = (rc->code << 8) | (uint32_t)rc->d[rc->i++];
    }
    uint32_t bound = (uint32_t)(((uint64_t)(rc->range >> 11) * (uint32_t)*prob) & 0xFFFFFFFFu);
    if (rc->code < bound) {
        if (SW_LZMA_TRACE) fprintf(stderr, "rc_bit ->0 code=%08x range=%08x bound=%08x\n",
            rc->code, rc->range, bound);
        rc->range = bound;
        *prob = (uint16_t)(*prob + ((kBitModelTotal - *prob) >> kNumMoveBits));
        return 0;
    }
    if (SW_LZMA_TRACE) fprintf(stderr, "rc_bit ->1 code=%08x range=%08x bound=%08x\n",
        rc->code, rc->range, bound);
    rc->range -= bound;
    rc->code -= bound;
    *prob = (uint16_t)(*prob - (*prob >> kNumMoveBits));
    return 1;
}

/* Bit-tree, mirroring reference RangeDecoderBitTreeDecode: start at index
 * 1, each bit doubles the 1-based path index and adds the decoded bit;
 * final value minus (1<<n) yields 0..(1<<n)-1.  Returns -1 on eof. */
static int rc_tree(sw_rc *rc, uint16_t *base, int n)
{
    int res = 1;
    for (int i = 0; i < n; i++) {
        int b = rc_bit(rc, base + res);
        if (b < 0) return -1;
        res = (res + res) + b;
    }
    return res - (1 << n);
}

/* Reference RC_DIRECT high-distance bits. */
static int rc_direct(sw_rc *rc, int bits)
{
    if (bits <= 0) return 0;
    uint32_t hi = 0;
    for (int i = 0; i < bits; i++) {
        uint32_t t;
        if (rc->range < kTopValue) {
            if (rc->i >= (uint32_t)(rc->lim - rc->d)) { rc->eof = 1; return -1; }
            rc->range <<= 8;
            rc->code = (rc->code << 8) | (uint32_t)rc->d[rc->i++];
        }
        rc->range >>= 1;
        rc->code -= rc->range;
        t = (0u - (rc->code >> 31));   /* 0xFFFFFFFF if code MSB set, else 0 */
        hi = (hi << 1) + (t + 1);
        rc->code += rc->range & t;
    }
    return (int)hi;
}

/* Reference LzmaDecodeProperties (7z lc/lp/pb rule). */
static int props_decode(const uint8_t *props, uint32_t *lc, uint32_t *lp, uint32_t *pb)
{
    uint32_t p0 = props[0];
    if (p0 >= (9u * 5u * 5u)) return -1;
    uint32_t a = p0;
    uint32_t pbv = 0, lpv = 0;
    while (a >= (9u * 5u)) { a -= (9u * 5u); pbv++; }
    while (a >= 9u) { a -= 9u; lpv++; }
    uint32_t lcv = a;
    *lc = lcv; *lp = lpv; *pb = pbv;
    return 0;
}

/* ------------------------------------------------------------------ */
int sw_lzma_decompress(const uint8_t *props, const uint8_t *comp,
                       uint32_t comp_len, uint8_t *out, uint32_t out_cap)
{
    if (!props || !comp || !out) return -1;

    uint32_t lc, lp, pb;
    if (props_decode(props, &lc, &lp, &pb) < 0) return -1;
    if (lc > 8 || lp > 4 || pb > 4) return -1;

    uint32_t num_probs = (uint32_t)Literal + (SW_LIT_PROBS << ((uint32_t)lc + lp));
    uint16_t *p = (uint16_t *)sw_malloc(sizeof(uint16_t) * num_probs);
    if (!p) return -1;
    for (uint32_t i = 0; i < num_probs; i++) p[i] = (uint16_t)kBitModelHalf;

    sw_rc rc;
    rc.d = comp; rc.lim = comp + comp_len; rc.i = 0;
    rc.code = 0; rc.range = 0xFFFFFFFFu; rc.eof = 0;
    for (int k = 0; k < 5 && rc.i < comp_len; k++)
        rc.code = (rc.code << 8) | (uint32_t)rc.d[rc.i++];

    uint32_t pos_state_mask   = (1u << (int)pb) - 1u;
    uint32_t literal_pos_mask = (1u << (int)lp) - 1u;
    uint8_t previous_byte = 0;
    uint32_t rep0 = 1, rep1 = 1, rep2 = 1, rep3 = 1;
    uint32_t pos = 0;
    int state = 0;

    while (pos < out_cap) {
        uint32_t pos_state = pos & pos_state_mask;

        int is_match = rc_bit(&rc, &p[IsMatch + (state << kNumPosBitsMax) + pos_state]);
        if (is_match < 0) goto fail;
        if (SW_LZMA_TRACE) fprintf(stderr, "pos=%u is_match=%d state=%d pos_state=%u\n", pos, is_match, state, pos_state);

        if (is_match == 0) {
            /* ---- literal ---- */
            int symbol = 1;
            uint16_t *prob_lit = &p[Literal + SW_LIT_PROBS * (uint32_t)(
                (((pos) & literal_pos_mask) << lc)
                + ((uint32_t)previous_byte >> (8 - (int)lc)))];
            if (state >= kNumLitStates) {
                if (rep0 > pos) goto fail;   /* guard OOB read on bad input */
                int match_byte = out[pos - rep0];
                int offs = 0x100;   /* 7-zip MATCHED_LITER_DEC */
                do {
                    match_byte <<= 1;
                    int bit = offs;
                    offs &= match_byte;
                    int got = rc_bit(&rc, prob_lit + (offs + bit + symbol));
                    if (got < 0) goto fail;
                    symbol = (symbol << 1) + got;
                    if (got == 0) offs ^= bit;
                } while (symbol < 0x100);
            }
            while (symbol < 0x100) {
                int b = rc_bit(&rc, prob_lit + symbol);
                if (b < 0) goto fail;
                symbol = (symbol + symbol) + b;
            }
            SW_TRACE((stderr, "LIT pos=%u sym=%02x state=%d\n", pos, symbol, state));
            if (rc.eof) goto fail;
            previous_byte = (uint8_t)symbol;
            out[pos++] = previous_byte;
            if (state < 4) state = 0;
            else if (state < 10) state -= 3;
            else state -= 6;
            continue;
        }

        /* ---- match ---- */
        int is_rep = rc_bit(&rc, &p[IsRep + state]);
        if (is_rep < 0) goto fail;
        if (SW_LZMA_TRACE) fprintf(stderr, "pos=%u is_rep=%d\n", pos, is_rep);

        uint16_t *prob_len;
        int len;
        if (is_rep == 0) {
            rep3 = rep2; rep2 = rep1; rep1 = rep0;
            state = (state < kNumLitStates) ? 0 : 3;
            prob_len = p + LenCoder;
            if (rc_bit(&rc, &prob_len[LenChoice]) == 0) {
                int t = rc_tree(&rc, prob_len + LenLow + (pos_state << kLenNumLowBits), kLenNumLowBits);
                if (t < 0) goto fail;
                len = t;
            } else if (rc_bit(&rc, &prob_len[LenChoice2]) == 0) {
                int t = rc_tree(&rc, prob_len + LenMid + (pos_state << kLenNumMidBits), kLenNumMidBits);
                if (t < 0) goto fail;
                len = t + (int)kLenNumLowSymbols;
            } else {
                int t = rc_tree(&rc, prob_len + LenHigh, kLenNumHighBits);
                if (t < 0) goto fail;
                len = t + (int)(kLenNumLowSymbols + kLenNumMidSymbols);
            }
            if (rc.eof) goto fail;
            /* decode new distance */
            if (state < kNumLitStates) state += kNumLitStates;
            {
                int lenForPos = (len < kNumLenToPosStates) ? len : (kNumLenToPosStates - 1);
                int pos_slot = rc_tree(&rc,
                    p + PosSlot + (uint32_t)(lenForPos << kNumPosSlotBits),
                    kNumPosSlotBits);
                if (pos_slot < 0) goto fail;
                SW_TRACE((stderr, "POSSLOT pos=%u slot=%d lenForPos=%d\n", pos, pos_slot,
                          len < (int)kNumLenToPosStates ? len : (int)kNumLenToPosStates-1));
                uint32_t distance;
                if (pos_slot < kStartPosModelIndex) {
                    distance = (uint32_t)pos_slot;
                } else {
                    uint32_t posSlot = (uint32_t)pos_slot;
                    int numDirectBits = (int)((posSlot >> 1) - 1);
                    distance = (2u | (posSlot & 1u));
                    if (posSlot < (uint32_t)kEndPosModelIndex) {
                        /* SpecPos reverse bit-tree (matches 7-zip REV_BIT_VAR) */
                        distance <<= (uint32_t)numDirectBits;
                        uint32_t m = 1;
                        distance++;
                        do {
                            int bit = rc_bit(&rc, &p[SpecPos + distance]);
                            if (bit < 0) goto fail;
                            if (bit == 0) { distance += m; m += m; }
                            else          { m += m; distance += m; }
                        } while (--numDirectBits);
                        distance -= m;
                    } else {
                        /* high distance: direct bits then align reverse tree */
                        numDirectBits -= kNumAlignBits;
                        int hi = rc_direct(&rc, numDirectBits);
                        if (hi < 0) goto fail;
                        distance = (distance << (uint32_t)numDirectBits) | (uint32_t)hi;
                        distance <<= kNumAlignBits;
                        uint32_t i = 1;
                        #define SW_ALIGN_STEP(m) do { \
                            int b = rc_bit(&rc, &p[Align + i]); \
                            if (b < 0) goto fail; \
                            if (b == 0) i += (m); else i += 2 * (m); \
                        } while (0)
                        SW_ALIGN_STEP(1);
                        SW_ALIGN_STEP(2);
                        SW_ALIGN_STEP(4);
                        { int b = rc_bit(&rc, &p[Align + i]); if (b < 0) goto fail; if (b == 0) i -= 8; }
                        #undef SW_ALIGN_STEP
                        distance |= i;
                        if (distance == 0xFFFFFFFFu) goto fail;   /* end marker (file mode) */
                    }
                }
                rep0 = distance + 1;   /* 7-zip: rep0 = distance + 1 */
                SW_TRACE((stderr, "NEWDIST pos=%u d=%u\n", pos, rep0));
            }
        } else {
            int g0 = rc_bit(&rc, &p[IsRepG0 + state]);
            if (g0 < 0) goto fail;
            if (g0 == 0) {
                int lng = rc_bit(&rc, &p[IsRep0Long + (state << kNumPosBitsMax) + pos_state]);
                if (lng < 0) goto fail;
                if (lng == 0) {
                    if (rep0 > pos) goto fail;   /* guard OOB read */
                    state = (state < kNumLitStates) ? 9 : 11;
                    previous_byte = out[pos - rep0];
                    out[pos++] = previous_byte;
                    continue;
                }
            } else {
                int g1 = rc_bit(&rc, &p[IsRepG1 + state]);
                if (g1 < 0) goto fail;
                if (g1 == 0) {
                    rep0 = rep1;
                } else {
                    int g2 = rc_bit(&rc, &p[IsRepG2 + state]);
                    if (g2 < 0) goto fail;
                    if (g2 == 0) {
                        rep0 = rep2;
                    } else {
                        rep0 = rep3;
                        rep3 = rep2;
                    }
                    rep2 = rep1;
                    rep1 = rep0;
                }
            }
            state = (state < kNumLitStates) ? 8 : 11;
            prob_len = p + RepLenCoder;
            if (rc_bit(&rc, &prob_len[LenChoice]) == 0) {
                int t = rc_tree(&rc, prob_len + LenLow + (pos_state << kLenNumLowBits), kLenNumLowBits);
                if (t < 0) goto fail;
                len = t;
            } else if (rc_bit(&rc, &prob_len[LenChoice2]) == 0) {
                int t = rc_tree(&rc, prob_len + LenMid + (pos_state << kLenNumMidBits), kLenNumMidBits);
                if (t < 0) goto fail;
                len = t + (int)kLenNumLowSymbols;
            } else {
                int t = rc_tree(&rc, prob_len + LenHigh, kLenNumHighBits);
                if (t < 0) goto fail;
                len = t + (int)(kLenNumLowSymbols + kLenNumMidSymbols);
            }
            if (rc.eof) goto fail;
        }

        SW_TRACE((stderr, "MATCH pos=%u dist=%u len=%d\n", pos, rep0, len + kMatchMinLen));
        if (rep0 > pos) goto fail;
        int full = len + kMatchMinLen;
        if ((uint32_t)full > out_cap - pos) goto fail;
        for (int i = 0; i < full; i++, pos++)
            out[pos] = out[pos - rep0];
        /* The literal-context byte is the last byte written (7-zip reads
         * dic[dicPos-1]), so a match must refresh it or the next literal is
         * decoded from the wrong probability tree and the range coder
         * desynchronises. */
        previous_byte = out[pos - 1];
    }
    sw_free(p);
    if (SW_LZMA_TRACE) fprintf(stderr, "END pos=%u/%u\n", pos, out_cap);
    return 0;

fail:
    sw_free(p);
    if (SW_LZMA_TRACE) fprintf(stderr, "END pos=%u/%u fail (eof=%d)\n", pos, out_cap, rc.eof);
    return -1;
}
