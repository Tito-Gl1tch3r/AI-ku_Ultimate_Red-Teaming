package com.six2dez.burp.aiagent.mcp

import burp.api.montoya.MontoyaApi
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.kotlin.mock
import java.lang.reflect.Method

/**
 * Predicate-level access-control assertions for the MCP transport, including the SC5b (bracketed IPv6)
 * and SC5c (blank bearer token) gate assertions.
 *
 * Naming note: `KtorMcpServerManagerSecurityTest` is deliberately OUTSIDE the `*IntegrationTest` /
 * `*ConcurrencyTest` / `*BackpressureTest` / `*RestartPolicyTest` / `*SupervisionTest` exclusion globs
 * in the `tasks.test` block of `build.gradle.kts` (lines 151-165; cited as 145-157 in 20-03-PLAN.md),
 * so these assertions run in the fast PR gate under `-PexcludeHeavyTests=true` rather than only in
 * `nightlyRegressionTest`. Do not rename this class into one of those suffixes.
 *
 * The decision-core predicates are `internal`, so they are called directly here; only the manager's
 * surviving `private` members need the reflection helpers at the bottom of the file.
 */
class KtorMcpServerManagerSecurityTest {
    private val manager = KtorMcpServerManager(mock<MontoyaApi>())

    @Test
    fun isAuthorized_acceptsOnlyExactBearerToken() {
        assertTrue(invokeBoolean("isAuthorized", "Bearer token-123", "token-123"))
        assertFalse(invokeBoolean("isAuthorized", "", "token-123"))
        assertFalse(invokeBoolean("isAuthorized", "Bearer wrong", "token-123"))
        assertFalse(invokeBoolean("isAuthorized", "bearer token-123", "token-123"))
        // SEC-05 5c / F19: SC4 gate assertion #9. This returned TRUE against the pre-fix code, where
        // "Bearer " was compared against the string built from a blank configured token.
        assertFalse(invokeBoolean("isAuthorized", "Bearer ", ""))
    }

    /**
     * The manager's private `constantTimeEquals` was deleted in favour of the decision core's
     * `constantTimeCompare`, which is `internal` and therefore reachable from the test source set with
     * no reflection at all (the `redact/Redaction.kt:215-228` test-seam precedent).
     */
    @Test
    fun constantTimeCompare_handlesEqualAndDifferentLengths() {
        assertTrue(constantTimeCompare("abc123", "abc123"))
        assertFalse(constantTimeCompare("abc123", "abc124"))
        assertFalse(constantTimeCompare("short", "much-longer-value"))
    }

    @Test
    fun parseExternalCorsHosts_normalizes_filters_and_deduplicatesOrigins() {
        val hosts =
            invokeCorsHosts(
                listOf(
                    "https://Example.com",
                    "http://example.com:8443/path",
                    "://broken-origin",
                    "https://example.com",
                ),
            )

        assertEquals(2, hosts.size)
        val rendered = hosts.joinToString("\n") { it.toString() }
        assertTrue(rendered.contains("hostAndPort=example.com"))
        assertTrue(rendered.contains("scheme=https"))
        assertTrue(rendered.contains("hostAndPort=example.com:8443"))
        assertTrue(rendered.contains("scheme=http"))
    }

    /**
     * SC5b. `isLoopbackAuthority` is the real name of the shared D-11 authority predicate; the plan's
     * `isValidHostAuthority` alias was deliberately never created (see 20-01-SUMMARY deviation 2).
     */
    @Test
    fun isLoopbackAuthority_acceptsBracketedIpv6Loopback() {
        // SC4 gate assertion #8: false against the pre-fix split(":") implementation, which took "["
        // as the hostname for a bracketed IPv6 authority.
        assertTrue(isLoopbackAuthority("[::1]:9876", 9876))
        assertTrue(isLoopbackAuthority("[0:0:0:0:0:0:0:1]:9876", 9876))
        assertTrue(isLoopbackAuthority("localhost:9876", 9876))
        assertTrue(isLoopbackAuthority("127.0.0.1", 9876))
        assertFalse(isLoopbackAuthority("evil.example:9876", 9876))
        assertFalse(isLoopbackAuthority("localhost:1234", 9876))
        assertFalse(isLoopbackAuthority("[::1", 9876))
        assertFalse(isLoopbackAuthority("", 9876))
    }

    /**
     * SC5b for full URL values. `isLoopbackUrlAuthority` backs BOTH the `Origin` and the `Referer`
     * check (D-11), which is why the plan's separate `isValidOriginValue` / `isValidRefererValue`
     * aliases do not exist.
     */
    @Test
    fun isLoopbackUrlAuthority_acceptsBracketedIpv6Loopback() {
        assertTrue(isLoopbackUrlAuthority("http://[::1]:9876"))
        assertTrue(isLoopbackUrlAuthority("http://localhost:9876"))
        assertTrue(isLoopbackUrlAuthority("http://127.0.0.1"))
        assertFalse(isLoopbackUrlAuthority("http://evil.example"))
        assertFalse(isLoopbackUrlAuthority("not-a-uri"))
        assertFalse(isLoopbackUrlAuthority(""))
    }

    /**
     * D-11 drift guard, asserted one level up from the predicate. Since `Origin` and `Referer` now share
     * a single helper, comparing two predicates would be vacuous; instead the same authority is supplied
     * once as `Origin` and once as `Referer` and the two [GateDecision]s must agree on allow-vs-deny.
     */
    @Test
    fun evaluate_treatsOriginAndRefererIdentically() {
        val settings = McpTestServerSupport.localSettings(port = 9876)
        // The matching loopback `Host` is load-bearing. Since gap-closure plan 20-07 the authority
        // branch denies an absent authority, and it sits BEFORE the Referer branch: without a Host
        // every iteration would deny, the comparison below would read `false == false`, and this
        // guard would stay green while asserting nothing about Referer handling at all.
        var bothAllowedCount = 0
        listOf(
            "http://[::1]:9876",
            "http://localhost:9876",
            "http://127.0.0.1",
            "http://evil.example",
            "not-a-uri",
            "",
        ).forEach { authority ->
            val asOrigin = evaluate(RequestFacts(path = "/sse", host = "127.0.0.1:9876", origin = authority), settings)
            val asReferer = evaluate(RequestFacts(path = "/sse", host = "127.0.0.1:9876", referer = authority), settings)
            if (asOrigin is GateDecision.Allow && asReferer is GateDecision.Allow) bothAllowedCount++
            assertEquals(
                asOrigin is GateDecision.Allow,
                asReferer is GateDecision.Allow,
                "Origin and Referer handling drifted for '$authority'",
            )
        }
        // PERMANENT non-vacuity contract, not a one-time observation. A pure allow-vs-deny comparison
        // is satisfied just as well by two denials, so at least one authority must reach the Referer
        // predicate and be ALLOWED on both sides for this guard to mean anything.
        assertTrue(
            bothAllowedCount > 0,
            "D-11 drift guard has gone VACUOUS: no authority was allowed as both Origin and Referer, " +
                "so the loop only proved that two denials agree. A branch inserted ahead of the Referer " +
                "check is denying every iteration before the Referer predicate is ever consulted.",
        )
    }

    /** SC5c: a blank configured token can never authenticate, whatever the client sends. */
    @Test
    fun isAuthorizedBearer_rejectsBlankConfiguredToken() {
        assertFalse(isAuthorizedBearer("Bearer ", ""))
        assertFalse(isAuthorizedBearer("", ""))
        assertFalse(isAuthorizedBearer("Bearer", ""))
        assertTrue(isAuthorizedBearer("Bearer tok", "tok"))
        assertFalse(isAuthorizedBearer("bearer tok", "tok"))
    }

    private fun invokeBoolean(
        methodName: String,
        vararg args: String,
    ): Boolean {
        val method: Method =
            manager.javaClass.getDeclaredMethod(
                methodName,
                String::class.java,
                String::class.java,
            )
        method.isAccessible = true
        return method.invoke(manager, args[0], args[1]) as Boolean
    }

    private fun invokeCorsHosts(origins: List<String>): List<Any> {
        val method = manager.javaClass.getDeclaredMethod("parseExternalCorsHosts", List::class.java)
        method.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        return method.invoke(manager, origins) as List<Any>
    }
}
