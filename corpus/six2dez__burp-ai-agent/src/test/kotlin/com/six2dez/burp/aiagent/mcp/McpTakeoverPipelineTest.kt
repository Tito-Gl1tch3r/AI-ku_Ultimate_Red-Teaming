package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.config.McpSettings
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.nio.file.Files

/**
 * SEC-07 / SC1 — the legitimate half of the bind-conflict takeover, proven end to end.
 *
 * `McpTakeoverSquatterTest` proves the attacker gets nothing. This class proves the operator does not
 * lose the feature in the process: a REAL [KtorMcpServerManager] on a loopback port must still accept
 * the new proof credential and actually stop, otherwise every ordinary extension reload that hits a
 * bind conflict would leave the MCP server permanently down. That failure mode would be invisible to
 * a mock-based test, which is why this binds a real Netty server.
 *
 * Bounded waiting here is ATTEMPT-bounded, never a fixed sleep and never a wall-clock threshold: this
 * repo has a recorded wall-clock flake class (a 50ms deadline in `RedactionTest` that fails under CPU
 * load), and a parallel-executed suite is exactly the load that reproduces it.
 *
 * Naming note, inherited verbatim from `McpTestServerSupport.kt`: test classes in this package MUST
 * NOT be named `*IntegrationTest`, `*ConcurrencyTest`, `*BackpressureTest`, `*RestartPolicyTest` or
 * `*SupervisionTest`. The `excludeHeavyTests` filter block inside `tasks.test` in `build.gradle.kts`
 * excludes exactly those globs under `-PexcludeHeavyTests=true`, so a security gate wearing one of
 * those suffixes would be silently skipped in a fast PR gate and prove nothing.
 */
class McpTakeoverPipelineTest {
    private val api = McpTestServerSupport.deepStubApi()
    private val supervisor = McpSupervisor(api)

    @AfterEach
    fun tearDown() {
        // Releases the supervisor's scheduler thread and its default (never started) server manager.
        supervisor.shutdown()
    }

    @Test
    fun theProofCredentialTakesOverOurOwnRunningServer() {
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localSettings(port)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                requestRemoteShutdown(settings),
                "The takeover client must be accepted by our own server through the proof header alone. " +
                    "If this is red, the client and server halves of McpTakeoverProof have drifted: the " +
                    "MCP server would stay down after every bind conflict, which is the reliability " +
                    "regression Option A was rejected for.",
            )

            assertTrue(
                awaitServerStopped(port),
                "A 2xx on /__mcp/shutdown is not proof of shutdown — the route responds before it submits " +
                    "the stop. The server must actually stop listening, otherwise the retry that follows a " +
                    "bind conflict would hit the same busy port forever.",
            )
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun aBlankTokenMakesNoRequestAtAll() {
        // A blank configured token cannot key a meaningful proof. The client must fail closed BEFORE
        // opening a connection rather than presenting an empty credential to the port holder.
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localSettings(port, token = "")
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                !requestRemoteShutdown(settings),
                "With a blank token the takeover must be refused client-side",
            )
            assertTrue(
                !awaitServerStopped(port, maxAttempts = SHORT_ATTEMPTS),
                "The server must still be listening: a blank-token takeover must not have been attempted",
            )
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun theProofCredentialAlsoTakesOverOurOwnExternalModeServer() {
        // DISCOVERED DURING EXECUTION, not written into the plan. The plan's server-side change is
        // route-level only, but in EXTERNAL mode the McpAccessControl gate runs in the Plugins phase —
        // before routing — and `evaluateExternal` denies every non-health path that does not carry a
        // valid bearer. A proof-only request would therefore have been 401'd before the shutdown route
        // ever saw it, so removing the bearer from the client would have silently broken external-mode
        // takeover: the MCP server would stay down after every bind conflict in the one configuration
        // where the operator is least able to notice. The gate now recognises the proof form for the
        // shutdown path, which is what makes the route's "401 only when both forms fail" true.
        val keystoreDir = Files.createTempDirectory("mcp-takeover-ks")
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.externalTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                requestRemoteShutdown(settings),
                "External-mode takeover must still succeed through the proof credential alone. If this " +
                    "is red, the access-control gate is rejecting the proof before the shutdown route " +
                    "runs and the MCP server will stay down after every external-mode bind conflict.",
            )
            assertTrue(awaitServerStopped(port, tls = true), "The external-mode server must actually stop listening")
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun anExternalModeShutdownWithNoCredentialIsStillRejected() {
        // The other half of the gate change: recognising the proof must not have opened the shutdown
        // route to an unauthenticated caller. An attacker who does not hold the token gets 401 exactly
        // as before, and a garbage proof is no better than none.
        val keystoreDir = Files.createTempDirectory("mcp-takeover-ks")
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.externalTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)
            val client = McpTestServerSupport.trustAllClient()
            val url = "${McpTestServerSupport.baseUrl(port, tls = true)}$SHUTDOWN_PATH"

            val bare =
                Request
                    .Builder()
                    .url(url)
                    .post(EMPTY_BODY)
                    .build()
            client
                .newCall(bare)
                .execute()
                .use { assertEquals(401, it.code, "An unauthenticated external shutdown must still be refused") }

            client
                .newCall(
                    Request
                        .Builder()
                        .url(url)
                        .post(EMPTY_BODY)
                        .header(McpTakeoverProof.HEADER, "not-a-real-proof")
                        .build(),
                ).execute()
                .use { assertEquals(401, it.code, "A forged proof must be refused just like no credential at all") }

            assertTrue(
                !awaitServerStopped(port, maxAttempts = SHORT_ATTEMPTS, tls = true),
                "The server must still be listening after two refused shutdown attempts",
            )
        } finally {
            manager.shutdown()
        }
    }

    /**
     * Reaches the private shutdown client by reflection, exactly as `McpSupervisorProbeTest.probe`
     * reaches `probeExistingServer`. The name is `requestRemoteShutdown` and not the Phase-22-era
     * `requestRemoteShutdownWithToken`: the token is no longer on the wire, so the old name was a lie.
     */
    private fun requestRemoteShutdown(settings: McpSettings): Boolean {
        val method = supervisor.javaClass.getDeclaredMethod("requestRemoteShutdown", McpSettings::class.java)
        method.isAccessible = true
        return method.invoke(supervisor, settings) as Boolean
    }

    /**
     * Polls `/__mcp/health` until the connection fails, bounded by an ATTEMPT COUNT rather than by a
     * wall-clock deadline. Returns true once the port stops answering.
     */
    private fun awaitServerStopped(
        port: Int,
        maxAttempts: Int = DEFAULT_ATTEMPTS,
        tls: Boolean = false,
    ): Boolean {
        val client = if (tls) McpTestServerSupport.trustAllClient() else McpTestServerSupport.plainClient()
        val request =
            Request
                .Builder()
                .url("${McpTestServerSupport.baseUrl(port, tls)}$HEALTH_PATH")
                .get()
                .build()
        repeat(maxAttempts) {
            val stillListening =
                try {
                    client.newCall(request).execute().use { true }
                } catch (_: Exception) {
                    false
                }
            if (!stillListening) return true
            Thread.sleep(POLL_INTERVAL_MS)
        }
        return false
    }

    private companion object {
        private const val DEFAULT_ATTEMPTS = 200
        private const val SHORT_ATTEMPTS = 5
        private const val POLL_INTERVAL_MS = 50L
        private val EMPTY_BODY = ByteArray(0).toRequestBody()
    }
}
