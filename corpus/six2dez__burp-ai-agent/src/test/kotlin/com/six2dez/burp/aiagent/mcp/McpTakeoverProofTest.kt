package com.six2dez.burp.aiagent.mcp

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * SEC-07 / SC1 — unit coverage for the bind-conflict takeover credential.
 *
 * Every assertion here uses a WINDOW-ALIGNED base instant so the window arithmetic is deterministic:
 * `1_700_000_000_000 / 10_000` divides exactly, which makes `BASE + 9_999` provably the same window
 * and `BASE + 10_001` provably the next one. Using `System.currentTimeMillis()` instead would make
 * the boundary cases depend on when the suite happened to run, and this repo already has one recorded
 * wall-clock flake class — do not reintroduce the pattern here.
 *
 * Naming note, inherited verbatim from `McpTestServerSupport.kt`: test classes in this package MUST
 * NOT be named `*IntegrationTest`, `*ConcurrencyTest`, `*BackpressureTest`, `*RestartPolicyTest` or
 * `*SupervisionTest`. The `excludeHeavyTests` filter block inside `tasks.test` in `build.gradle.kts`
 * excludes exactly those globs under `-PexcludeHeavyTests=true`, so a security gate wearing one of
 * those suffixes would be silently skipped in a fast PR gate and prove nothing.
 */
class McpTakeoverProofTest {
    @Test
    fun forTargetIsDeterministicWithinAWindowAndIsUnpaddedBase64Url() {
        val first = McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE)
        val second = McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE + 9_999)

        assertEquals(first, second, "Two instants inside one window must mint the same proof")
        assertTrue(
            first.matches(Regex("^[A-Za-z0-9_-]+$")),
            "The proof must be Base64-URL with no padding, matching McpSettings.generateToken's encoder shape. Got: $first",
        )
        assertEquals(43, first.length, "An unpadded Base64-URL encoding of a 32-byte HMAC-SHA256 tag is 43 characters")
    }

    @Test
    fun acceptsAProofMintedInTheCurrentWindow() {
        val proof = McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE)

        assertTrue(McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE, proof), "A proof must validate at the instant it was minted")
        assertTrue(
            McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE + 9_999, proof),
            "A proof must still validate at the last millisecond of its own window",
        )
    }

    @Test
    fun acceptsAProofFromTheImmediatelyPreviousWindow() {
        val proof = McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE)

        assertTrue(
            McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE + 10_001, proof),
            "A-25-04: the one-window fallback is what makes a legitimate takeover that straddles a window " +
                "boundary safe. Without it a takeover minted at 9_999ms into a window would be rejected " +
                "2ms later and the MCP server would stay down after an ordinary extension reload.",
        )
    }

    @Test
    fun rejectsAProofFromTwoOrMoreWindowsAgo() {
        val proof = McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE)

        assertFalse(
            McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE + 25_000, proof),
            "T-25-04 bounds replay at two windows. A proof older than that must not validate.",
        )
    }

    @Test
    fun rejectsEverythingWhenTheTokenIsBlank() {
        // Mirrors isAuthorizedBearer's SEC-05 5c guard: a blank configured token can never authenticate.
        assertFalse(McpTakeoverProof.accepts("", HOST, PORT, BASE, "anything"))
        assertFalse(McpTakeoverProof.accepts("   ", HOST, PORT, BASE, "anything"))
        assertFalse(
            McpTakeoverProof.accepts("", HOST, PORT, BASE, ""),
            "A blank token paired with a blank presented value must not degrade into an accidental match",
        )
    }

    @Test
    fun rejectsAnEmptyPresentedValueOrTheRawTokenItself() {
        assertFalse(McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE, ""), "An absent proof header must never authorize")
        assertFalse(McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE, "   "), "A whitespace-only proof header must never authorize")
        assertFalse(
            McpTakeoverProof.accepts(TOKEN, HOST, PORT, BASE, TOKEN),
            "The raw token is not a proof. If this ever passes, a client that regressed to sending the " +
                "bearer secret would be silently accepted and Finding 7 would be reopened without a red test.",
        )
        assertNotEquals(
            TOKEN,
            McpTakeoverProof.forTarget(TOKEN, HOST, PORT, BASE),
            "The proof must not be the token — the whole point is that the wire value is worthless to a non-holder",
        )
    }

    @Test
    fun rejectsAProofMintedForADifferentHostOrPort() {
        val proof = McpTakeoverProof.forTarget(TOKEN, "localhost", PORT, BASE)

        assertFalse(
            McpTakeoverProof.accepts(TOKEN, "127.0.0.1", PORT, BASE, proof),
            "A-25-05: host-string identity. A proof minted for `localhost` must not validate against " +
                "`127.0.0.1`. That is a safe failure — the server stays down with an error log and no " +
                "credential leaks — but it must be a failure, not a silent acceptance.",
        )
        assertFalse(
            McpTakeoverProof.accepts(TOKEN, "localhost", PORT + 1, BASE, proof),
            "The proof is bound to the port so it cannot be lifted to another instance (T-25-05)",
        )
    }

    @Test
    fun hostComparisonIsCaseInsensitiveAndWhitespaceInsensitive() {
        val canonical = McpTakeoverProof.forTarget(TOKEN, "localhost", PORT, BASE)

        assertEquals(canonical, McpTakeoverProof.forTarget(TOKEN, "LOCALHOST", PORT, BASE), "Casing alone must never break a takeover")
        assertEquals(canonical, McpTakeoverProof.forTarget(TOKEN, " localhost ", PORT, BASE), "Surrounding whitespace must never break a takeover")
        assertTrue(McpTakeoverProof.accepts(TOKEN, " LOCALHOST ", PORT, BASE, canonical), "accepts must normalise the host exactly as forTarget does")
    }

    private companion object {
        private const val TOKEN = "test-token"
        private const val HOST = "127.0.0.1"
        private const val PORT = 8765

        /** Window-aligned: 1_700_000_000_000 is an exact multiple of the 10_000ms window. */
        private const val BASE = 1_700_000_000_000L
    }
}
