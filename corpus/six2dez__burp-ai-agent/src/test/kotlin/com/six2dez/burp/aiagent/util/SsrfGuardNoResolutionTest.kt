package com.six2dez.burp.aiagent.util

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.MethodOrderer
import org.junit.jupiter.api.Order
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestMethodOrder
import java.net.InetAddress
import java.util.UUID

/**
 * SEC-07 / SC4, asserted rather than assumed: classifying a host string performs zero name lookups.
 *
 * The observable is [CountingInetAddressResolverProvider]'s counter, never elapsed time. This repo
 * has a recorded wall-clock flake class (`RedactionTest` under CPU load via the `SafeRegex` 50 ms
 * deadline) and a timing threshold here would join it.
 *
 * This is a genuine regression gate, not a formality. Before the SEC-07 rewiring, `http://256.0.0.1/`
 * matched the old dotted-quad regex, passed the literal gate and reached the JDK's name-resolving
 * lookup — which could not read `256.0.0.1` as a literal and therefore resolved it as a NAME, leaking
 * a typed or imported settings value to the configured resolver.
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation::class)
class SsrfGuardNoResolutionTest {
    /**
     * The control. Without it, [classifyingEveryNotationResolvesNothing] could pass against a counter
     * that was never installed — a vacuous pass is the only way this gate can lie.
     */
    @Test
    @Order(1)
    fun theCountingResolverIsActuallyInstalled() {
        CountingInetAddressResolverProvider.reset()
        // Freshly generated, so it cannot be served from InetAddress's positive or negative cache and
        // the lookup must reach the resolver. `.invalid` is reserved by RFC 6761 and never resolves,
        // so the outcome is a fast UnknownHostException and this test depends on no network.
        val probe = "gsd-ssrf-control-${UUID.randomUUID()}.invalid"
        runCatching { InetAddress.getByName(probe) }

        assertTrue(
            CountingInetAddressResolverProvider.count() > 0L,
            "The counting InetAddressResolverProvider is NOT installed: resolving '$probe' never " +
                "reached it. Either src/test/resources/META-INF/services/" +
                "java.net.spi.InetAddressResolverProvider is missing from the test classpath, or it " +
                "names the wrong class. Until this test passes, classifyingEveryNotationResolvesNothing " +
                "is proving NOTHING — it would pass vacuously against a counter that never moves.",
        )
    }

    @Test
    @Order(2)
    fun classifyingEveryNotationResolvesNothing() {
        CountingInetAddressResolverProvider.reset()

        // A shrinking corpus is the other way this gate can quietly stop proving anything: deleting
        // the awkward inputs makes "zero lookups" trivially true. Pin the floor.
        assertTrue(
            CORPUS.size >= MIN_CORPUS_SIZE,
            "The no-resolution corpus shrank to ${CORPUS.size} entries (floor: $MIN_CORPUS_SIZE). " +
                "Entries are added here when a classification path widens; removing them narrows " +
                "what SC4 proves rather than fixing anything.",
        )

        CORPUS.forEach { SsrfGuard.isPrivateOrLinkLocal(it) }

        assertEquals(
            0L,
            CountingInetAddressResolverProvider.count(),
            "SsrfGuard performed name resolution while classifying. Leaked host names: " +
                "${CountingInetAddressResolverProvider.recentNames()}. Classification must be a pure " +
                "function of the host string; a resolving call here turns unvalidated settings text " +
                "into an outbound lookup (SEC-07 / T-25-07).",
        )
    }

    private companion object {
        /** Floor on [CORPUS]'s size, so the gate cannot be made green by deleting inputs. */
        const val MIN_CORPUS_SIZE = 19

        /**
         * Every notation, every rejected form, hostnames and IPv6 — plus the two inputs measured to
         * behave interestingly on the pre-SEC-07 tree: `256.0.0.1`, which resolved as a name, and
         * `0400.0.0.1`, which the old four-digit-rejecting regex turned away before it could.
         */
        val CORPUS =
            listOf(
                // The four SC3 forms.
                "http://2130706433/",
                "http://0177.0.0.1/",
                "http://0x7f.1/",
                "http://2852039166/",
                // Literals the parser rejects — rejection must never become a resolution attempt.
                "http://256.0.0.1/",
                "http://0400.0.0.1/",
                // Hostnames: the classifier must decline them, not look them up.
                "https://api.openai.com",
                "http://internal-service.corp/",
                "http://localhost:11434",
                "http://not-a-url",
                "",
                // Dotted quad and IPv6, the paths that already worked.
                "http://192.168.1.10/",
                "http://[fc00::1]",
                "http://fe80::1",
                // WR-02: the IPv4-mapped IPv6 forms. These now pass the widened literal gate and so
                // reach the one resolving call for the first time — which is exactly why they belong
                // here. A mapped literal is parsed as a literal and must move the counter by zero.
                "http://[::ffff:169.254.169.254]/",
                "http://[::ffff:192.168.1.10]/",
                "http://[0:0:0:0:0:ffff:192.168.1.10]/",
                "http://::ffff:192.168.1.10/",
                "http://[::ffff:127.0.0.1]/",
                // Colon-and-dot strings that match the widened class but are NOT valid literals: the
                // gate must turn them away as a rejection, never as a lookup.
                "http://1.2:3/",
                "http://[a.b:c]/",
            )
    }
}
