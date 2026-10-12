package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.config.McpSettings
import okhttp3.Request
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.nio.file.Files

/**
 * SEC-04 / D-02 — the FIRST coverage `McpSupervisor.probeExistingServer` has ever had.
 *
 * `McpSupervisorRestartPolicyTest` is NOT the analog of this class: it injects a fake
 * [McpTakeoverClient], so the real `probeExistingServer` is never executed there. That is precisely
 * why the D-02 header change could have silently disabled external-mode bind-conflict takeover with a
 * fully green suite.
 *
 * Every test here probes a REAL [KtorMcpServerManager] bound to a loopback port, because the point is
 * to assert the interaction between the probe and the access-control gate, not the probe in isolation.
 *
 * Naming note: `McpSupervisorProbeTest` is deliberately outside the `*IntegrationTest` /
 * `*ConcurrencyTest` / `*BackpressureTest` / `*RestartPolicyTest` / `*SupervisionTest` exclusion globs
 * applied under `-PexcludeHeavyTests=true` (`build.gradle.kts` lines 158-166; the plan cites 145-157),
 * so it runs in the fast PR gate. Do NOT rename it into one of those suffixes — a security regression
 * guard that is skipped proves nothing.
 *
 * One manager per test, always torn down in a `finally` block (RESEARCH P6): `shutdown()` terminates
 * the manager's shared single-thread executor, so an instance cannot be restarted afterwards.
 */
class McpSupervisorProbeTest {
    private val api = McpTestServerSupport.deepStubApi()
    private val supervisor = McpSupervisor(api)

    @AfterEach
    fun tearDown() {
        // Releases the supervisor's scheduler thread and its default (never started) server manager.
        supervisor.shutdown()
    }

    @Test
    fun probeExistingServer_localMode_returnsTrueAgainstRunningServer() {
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localSettings(port)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                probe(settings),
                "The local-mode probe must still reach GET /__mcp/health and see X-Burp-AI-Agent: mcp. " +
                    "If this is red, the access-control gate started rejecting the supervisor's own probe: " +
                    "the probe is server-side, sends no Origin/Referer, and its HttpURLConnection default " +
                    "User-Agent (Java/21...) matches none of the browser indicators, so D-03's local " +
                    "heuristics must not fire on it.",
            )
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun probeExistingServer_localMode_returnsFalseWhenNothingIsListening() {
        val settings = McpTestServerSupport.localSettings(McpTestServerSupport.freePort())

        assertFalse(probe(settings), "Probing a port with no listener must fail closed")
    }

    @Test
    fun probeExistingServer_externalMode_returnsTrueWithoutTheIdentityHeader() {
        val keystoreDir = Files.createTempDirectory("mcp-probe-ks")
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.externalTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                probe(settings),
                "T-20-18 regression guard: in external mode the probe must accept 2xx liveness alone, " +
                    "otherwise attemptTakeover returns NO_COMPATIBLE_SERVER and handleBindFailure " +
                    "schedules no retry — the MCP server stays down silently after a bind conflict.",
            )

            // Without this second assertion the test above would be a tautology: it must be proven that
            // the identity header really is absent in external mode (D-02), not merely unchecked.
            McpTestServerSupport
                .trustAllClient()
                .newCall(
                    Request
                        .Builder()
                        .url("${McpTestServerSupport.baseUrl(port, tls = true)}$HEALTH_PATH")
                        .get()
                        .build(),
                ).execute()
                .use { response ->
                    assertEquals(200, response.code, "$HEALTH_PATH must stay reachable for liveness (D-01)")
                    assertNull(
                        response.header("X-Burp-AI-Agent"),
                        "D-02: the identifying header must NOT be emitted when external access is enabled",
                    )
                }
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun probeExistingServer_neverSendsAuthorization() {
        // Presenting the bearer token to a listener whose identity has not been established is
        // Finding 7 and belongs to Phase 25 / SEC-07 (D-05). This test pins that Phase 20 did not
        // introduce it: the probe succeeds against a token-protected external server WITHOUT any
        // credential, because /__mcp/health is the deliberate D-01 exemption.
        val keystoreDir = Files.createTempDirectory("mcp-probe-ks")
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.externalTlsSettings(port, keystoreDir, token = "test-token")
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(probe(settings), "The probe must succeed without presenting the bearer token")

            // The same unauthenticated request through a real client confirms the exemption is the
            // server's behaviour and not an artefact of the probe.
            McpTestServerSupport
                .trustAllClient()
                .newCall(
                    Request
                        .Builder()
                        .url("${McpTestServerSupport.baseUrl(port, tls = true)}$HEALTH_PATH")
                        .get()
                        .build(),
                ).execute()
                .use { response ->
                    assertEquals(
                        200,
                        response.code,
                        "$HEALTH_PATH is exempt from bearer auth in external mode (D-01)",
                    )
                }
        } finally {
            manager.shutdown()
        }
    }

    /** Reaches the private probe by reflection, as `McpSupervisorConnectionTest` reaches `openConnection`. */
    private fun probe(settings: McpSettings): Boolean {
        val method = supervisor.javaClass.getDeclaredMethod("probeExistingServer", McpSettings::class.java)
        method.isAccessible = true
        return method.invoke(supervisor, settings) as Boolean
    }
}
