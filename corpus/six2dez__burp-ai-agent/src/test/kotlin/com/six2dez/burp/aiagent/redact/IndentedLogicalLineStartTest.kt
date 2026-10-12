package com.six2dez.burp.aiagent.redact

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * (PRIV-05) Phase 27 plan 27-17 — the FOURTH logical line start: a header line preceded by leading
 * horizontal whitespace, including an RFC 7230 obs-folded continuation line.
 *
 * WHAT THIS IS FOR.
 *
 * `AR-27-09` was filed OPEN at LOW in round 4 on a MEASURED survival: with the real-line branch of
 * `Redaction.logicalLineHeaderRule` anchored on a bare `^`, the shape
 * `GET / HTTP/1.1\r\n Cookie: a=SECRET5\r\n\r\n` came out of `Redaction.apply` BYTE-UNCHANGED under
 * `PrivacyMode.STRICT` and under `PrivacyMode.BALANCED`, while the un-indented control stripped to
 * `Cookie: [STRIPPED]` in the same run. Canonical `Cookie:` — no variant spelling and no unusual
 * character required. The LOW severity rested on a reachability argument that was explicitly
 * UNMEASURED, which is the defect class that reopened this phase five times, so the maintainer
 * decided the finding at UAT by FIX rather than by acceptance (`27-HUMAN-UAT.md` item 10).
 *
 * This file is the behavioural half of that closure. `LogicalLineBoundaryScopeTest` is the source
 * half: it reads `Redaction.kt` at test time and pins the start boundary's VALUE, so a revert to
 * `^` cannot ship green through a source scan either.
 *
 * WHAT IT ASSERTS, AND IN WHICH DIRECTION. Three things, deliberately in three groups:
 *
 *  1. POSITIVE — the indented shapes are now redacted, in BOTH redacting modes, for ALL THREE rules
 *     composed from the boundary (`cookieHeaderRegex`, `setCookieHeaderRegex`, `authHeaderRegex`).
 *  2. NON-VACUITY — the un-indented control still redacts, so a fixture that stopped matching for
 *     an unrelated reason cannot make group 1 pass by accident.
 *  3. NEGATIVE — indented NON-header content comes back BYTE-IDENTICAL. Widening a redaction rule
 *     is only a fix while it stays inside the header shape; a widening that started eating indented
 *     prose, pretty-printed JSON or indented source would be a content-destruction regression, which
 *     is precisely the failure `Redaction.kt`'s own rationale block records for the bare-quote start
 *     shipped at 27-11 (1589 of 1714 characters destroyed, all shape assertions still green).
 *
 * WHAT IT IS BOUNDED BY — read this before quoting it as evidence.
 *
 * It exercises `Redaction.apply` on hand-written shapes. It does NOT prove the boundary is complete:
 * `AR-27-10` (the thirteen uncovered RFC 9110 tchars) and `AR-27-11` (the four JSON-string-open
 * families) are open and untouched by this file. It says nothing about any header matcher outside
 * `redact/Redaction.kt`.
 *
 * NO ASSERTION HERE PINS A SENSITIVE VALUE AS SURVIVING A REDACTING POLICY. The negative gates are
 * byte-identity assertions over fixtures that carry NO credential at all — that is the whole reason
 * they are written with content that is inert rather than with a stripped-looking secret.
 */
class IndentedLogicalLineStartTest {
    @Test
    fun theIndentedCookieHeaderIsStrippedInBothRedactingModes() {
        forEachRedactingMode { mode ->
            val raw = "GET / HTTP/1.1\r\n Cookie: a=SECRET5\r\n\r\n"
            val out = redact(raw, mode)
            assertEquals(
                "GET / HTTP/1.1\r\n Cookie: [STRIPPED]\r\n\r\n",
                out,
                "the indented canonical `Cookie:` header is the shape AR-27-09 was filed on. It must " +
                    "now be stripped under $mode, and the ONE leading space must be re-emitted " +
                    "verbatim — the fix consumes the indent into the match, so a replacement that " +
                    "dropped it would silently rewrite the analyst's view of the traffic.",
            )
        }
    }

    @Test
    fun theIndentedSetCookieHeaderIsStrippedInBothRedactingModes() {
        forEachRedactingMode { mode ->
            val raw = "HTTP/1.1 200 OK\r\n\tSet-Cookie: s=SECRET6; Path=/\r\n\r\n"
            val out = redact(raw, mode)
            assertEquals(
                "HTTP/1.1 200 OK\r\n\tSet-Cookie: [STRIPPED]\r\n\r\n",
                out,
                "`setCookieHeaderRegex` shares the composer, so it must gain the fourth start with " +
                    "the other two under $mode. The indent here is a TAB rather than a space, because " +
                    "the boundary claims horizontal whitespace and a fix measured only on spaces " +
                    "would be a claim wider than its control.",
            )
        }
    }

    @Test
    fun theIndentedPlainTokenAuthHeaderIsRedactedInBothRedactingModes() {
        // X-Api-Key rather than Authorization, and this choice is load-bearing rather than
        // arbitrary. An indented `Authorization: Bearer …` line was ALREADY losing its token before
        // this fix — to `bearerRegex`, a VALUE-level rule, which rewrote it to
        // `Authorization: Bearer [REDACTED]` while the HEADER rule missed the line entirely. Measured
        // on the pre-fix classes. A gate built on `Authorization` would therefore have been green
        // before the fix and would have proved nothing. `X-Api-Key` has no second rule behind it.
        forEachRedactingMode { mode ->
            val raw = "GET / HTTP/1.1\r\n  X-Api-Key: SECRET8\r\n\r\n"
            val out = redact(raw, mode)
            assertEquals(
                "GET / HTTP/1.1\r\n  X-Api-Key: [REDACTED]\r\n\r\n",
                out,
                "`authHeaderRegex` is the third rule composed from the boundary and a plain-token " +
                    "auth header is the shape that isolates it under $mode — no bearer, basic or JWT " +
                    "rule can reach this value, so only the header rule can remove it.",
            )
        }
    }

    @Test
    fun theIndentedAuthorizationHeaderIsRedactedByTheHeaderRuleAndNotOnlyByTheValueRule() {
        // The masked-control case, pinned so the masking cannot come back unnoticed: BEFORE the fix
        // this input produced "Authorization: Bearer [REDACTED]" (bearerRegex), AFTER it produces
        // "Authorization: [REDACTED]" (authHeaderRegex). Asserting the WHOLE header is gone is what
        // distinguishes the two rules.
        forEachRedactingMode { mode ->
            val raw = "GET / HTTP/1.1\r\n Authorization: Bearer SECRET7\r\n\r\n"
            val out = redact(raw, mode)
            assertEquals(
                "GET / HTTP/1.1\r\n Authorization: [REDACTED]\r\n\r\n",
                out,
                "under $mode the indented `Authorization:` line must be replaced by the HEADER rule. " +
                    "`Authorization: Bearer [REDACTED]` here would mean the header rule still misses " +
                    "the line and only the value rule fired, which is the pre-fix state.",
            )
        }
    }

    @Test
    fun theObsFoldedContinuationLineIsARecognisedLogicalLineStart() {
        forEachRedactingMode { mode ->
            val raw = "GET / HTTP/1.1\r\nX-Foo: bar\r\n Cookie: a=SECRET9\r\n\r\n"
            val out = redact(raw, mode)
            assertEquals(
                "GET / HTTP/1.1\r\nX-Foo: bar\r\n Cookie: [STRIPPED]\r\n\r\n",
                out,
                "an RFC 7230 obs-folded continuation line IS a line start followed by horizontal " +
                    "whitespace, so it is bought by the same token. Under $mode it must be stripped " +
                    "with its preceding real header line left byte-intact.",
            )
        }
    }

    @Test
    fun theUnindentedControlsStillRedact() {
        // NON-VACUITY. If the composed rules stopped matching for a reason unrelated to the indent,
        // every negative gate below would pass for the wrong reason and the positives above would be
        // the only thing holding. These three are the shapes that shipped and worked before 27-17.
        forEachRedactingMode { mode ->
            assertEquals(
                "GET / HTTP/1.1\r\nCookie: [STRIPPED]\r\n\r\n",
                redact("GET / HTTP/1.1\r\nCookie: a=SECRET7\r\n\r\n", mode),
                "the un-indented `Cookie:` control must still strip under $mode",
            )
            assertEquals(
                "HTTP/1.1 200 OK\r\nSet-Cookie: [STRIPPED]\r\n\r\n",
                redact("HTTP/1.1 200 OK\r\nSet-Cookie: s=SECRET7; Path=/\r\n\r\n", mode),
                "the un-indented `Set-Cookie:` control must still strip under $mode",
            )
            assertEquals(
                "GET / HTTP/1.1\r\nX-Api-Key: [REDACTED]\r\n\r\n",
                redact("GET / HTTP/1.1\r\nX-Api-Key: SECRET8\r\n\r\n", mode),
                "the un-indented plain-token auth control must still redact under $mode",
            )
        }
    }

    @Test
    fun theWidenedStartDoesNotEatIndentedNonHeaderContent() {
        // THE OVER-REDACTION NEGATIVE. Byte-identity, not "the secret is gone" — because there is no
        // secret in any of these fixtures. Each one puts the word `cookie` on an INDENTED line in a
        // shape that is not a header, which is exactly the content a widened start would reach for.
        forEachRedactingMode { mode ->
            INDENTED_NON_HEADER_CORPUS.forEach { doc ->
                assertEquals(
                    doc,
                    redact(doc, mode),
                    "indented NON-header content must come back BYTE-IDENTICAL under $mode. The " +
                        "fourth start widens the boundary, and a widening that starts consuming " +
                        "indented prose, pretty-printed JSON or indented source is a " +
                        "content-destruction regression rather than a fix — the same failure this " +
                        "file's rationale records for the bare-quote start shipped at 27-11.",
                )
            }
        }
    }

    @Test
    fun theShippedAnchorsBehaviourIsPreservedWhereNoLineBeginsWithWhitespace() {
        // THE DIRECTION PROOF, half one — the CONTROL half, and it is deliberately its own test.
        //
        // `[ \t]*+` matches the empty string and no composed name pattern can begin with a space or a
        // tab, so wherever the shipped `^` matched there is no leading whitespace to consume and the
        // two spellings pick the same start position. The observable consequence is that a document
        // with NO line beginning in horizontal whitespace redacts exactly as it did before 27-17.
        //
        // These expectations were captured from the PRE-FIX classes. MUTATION-VERIFIED: this test
        // stays GREEN when `REAL_LINE_START` is reverted to `^`, which is what makes it a control
        // rather than a restatement of the fix. Keeping it separate from the half below is the whole
        // point — merged, its greenness under a revert would be invisible.
        forEachRedactingMode { mode ->
            UNINDENTED_CORPUS.forEach { (raw, expected) ->
                assertEquals(expected, redact(raw, mode), "pre-fix behaviour must be preserved under $mode for: $raw")
            }
        }
    }

    @Test
    fun theWideningAddsRedactionWithoutMovingTheSurroundingBytes() {
        // THE DIRECTION PROOF, half two — what the widening ADDS. A strict superset can only turn an
        // unchanged document into a redacted one, never the reverse, and it must do so without
        // disturbing anything outside the header it matched.
        val indented = "GET / HTTP/1.1\r\n Cookie: a=SECRET5\r\n\r\n"
        forEachRedactingMode { mode ->
            val out = redact(indented, mode)
            assertNotEquals(
                indented,
                out,
                "the added direction must be a REDACTION, so under $mode the indented shape cannot " +
                    "come back unchanged — that is the pre-fix state AR-27-09 recorded",
            )
            assertTrue(
                out.startsWith("GET / HTTP/1.1\r\n ") && out.endsWith("\r\n\r\n"),
                "under $mode the widening must ADD a replacement without moving the surrounding " +
                    "bytes: the request line, the indent that precedes the header name and the " +
                    "trailing blank line are all re-emitted verbatim. Read as: $out",
            )
        }
    }

    private fun forEachRedactingMode(block: (PrivacyMode) -> Unit) {
        listOf(PrivacyMode.STRICT, PrivacyMode.BALANCED).forEach(block)
    }

    private fun redact(
        raw: String,
        mode: PrivacyMode,
    ): String = Redaction.apply(raw, RedactionPolicy.fromMode(mode), SALT, recordMapping = false)

    private companion object {
        const val SALT = "indented-logical-line-start-salt"

        /**
         * Indented content that is NOT a header line, in the three shapes that actually reach
         * `Redaction.apply` in this repository: free prose in a tool result, pretty-printed JSON from
         * a captured response body, and source text. Every entry indents a line that CONTAINS the
         * token `cookie`, so a start that widened past the header shape would be caught here rather
         * than left to a reviewer.
         */
        val INDENTED_NON_HEADER_CORPUS =
            listOf(
                "notes:\r\n    We set a cookie policy here.\r\n    cookies are fine\r\n",
                "{\r\n    \"notes\": \"no header here\",\r\n    \"desc\": \"cookie handling\"\r\n}",
                "fun f() {\r\n    val cookieJar = mapOf(\"a\" to 1)\r\n    return cookieJar\r\n}",
                "  Cookie\r\n  policy\r\n",
                "changelog:\r\n  - cookie handling reworked\r\n  - set-cookie parsing fixed\r\n",
                // The two MUTATION-SENSITIVE entries. Every line above survives a start that
                // dropped the header shape entirely, so on their own they would be a decorative
                // negative. These two put a COLON-terminated `cookie` run on an indented line that
                // is NOT at the line start, so a start widened past horizontal whitespace — the
                // realistic wrong fix, `^[^:]*` or a dropped anchor — eats them and turns this gate
                // RED. Verified by mutation, not by reading.
                "log:\r\n    2026-08-26 cookie: refreshed\r\n",
                "  X-Trace-Id: abc\r\n  Note the cookie: policy applies here\r\n",
            )

        /**
         * Documents in which NO line begins with horizontal whitespace, paired with the output the
         * PRE-FIX classes produced for them. The pairing is the control for the direction claim.
         */
        val UNINDENTED_CORPUS =
            listOf(
                "GET / HTTP/1.1\r\nCookie: a=SECRET7\r\n\r\n" to "GET / HTTP/1.1\r\nCookie: [STRIPPED]\r\n\r\n",
                "{\"notes\":\"Cookie: a=SECRET1\\r\\nX: y\"}" to "{\"notes\":\"Cookie: [STRIPPED]\\r\\nX: y\"}",
                "plain text with no header at all\r\nand a second line\r\n" to
                    "plain text with no header at all\r\nand a second line\r\n",
                "cookie-consent-banner shown\r\n" to "cookie-consent-banner shown\r\n",
            )
    }
}
