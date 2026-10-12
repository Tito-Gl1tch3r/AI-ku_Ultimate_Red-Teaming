package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.TestSettings
import com.six2dez.burp.aiagent.config.McpSettings
import io.ktor.http.HttpStatusCode
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

private const val VALID_TOKEN = "s3cr3t-mcp-token"
private const val MCP_PORT = 9876
private const val CHROME_USER_AGENT =
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

/**
 * SEC-04 / SEC-05 unit coverage for the pure access-control decision core.
 *
 * Every assertion runs against [evaluate] and the relocated predicates directly — no Ktor engine,
 * no bound port, no reflection. That is the whole point of extracting the decision out of
 * `KtorMcpServerManager`: the security logic is provable without a server.
 */
class McpAccessControlDecisionTest {
    // ---------------------------------------------------------------------------------------
    // External mode — bearer authentication (D-01, SEC-05 5c)
    // ---------------------------------------------------------------------------------------

    @Test
    fun evaluate_externalHealthPathWithoutAuthorizationIsAllowed() {
        // D-01: the liveness probe stays token-free so McpSupervisor can identify a foreign
        // port holder without first holding a credential.
        val facts = RequestFacts(path = HEALTH_PATH, authorization = null)

        assertEquals(GateDecision.Allow, evaluate(facts, externalSettings()))
    }

    @Test
    fun evaluate_externalMessagePathWithoutAuthorizationIsUnauthorized() {
        val facts = RequestFacts(path = "/message", authorization = null)

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.UNAUTHORIZED, facts),
            evaluate(facts, externalSettings()),
        )
    }

    @Test
    fun evaluate_externalValidBearerTokenIsAllowed() {
        val facts = RequestFacts(path = "/message", authorization = "Bearer $VALID_TOKEN")

        assertEquals(GateDecision.Allow, evaluate(facts, externalSettings()))
    }

    @Test
    fun evaluate_externalEmptyAuthorizationHeaderIsUnauthorized() {
        val facts = RequestFacts(path = "/sse", authorization = "")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.UNAUTHORIZED, facts),
            evaluate(facts, externalSettings()),
        )
    }

    @Test
    fun evaluate_externalWrongBearerTokenIsUnauthorized() {
        val facts = RequestFacts(path = "/sse", authorization = "Bearer wrong-token")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.UNAUTHORIZED, facts),
            evaluate(facts, externalSettings()),
        )
    }

    @Test
    fun evaluate_externalLowercaseBearerSchemeIsUnauthorized() {
        // The comparison is byte-for-byte against "Bearer <token>"; the scheme is case-sensitive.
        val facts = RequestFacts(path = "/message", authorization = "bearer $VALID_TOKEN")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.UNAUTHORIZED, facts),
            evaluate(facts, externalSettings()),
        )
    }

    @Test
    fun evaluate_externalBlankConfiguredTokenDeniesEveryNonHealthRequest() {
        // SEC-05 5c: a blank configured token must fail closed rather than admit "Bearer ".
        val facts = RequestFacts(path = "/message", authorization = "Bearer $VALID_TOKEN")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.BLANK_TOKEN, facts),
            evaluate(facts, externalSettings(token = "")),
        )
    }

    @Test
    fun evaluate_externalBlankTokenWithBearerSpaceIsBlankTokenNotAllow() {
        // SEC-05 5c assertion #9: pre-fix this exact request authenticated successfully.
        val facts = RequestFacts(path = "/message", authorization = "Bearer ")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Unauthorized, BlockReason.BLANK_TOKEN, facts),
            evaluate(facts, externalSettings(token = "")),
        )
    }

    @Test
    fun evaluate_externalBlankTokenStillAllowsHealthPath() {
        val facts = RequestFacts(path = HEALTH_PATH, authorization = null)

        assertEquals(GateDecision.Allow, evaluate(facts, externalSettings(token = "")))
    }

    @Test
    fun evaluate_externalIgnoresOriginHostRefererAndUserAgent() {
        // In external mode the CORS plugin owns Origin; the gate only owns the bearer token.
        val facts =
            RequestFacts(
                path = "/message",
                origin = "http://evil.example",
                host = "evil.example",
                referer = "http://evil.example/x",
                userAgent = CHROME_USER_AGENT,
                authorization = "Bearer $VALID_TOKEN",
            )

        assertEquals(GateDecision.Allow, evaluate(facts, externalSettings()))
    }

    // ---------------------------------------------------------------------------------------
    // Local mode — DNS rebinding / browser CSRF (D-03)
    // ---------------------------------------------------------------------------------------

    @Test
    fun evaluate_localForeignOriginIsForbidden() {
        // The absent authority is DELIBERATE: the Origin branch precedes the fail-closed authority
        // branch, so this test staying green is the proof that branch precedence survived 20-07.
        val facts = RequestFacts(path = "/message", origin = "http://evil.example")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.ORIGIN_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localBrowserUserAgentWithoutOriginIsForbidden() {
        // The absent authority is DELIBERATE: the browser-UA branch precedes the fail-closed
        // authority branch, so BROWSER_NO_ORIGIN — not HOST_MISMATCH — must still be the reason.
        val facts = RequestFacts(path = "/message", origin = null, userAgent = CHROME_USER_AGENT)

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.BROWSER_NO_ORIGIN, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localLoopbackOriginWithBrowserUserAgentIsAllowed() {
        // DELIBERATE NARROWING — do NOT "restore" the pre-fix `else if`.
        // KtorMcpServerManager.kt:195 used `else if (isBrowserRequest(userAgent))`, which fired
        // whenever the Origin branch did not — including for a present-and-VALID loopback Origin.
        // SEC-04's text mandates only the Origin-ABSENT case, so this request is now allowed.
        // Exposure is nil: Ktor's CORS plugin admits only localhost/127.0.0.1 on the MCP port in
        // local mode and the server serves no HTML, so a valid loopback Origin already had to pass
        // CORS to reach the gate. Recorded in 20-01-SUMMARY.md as a behaviour change.
        val facts =
            RequestFacts(
                path = "/message",
                origin = "http://localhost:$MCP_PORT",
                host = "127.0.0.1:$MCP_PORT",
                userAgent = CHROME_USER_AGENT,
            )

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localForeignHostIsForbidden() {
        val facts = RequestFacts(path = "/message", host = "evil.example")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.HOST_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localHealthPathIsGatedToo() {
        // D-03: the local-mode checks apply to EVERY path, including the liveness probe.
        val facts = RequestFacts(path = HEALTH_PATH, host = "evil.example")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.HOST_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localMatchingLoopbackHostAndPortIsAllowed() {
        val facts = RequestFacts(path = "/message", host = "localhost:$MCP_PORT")

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localHostWithWrongPortIsForbidden() {
        val facts = RequestFacts(path = "/message", host = "localhost:1234")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.HOST_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localBracketedIpv6HostIsAllowed() {
        // SEC-05 5b: pre-fix `host.split(":")` yielded hostname "[" and denied the server's own Host.
        val facts = RequestFacts(path = "/message", host = "[::1]:$MCP_PORT")

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localForeignRefererIsForbidden() {
        // The matching loopback authority is REQUIRED, not decoration: the fail-closed authority
        // branch precedes the Referer branch, so without it this test would measure HOST_MISMATCH
        // and the Referer coverage would silently disappear.
        val facts =
            RequestFacts(
                path = "/message",
                host = "127.0.0.1:$MCP_PORT",
                referer = "http://evil.example/x",
            )

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.REFERER_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    @Test
    fun evaluate_localLoopbackRefererIsAllowed() {
        val facts =
            RequestFacts(
                path = "/message",
                host = "127.0.0.1:$MCP_PORT",
                referer = "http://127.0.0.1:$MCP_PORT/x",
            )

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localMatchingLoopbackAuthorityAloneIsAllowed() {
        // The minimum a real MCP client sends: a matching loopback authority and nothing else the
        // gate inspects. This is the ALLOW half of the fail-closed authority branch.
        val facts = RequestFacts(path = "/message", host = "127.0.0.1:$MCP_PORT")

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localAbsentAuthorityIsForbiddenOnEveryPath() {
        // FAIL-OPEN CLOSED by gap-closure plan 20-07 — do NOT "restore" the old permissiveness.
        // This request used to be ALLOWED: the host branch was guarded by a non-null check, so a
        // request carrying neither an HTTP/1 `Host` header nor an HTTP/2 `:authority` skipped the
        // DNS-rebinding limb entirely. The maintainer's locked answer is that an absent authority
        // DENIES; every conforming HTTP/1.1 and HTTP/2 client sends one. D-03 gates every path, so
        // the liveness probe is denied on the same terms.
        val messageFacts = RequestFacts(path = "/message")
        val healthFacts = RequestFacts(path = HEALTH_PATH)

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.HOST_MISMATCH, messageFacts),
            evaluate(messageFacts, localSettings()),
        )
        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.HOST_MISMATCH, healthFacts),
            evaluate(healthFacts, localSettings()),
        )
    }

    @Test
    fun evaluate_localNeverInspectsAuthorization() {
        // Requiring a bearer token in local mode is a deferred idea, deliberately NOT added here.
        // The matching loopback authority keeps this test measuring what its name says instead of
        // tripping the fail-closed authority branch.
        val facts =
            RequestFacts(
                path = "/message",
                host = "127.0.0.1:$MCP_PORT",
                authorization = "Bearer nonsense",
            )

        assertEquals(GateDecision.Allow, evaluate(facts, localSettings()))
    }

    @Test
    fun evaluate_localOriginIsCheckedBeforeHost() {
        // Branch order is load-bearing for the reported reason: Origin wins over Host.
        val facts = RequestFacts(path = "/message", origin = "http://evil.example", host = "evil.example")

        assertEquals(
            GateDecision.Deny(HttpStatusCode.Forbidden, BlockReason.ORIGIN_MISMATCH, facts),
            evaluate(facts, localSettings()),
        )
    }

    // ---------------------------------------------------------------------------------------
    // isLoopbackAuthority — D-11 shared authority predicate
    // ---------------------------------------------------------------------------------------

    @Test
    fun isLoopbackAuthority_acceptsNamedAndIpv4LoopbackWithMatchingPort() {
        assertTrue(isLoopbackAuthority("localhost:$MCP_PORT", MCP_PORT))
        assertTrue(isLoopbackAuthority("127.0.0.1", null))
        assertTrue(isLoopbackAuthority("127.0.0.1", MCP_PORT))
        assertTrue(isLoopbackAuthority("LOCALHOST:$MCP_PORT", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_acceptsBracketedIpv6LoopbackWithPort() {
        // SC5b — false in the pre-fix code.
        assertTrue(isLoopbackAuthority("[::1]:$MCP_PORT", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_acceptsBracketedIpv6WithoutPortAndExpandedForm() {
        assertTrue(isLoopbackAuthority("[::1]", null))
        assertTrue(isLoopbackAuthority("[0:0:0:0:0:0:0:1]:$MCP_PORT", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_acceptsBareIpv6LiteralWithoutPort() {
        assertTrue(isLoopbackAuthority("::1", null))
        assertTrue(isLoopbackAuthority("0:0:0:0:0:0:0:1", null))
    }

    @Test
    fun isLoopbackAuthority_rejectsAmbiguousUnbracketedIpv6WithPort() {
        assertFalse(isLoopbackAuthority("::1:$MCP_PORT", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_rejectsForeignHostAndMismatchedPort() {
        assertFalse(isLoopbackAuthority("evil.example:$MCP_PORT", MCP_PORT))
        assertFalse(isLoopbackAuthority("localhost:1234", MCP_PORT))
        assertFalse(isLoopbackAuthority("[::2]:$MCP_PORT", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_failsClosedOnMalformedInput() {
        assertFalse(isLoopbackAuthority("", null))
        assertFalse(isLoopbackAuthority("   ", null))
        assertFalse(isLoopbackAuthority("[::1", null))
        assertFalse(isLoopbackAuthority("localhost:abc", MCP_PORT))
    }

    @Test
    fun isLoopbackAuthority_rejectsAPortThatIsNumericButOutOfRange() {
        // WR-01. The two inputs below disagreed before gap-closure plan 20-07: "localhost:65536"
        // returned FALSE (it parses to an Int that simply differs from the expected port) while
        // "localhost:99999999999" returned TRUE (it overflows an Int, the parser reported "no port
        // was present", and the port comparison was silently skipped). That inconsistency is the
        // defect: a port outside the RFC 3986 range now makes the whole authority malformed.
        assertFalse(isLoopbackAuthority("localhost:99999999999", MCP_PORT))
        assertFalse(isLoopbackAuthority("localhost:65536", MCP_PORT))
        // A null expectedPort must not rescue an unusable port either.
        assertFalse(isLoopbackAuthority("localhost:65536", null))
        assertFalse(isLoopbackAuthority("localhost:99999999999", null))
        assertFalse(isLoopbackAuthority("localhost:0", null))
        // Contrast: an authority carrying NO port still yields a null port and still passes.
        assertTrue(isLoopbackAuthority("127.0.0.1", null))
        assertTrue(isLoopbackAuthority("localhost:$MCP_PORT", MCP_PORT))
    }

    // ---------------------------------------------------------------------------------------
    // isLoopbackUrlAuthority — Origin / Referer values
    // ---------------------------------------------------------------------------------------

    @Test
    fun isLoopbackUrlAuthority_acceptsLoopbackUrlsIncludingBracketedIpv6() {
        assertTrue(isLoopbackUrlAuthority("http://localhost:$MCP_PORT"))
        assertTrue(isLoopbackUrlAuthority("http://127.0.0.1:$MCP_PORT"))
        // java.net.URI reports the IPv6 host WITH brackets — the shared predicate strips them.
        assertTrue(isLoopbackUrlAuthority("http://[::1]:$MCP_PORT"))
    }

    @Test
    fun isLoopbackUrlAuthority_failsClosedOnForeignAndMalformedValues() {
        assertFalse(isLoopbackUrlAuthority("http://evil.example"))
        assertFalse(isLoopbackUrlAuthority("null"))
        assertFalse(isLoopbackUrlAuthority(""))
        assertFalse(isLoopbackUrlAuthority("h t t p://localhost"))
    }

    // ---------------------------------------------------------------------------------------
    // isAuthorizedBearer / isBrowserUserAgent
    // ---------------------------------------------------------------------------------------

    @Test
    fun isAuthorizedBearer_rejectsBearerSpaceAgainstBlankToken() {
        // SC5c / SC4 gate assertion #9 — true in the pre-fix code.
        assertFalse(isAuthorizedBearer("Bearer ", ""))
    }

    @Test
    fun isAuthorizedBearer_rejectsBlankTokenRegardlessOfHeader() {
        assertFalse(isAuthorizedBearer("", ""))
        assertFalse(isAuthorizedBearer("Bearer", ""))
        assertFalse(isAuthorizedBearer("Bearer  ", "   "))
    }

    @Test
    fun isAuthorizedBearer_acceptsExactMatchAndRejectsMismatch() {
        assertTrue(isAuthorizedBearer("Bearer x", "x"))
        assertFalse(isAuthorizedBearer("Bearer y", "x"))
        assertFalse(isAuthorizedBearer("Bearer x ", "x"))
    }

    @Test
    fun isBrowserUserAgent_detectsBrowsersAndIgnoresToolingAndNull() {
        assertTrue(isBrowserUserAgent(CHROME_USER_AGENT))
        assertTrue(isBrowserUserAgent("Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"))
        assertFalse(isBrowserUserAgent(null))
        assertFalse(isBrowserUserAgent("curl/8.4.0"))
        assertFalse(isBrowserUserAgent(""))
    }

    // ---------------------------------------------------------------------------------------
    // BlockReason wire values (D-06)
    // ---------------------------------------------------------------------------------------

    @Test
    fun blockReason_wireValuesMatchTheD06Contract() {
        assertEquals("origin_mismatch", BlockReason.ORIGIN_MISMATCH.wireValue)
        assertEquals("host_mismatch", BlockReason.HOST_MISMATCH.wireValue)
        assertEquals("referer_mismatch", BlockReason.REFERER_MISMATCH.wireValue)
        assertEquals("browser_no_origin", BlockReason.BROWSER_NO_ORIGIN.wireValue)
        assertEquals("unauthorized", BlockReason.UNAUTHORIZED.wireValue)
        assertEquals("blank_token", BlockReason.BLANK_TOKEN.wireValue)
        assertEquals(6, BlockReason.entries.size)
    }

    @Test
    fun healthPath_matchesTheSupervisorLivenessRoute() {
        assertEquals("/__mcp/health", HEALTH_PATH)
    }

    // ---------------------------------------------------------------------------------------
    // Fixtures — built from TestSettings so new McpSettings fields cannot break this class.
    // ---------------------------------------------------------------------------------------

    private fun externalSettings(token: String = VALID_TOKEN): McpSettings = settings(externalEnabled = true, token = token)

    private fun localSettings(token: String = VALID_TOKEN): McpSettings = settings(externalEnabled = false, token = token)

    private fun settings(
        externalEnabled: Boolean,
        token: String,
    ): McpSettings =
        TestSettings
            .baselineSettings()
            .mcpSettings
            .copy(
                externalEnabled = externalEnabled,
                token = token,
                port = MCP_PORT,
            )
}
