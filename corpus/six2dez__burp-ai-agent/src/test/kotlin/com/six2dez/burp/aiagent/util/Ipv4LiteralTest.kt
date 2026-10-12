package com.six2dez.burp.aiagent.util

import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

/**
 * Boundary contract for the `inet_aton` parser (SEC-07, A-25-07 and A-25-08).
 *
 * Every limit is pinned on BOTH sides — the largest accepted value and the smallest rejected one —
 * because a parser that is merely "permissive enough" would silently widen the classifier's input
 * domain. Expectations are raw `ByteArray`s compared with `assertArrayEquals`: Kotlin's `Byte` is
 * signed, so an assertion that normalised both sides with `toInt() and 0xFF` could pass while the
 * parser emitted the wrong sign.
 */
class Ipv4LiteralTest {
    // --- Arity: the last part absorbs every byte the preceding parts did not supply. ---

    @Test
    fun fourPartForm_isTheOrdinaryDottedQuad() {
        assertArrayEquals(byteArrayOf(192.toByte(), 168.toByte(), 1, 10), Ipv4Literal.parse("192.168.1.10"))
    }

    @Test
    fun threePartForm_lastPartAbsorbsTwoBytes() {
        assertArrayEquals(byteArrayOf(192.toByte(), 168.toByte(), 0, 1), Ipv4Literal.parse("192.168.1"))
    }

    @Test
    fun twoPartForm_lastPartAbsorbsThreeBytes() {
        assertArrayEquals(byteArrayOf(10, 0, 0, 1), Ipv4Literal.parse("10.1"))
    }

    @Test
    fun onePartForm_absorbsAllFourBytes() {
        assertArrayEquals(byteArrayOf(127, 0, 0, 1), Ipv4Literal.parse("2130706433"))
    }

    // --- A-25-08: every intermediate value is a Long, so nothing overflows to a negative Int. ---

    @Test
    fun decimalAboveIntMaxValue_doesNotOverflow() {
        // 2_852_039_166 exceeds Int.MAX_VALUE and would wrap negative in 32-bit arithmetic.
        assertArrayEquals(
            byteArrayOf(169.toByte(), 254.toByte(), 169.toByte(), 254.toByte()),
            Ipv4Literal.parse("2852039166"),
        )
    }

    @Test
    fun precisionBoundary_isPinnedOnBothSides() {
        assertArrayEquals(
            byteArrayOf(255.toByte(), 255.toByte(), 255.toByte(), 255.toByte()),
            Ipv4Literal.parse("4294967295"),
        )
        assertNull(Ipv4Literal.parse("4294967296"))
        // Rejected by toLongOrNull overflow, not by a length rule — the string is well under the cap.
        assertNull(Ipv4Literal.parse("99999999999999999999"))
    }

    // --- Radix boundaries. ---

    @Test
    fun decimalOctetBoundary_isPinnedOnBothSides() {
        assertArrayEquals(
            byteArrayOf(255.toByte(), 255.toByte(), 255.toByte(), 255.toByte()),
            Ipv4Literal.parse("255.255.255.255"),
        )
        assertNull(Ipv4Literal.parse("256.0.0.1"))
    }

    @Test
    fun octalBoundary_isPinnedOnBothSides() {
        // A-25-09: the JDK reads 0177 as decimal 177. This parser reads it as octal 127.
        assertArrayEquals(byteArrayOf(127, 0, 0, 1), Ipv4Literal.parse("0177.0.0.1"))
        assertArrayEquals(byteArrayOf(255.toByte(), 0, 0, 1), Ipv4Literal.parse("0377.0.0.1"))
        assertNull(Ipv4Literal.parse("0400.0.0.1"))
        assertNull(Ipv4Literal.parse("08.0.0.1"))
    }

    @Test
    fun hexadecimalBoundary_isPinnedOnBothSides() {
        assertArrayEquals(byteArrayOf(127, 0, 0, 1), Ipv4Literal.parse("0x7f.1"))
        assertArrayEquals(
            byteArrayOf(255.toByte(), 255.toByte(), 255.toByte(), 255.toByte()),
            Ipv4Literal.parse("0xFFFFFFFF"),
        )
        assertNull(Ipv4Literal.parse("0x100000000"))
        assertNull(Ipv4Literal.parse("0x"))
        assertNull(Ipv4Literal.parse("0xg"))
    }

    // --- Shape: one rule (no empty part, at most four parts) rejects every malformed dot pattern. ---

    @Test
    fun malformedDotPatterns_areRejected() {
        assertNull(Ipv4Literal.parse(""))
        assertNull(Ipv4Literal.parse("."))
        assertNull(Ipv4Literal.parse("1.2.3.4."))
        assertNull(Ipv4Literal.parse(".1.2.3"))
        assertNull(Ipv4Literal.parse("1..2.3"))
        assertNull(Ipv4Literal.parse("1.2.3.4.5"))
    }

    @Test
    fun lengthCap_isPinnedOnBothSides() {
        // Padded with leading zeros so the ONLY thing separating the two cases is the length cap:
        // without it, both would parse as 0.1.2.3.
        val suffix = ".1.2.3"
        val atCap = "0".repeat(Ipv4Literal.MAX_LITERAL_LENGTH - suffix.length) + suffix
        val overCap = "0".repeat(Ipv4Literal.MAX_LITERAL_LENGTH + 1 - suffix.length) + suffix

        assertArrayEquals(byteArrayOf(0, 1, 2, 3), Ipv4Literal.parse(atCap))
        assertNull(Ipv4Literal.parse(overCap))
    }

    @Test
    fun signedParts_areRejected() {
        // The radix alphabet check rejects these; no sign is special-cased.
        assertNull(Ipv4Literal.parse("+1.2.3.4"))
        assertNull(Ipv4Literal.parse("-1.2.3.4"))
    }

    // --- Non-literals stay the IPv6 branch's or the hostname path's business, never the parser's. ---

    @Test
    fun nonLiteralHosts_areRejected() {
        assertNull(Ipv4Literal.parse("api.openai.com"))
        assertNull(Ipv4Literal.parse("localhost"))
        assertNull(Ipv4Literal.parse("not-a-url"))
        assertNull(Ipv4Literal.parse("fe80::1"))
    }
}
