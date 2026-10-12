package com.six2dez.burp.aiagent.util

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SsrfGuardTest {
    @Test
    fun rfc1918_192_168_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://192.168.1.10/api"))
    }

    @Test
    fun rfc1918_10_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://10.0.0.1:8080"))
    }

    @Test
    fun rfc1918_172_16_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://172.16.0.1"))
    }

    @Test
    fun cloudMetadata_169_254_169_254_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://169.254.169.254/latest/meta-data/"))
    }

    @Test
    fun ipv6LinkLocal_fe80_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://fe80::1"))
    }

    @Test
    fun loopback_127_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://127.0.0.1:11434"))
    }

    @Test
    fun publicHost_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("https://api.openai.com"))
    }

    @Test
    fun blankInput_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal(""))
    }

    @Test
    fun malformedInput_isNotFlagged_noException() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("not-a-url"))
    }

    // WR-04: IPv6 Unique Local Addresses (fc00::/7) must be flagged.
    // Java's isSiteLocalAddress() covers only the deprecated fec0::/10 range and misses these.

    @Test
    fun ipv6Ula_fc00_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://[fc00::1]"))
    }

    @Test
    fun ipv6Ula_fd_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://[fd12:3456::1]"))
    }

    // SEC-07 tracer: non-dotted-quad IPv4 notations must be parsed and classified, not rejected.

    @Test
    fun decimalLiteral_cloudMetadata_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://2852039166/"))
    }

    @Test
    fun decimalLiteral_loopback_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://2130706433/"))
    }

    // SEC-07 / SC3: the four named forms, asserted through the PUBLIC entry point rather than
    // through Ipv4Literal. URI(...).host is null for "0x7f.1" (measured on JDK 21), so that form
    // reaches the parser only via the extractAuthorityHost fallback — a parser-only test would pass
    // while the user-visible behaviour stayed broken.

    @Test
    fun octalLiteral_loopback_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://0177.0.0.1/"))
    }

    @Test
    fun hexLiteral_loopback_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://0x7f.1/"))
    }

    // SEC-07: RFC-1918 ranges must be flagged in every notation, not only as a dotted quad.

    @Test
    fun rfc1918_inAlternateNotations_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://3232235786/")) // 192.168.1.10, decimal
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://0xC0A8010A/")) // 192.168.1.10, hexadecimal
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://0300.0250.1.10/")) // 192.168.1.10, octal
    }

    // SEC-07: a literal the parser rejects must stay a plain "false" and must never become a
    // resolution attempt. SsrfGuardNoResolutionTest is what proves the second half.

    @Test
    fun rejectedLiterals_areNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://256.0.0.1/"))
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://0400.0.0.1/"))
    }

    // WR-02 (25-REVIEW): the IPv4-mapped IPv6 notation. The hex spelling of an address was flagged
    // while the dotted spelling of the SAME address was not, which is the notation-evasion class
    // SC3 closed on the IPv4 arm. Each mapped case is asserted AGAINST its hex spelling rather than
    // against a hardcoded `true`, so the property under test is "the two spellings agree", which is
    // what the object KDoc claims — a future change that breaks both spellings the same way still
    // fails the absolute assertion beside it.

    @Test
    fun ipv4MappedIpv6_cloudMetadata_isFlagged_andAgreesWithHexSpelling() {
        val dotted = SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:169.254.169.254]/")
        val hex = SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:a9fe:a9fe]/")

        assertTrue(dotted, "IPv4-mapped cloud-metadata literal must be flagged")
        assertEquals(hex, dotted, "The mapped and hex spellings of 169.254.169.254 must agree")
    }

    @Test
    fun ipv4MappedIpv6_rfc1918_isFlagged_andAgreesWithHexSpelling() {
        val dotted = SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:192.168.1.10]/")
        val hex = SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:c0a8:10a]/")

        assertTrue(dotted, "IPv4-mapped RFC-1918 literal must be flagged")
        assertEquals(hex, dotted, "The mapped and hex spellings of 192.168.1.10 must agree")
    }

    @Test
    fun ipv4MappedIpv6_expandedForm_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://[0:0:0:0:0:ffff:192.168.1.10]/"))
    }

    /** Unbracketed, so the host arrives through the `extractAuthorityHost` fallback, not `URI.host`. */
    @Test
    fun ipv4MappedIpv6_unbracketed_isFlagged() {
        assertTrue(SsrfGuard.isPrivateOrLinkLocal("http://::ffff:192.168.1.10/"))
    }

    /** D-01: loopback stays excluded under every spelling, so local Ollama/LM Studio stays quiet. */
    @Test
    fun ipv4MappedIpv6_loopback_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:127.0.0.1]/"))
    }

    @Test
    fun ipv4MappedIpv6_publicAddress_isNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://[::ffff:8.8.8.8]/"))
    }

    /**
     * Admitting '.' into the literal gate must not admit hostnames: a dotted host with no ':' never
     * reaches the literal branch at all, because the ':' conjunct — not the character class — is the
     * resolver gate.
     */
    @Test
    fun dottedHostname_isStillNotFlagged() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://example.com/"))
    }

    /** A colon-bearing, dot-bearing string that is not a valid IPv6 literal: false, and no throw. */
    @Test
    fun colonAndDotBearingNonLiteral_isNotFlagged_noException() {
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://1.2:3/"))
        assertFalse(SsrfGuard.isPrivateOrLinkLocal("http://[a.b:c]/"))
    }
}
