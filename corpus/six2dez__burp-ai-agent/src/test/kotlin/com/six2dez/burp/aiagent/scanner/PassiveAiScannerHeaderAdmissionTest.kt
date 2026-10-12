package com.six2dez.burp.aiagent.scanner

import burp.api.montoya.MontoyaApi
import burp.api.montoya.http.message.HttpHeader
import com.six2dez.burp.aiagent.audit.AuditLogger
import com.six2dez.burp.aiagent.redact.Redaction
import com.six2dez.burp.aiagent.supervisor.AgentSupervisor
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.parallel.ResourceLock
import org.junit.jupiter.api.parallel.Resources
import org.mockito.kotlin.mock
import org.mockito.kotlin.whenever
import java.util.Locale

/**
 * (PRIV-05) Phase 27 Task 3 — the passive-scan ADMITTER, after its hand-written cookie substring
 * test was routed through `Redaction.isCookieHeaderName`.
 *
 * `sanitizeHeadersForPrompt` decides which headers enter the passive-scan prompt at all; the
 * redaction of their VALUES is `Redaction.apply`'s job on the way out. So this site is an admitter,
 * not a redactor: narrowing it does not leak, it merely analyses less. It was routed through the
 * shared predicate anyway, because a rule that lives in one place cannot drift — and drift between
 * two copies of one cookie rule is exactly what the v0.10.0 milestone audit found.
 *
 * The admission set is therefore expected to be UNCHANGED by that refactor: the conjunct it replaced
 * was already `name.contains("cookie")`. These assertions are the regression guard proving that, not
 * a claim of new behaviour.
 *
 * Header fixtures are mockito mocks rather than `HttpHeader.httpHeader(...)`: the Montoya static
 * factory dereferences a null `ObjectFactoryLocator.FACTORY` outside the Burp runtime. This mirrors
 * `McpToolHelpersTest` and `InjectionPointExtractorTest`.
 */
class PassiveAiScannerHeaderAdmissionTest {
    private var localeAtStart: Locale = Locale.getDefault()

    @BeforeEach
    fun setUp() {
        localeAtStart = Locale.getDefault()
        // Redaction is a singleton object: custom patterns left behind by another test class in the
        // same JVM would bleed in here. Mirrors PassiveAiScannerPromptRedactionTest.
        Redaction.setCustomPatterns(emptyList())
    }

    @AfterEach
    fun tearDown() {
        Redaction.setCustomPatterns(emptyList())
        assertEquals(localeAtStart, Locale.getDefault(), "the JVM default locale must be restored")
    }

    @Test
    fun admitsEveryCookieNameVariantAfterRoutingThroughTheSharedPredicate() {
        listOf(true, false).forEach { isRequest ->
            val admitted =
                scanner().sanitizeHeadersForPrompt(
                    cookieVariants.map { (name, value) -> stubHeader(name, value) },
                    isRequest = isRequest,
                )

            assertEquals(
                cookieVariants.size,
                admitted.size,
                "isRequest=$isRequest: every cookie-named header must be admitted (got: $admitted)",
            )
            cookieVariants.forEach { (name, value) ->
                assertTrue(
                    admitted.contains("$name: $value"),
                    "isRequest=$isRequest: $name must be admitted under its OWN name (got: $admitted)",
                )
            }
        }
    }

    /**
     * The `encoding` edge on the admitter.
     *
     * MEASURED BOUND, stated so this is not read as proving more than it does: Kotlin's no-argument
     * `String.lowercase()` is already locale-agnostic, so this passes even without the explicit
     * `Locale.ROOT`. The dotless-i hazard belongs to the JAVA spelling (`"COOKIE".toLowerCase()`
     * yields `cookıe` under a `tr-TR` default). What this test guards is a future switch to a
     * locale-SENSITIVE spelling in this filter.
     */
    @Test
    @ResourceLock(Resources.LOCALE)
    fun admissionSurvivesATurkishDefaultLocale() {
        val previous = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"))

            val admitted =
                scanner().sanitizeHeadersForPrompt(
                    listOf(
                        stubHeader("X-COOKIE", "turkishcookievalue"),
                        stubHeader("SET-COOKIE", "turkishsetcookievalue"),
                    ),
                    isRequest = false,
                )

            assertTrue(admitted.contains("X-COOKIE: turkishcookievalue"), "got: $admitted")
            assertTrue(admitted.contains("SET-COOKIE: turkishsetcookievalue"), "got: $admitted")
        } finally {
            // Restored in `finally`: a failed assertion above must not leave a Turkish default
            // locale behind for every later test class in the shared JVM.
            Locale.setDefault(previous)
        }
    }

    /**
     * The regression guard on the branches this task must NOT change. The cookie conjunct was the
     * only edit; the denylist, the `x-` prefix rule, the deferred `auth`/`token` vendor class and
     * both allowlists must behave exactly as before.
     */
    @Test
    fun nonCookieAdmissionRulesAreUnchanged() {
        val requestAdmitted =
            scanner().sanitizeHeadersForPrompt(
                listOf(
                    stubHeader("Accept-Encoding", "gzip"),
                    stubHeader("X-Custom-Thing", "kept"),
                    stubHeader("My-Auth-Thing", "authvalue"),
                    stubHeader("My-Token-Thing", "tokenvalue"),
                    stubHeader("Referer", "https://example.com/"),
                    stubHeader("Accept-Charset", "utf-8"),
                ),
                isRequest = true,
            )

        assertFalse(
            requestAdmitted.any { it.startsWith("Accept-Encoding:") },
            "a denylisted header must still be rejected (got: $requestAdmitted)",
        )
        assertTrue(requestAdmitted.contains("X-Custom-Thing: kept"), "got: $requestAdmitted")
        assertTrue(requestAdmitted.contains("My-Auth-Thing: authvalue"), "got: $requestAdmitted")
        assertTrue(requestAdmitted.contains("My-Token-Thing: tokenvalue"), "got: $requestAdmitted")
        assertTrue(requestAdmitted.contains("Referer: https://example.com/"), "got: $requestAdmitted")
        assertFalse(
            requestAdmitted.any { it.startsWith("Accept-Charset:") },
            "a name in neither allowlist nor any widening rule must still be rejected (got: $requestAdmitted)",
        )

        // Direction matters: `referer` is on the REQUEST allowlist only, `server` on the RESPONSE one.
        val responseAdmitted =
            scanner().sanitizeHeadersForPrompt(
                listOf(
                    stubHeader("Server", "nginx"),
                    stubHeader("Referer", "https://example.com/"),
                ),
                isRequest = false,
            )

        assertTrue(responseAdmitted.contains("Server: nginx"), "got: $responseAdmitted")
        assertFalse(
            responseAdmitted.any { it.startsWith("Referer:") },
            "a request-only allowlist entry must not be admitted on the response side (got: $responseAdmitted)",
        )
    }

    // The two canonical names plus the five measured variants, the same seven names the tool-result
    // path asserts in McpToolHelpersTest so the two suites are comparable by eye.
    private val cookieVariants =
        listOf(
            "Cookie" to "admitfoxtrotsix",
            "Set-Cookie" to "admitgolfseven",
            "Cookie2" to "admitalphaone",
            "X-Cookie" to "admitbravotwo",
            "Set-Cookie2" to "admitcharliethree",
            "X-Original-Cookie" to "admitdeltafour",
            "X-Forwarded-Cookie" to "admitechofive",
        )

    // getSettings is deliberately a throwing lambda: sanitizeHeadersForPrompt reads only the
    // scanner's own denylist/allowlists and headerMaxCount, so a call into settings here would mean
    // the function grew a dependency this test is not modelling, and should fail loudly.
    private fun scanner(): PassiveAiScanner =
        PassiveAiScanner(
            api = mock<MontoyaApi>(),
            supervisor = mock<AgentSupervisor>(),
            audit = mock<AuditLogger>(),
        ) { error("sanitizeHeadersForPrompt must not depend on AgentSettings") }

    private fun stubHeader(
        name: String,
        value: String,
    ): HttpHeader {
        val header = mock<HttpHeader>()
        whenever(header.name()).thenReturn(name)
        whenever(header.value()).thenReturn(value)
        return header
    }
}
