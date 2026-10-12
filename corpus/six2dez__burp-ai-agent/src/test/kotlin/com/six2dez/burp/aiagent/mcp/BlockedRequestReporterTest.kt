package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.audit.AuditLogger
import com.six2dez.burp.aiagent.audit.Hashing
import io.ktor.http.HttpStatusCode
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.concurrent.CopyOnWriteArrayList

private const val FOREIGN_ORIGIN = "http://evil.example"
private const val T0 = 1_000_000L
private const val T_INSIDE_WINDOW = 1_010_000L
private const val T_AFTER_WINDOW = 1_061_000L
private const val T_AFTER_AGGREGATE = 1_062_000L

/**
 * D-06 / D-07 / D-09 / D-10 coverage for blocked-request observability.
 *
 * The clock is injected through `report(..., nowMs)` and the Output sink is a lambda, so every
 * window assertion is exact and nothing here sleeps or binds a port.
 */
class BlockedRequestReporterTest {
    private val lines = CopyOnWriteArrayList<String>()

    // The emitter fires on the caller's thread (a Netty event-loop thread in production) and is read
    // from the JUnit thread, so the capture list must be concurrent. The payload type is `Any`, not
    // `Map<String, Any?>` — AuditLogger.kt:20 declares `((String, Any) -> Unit)?`.
    private val captured = CopyOnWriteArrayList<Pair<String, Any>>()

    @BeforeEach
    fun registerCapturingEmitter() {
        lines.clear()
        captured.clear()
        AuditLogger.registerGlobalEmitter { type, payload -> captured += type to payload }
    }

    @AfterEach
    fun clearGlobalEmitter() {
        // globalEmitter is a @Volatile companion field — leaving it registered leaks into other
        // test classes running in the same JVM.
        AuditLogger.registerGlobalEmitter(null)
    }

    // ---------------------------------------------------------------------------------------
    // D-06 — audit event on every block, with the agreed payload shape
    // ---------------------------------------------------------------------------------------

    @Test
    fun report_emitsExactlyOneTransportBlockedEventPerInvocation() {
        reporter().report(denyOrigin(), externalMode = false, nowMs = T0)

        assertEquals(1, captured.size)
        assertEquals("mcp_transport_blocked", captured[0].first)
        assertEquals(
            listOf("reason", "mode", "method", "path", "origin", "host", "referer", "userAgent"),
            payloadAt(0).keys.toList(),
        )
    }

    @Test
    fun report_payloadCarriesWireReasonAndLocalMode() {
        reporter().report(denyOrigin(), externalMode = false, nowMs = T0)

        assertEquals("origin_mismatch", payloadAt(0)["reason"])
        assertEquals("local", payloadAt(0)["mode"])
    }

    @Test
    fun report_payloadCarriesExternalModeAndUnauthorizedReason() {
        val deny =
            GateDecision.Deny(
                HttpStatusCode.Unauthorized,
                BlockReason.UNAUTHORIZED,
                RequestFacts(method = "POST", path = "/message"),
            )

        reporter().report(deny, externalMode = true, nowMs = T0)

        assertEquals("unauthorized", payloadAt(0)["reason"])
        assertEquals("external", payloadAt(0)["mode"])
        assertEquals("POST", payloadAt(0)["method"])
        assertEquals("/message", payloadAt(0)["path"])
    }

    @Test
    fun report_emitsAuditEventEvenWhenTheOutputLineIsSuppressed() {
        val reporter = reporter()

        reporter.report(denyOrigin(), externalMode = false, nowMs = T0)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)

        // D-09 rate-limits the Output tab only; D-06 requires an audit event on every occurrence.
        assertEquals(1, lines.size)
        assertEquals(3, captured.size)
    }

    // ---------------------------------------------------------------------------------------
    // D-10 — hashing by default, plaintext only behind the verboseAudit seam
    // ---------------------------------------------------------------------------------------

    @Test
    fun report_hashesReflectedHeaderValuesByDefault() {
        reporter(verboseAudit = false).report(denyOrigin(), externalMode = false, nowMs = T0)

        assertEquals(Hashing.sha256Hex(FOREIGN_ORIGIN), payloadAt(0)["origin"])
    }

    @Test
    fun report_emitsPlaintextReflectedValuesWhenVerboseAuditIsOn() {
        reporter(verboseAudit = true).report(denyOrigin(), externalMode = false, nowMs = T0)

        assertEquals(FOREIGN_ORIGIN, payloadAt(0)["origin"])
    }

    @Test
    fun report_leavesAbsentHeadersNullRatherThanHashingTheEmptyString() {
        reporter(verboseAudit = false).report(denyOrigin(), externalMode = false, nowMs = T0)

        assertNull(payloadAt(0)["host"])
        assertNull(payloadAt(0)["referer"])
        assertNull(payloadAt(0)["userAgent"])
        assertFalse(payloadAt(0).containsValue(Hashing.sha256Hex("")))
    }

    // ---------------------------------------------------------------------------------------
    // D-07 — sanitization before either sink (CWE-117)
    // ---------------------------------------------------------------------------------------

    @Test
    fun report_stripsCarriageReturnAndLineFeedFromTheOutputLine() {
        reporter().report(denyOrigin("a\r\nInjected: line"), externalMode = false, nowMs = T0)

        val line = lines.single()
        assertFalse(line.contains('\r'), "CR survived into the Output tab: $line")
        assertFalse(line.contains('\n'), "LF survived into the Output tab: $line")
        assertEquals("aInjected: line", originFieldOf(line))
    }

    @Test
    fun report_stripsAnsiEscapeAndOtherControlCharacters() {
        // ESC (0x1B), BEL (0x07) and a C1 control (0x85 NEL) must all be removed. The surviving
        // "[31m" is inert text once the ESC introducer is gone.
        reporter().report(denyOrigin("a\u001B[31mb\u0007c\u0085d"), externalMode = false, nowMs = T0)

        val origin = originFieldOf(lines.single())
        assertEquals("a[31mbcd", origin)
        assertFalse(origin.any { it.isISOControl() }, "a control character survived: $origin")
    }

    @Test
    fun report_truncatesOverlongHeaderValuesWithAnEllipsis() {
        reporter().report(denyOrigin("a".repeat(900)), externalMode = false, nowMs = T0)

        val origin = originFieldOf(lines.single())
        assertEquals(203, origin.length)
        assertTrue(origin.endsWith("..."), "expected an ellipsis suffix but was: $origin")
    }

    @Test
    fun report_sanitizesTheAuditPayloadBeforeHashing() {
        reporter(verboseAudit = true).report(denyOrigin("a\r\nInjected: line"), externalMode = false, nowMs = T0)

        assertEquals("aInjected: line", payloadAt(0)["origin"])
    }

    // ---------------------------------------------------------------------------------------
    // D-09 — per-reason 60 s window with an aggregate count
    // ---------------------------------------------------------------------------------------

    @Test
    fun report_logsTheFirstBlockForAReasonImmediately() {
        reporter().report(denyOrigin(), externalMode = false, nowMs = T0)

        val line = lines.single()
        assertTrue(line.contains("origin_mismatch"), line)
        assertTrue(line.contains(FOREIGN_ORIGIN), line)
    }

    @Test
    fun report_suppressesFurtherBlocksInsideTheWindow() {
        val reporter = reporter()

        reporter.report(denyOrigin(), externalMode = false, nowMs = T0)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)

        assertEquals(1, lines.size)
    }

    @Test
    fun report_emitsAnAggregateCountOnceTheWindowElapses() {
        val reporter = reporter()

        reporter.report(denyOrigin(), externalMode = false, nowMs = T0)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_AFTER_WINDOW)

        assertEquals(2, lines.size)
        assertEquals("[McpAccessControl] 2 further blocks for origin_mismatch in the last 60s", lines[1])
    }

    @Test
    fun report_resetsTheSuppressedCounterAfterTheAggregateLine() {
        val reporter = reporter()

        reporter.report(denyOrigin(), externalMode = false, nowMs = T0)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_AFTER_WINDOW)
        reporter.report(denyOrigin(), externalMode = false, nowMs = T_AFTER_AGGREGATE)

        // The fifth block falls inside the new window, so it is counted and not printed.
        assertEquals(2, lines.size)
    }

    @Test
    fun report_windowsArePerReasonNotGlobal() {
        val reporter = reporter()
        val denyHost =
            GateDecision.Deny(
                HttpStatusCode.Forbidden,
                BlockReason.HOST_MISMATCH,
                RequestFacts(path = "/message", host = "evil.example"),
            )

        reporter.report(denyOrigin(), externalMode = false, nowMs = T0)
        reporter.report(denyHost, externalMode = false, nowMs = T_INSIDE_WINDOW)

        assertEquals(2, lines.size)
        assertTrue(lines[1].contains("host_mismatch"), lines[1])
    }

    // ---------------------------------------------------------------------------------------
    // ADR-13 — the audit sink coalesces the two pre-authentication reasons only
    //
    // `unauthorized` and `blank_token` are the only reasons an unauthenticated remote peer can
    // trigger (in external mode every route but /__mcp/health answers 401), so they are the
    // flood-capable ones. The four local-mode reasons need local code execution and keep D-06's
    // per-occurrence emission.
    // ---------------------------------------------------------------------------------------

    @Test
    fun report_coalescesRepeatedUnauthorizedAuditEventsInsideOneWindow() {
        val reporter = reporter()

        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T0)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)

        assertEquals(1, captured.size)
        // `suppressed` counts occurrences collapsed away SINCE the previous emission, so the first
        // event of a burst always carries 0.
        assertEquals(0L, payloadAt(0)["suppressed"])
    }

    @Test
    fun report_carriesTheSuppressedCountOnTheFirstAuditEventAfterTheWindowElapses() {
        val reporter = reporter()

        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T0)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_AFTER_WINDOW)

        assertEquals(2, captured.size)
        assertEquals(3L, payloadAt(1)["suppressed"])
    }

    @Test
    fun report_coalescesBlankTokenInAWindowIndependentOfUnauthorized() {
        val reporter = reporter()

        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T0)
        reporter.report(denyBlankToken(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyBlankToken(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)

        // One event per reason, and neither reason's counter is consumed by the other.
        assertEquals(2, captured.size)
        assertEquals("unauthorized", payloadAt(0)["reason"])
        assertEquals(0L, payloadAt(0)["suppressed"])
        assertEquals("blank_token", payloadAt(1)["reason"])
        assertEquals(0L, payloadAt(1)["suppressed"])
    }

    @Test
    fun report_keepsPerOccurrenceAuditEventsForLocalModeReasonsWithNoSuppressedKey() {
        val reporter = reporter()

        reporter.report(denyHost(), externalMode = false, nowMs = T0)
        reporter.report(denyHost(), externalMode = false, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyHost(), externalMode = false, nowMs = T_INSIDE_WINDOW)

        assertEquals(3, captured.size)
        assertFalse(payloadAt(0).containsKey("suppressed"), "local-mode payload gained a suppressed key")
        assertFalse(payloadAt(1).containsKey("suppressed"), "local-mode payload gained a suppressed key")
        assertFalse(payloadAt(2).containsKey("suppressed"), "local-mode payload gained a suppressed key")
    }

    @Test
    fun report_coalescedPayloadAppendsSuppressedAfterTheExistingKeys() {
        reporter().report(denyUnauthorized(), externalMode = true, nowMs = T0)

        assertEquals(
            listOf("reason", "mode", "method", "path", "origin", "host", "referer", "userAgent", "suppressed"),
            payloadAt(0).keys.toList(),
        )
    }

    @Test
    fun report_auditCoalescingLeavesTheOutputTabWindowUntouched() {
        val reporter = reporter()

        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T0)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_INSIDE_WINDOW)
        reporter.report(denyUnauthorized(), externalMode = true, nowMs = T_AFTER_WINDOW)

        // The two sinks hold distinct ReasonWindow instances, so neither getAndSet(0L) steals the
        // other's suppression count: both report 3 from the same sequence of calls.
        assertEquals(2, lines.size)
        assertEquals("[McpAccessControl] 3 further blocks for unauthorized in the last 60s", lines[1])
        assertEquals(2, captured.size)
        assertEquals(3L, payloadAt(1)["suppressed"])
    }

    // ---------------------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------------------

    private fun reporter(verboseAudit: Boolean = false): McpBlockedRequestReporter = McpBlockedRequestReporter(logToOutput = { line -> lines += line }, verboseAudit = verboseAudit)

    private fun denyUnauthorized(): GateDecision.Deny =
        GateDecision.Deny(
            HttpStatusCode.Unauthorized,
            BlockReason.UNAUTHORIZED,
            RequestFacts(method = "POST", path = "/message"),
        )

    private fun denyBlankToken(): GateDecision.Deny =
        GateDecision.Deny(
            HttpStatusCode.Unauthorized,
            BlockReason.BLANK_TOKEN,
            RequestFacts(method = "POST", path = "/message"),
        )

    private fun denyHost(): GateDecision.Deny =
        GateDecision.Deny(
            HttpStatusCode.Forbidden,
            BlockReason.HOST_MISMATCH,
            RequestFacts(path = "/message", host = "evil.example"),
        )

    private fun denyOrigin(origin: String = FOREIGN_ORIGIN): GateDecision.Deny =
        GateDecision.Deny(
            HttpStatusCode.Forbidden,
            BlockReason.ORIGIN_MISMATCH,
            RequestFacts(method = "POST", path = "/message", origin = origin),
        )

    @Suppress("UNCHECKED_CAST")
    private fun payloadAt(index: Int): Map<String, Any?> = captured[index].second as Map<String, Any?>

    /** Pulls the `origin=` field out of an Output line; `host=` is always the next field. */
    private fun originFieldOf(line: String): String = line.substringAfter("origin=").substringBefore(" host=")
}
