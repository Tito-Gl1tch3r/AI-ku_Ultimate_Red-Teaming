package com.six2dez.burp.aiagent.scanner

import burp.api.montoya.http.message.params.HttpParameterType
import burp.api.montoya.http.message.params.ParsedHttpParameter
import com.six2dez.burp.aiagent.redact.PrivacyMode
import com.six2dez.burp.aiagent.redact.Redaction
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.kotlin.mock
import org.mockito.kotlin.whenever

// (PRIV-05 / PRIV-06) Wave 0 seam for Phase 21. doAnalysis itself needs a MontoyaApi, a backend
// session and ScanKnowledgeBase state, so the PRIV-05-relevant logic was extracted into
// PassiveAiScannerPrompts.kt. This file asserts SC1 (the emitted section shapes), SC2 (the parameter
// line's Montoya type suffix) and D-06 (redactScanMetadata really reaches Redaction.apply) against
// the REAL emitted blob rather than a hand-written string — the gap that let PRIV-05 ship.
// Plans 21-05 and 21-06 extend this file. It deliberately asserts no current leak behaviour: an
// assertion of the defect would have to be deleted a wave later, when the cookie rules land.

// Mirrors PARAM_VALUE_MAX_CHARS, private in PassiveAiScannerAnalysis.kt:26. Truncation stays at the
// call site, so the test must apply it exactly as doAnalysis does.
private const val PARAM_VALUE_MAX_CHARS = 200
private const val HOST_SALT = "phase-21-wave-0-salt"

// (PRIV-05) W-01: COOKIES_MAX_COUNT is NOT mirrored here. It used to be — a file-private copy of the
// literal 6 with a comment saying the real one was private — which made this the FOURTH copy of a
// number whose drift silently reopens PRIV-05. It is now internal in PassiveAiScannerAnalysis.kt and
// referenced directly from the same package, so a change to the shipped bound reaches this test
// instead of being shadowed by a stale duplicate. PARAM_VALUE_MAX_CHARS above is still mirrored
// because truncation genuinely stays at the call site and no redactor rule depends on it.

class PassiveAiScannerPromptRedactionTest {
    @BeforeEach
    fun clearCustomPatterns() {
        // Redaction is a singleton object: custom patterns set by another test class in the same JVM
        // would bleed in here. Under D-05 custom patterns apply even in OFF, so the byte-identity
        // assertion below is only meaningful with the list provably empty.
        Redaction.setCustomPatterns(emptyList())
    }

    @AfterEach
    fun clearCustomPatternsAfterEach() {
        // The @BeforeEach above only protects THIS class. offStillAppliesCustomPatterns configures a
        // pattern on the Redaction singleton that would otherwise bleed OUT into every later test
        // class in the shared JVM, so the list is cleared on the way out as well as on the way in.
        clearCustomPatterns()
    }

    @Test
    fun parameterLineShape_carriesTheMontoyaTypeSuffix() {
        val cookieParam = mock<ParsedHttpParameter>()
        whenever(cookieParam.type()).thenReturn(HttpParameterType.COOKIE)
        whenever(cookieParam.name()).thenReturn("JSESSIONID")
        whenever(cookieParam.value()).thenReturn("8F3A9C2B7E1D4A6F0B5C8E2D")

        val urlParam = mock<ParsedHttpParameter>()
        whenever(urlParam.type()).thenReturn(HttpParameterType.URL)
        whenever(urlParam.name()).thenReturn("q")
        whenever(urlParam.value()).thenReturn("red running shoes")

        // The type suffix comes from the real Montoya enum constant, never a hand-written string —
        // otherwise the test proves nothing about the shape the SC2 redaction rule keys on.
        assertEquals(
            "JSESSIONID=8F3A9C2B7E1D4A6F0B5C8E2D (COOKIE)",
            formatParamLine(cookieParam.name(), truncateWithEllipsis(cookieParam.value(), PARAM_VALUE_MAX_CHARS), cookieParam.type().name),
            "Cookie-typed parameters must render with the type suffix the cookie rule discriminates on",
        )
        assertEquals(
            "q=red running shoes (URL)",
            formatParamLine(urlParam.name(), truncateWithEllipsis(urlParam.value(), PARAM_VALUE_MAX_CHARS), urlParam.type().name),
            "A URL-typed parameter must carry its own suffix — the negative discriminator SC2 depends on",
        )
    }

    @Test
    fun buildScanMetadataText_emitsCookieAndParameterSections() {
        val cookieLines = listOf("JSESSIONID=SEED_A", "abtest_bucket=SEED_B")
        val paramLines = listOf("JSESSIONID=SEED_C (COOKIE)", "q=shoes (URL)")

        val blob = metadataBlob(cookies = cookieLines, params = paramLines)
        val lines = blob.lines()

        // Pins the emitter format that plan 21-05's section-scoped rule keys on.
        assertTrue(lines.contains("=== COOKIES ==="), "The cookie section header must be emitted verbatim on its own line")
        assertTrue(lines.contains("=== PARAMETERS ==="), "The parameter section header must be emitted verbatim on its own line")
        for (line in cookieLines) {
            assertTrue(lines.contains(line), "Cookie line '$line' must be emitted verbatim")
        }
        for (line in paramLines) {
            assertTrue(lines.contains(line), "Parameter line '$line' must be emitted verbatim")
        }
    }

    @Test
    fun redactScanMetadata_offModeIsByteIdentical() {
        val blob =
            metadataBlob(
                requestHeaders = listOf("Host: example.com", "User-Agent: burp-ai-agent-test"),
                cookies = listOf("JSESSIONID=SEED_A"),
                params = listOf("JSESSIONID=SEED_C (COOKIE)"),
            )

        // D-06 relies on the caller-side OFF branch having been behaviour-preserving: with no custom
        // patterns configured, RedactionPolicy.fromMode(OFF) leaves the blob untouched.
        assertEquals(
            blob,
            redactScanMetadata(blob, PrivacyMode.OFF, HOST_SALT),
            "OFF with no custom patterns must return the blob byte-identically",
        )
    }

    @Test
    fun redactScanMetadata_strictAnonymizesHosts() {
        val blob = metadataBlob(requestHeaders = listOf("Host: example.com"))

        val redacted = redactScanMetadata(blob, PrivacyMode.STRICT, HOST_SALT)

        // Proves the extracted seam really reaches Redaction.apply rather than returning its input.
        assertTrue(redacted.contains("Host: host-"), "STRICT must rewrite the Host header to the anonymized form")
        assertFalse(redacted.contains("Host: example.com"), "STRICT must not leave the real host in the Host header")
    }

    // (PRIV-05) SC1, end to end. Asserting only at the Redaction.apply level over a hand-written
    // blob would leave the emitter's exact format unasserted — and that unasserted gap is precisely
    // what let PRIV-05 ship. This test runs the REAL builder output through the REAL redaction step,
    // and asserts per cookie name rather than on the aggregate.
    @Test
    fun emittedCookieSectionValuesAreRedacted_sc1() {
        val cookieValues =
            mapOf(
                "JSESSIONID" to "8F3A9C2B7E1D4A6F0B5C8E2D",
                "PHPSESSID" to "abc123def456",
                "connect.sid" to "s%3ARZxYqL9.opaquevalue",
                "auth_token" to "secretvalue123",
                "csrftoken" to "abcdef",
                // Unreachable by the widened key expression from plan 21-04 — only the
                // section-scoped rule can save it, which is why both mechanisms are kept.
                "abtest_bucket" to "OPAQUE_VALUE_XYZ",
            )

        val blob = metadataBlob(cookies = cookieValues.map { (name, value) -> "$name=$value" })

        for (mode in listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED)) {
            val redacted = redactScanMetadata(blob, mode, HOST_SALT)
            for ((name, value) in cookieValues) {
                assertFalse(
                    redacted.contains(value),
                    "$mode: the emitted value of cookie '$name' must not survive redaction",
                )
                assertTrue(
                    redacted.lines().contains("$name=[REDACTED]"),
                    "$mode: cookie '$name' must keep its name in the emitted blob",
                )
            }
        }
    }

    // (PRIV-05) SC2, end to end. The parameter lines are built through formatParamLine and the REAL
    // HttpParameterType constants, never hand-written strings: the whole point is that the shape the
    // emitter produces and the shape the redaction rule keys on are the same object.
    //
    // abtest_bucket is the decisive line. JSESSIONID alone would pass even with the type-suffix rule
    // unwired, because the key expression from plan 21-04 already redacts it from the leading-field
    // position; an unremarkable cookie name is what the type suffix alone has to save.
    @Test
    fun emittedCookieTypedParametersAreRedacted_sc2() {
        val blob =
            metadataBlob(
                params =
                    listOf(
                        formatParamLine("JSESSIONID", "8F3A9C2B7E1D4A6F0B5C8E2D", HttpParameterType.COOKIE.name),
                        formatParamLine("abtest_bucket", "OPAQUE_PARAM_XYZ", HttpParameterType.COOKIE.name),
                        formatParamLine("q", "red running shoes", HttpParameterType.URL.name),
                        formatParamLine("quantity", "2", HttpParameterType.BODY.name),
                    ),
            )

        for (mode in listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED)) {
            val lines = redactScanMetadata(blob, mode, HOST_SALT).lines()

            assertTrue(
                lines.contains("JSESSIONID=[REDACTED] (COOKIE)"),
                "$mode: an emitted COOKIE-typed parameter keeps its name and its Montoya type suffix",
            )
            assertTrue(
                lines.contains("abtest_bucket=[REDACTED] (COOKIE)"),
                "$mode: the type suffix alone must save an unremarkably-named cookie parameter",
            )
            assertFalse(
                lines.any { it.contains("8F3A9C2B7E1D4A6F0B5C8E2D") || it.contains("OPAQUE_PARAM_XYZ") },
                "$mode: no emitted COOKIE-typed parameter value may reach the backend",
            )
            assertTrue(
                lines.contains("q=red running shoes (URL)"),
                "$mode: a URL-typed parameter line must survive byte-for-byte",
            )
            assertTrue(
                lines.contains("quantity=2 (BODY)"),
                "$mode: a BODY-typed parameter line must survive byte-for-byte",
            )
        }
    }

    // (PRIV-05 / T-21-20) The parity half of the shared-constant coupling, in the spirit of
    // McpToolParityTest.registeredToolIds_matchCatalog. The constant makes a RENAME of the section a
    // compile error; this assertion makes a silent FORMAT CHANGE around it a test failure, which is
    // the other way a section-scoped security control can be disabled without anyone noticing.
    @Test
    fun emittedBlobContainsTheSectionConstant_parity() {
        val blob = metadataBlob(cookies = listOf("JSESSIONID=SEED_A"))

        // Line-exact rather than String.contains, so a future edit that merges the header onto
        // another line fails here instead of passing on a substring match.
        assertTrue(
            blob.lines().contains(Redaction.COOKIE_SECTION_HEADER),
            "The emitted blob must carry the section header the redaction rule keys on, on its own line",
        )
    }

    // (PRIV-06) D-05 / D-06: custom patterns must apply under PrivacyMode.OFF, proven on a REAL
    // caller seam rather than only against Redaction.apply in isolation.
    //
    // This is what makes D-06's deleted caller-side short-circuits load-bearing: before this phase
    // the scanner tested `if (privacyMode == OFF) metadataText else Redaction.apply(...)`, so under
    // OFF the engine was never entered and a configured custom pattern could not fire no matter
    // what the engine did. Asserting only on Redaction.apply would leave exactly that gap
    // unasserted — the same class of gap that let PRIV-05 ship.
    //
    // The value is attributable to the custom pattern and to nothing else: OFF sets stripCookies,
    // redactTokens and anonymizeHosts all false, so every built-in rule is inert, and 'leaked' is
    // not a sensitive key name in any case.
    @Test
    fun offStillAppliesCustomPatterns() {
        Redaction.setCustomPatterns(listOf("\\bOFF-CUSTOM-[A-Z0-9]{6}\\b"))

        val blob = metadataBlob(responseBody = "leaked=OFF-CUSTOM-A1B2C3")
        val redacted = redactScanMetadata(blob, PrivacyMode.OFF, HOST_SALT)

        assertFalse(
            redacted.contains("OFF-CUSTOM-A1B2C3"),
            "OFF: a user's custom pattern is a 'never send this' list and must still redact",
        )
        assertTrue(
            redacted.contains("[REDACTED]"),
            "OFF: the custom-pattern replacement must appear in the emitted blob",
        )
    }

    // (PRIV-05) CR-01, SECOND TRIGGER / T-21-32, end to end. A cookie element that is itself shaped
    // like a section header terminates the redactor's cookie span, and every cookie below it leaks.
    // The redactor provably cannot close this on its own: the span terminator is derived from
    // content INSIDE the region the rule protects, which is in-band signalling, and simply refusing
    // to terminate on "=== " would let the cookie span swallow "=== PARAMETERS ===" and everything
    // after it. So it is closed at the emitter, via the redact/-owned
    // Redaction.sanitizeCookieSectionEntries. RedactionTest's
    // cookieSectionHeaderShapedEntryTerminatesSpan_documentedResidual pins the redactor-level
    // behaviour and stays green before and after; THIS test is the one that proves the combined
    // pipeline is closed, so it is the named guard for the sanitizer call.
    //
    // abtest_bucket=OPAQUE_VALUE_XYZ is the load-bearing sentinel and MUST NOT be swapped for a
    // more obviously sensitive name. Reachability, in the style of the note at RedactionTest:670:
    // the tokens 'abtest' and 'bucket' belong to neither SENSITIVE_WORDS nor KNOWN_SESSION_KEYS, so
    // SENSITIVE_KEY_EXPR and its three consumers (urlTokenParamRegex, formBodyParamRegex,
    // jsonSecretKeyRegex) cannot reach the line; it carries no " (COOKIE)" suffix, so
    // cookieTypedParamRegex cannot; it has no Cookie:/Set-Cookie:/Host:/auth-header prefix, no
    // Bearer or Basic prefix, no eyJ JWT shape and no '?' or '&' before the key, so no other
    // header-stage rule can either; the value contains no '=' and sits in no JSON pair; and
    // @BeforeEach clears the custom patterns. ONLY the section-scoped rule can redact it.
    //
    // Swapping the sentinel for a name the key expression already covers would make this test pass
    // with the defect fully present. JSESSIONID is exactly such a name — it is asserted here as a
    // deliberately NON-decisive companion, because formBodyParamRegex redacts it from the leading
    // field position even with the section rule completely broken. That substitution is the mistake
    // two earlier tests in this phase made, and it is why a live cookie leak shipped underneath 628
    // green tests.
    @Test
    fun poisonedCookieHeaderCannotTerminateTheCookieSection() {
        val blob =
            metadataBlob(
                cookies =
                    listOf(
                        "",
                        "JSESSIONID=REALSECRET",
                        "=== FOO ===",
                        "abtest_bucket=OPAQUE_VALUE_XYZ",
                    ),
            )

        // Asserted before the behaviour so a future emitter change that drops the section entirely
        // cannot silently defuse the assertions below into vacuous truths.
        assertTrue(
            blob.lines().contains(Redaction.COOKIE_SECTION_HEADER),
            "Fixture: the blob under test must really carry a cookie section",
        )

        for (mode in listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED)) {
            val redacted = redactScanMetadata(blob, mode, HOST_SALT)

            assertFalse(
                redacted.contains("OPAQUE_VALUE_XYZ"),
                "$mode: a cookie element shaped like a section header must not let the value of " +
                    "'abtest_bucket' reach the backend",
            )
            assertFalse(
                redacted.contains("REALSECRET"),
                "$mode: the cookie above the planted header must stay redacted too",
            )
            assertTrue(
                redacted.lines().contains("abtest_bucket=[REDACTED]"),
                "$mode: the cookie NAME must survive — the section rule redacts values, not lines",
            )
        }
    }

    // (PRIV-05) CR-01 / T-21-20: the STRUCTURAL half, asserted on the UNREDACTED emitter output.
    // poisonedCookieHeaderCannotTerminateTheCookieSection could in principle be satisfied by some
    // unrelated redaction change; this one can only be satisfied by the section framing itself being
    // unforgeable, which is the actual control. It also pins "neutralised" rather than "dropped": a
    // future change that silently discarded a section-shaped entry would lose analytic content and
    // fails here.
    @Test
    fun cookieSectionEntriesAreSanitizedAtTheEmitter() {
        val blob =
            metadataBlob(
                cookies =
                    listOf(
                        "",
                        "JSESSIONID=REALSECRET",
                        "=== FOO ===",
                        "abtest_bucket=OPAQUE_VALUE_XYZ",
                    ),
                // A following section makes the span's real terminator explicit, and is the content
                // that the poisoned entry would otherwise pull inside the cookie span.
                params = listOf("q=red running shoes (URL)"),
            )

        val lines = blob.lines()
        val headerIndex = lines.indexOf(Redaction.COOKIE_SECTION_HEADER)
        assertTrue(headerIndex >= 0, "Fixture: the cookie section header must be emitted on its own line")

        // Sliced with the SAME predicate the redactor's span walk uses — a raw startsWith on the
        // NEXT_SECTION_PREFIX "=== " at a line start, never a trimmed one — so this test and
        // Redaction.cookieSectionEnd agree byte for byte on what a section boundary is.
        val body = lines.drop(headerIndex + 1)
        val nextSection = body.indexOfFirst { it.startsWith("=== ") }
        val section = if (nextSection >= 0) body.take(nextSection) else body

        // The emitter closes the section with one appendLine(); that trailing blank is FRAMING, not
        // an entry, and its byte-identical shape is contractual. Everything before it is the entry
        // list. Split this way rather than "slice to the first blank line" so that a blank sitting
        // BETWEEN two entries still surfaces as a failure instead of silently ending the slice.
        val entries = section.dropLastWhile { it.isBlank() }
        val framingBlanks = section.size - entries.size

        assertFalse(
            entries.any { it.isBlank() },
            "No blank line may sit between cookie entries: a blank consumes a display slot and used " +
                "to collapse the redaction span",
        )
        assertFalse(
            entries.any { it.startsWith("===") },
            "No cookie entry may be shaped like a section header — that is the forged framing " +
                "T-21-32 is about",
        )
        assertTrue(
            entries.any { it.contains("=== FOO ===") },
            "The section-shaped entry must be NEUTRALISED, not dropped: a leading space is the " +
                "expected shape, so the value still reaches the analysis and is still redacted",
        )
        assertEquals(
            1,
            framingBlanks,
            "The cookie section must close with exactly one framing blank line before the next section",
        )
    }

    // (PRIV-05) CR-01 / T-21-06: the PRODUCER. Asserts cookieSectionLines, the real chain doAnalysis
    // calls, rather than a copy of it pasted into the test — a copy would have to include the
    // sanitize call in order to be written at all, and would therefore stay green no matter what the
    // production code did. That is the vacuity trap this phase keeps walking into.
    //
    // ORDERING IS THE WHOLE POINT: sanitising must happen BEFORE take(maxCount). Sanitising after
    // would leave the two blank elements holding display slots, so "Cookie: ;;a=1; b=2; ..." would
    // surface four real cookies to the model where six were available.
    @Test
    fun blankCookieElementsDoNotConsumeDisplaySlots() {
        val lines = cookieSectionLines(listOf(";;a=1; b=2; c=3; d=4; e=5; f=6; g=7"), COOKIES_MAX_COUNT)

        assertEquals(COOKIES_MAX_COUNT, lines.size, "The producer must still surface a full six cookie lines")
        assertFalse(lines.any { it.isBlank() }, "A blank element must not consume one of the six display slots")
        assertEquals(
            listOf("a=1", "b=2", "c=3", "d=4", "e=5", "f=6"),
            lines,
            "The six surfaced cookies must be the first six REAL elements, in order",
        )
    }

    private fun metadataBlob(
        requestHeaders: List<String> = listOf("User-Agent: burp-ai-agent-test"),
        cookies: List<String> = emptyList(),
        params: List<String> = emptyList(),
        responseBody: String = "",
    ): String =
        buildScanMetadataText(
            kbSummary = null,
            displayUrl = "http://example.com/search",
            urlPath = "/search",
            method = "GET",
            statusCode = 200,
            mimeType = "HTML",
            potentialIds = emptyList(),
            requestHeaders = requestHeaders,
            responseHeaders = listOf("Content-Type: text/html"),
            authHeaders = emptyList(),
            cookies = cookies,
            params = params,
            requestBody = "",
            responseBody = responseBody,
        )
}
