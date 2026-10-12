package com.six2dez.burp.aiagent.util

import java.net.Inet6Address
import java.net.InetAddress
import java.net.URI

/**
 * Pure, network-free classifier for backend base-URLs (SEC-03 / A6).
 *
 * [isPrivateOrLinkLocal] returns true when a URL's host is a literal IP address in a private
 * (RFC-1918), link-local (169.254.0.0/16, fe80::/10), or cloud-metadata (169.254.169.254) range.
 * Loopback is explicitly EXCLUDED (Ollama/LM Studio local use is legitimate).
 *
 * Constraints (per D-01 "classify by address range inspection only"):
 * - No DNS resolution: only literal IP hosts are classified. Hostname-format hosts return false.
 * - No network calls; never throws on malformed/blank input.
 *
 * "Literal" means every `inet_aton` notation, not only the dotted quad (SEC-07). Decimal, octal and
 * hexadecimal IPv4 literals are parsed locally by [Ipv4Literal] and classified from their bytes, so
 * `http://2852039166/` — the decimal spelling of the cloud-metadata address 169.254.169.254 — is now
 * flagged exactly as its dotted-quad equivalent is, and `2130706433`, `0177.0.0.1` and `0x7f.1` are
 * all recognised as loopback and therefore excluded.
 *
 * Notation independence extends to the IPv6 arm (WR-02, 25-REVIEW). The IPv4-mapped IPv6 forms —
 * `[::ffff:169.254.169.254]`, `[0:0:0:0:0:ffff:192.168.1.10]` and their unbracketed spellings — are
 * classified IDENTICALLY to their hex equivalents `[::ffff:a9fe:a9fe]` and `[::ffff:c0a8:10a]`, and
 * `[::ffff:127.0.0.1]` stays excluded exactly as `127.0.0.1` does. Before this was fixed the hex
 * spelling was flagged and the dotted spelling of the same address was not, so the paragraph above
 * described the IPv4 arm only while reading as though it covered both. What makes the fix safe is
 * that [IPV6_REGEX] is not the gate that keeps hostnames away from the one resolving call — the
 * `host.contains(':')` conjunct is. Admitting '.' into the character class therefore widens which
 * LITERALS are recognised without widening what a name lookup could ever be attempted on: a dotted
 * host with no ':' does not reach that branch at all, and `SsrfGuardNoResolutionTest` asserts the
 * JVM-wide lookup count is zero across a corpus that now includes the mapped forms.
 *
 * The IPv4 branch calls no resolving API at all. That CLOSED a real defect rather than preserving a
 * property: `256.0.0.1` matched the old dotted-quad regex, passed the literal gate and reached the
 * JDK's name-resolving lookup, which could not read it as a literal and resolved it as a NAME — a
 * real outbound lookup, measured at 27 ms on JDK 21 (2026-08-22), leaking the typed or imported
 * string to the configured resolver. (`0400.0.0.1` did NOT match the old regex — corrected
 * 2026-08-22 — so `256.0.0.1` alone carries that evidence.) `InetAddress.getByAddress` cannot
 * resolve, and the one surviving resolving call is on the IPv6 branch, which a ':' guard already
 * keeps away from names. That one call is why a bare `grep -c` for the resolving method name in this
 * file must return exactly 1: the count simultaneously proves the IPv4 branch stopped resolving and
 * proves the IPv6 branch was not deleted along with it. Do not name it again in prose here.
 *
 * The result is advisory only — the caller shows a non-blocking inline warning and proceeds.
 */
object SsrfGuard {
    // Conservative literal-IP detector for IPv6: anything with a ':' that is all hex/colon/dot is
    // treated as a literal IPv6 candidate. The '.' is what admits the IPv4-mapped spellings
    // (`::ffff:192.168.1.10`); it does NOT admit hostnames, because the `host.contains(':')`
    // conjunct at the call site — not this character class — is the resolver gate. IPv4 literals
    // need no such guard at all — Ipv4Literal parses them without any lookup.
    private val IPV6_REGEX = Regex("""^[0-9a-fA-F:.]+$""")

    fun isPrivateOrLinkLocal(url: String): Boolean {
        if (url.isBlank()) return false

        val rawHost =
            try {
                URI(url).host
            } catch (e: Exception) {
                null
            }
        // URI(...).host is null for IPv6 hosts that are not bracketed (e.g. http://fe80::1) and for
        // some malformed inputs. Fall back to a manual authority parse so unbracketed IPv6 literals
        // are still classified.
        val host = (rawHost ?: extractAuthorityHost(url))?.trim()?.removeSurrounding("[", "]")
        if (host.isNullOrBlank()) return false

        // Only classify literal IPs — never resolve hostnames. IPv4 literals are parsed locally in
        // every inet_aton notation and turned into an address from their raw bytes, so this branch
        // performs no name resolution whatsoever.
        val ipv4Bytes = Ipv4Literal.parse(host)
        val addr =
            when {
                ipv4Bytes != null -> InetAddress.getByAddress(ipv4Bytes)
                host.contains(':') && IPV6_REGEX.matches(host) -> resolveIpv6Literal(host)
                else -> null
            } ?: return false

        return when {
            addr.isLoopbackAddress -> false // loopback excluded per D-01
            addr.isSiteLocalAddress -> true // RFC-1918: 10.x, 172.16-31.x, 192.168.x
            addr.isLinkLocalAddress -> true // 169.254.x.x and fe80::/10
            addr.hostAddress == "169.254.169.254" -> true // cloud metadata (also link-local; explicit)
            // WR-04: IPv6 Unique Local Addresses (fc00::/7) — Java's isSiteLocalAddress() covers only
            // the deprecated fec0::/10 site-local range and does not flag fc00::/7 (fc and fd prefixes).
            addr is Inet6Address && isIpv6Ula(addr) -> true
            else -> false
        }
    }

    /**
     * Turns an already-validated literal IPv6 host into an address, or null when the JDK rejects it.
     *
     * This is the ONLY resolving call left in this object, and it is unreachable for anything that is
     * not colon-shaped: the caller gates it behind `host.contains(':')` plus [IPV6_REGEX], and a
     * string containing ':' never reaches the resolver (measured on JDK 21: resolving `abcd:efab`
     * throws in 0 ms, i.e. without a lookup). IPv4 no longer comes through here at all.
     */
    private fun resolveIpv6Literal(host: String): InetAddress? =
        try {
            InetAddress.getByName(host)
        } catch (e: Exception) {
            null
        }

    /**
     * Returns true when [addr] falls within the IPv6 Unique Local Address range fc00::/7.
     *
     * The range covers all addresses whose first 7 bits are 1111110x, i.e. prefix bytes 0xFC and
     * 0xFD. Masking the first byte with 0xFE and comparing to 0xFC detects both. This is a
     * network-free, pure byte inspection.
     */
    private fun isIpv6Ula(addr: Inet6Address): Boolean {
        val firstByte = addr.address[0].toInt() and 0xFF
        return firstByte and 0xFE == 0xFC // matches fc00::/7 (fc and fd prefixes)
    }

    /**
     * Best-effort extraction of the host portion from a URL authority for inputs that
     * [URI.getHost] cannot parse (e.g. unbracketed IPv6 literals). Returns null when no authority
     * is present. Performs no DNS — pure string parsing.
     */
    private fun extractAuthorityHost(url: String): String? {
        val schemeIdx = url.indexOf("://")
        if (schemeIdx < 0) return null
        var authority = url.substring(schemeIdx + 3)
        // Strip path/query/fragment.
        authority = authority.substringBefore('/').substringBefore('?').substringBefore('#')
        // Strip userinfo.
        authority = authority.substringAfterLast('@')
        if (authority.isBlank()) return null
        // Bracketed IPv6 with optional :port — return the inside of the brackets.
        if (authority.startsWith("[")) {
            val close = authority.indexOf(']')
            if (close > 0) return authority.substring(1, close)
        }
        // Unbracketed IPv6 literal: more than one ':' means it is not host:port.
        if (authority.count { it == ':' } > 1) return authority
        // host:port (IPv4 or hostname).
        return authority.substringBefore(':')
    }
}
