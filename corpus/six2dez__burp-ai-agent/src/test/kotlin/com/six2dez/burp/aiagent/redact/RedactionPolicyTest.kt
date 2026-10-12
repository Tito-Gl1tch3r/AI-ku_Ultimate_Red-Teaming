package com.six2dez.burp.aiagent.redact

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.UUID

/**
 * The policy table and the host-anonymisation primitive it gates.
 *
 * `RedactionPolicy.fromMode` is the table `Redaction.redact` and `sanitizeHeaders` both branch on,
 * so a silent flip in one of its nine flags changes what leaves the host without changing anything
 * a reader would look at. Each flag is therefore asserted individually rather than by data-class
 * equality: an equality failure says "the policy is wrong", a per-flag failure says WHICH flag.
 */
class RedactionPolicyTest {
    @Test
    fun defaultPolicyEnablesAllThreeControls() {
        val policy = RedactionPolicy.default()

        assertTrue(policy.stripCookies, "default() must strip cookies")
        assertTrue(policy.redactTokens, "default() must redact tokens")
        assertTrue(policy.anonymizeHosts, "default() must anonymize hosts")
    }

    @Test
    fun strictModeEnablesAllThreeControls() {
        val policy = RedactionPolicy.fromMode(PrivacyMode.STRICT)

        assertTrue(policy.stripCookies, "STRICT must strip cookies")
        assertTrue(policy.redactTokens, "STRICT must redact tokens")
        assertTrue(policy.anonymizeHosts, "STRICT must anonymize hosts")
    }

    @Test
    fun balancedModeRedactsButKeepsHostsIntact() {
        val policy = RedactionPolicy.fromMode(PrivacyMode.BALANCED)

        assertTrue(policy.stripCookies, "BALANCED must strip cookies")
        assertTrue(policy.redactTokens, "BALANCED must redact tokens")
        assertFalse(policy.anonymizeHosts, "BALANCED keeps real hostnames — that is the whole trade")
    }

    @Test
    fun offModeDisablesAllThreeControls() {
        val policy = RedactionPolicy.fromMode(PrivacyMode.OFF)

        assertFalse(policy.stripCookies, "OFF must not strip cookies")
        assertFalse(policy.redactTokens, "OFF must not redact tokens")
        assertFalse(policy.anonymizeHosts, "OFF must not anonymize hosts")
    }

    @Test
    fun privacyModeFromStringIsCaseInsensitiveAndFallsBackToBalanced() {
        assertEquals(PrivacyMode.STRICT, PrivacyMode.fromString("strict"))
        assertEquals(PrivacyMode.OFF, PrivacyMode.fromString("OfF"))
        assertEquals(PrivacyMode.BALANCED, PrivacyMode.fromString(null), "an absent mode falls back to BALANCED")
        assertEquals(PrivacyMode.BALANCED, PrivacyMode.fromString("nonsense"), "an unknown mode falls back to BALANCED")
    }

    // ---- Redaction.anonymizeHost: the HKDF primitive STRICT mode depends on ----

    @Test
    fun anonymizeHostIsDeterministicForAFixedSalt() {
        val salt = freshSalt()
        val first = Redaction.anonymizeHost("internal.corp", salt)
        val second = Redaction.anonymizeHost("internal.corp", salt)

        assertEquals(first, second, "the same host under the same salt must map to the same pseudonym")
        assertTrue(
            first.matches(Regex("""host-[0-9a-f]{12}\.local""")),
            "the output format host-<12 hex>.local is depended on by ~10 call sites; got '$first'",
        )
    }

    @Test
    fun anonymizeHostDiffersAcrossSaltsAndAcrossHosts() {
        val saltA = freshSalt()
        val saltB = freshSalt()

        assertNotEquals(
            Redaction.anonymizeHost("internal.corp", saltA),
            Redaction.anonymizeHost("internal.corp", saltB),
            "a per-session salt must repartition the mapping, or pseudonyms correlate across sessions",
        )
        assertNotEquals(
            Redaction.anonymizeHost("a.internal.corp", saltA),
            Redaction.anonymizeHost("b.internal.corp", saltA),
            "distinct hosts under one salt must not collide",
        )
    }

    /**
     * An empty salt is the JCA edge case the HMAC primitive substitutes a single zero byte for —
     * `SecretKeySpec` rejects a zero-length key outright, so without the substitution this throws
     * instead of returning a pseudonym. Asserted as an outcome rather than read off the comment.
     */
    @Test
    fun anonymizeHostWithAnEmptySaltStillProducesAWellFormedPseudonym() {
        val anon = Redaction.anonymizeHost("internal.corp", "", recordMapping = false)

        assertTrue(
            anon.matches(Regex("""host-[0-9a-f]{12}\.local""")),
            "an empty salt must not throw and must still yield the standard form; got '$anon'",
        )
    }

    @Test
    fun anonymizeHostWithAnEmptyHostStillProducesAWellFormedPseudonym() {
        val anon = Redaction.anonymizeHost("", freshSalt(), recordMapping = false)

        assertTrue(
            anon.matches(Regex("""host-[0-9a-f]{12}\.local""")),
            "an empty host must not throw — callers pass whatever the URL parser gave them; got '$anon'",
        )
    }

    /**
     * An IP literal is anonymised exactly like a name: the function does not special-case it. That
     * is the observed behaviour, and it is named here rather than assumed, because a reader could
     * reasonably expect a literal to pass through.
     */
    @Test
    fun anonymizeHostTreatsAnIpLiteralLikeAnyOtherHost() {
        val salt = freshSalt()
        val anon = Redaction.anonymizeHost("10.0.0.7", salt)

        assertTrue(
            anon.matches(Regex("""host-[0-9a-f]{12}\.local""")),
            "an IP literal is anonymised, not passed through; got '$anon'",
        )
        assertEquals("10.0.0.7", Redaction.deAnonymizeHost(anon, salt))
    }

    @Test
    fun recordMappingFalseLeavesNoReverseMappingBehind() {
        val salt = freshSalt()
        val anon = Redaction.anonymizeHost("unrecorded.corp", salt, recordMapping = false)

        assertNull(
            Redaction.deAnonymizeHost(anon, salt),
            "recordMapping = false must not populate the reverse map — callers that only need a " +
                "stable pseudonym must not grow the in-memory table",
        )
    }

    @Test
    fun clearMappingsForOneSaltLeavesOtherSaltsIntact() {
        val kept = freshSalt()
        val dropped = freshSalt()
        val keptAnon = Redaction.anonymizeHost("kept.corp", kept)
        val droppedAnon = Redaction.anonymizeHost("dropped.corp", dropped)

        Redaction.clearMappings(dropped)

        assertNull(Redaction.deAnonymizeHost(droppedAnon, dropped), "the cleared salt must be gone")
        assertEquals("kept.corp", Redaction.deAnonymizeHost(keptAnon, kept), "other salts must survive")
    }

    // ---- SecretShapes: the curated shape list the tripwire reports category names from ----

    @Test
    fun secretShapesAreNonEmptyAndUniquelyNamed() {
        val shapes = SecretShapes.shapes

        assertTrue(shapes.isNotEmpty(), "the curated shape list must not be empty")
        assertEquals(
            shapes.size,
            shapes.map { it.category }.toSet().size,
            "shape categories are what the tripwire reports instead of the matched token, so they must be unique",
        )
        assertTrue(
            shapes.all { it.category.isNotBlank() },
            "a blank shape category would surface as an unnamed finding in the audit trail",
        )
    }

    // ---- the cookie-section walk's UNDER-redaction bound, pinned as an outcome ----

    /**
     * `MAX_COOKIE_SECTION_LINES` is an accepted residual, not a safety margin: a cookie section
     * longer than the bound is redacted only up to that line, and every entry below it reaches the
     * backend verbatim. The constant's own comment records the measurement (a 20-entry section
     * leaves `ck16`..`ck19` untouched) but nothing asserted it, so the leak could widen — by raising
     * the emitter's bound, or by a walk that consumed budget faster — with the suite still green.
     *
     * This pins BOTH halves: everything inside the bound is redacted, and the first entry outside it
     * is not. The second assertion is the one that would go red if the bound silently grew, and it
     * is deliberately written as "still leaks" rather than as a desired behaviour.
     */
    @Test
    fun aCookieSectionLongerThanTheLineBoundIsRedactedOnlyUpToTheBound() {
        val entries = (0 until 20).joinToString("\n") { "ck$it=secret$it" }
        val raw = "${Redaction.COOKIE_SECTION_HEADER}\n$entries\n"

        val out =
            Redaction.apply(
                raw,
                RedactionPolicy.fromMode(PrivacyMode.STRICT),
                freshSalt(),
                recordMapping = false,
            )

        for (index in 0 until Redaction.MAX_COOKIE_SECTION_LINES) {
            assertTrue(
                out.contains("ck$index=[REDACTED]"),
                "entry ck$index is inside the ${Redaction.MAX_COOKIE_SECTION_LINES}-line bound and must be redacted",
            )
        }
        assertTrue(
            out.contains("ck${Redaction.MAX_COOKIE_SECTION_LINES}=secret${Redaction.MAX_COOKIE_SECTION_LINES}"),
            "ACCEPTED RESIDUAL: the first entry past the line bound is NOT redacted. If this assertion " +
                "fails because the entry is now redacted, the bound was widened — update this test and " +
                "the constant's comment together, deliberately.",
        )
    }

    /**
     * The walk's malformed-input arms. `redactCookieSections` runs over arbitrary MCP tool output
     * as well as emitter-shaped prompts, so the header can arrive truncated, unterminated, or
     * immediately followed by the next section. None of those may throw, and none may pass a
     * name=value pair through — a crash here aborts redaction on a scanner or MCP tool thread.
     */
    @Test
    fun aTruncatedOrUnterminatedCookieSectionIsHandledWithoutThrowing() {
        val policy = RedactionPolicy.fromMode(PrivacyMode.STRICT)

        // (a) The header is the entire text — no newline after it at all.
        val headerOnly = Redaction.apply(Redaction.COOKIE_SECTION_HEADER, policy, freshSalt(), recordMapping = false)
        assertTrue(
            headerOnly.contains(Redaction.COOKIE_SECTION_HEADER),
            "a bare header must survive the walk intact; got '$headerOnly'",
        )

        // (b) A short section whose last entry has no trailing newline.
        val unterminated =
            Redaction.apply(
                "${Redaction.COOKIE_SECTION_HEADER}\nsid=abc123\ncsrf=deadbeef",
                policy,
                freshSalt(),
                recordMapping = false,
            )
        assertTrue(unterminated.contains("sid=[REDACTED]"), "first entry must be redacted; got '$unterminated'")
        assertTrue(
            unterminated.contains("csrf=[REDACTED]"),
            "a final entry with no trailing newline must still be redacted; got '$unterminated'",
        )

        // (c) A section terminated by the next section header rather than by the end of the text.
        val nextSection =
            Redaction.apply(
                "${Redaction.COOKIE_SECTION_HEADER}\nsid=abc123\n=== REQUEST ===\nkeep=this\n",
                policy,
                freshSalt(),
                recordMapping = false,
            )
        assertTrue(nextSection.contains("sid=[REDACTED]"), "the cookie entry must be redacted; got '$nextSection'")
        assertTrue(
            nextSection.contains("keep=this"),
            "the span must STOP at the next section header — content beyond it is not a cookie; got '$nextSection'",
        )
    }

    /** Unique per call, so tests never share the process-wide host mapping tables. */
    private fun freshSalt(): String = "gsd-26-03-${UUID.randomUUID()}"
}
