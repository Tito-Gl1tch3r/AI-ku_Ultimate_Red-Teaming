package com.six2dez.burp.aiagent.redact

import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

// (PRIV-05) Phase 27 plan 27-02. WHAT THIS FILE IS FOR: the v0.10.0 milestone audit found the
// prompt path (Redaction.apply's two cookie regexes) and the MCP tool-RESULT path
// (McpToolHelpers.sanitizeHeaders) disagreeing about what a cookie header is CALLED — the prompt
// path matched name-contains-"cookie" while the tool-result path compared against the two canonical
// spellings — and nothing in the repository was able to notice. Plan 27-01 made the two paths agree
// by promoting the rule to Redaction.isCookieHeaderName. This file is the mechanism that keeps them
// agreeing: it asserts, behaviourally, that every header name the prompt path strips is a name the
// shared predicate also matches, so a future one-sided widening fails a test instead of shipping.
//
// DIRECTION, stated once so it cannot be misread. The invariant is
//   promptStrips(N)  =>  isCookieHeaderName(N)
// and ONLY that direction. The converse must NEVER be asserted here, and the reason is about which
// repair a red test would provoke: asserting it would create pressure to NARROW the predicate, and
// narrowing the predicate shrinks what McpToolHelpers.sanitizeHeaders strips on the MCP path —
// the exact direction that reopens this phase's gap. When the two sides disagree, the repair is
// always to WIDEN the regex side.
//
// WHAT THE GAP BETWEEN THE TWO SIDES IS NOW, corrected by plan 27-10. It used to be the underscore
// class: COOKIE_NAME_PART was [A-Za-z0-9-]* (the PRE-FIX value, quoted here as history), my_cookie
// was a predicate-only corpus entry, and this file asserted its value SURVIVED STRICT. That was not
// a benign asymmetry. isCookieHeaderName has three consumers and one of them —
// PassiveAiScannerFilters.sanitizeHeadersForPrompt — is an ADMITTER, so a name the predicate claims
// and the regexes cannot match is put on the outbound prompt and never stripped: fail-OPEN, not
// fail-safe. Plan 27-10 widened the class to [A-Za-z0-9_-]* and inverted the assertion.
//
// The REMAINING gap, and the honest example to reason from: a header name carrying one of the
// thirteen RFC 9110 tchars still outside the widened class (! # $ % & ' * + . ^ ` | ~). Those are
// enumerated in source by CookieHeaderNameWidthTest.NOT_COVERED_TCHARS and filed as AR-27-10. Where
// the predicate is wider than the regexes it is fail-safe ONLY for the two REDACTING consumers; for
// the admitting one it is fail-open, which is why the residual is filed rather than dismissed.
//
// WHICH GUARD COVERS WHICH MUTATION (measured by plan 27-02's red probes 1 and 2, not assumed).
// Each bullet names its test, because plan 27-10 added a second behavioural test to this file and
// an unqualified "this test" no longer identifies one:
//   - a NARROWING of Redaction.isCookieHeaderName turns
//     everyNameThePromptPathStripsIsMatchedByTheSharedPredicate red (probe 1);
//   - a NARROWING of either prompt-path regex leaves that same implication test GREEN — shrinking an
//     implication's antecedent cannot falsify it — and is caught instead by
//     RedactionTest.cookieHeaderNameVariantsAreStripped (probe 2);
//   - a narrowing of COOKIE_NAME_PART specifically back off the underscore class turns
//     theUnderscoreNameClassIsStrippedByBothTheRegexesAndThePredicate red (plan 27-10's red probe),
//     which is the one mutation the implication test structurally cannot see.
//
// FIXTURE REACHABILITY, following the same discipline as RedactionTest's comment block above
// cookieHeaderNameVariantsAreStripped. Every sentinel is a bare lowercase alphabetic word on an
// unquoted header line: no '=' (formBodyParamRegex, urlTokenParamRegex and cookieTypedParamRegex all
// need one), no quotes (jsonSecretKeyRegex needs them), no Bearer/Basic prefix and no dotted eyJ
// segment (bearerRegex, basicAuthRegex, jwtRegex), and no "=== COOKIES ===" header
// (redactCookieSections never runs). SENSITIVE_KEY_EXPR is only ever consulted as a KEY immediately
// followed by '=' or inside quotes, so it cannot reach a sentinel here either. A cookie header rule
// is therefore the only thing in the pipeline that can remove one.
//
// FOUR HEADER NAMES ARE DELIBERATELY EXCLUDED FROM THE CORPUS, each because a DIFFERENT redaction
// rule claims it — including them would make the implication fail for a reason that has nothing to
// do with cookies:
//   - Authorization        — claimed by Redaction.authHeaderRegex (its first alternative).
//   - Proxy-Authorization  — claimed by Redaction.authHeaderRegex (its second alternative).
//   - X-API-Key            — claimed by Redaction.authHeaderRegex (its x-api-key alternative).
//   - Host                 — claimed by Redaction.hostHeaderRegex, which rewrites the value under a
//                            host-anonymising policy.
// For each of the four, promptStrips(N) would be true while isCookieHeaderName(N) is false.
//
// This file uses NO reflection and does not widen the visibility of cookieHeaderRegex or
// setCookieHeaderRegex. Those stay private, and the assertion goes through Redaction.apply's
// observable output — the behaviour that actually ships.

// The parity corpus: header name -> its own unique sentinel value. Both polarities are present, and
// parityCorpusIsNonEmptyAndContainsBothPolarities asserts that fact so the two tests below cannot
// pass vacuously over an empty or one-sided list.
private val PARITY_CORPUS: List<Pair<String, String>> =
    listOf(
        // cookie-positive: predicate true AND the prompt path strips the value
        "Cookie" to "sentinelparitycookiebare",
        "Set-Cookie" to "sentinelparitysetcookiebare",
        "COOKIE" to "sentinelparitycookieupper",
        "set-cookie" to "sentinelparitysetcookielower",
        "Cookie2" to "sentinelparitycookietwo",
        "X-Cookie" to "sentinelparityxcookie",
        "Set-Cookie2" to "sentinelparitysetcookietwo",
        "X-Original-Cookie" to "sentinelparityoriginalcookie",
        "X-Forwarded-Cookie" to "sentinelparityforwardedcookie",
        "Cookie-Consent" to "sentinelparitycookieconsent",
        "X-Cookie-Policy" to "sentinelparitycookiepolicy",
        // (PRIV-05) 27-10: the underscore class. These three were predicate-only until plan 27-10
        // widened COOKIE_NAME_PART to admit '_', and my_cookie was measured leaking under STRICT and
        // BALANCED. Each carries its OWN sentinel so a partial fix cannot hide behind a shared value.
        "my_cookie" to "sentinelparityunderscorecookie",
        "X_Cookie" to "sentinelparityunderscoreprefixed",
        "session_cookie" to "sentinelparityunderscoresession",
        // cookie-negative: predicate false AND the prompt path leaves the value alone
        "X-Request-Id" to "sentinelparityrequestid",
        "X-Cook" to "sentinelparityxcook",
        "Cook-ie" to "sentinelparitycookiehyphen",
        "Accept" to "sentinelparityaccept",
        "Content-Type" to "sentinelparitycontenttype",
    )

// FLOORS, not counts. Each is deliberately BELOW the measured actual so it catches a SHRINKING
// corpus rather than becoming a number to maintain. Measured at plan 27-10: 19 entries, 14
// predicate-positive, 5 predicate-negative.
private const val MIN_CORPUS_SIZE = 18 // actual 19
private const val MIN_PREDICATE_POSITIVES = 12 // actual 14
private const val MIN_PREDICATE_NEGATIVES = 4 // actual 5

// An EXACT count, not a floor: these three names are the measured underscore class, and each one is
// evidence in its own right. A floor would let one be dropped silently.
private const val EXPECTED_UNDERSCORE_NAMES = 3
private const val PARITY_HOST_SALT = "phase-27-plan-02-parity-salt"

class CookieHeaderNameParityTest {
    @BeforeEach
    fun clearCustomPatterns() {
        // Redaction is a singleton object: a custom pattern left behind by another test class in the
        // same JVM could remove a sentinel for the wrong reason, letting promptStrips report true
        // without any cookie rule having run. Precedent: PassiveAiScannerPromptRedactionTest.
        Redaction.setCustomPatterns(emptyList())
    }

    @AfterEach
    fun clearCustomPatternsAfterEach() {
        // The @BeforeEach only protects THIS class; clearing on the way out as well keeps this file
        // from becoming the source of the same bleed it defends against.
        clearCustomPatterns()
    }

    // Runs as its own test so the two below cannot pass over an empty or one-sided corpus — a
    // forEach over an empty list is a passing test about nothing (Phase 23 recorded exactly that
    // failure class). Red probe 3 of plan 27-02 (isCookieHeaderName widened to return true
    // unconditionally) turns the negatives clause below red, which is what proves this guard is
    // load-bearing rather than decorative.
    @Test
    fun parityCorpusIsNonEmptyAndContainsBothPolarities() {
        val names = PARITY_CORPUS.map { it.first }
        val sentinels = PARITY_CORPUS.map { it.second }

        assertTrue(
            names.size >= MIN_CORPUS_SIZE,
            "the parity corpus must hold at least $MIN_CORPUS_SIZE names (got ${names.size})",
        )
        assertTrue(
            names.size == names.toSet().size,
            "corpus header names must be distinct (got: $names)",
        )
        assertTrue(
            sentinels.size == sentinels.toSet().size,
            "each corpus name needs its OWN sentinel, or an absence assertion can be satisfied by another name's rule",
        )

        val positives = names.filter { Redaction.isCookieHeaderName(it) }
        val negatives = names.filterNot { Redaction.isCookieHeaderName(it) }

        assertTrue(
            positives.size >= MIN_PREDICATE_POSITIVES,
            "at least $MIN_PREDICATE_POSITIVES corpus names must satisfy the predicate (got ${positives.size}: $positives)",
        )
        assertTrue(
            negatives.size >= MIN_PREDICATE_NEGATIVES,
            "at least $MIN_PREDICATE_NEGATIVES corpus names must NOT satisfy the predicate — a predicate " +
                "widened to always-true makes the parity implication trivially true " +
                "(got ${negatives.size}: $negatives)",
        )
    }

    // THE INVARIANT. For each corpus name N under STRICT and BALANCED: if the prompt path removed
    // N's value, the shared predicate must also claim N. A widening applied to the prompt path and
    // forgotten in the predicate turns this red, naming the offending header.
    @Test
    fun everyNameThePromptPathStripsIsMatchedByTheSharedPredicate() {
        for (mode in listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED)) {
            for ((name, sentinel) in PARITY_CORPUS) {
                val output = redactHeaderBlob(mode, name, sentinel)
                val promptStrips = !output.contains(sentinel)
                val predicate = Redaction.isCookieHeaderName(name)

                if (promptStrips) {
                    assertTrue(
                        predicate,
                        "$mode: the prompt path strips '$name' but Redaction.isCookieHeaderName('$name') is " +
                            "false. The two redaction paths have drifted apart again: whatever widened the " +
                            "prompt-path cookie rule was not mirrored into the shared predicate, so the MCP " +
                            "tool-result path will emit this header's value verbatim (output: $output)",
                    )
                    // T-21-WA2: the prompt path keeps the header's OWN name rather than renaming it
                    // to the canonical spelling. A fixed replacement string would rewrite
                    // "X-Cookie: v" into "Cookie: [STRIPPED]" and silently relabel traffic.
                    assertTrue(
                        output.contains("$name: [STRIPPED]"),
                        "$mode: '$name' must keep its own name when stripped, not be renamed (output: $output)",
                    )
                }
            }
        }
    }

    // (PRIV-05) plan 27-10. The underscore name class, asserted in the SAFE direction. Before this
    // plan COOKIE_NAME_PART was [A-Za-z0-9-]*, which excludes '_', and this same fixture asserted
    // that my_cookie's value SURVIVED STRICT — a green test pinning a cookie disclosure. The
    // assertion is INVERTED rather than deleted, so the corpus entry keeps carrying its measurement.
    //
    // It covers ALL THREE measured underscore names rather than my_cookie alone, and that is
    // load-bearing rather than thorough: the implication test above is one-directional, so a
    // NARROWING of COOKIE_NAME_PART leaves it green (shrinking an antecedent cannot falsify an
    // implication). This is the only test in the file that a re-narrowing turns red, so a name absent
    // from HERE is a name no failing test covers, however many corpus entries it has.
    @Test
    fun theUnderscoreNameClassIsStrippedByBothTheRegexesAndThePredicate() {
        val underscoreNames = PARITY_CORPUS.filter { it.first.contains('_') }

        // Non-vacuity: a forEach over an empty or shrunken list is a passing test about nothing, and
        // deleting these entries is the exact tampering T-27-10-04 names.
        assertTrue(
            underscoreNames.size == EXPECTED_UNDERSCORE_NAMES,
            "the corpus must hold all $EXPECTED_UNDERSCORE_NAMES measured underscore names — each was " +
                "observed leaking under STRICT and BALANCED before plan 27-10 widened COOKIE_NAME_PART " +
                "(got ${underscoreNames.map { it.first }})",
        )

        for ((name, sentinel) in underscoreNames) {
            assertTrue(
                Redaction.isCookieHeaderName(name),
                "the shared predicate is a bare contains() and must match '$name'",
            )

            for (mode in listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED)) {
                val output = redactHeaderBlob(mode, name, sentinel)
                assertFalse(
                    output.contains(sentinel),
                    "$mode: the value of '$name' SURVIVED a redacting policy. '_' is a legal RFC 9110 tchar, " +
                        "so this is a real header name, and PassiveAiScannerFilters.sanitizeHeadersForPrompt " +
                        "ADMITS it into the outbound passive-scan prompt PRECISELY BECAUSE the shared predicate " +
                        "claims it. A value surviving here is therefore a cookie disclosure to a third-party AI " +
                        "backend, not an intended asymmetry. FIX THE DIRECTION THAT IS SAFE: widen " +
                        "COOKIE_NAME_PART so the two regexes reach every name the predicate admits. NEVER narrow " +
                        "the predicate to restore symmetry — that shrinks what McpToolHelpers.sanitizeHeaders " +
                        "strips on the MCP path, which is the direction that reopened this phase (output: $output)",
                )
                assertTrue(
                    output.contains("$name: [STRIPPED]"),
                    "$mode: '$name' must be rewritten to the stripped form and must keep its OWN name rather " +
                        "than be renamed to the canonical spelling (output: $output)",
                )
            }
        }
    }

    // One corpus header line per invocation, so a sentinel can only be removed by a rule that claims
    // THAT name. The Host line is fixture scaffolding, not a corpus entry — see the exclusion list in
    // this file's header for why Host is not measured here.
    private fun redactHeaderBlob(
        mode: PrivacyMode,
        name: String,
        sentinel: String,
    ): String {
        val blob = "GET / HTTP/1.1\nHost: example.com\n$name: $sentinel\n"
        return Redaction.apply(blob, RedactionPolicy.fromMode(mode), stableHostSalt = PARITY_HOST_SALT)
    }
}
