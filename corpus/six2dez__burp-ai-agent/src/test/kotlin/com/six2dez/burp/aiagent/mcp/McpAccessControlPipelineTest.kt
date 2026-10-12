package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.audit.AuditLogger
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.concurrent.CopyOnWriteArrayList

private const val HEALTH = "/__mcp/health"
private const val MESSAGE = "/message"
private const val SSE = "/sse"
private const val SHUTDOWN = "/__mcp/shutdown"

private const val FOREIGN_HOST = "evil.example"
private const val FOREIGN_REFERER = "http://evil.example/x"
private const val FOREIGN_ORIGIN = "http://evil.example"
private const val CHROME_USER_AGENT =
    "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"

private const val TRANSPORT_BLOCKED = "mcp_transport_blocked"

/** The four SC3 headers, asserted individually so a partial regression cannot hide behind an aggregate. */
private val EXPECTED_SECURITY_HEADERS =
    listOf(
        "X-Frame-Options" to "DENY",
        "X-Content-Type-Options" to "nosniff",
        "Referrer-Policy" to "same-origin",
        "Content-Security-Policy" to "default-src 'none'",
    )

/**
 * SEC-04 / SC2 / SC3 regression gate for LOCAL mode, driven against a REAL Netty server started
 * through [KtorMcpServerManager].
 *
 * Why this class exists: `KtorMcpServerManagerSecurityTest` and `McpServerIntegrationTest` were BOTH
 * green for the entire life of the F1 bypass. The first invoked the predicates directly and the
 * predicates were always correct — they were simply never reached, because the checks lived in an
 * `intercept(ApplicationCallPipeline.Call)` block registered after `routing {}`, i.e. behind
 * `RoutingRoot`'s own Call-phase interceptor. The second only exercises `/__mcp/shutdown`, whose
 * handler validates the token itself. Neither exercised the PIPELINE. This class does, and that is
 * the whole point: every assertion here is red against the pre-fix manager (proven by plan `20-06`)
 * and green against the `Plugins`-phase gate.
 *
 * Naming note: `McpAccessControlPipelineTest` is deliberately NOT matched by the `*IntegrationTest`
 * / `*ConcurrencyTest` / `*BackpressureTest` / `*RestartPolicyTest` / `*SupervisionTest` exclusion
 * globs that the `tasks.test` filter block in `build.gradle.kts` (cited as :145-157, actually
 * :154-166) applies under `-PexcludeHeavyTests=true`. A security gate wearing one of those suffixes
 * would be silently skipped in every fast PR gate and would prove nothing. Do not rename this class
 * into one of those patterns.
 *
 * Client note: OkHttp, and NEVER the JDK's built-in URL-connection client (the one
 * `McpServerIntegrationTest` uses through its `httpRequest` helper). That client applies a
 * restricted-header list: it silently drops `Origin` and always overwrites `Host` with the connect
 * authority, so the SC2 assertions below are physically unwritable with it — the forged header never
 * leaves the process and the test passes for the wrong reason. The identifier is spelled out in
 * `McpTestServerSupport`'s KDoc; it is paraphrased here so this file's zero-count guard grep for it
 * measures code and not prose.
 */
class McpAccessControlPipelineTest {
    /**
     * The audit emitter fires on a Netty event-loop thread and is read from the JUnit thread, so the
     * capture list must be concurrent. The payload type is `Any`, not `Map<String, Any?>` —
     * `AuditLogger.kt:20` declares `((String, Any) -> Unit)?`.
     */
    private val capturedAudit = CopyOnWriteArrayList<Pair<String, Any>>()

    @BeforeEach
    fun registerCapturingEmitter() {
        capturedAudit.clear()
        AuditLogger.registerGlobalEmitter { type, payload -> capturedAudit += type to payload }
    }

    @AfterEach
    fun clearGlobalEmitter() {
        // globalEmitter is a @Volatile companion field: leaving it registered leaks captures into
        // every other test class in this JVM. This reset is not optional.
        AuditLogger.registerGlobalEmitter(null)
    }

    // ---------------------------------------------------------------------------------------
    // SC3 + D-02 — security headers and the local-mode identity header on a MATCHED route
    // ---------------------------------------------------------------------------------------

    @Test
    fun health_matchedRouteCarriesAllFourSecurityHeaders() {
        withLocalServer { baseUrl, client ->
            client.newCall(get(baseUrl, HEALTH)).execute().use { response ->
                assertEquals(200, response.code, "local /__mcp/health must stay reachable")
                assertEquals("ok", response.body.string(), "the health body is the liveness contract (D-01)")
                assertAllFourSecurityHeaders(
                    response,
                    "GET $HEALTH is a MATCHED route; pre-fix it returned 200 with NONE of the four headers " +
                        "because the deleted Call-phase interceptor only ever reached unmatched paths (404s)",
                )
            }
        }
    }

    @Test
    fun health_localModeCarriesAgentIdentityHeader() {
        withLocalServer { baseUrl, client ->
            client.newCall(get(baseUrl, HEALTH)).execute().use { response ->
                assertEquals(200, response.code, "local /__mcp/health must stay reachable")
                assertEquals(
                    "mcp",
                    response.header("X-Burp-AI-Agent"),
                    "D-02: the identity header is RETAINED in local mode — McpSupervisor.probeExistingServer " +
                        "identifies a foreign holder of the MCP port through it",
                )
            }
        }
    }

    // ---------------------------------------------------------------------------------------
    // SC2 — DNS-rebinding and browser-CSRF denial, on EVERY path including the health route
    // ---------------------------------------------------------------------------------------

    @Test
    fun foreignHost_isRejectedOnEveryPath() {
        // OkHttp transmits an explicitly-set Host header (verified); the JDK client overwrites it.
        assertForbiddenOnEveryPath(
            headerName = "Host",
            headerValue = FOREIGN_HOST,
            preFixNote = "pre-fix: 200 / 400 / 200 — a DNS-rebinding Host reached every handler",
        )
    }

    @Test
    fun foreignReferer_isRejectedOnEveryPath() {
        assertForbiddenOnEveryPath(
            headerName = "Referer",
            headerValue = FOREIGN_REFERER,
            preFixNote = "pre-fix: 200 / 400 / 200 — isValidReferer was never called",
        )
    }

    @Test
    fun browserUserAgentWithoutOrigin_isRejectedOnEveryPath() {
        assertForbiddenOnEveryPath(
            headerName = "User-Agent",
            headerValue = CHROME_USER_AGENT,
            preFixNote =
                "pre-fix: /__mcp/health 200, POST /message 400 (the SDK handler RAN), and GET /sse 200 " +
                    "text/event-stream — an unauthenticated browser was granted a live MCP session. This is the " +
                    "sharpest expression of the F1 bypass",
        )
    }

    /**
     * NOT an SC4 gate assertion, kept for coverage only: Ktor's own CORS plugin already answered a
     * foreign `Origin` with 403 BEFORE the fix (RESEARCH pitfall P2), so this test was green against
     * the bypassed code and proves nothing about the gate. It is retained because the gate must not
     * turn a CORS 403 into something else, and because the `isCommitted` guard in
     * `McpAccessControlPlugin` exists precisely to avoid a second respond on this path.
     */
    @Test
    fun foreignOrigin_isRejected() {
        withLocalServer { baseUrl, client ->
            val code = statusOf(client, get(baseUrl, HEALTH, "Origin" to FOREIGN_ORIGIN))
            assertEquals(403, code, "a foreign Origin must not reach any MCP route")
        }
    }

    // ---------------------------------------------------------------------------------------
    // D-06 / D-07 / D-09 / D-10 — the ONLY end-to-end proof that onBlocked is wired at all
    // ---------------------------------------------------------------------------------------

    /**
     * `McpBlockedRequestReporter` is unit-tested in isolation by `BlockedRequestReporterTest` and is
     * reachable at runtime through exactly ONE call site: the `onBlocked` lambda wired in
     * `KtorMcpServerManager`. Without this test an executor could ship `onBlocked = { }` and every
     * other check in this phase would still pass, silently shipping D-06, D-07, D-09 and D-10 as dead
     * code. This assertion observes a REAL emitted audit event, not a non-null lambda.
     */
    @Test
    fun foreignHost_emitsExactlyOneTransportBlockedAuditEvent() {
        withLocalServer { baseUrl, client ->
            // Cleared immediately before the request: server startup may emit unrelated events.
            capturedAudit.clear()

            val code = statusOf(client, get(baseUrl, HEALTH, "Host" to FOREIGN_HOST))
            assertEquals(403, code, "a foreign Host must be denied")

            // No sleep and no polling: the gate calls onBlocked(decision) BEFORE call.respond(...),
            // so by the time the client holds the 403 the emit has already happened on the Netty
            // event-loop thread. Do NOT add a Thread.sleep here.
            val blocked = capturedAudit.filter { it.first == TRANSPORT_BLOCKED }
            assertEquals(
                1,
                blocked.size,
                "exactly one $TRANSPORT_BLOCKED event must reach the audit sink per blocked request; " +
                    "0 means KtorMcpServerManager's onBlocked lambda is a no-op and D-06/D-07/D-09/D-10 are " +
                    "dead code. Captured: ${capturedAudit.map { it.first }}",
            )
            assertEquals(
                "host_mismatch",
                payloadOf(blocked[0])["reason"],
                "the D-06 WIRE value is asserted, not the BlockReason enum name",
            )
        }
    }

    // ---------------------------------------------------------------------------------------
    // SC3 on the streaming response
    // ---------------------------------------------------------------------------------------

    @Test
    fun sse_authorizedConnectCarriesSecurityHeaders() {
        withLocalServer { baseUrl, client ->
            // The default OkHttp User-Agent (okhttp/5.x) matches none of the browser indicators and no
            // Origin is sent, so this request is allowed in local mode.
            client.newCall(get(baseUrl, SSE)).execute().use { response ->
                assertEquals(200, response.code, "a non-browser local SSE connect must still be allowed")
                val contentType = response.header("Content-Type").orEmpty()
                assertTrue(
                    contentType.startsWith("text/event-stream"),
                    "expected an SSE stream but Content-Type was: $contentType",
                )
                assertAllFourSecurityHeaders(
                    response,
                    "SC3: appending from the pre-routing Plugins phase is what puts the headers on the " +
                        "streaming response too — post-commit mutation was measured to work over TLS/HTTP-2 and " +
                        "fail over cleartext HTTP/1.1 (RESEARCH P3)",
                )
                // P5: never read this body. .body.string() on text/event-stream blocks until the read
                // timeout because the server holds the stream open; `use` closes it instead.
            }
        }
    }

    // ---------------------------------------------------------------------------------------
    // SC6 non-regression
    // ---------------------------------------------------------------------------------------

    @Test
    fun shutdownWithoutToken_stillReturns401() {
        withLocalServer { baseUrl, client ->
            val code = statusOf(client, post(baseUrl, SHUTDOWN))
            assertEquals(
                401,
                code,
                "the in-handler token check on /__mcp/shutdown is the one control that survived the F1 " +
                    "bypass (D-04) and must not regress",
            )
            // The authorized 200 case is deliberately NOT tested here — it would stop the server
            // mid-class. McpServerIntegrationTest owns that pair.
        }
    }

    // ---------------------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------------------

    /**
     * One manager and one port per test method (RESEARCH P6): `shutdown()` terminates the manager's
     * shared single-thread executor, so an instance can never be restarted and must not be shared
     * across tests.
     */
    private fun withLocalServer(body: (String, OkHttpClient) -> Unit) {
        val port = McpTestServerSupport.freePort()
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, McpTestServerSupport.localSettings(port))
            body(McpTestServerSupport.baseUrl(port, tls = false), McpTestServerSupport.plainClient())
        } finally {
            manager.shutdown()
        }
    }

    /** SC2: one forged header, three paths, three 403s. Nine such assertions across this class. */
    private fun assertForbiddenOnEveryPath(
        headerName: String,
        headerValue: String,
        preFixNote: String,
    ) {
        withLocalServer { baseUrl, client ->
            val header = headerName to headerValue
            assertEquals(
                403,
                statusOf(client, get(baseUrl, HEALTH, header)),
                "GET $HEALTH with $headerName: $headerValue must be denied — $preFixNote",
            )
            assertEquals(
                403,
                statusOf(client, post(baseUrl, MESSAGE, header)),
                "POST $MESSAGE with $headerName: $headerValue must be denied before the SDK handler runs — $preFixNote",
            )
            assertEquals(
                403,
                statusOf(client, get(baseUrl, SSE, header)),
                "GET $SSE with $headerName: $headerValue must be denied before a session is minted — $preFixNote",
            )
        }
    }

    private fun assertAllFourSecurityHeaders(
        response: Response,
        why: String,
    ) {
        EXPECTED_SECURITY_HEADERS.forEach { (name, value) ->
            assertEquals(value, response.header(name), "missing or wrong $name — $why")
        }
    }

    /** Executes and returns the status code only, always closing the response (P5-safe for /sse). */
    private fun statusOf(
        client: OkHttpClient,
        request: Request,
    ): Int = client.newCall(request).execute().use { it.code }

    private fun get(
        baseUrl: String,
        path: String,
        vararg headers: Pair<String, String>,
    ): Request = builder(baseUrl, path, headers).get().build()

    private fun post(
        baseUrl: String,
        path: String,
        vararg headers: Pair<String, String>,
    ): Request = builder(baseUrl, path, headers).post("{}".toRequestBody("application/json".toMediaType())).build()

    private fun builder(
        baseUrl: String,
        path: String,
        headers: Array<out Pair<String, String>>,
    ): Request.Builder =
        Request
            .Builder()
            .url("$baseUrl$path")
            .apply { headers.forEach { (name, value) -> header(name, value) } }

    @Suppress("UNCHECKED_CAST")
    private fun payloadOf(event: Pair<String, Any>): Map<String, Any?> = event.second as Map<String, Any?>
}
