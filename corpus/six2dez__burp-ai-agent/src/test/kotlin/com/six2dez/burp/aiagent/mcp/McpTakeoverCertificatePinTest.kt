package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.config.McpSettings
import okhttp3.Request
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import java.io.File
import java.nio.file.Files
import java.nio.file.Path

/**
 * SEC-07 / SC5 — the loopback TLS takeover client trusts exactly one certificate.
 *
 * `McpSupervisorConnectionTest` proves the WIRING: that a socket factory and a hostname verifier are
 * installed on the loopback TLS branch and withheld everywhere else. Wiring is not a handshake, and a
 * pin that is installed but never discriminates looks identical to no pin at all in a green run.
 * Every test here therefore drives a REAL [KtorMcpServerManager] over TLS on a loopback port and lets
 * the JDK's TLS stack decide.
 *
 * Three cases, and the negative two are the load-bearing ones:
 *  - the legitimate takeover still succeeds, so a bind conflict under TLS does not leave the MCP
 *    server permanently down;
 *  - a real second self-signed certificate, generated through the same `keytool` path, is refused and
 *    the server it was aimed at is still running afterwards;
 *  - no readable keystore means no TLS override at all — fail closed, and no key material created as
 *    a side effect of looking for one.
 *
 * Bounded waiting here is ATTEMPT-bounded. There is no `Thread.sleep` and no wall-clock threshold in
 * this file at all: this repo has a recorded wall-clock flake class (a 50 ms deadline in
 * `RedactionTest` that fails under CPU load) and a parallel-executed suite is exactly the load that
 * reproduces it. Pacing comes from the HTTP round trip each attempt performs.
 *
 * Naming note, inherited verbatim from `McpTestServerSupport.kt`: test classes in this package MUST
 * NOT be named `*IntegrationTest`, `*ConcurrencyTest`, `*BackpressureTest`, `*RestartPolicyTest` or
 * `*SupervisionTest`. The `excludeHeavyTests` filter block inside `tasks.test` in `build.gradle.kts`
 * excludes exactly those globs under `-PexcludeHeavyTests=true`, so a security gate wearing one of
 * those suffixes would be silently skipped in a fast PR gate and prove nothing.
 */
class McpTakeoverCertificatePinTest {
    companion object {
        private const val HTTP_OK = 200

        /**
         * Generous on purpose: the shutdown route submits `server.stop(1000, 5000)`, so the port stays
         * bound for a grace period. Each attempt costs a TLS round trip, so the bound is a work budget
         * rather than a time budget and it tightens automatically on a fast machine.
         */
        private const val STOP_POLL_ATTEMPTS = 4000

        /**
         * Created once per class so `keytool` auto-generation (1-2 s) runs once rather than per test.
         * A test must NEVER point `tlsKeystorePath` at the extension's real certificate directory
         * under the user's home: `McpTls.resolve` auto-generates into whatever path it is handed, so a
         * test naming it would silently overwrite the operator's own keystore. Always a
         * caller-supplied temp directory, deleted in teardown.
         */
        private lateinit var keystoreDir: Path

        @JvmStatic
        @BeforeAll
        fun createKeystoreDir() {
            keystoreDir = Files.createTempDirectory("mcp-pin-ks")
        }

        @JvmStatic
        @AfterAll
        fun deleteKeystoreDir() {
            // Review finding IN-07: a leaked temp keystore is exactly what this must not do.
            keystoreDir.toFile().deleteRecursively()
        }
    }

    private val supervisor = McpSupervisor(McpTestServerSupport.deepStubApi())

    @AfterEach
    fun tearDown() {
        // Releases the supervisor's scheduler thread and its default (never started) server manager.
        supervisor.shutdown()
    }

    @Test
    fun aLegitimateTlsTakeoverSucceedsAgainstThePinnedCertificate() {
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertTrue(
                requestRemoteShutdown(settings),
                "A TLS takeover against our OWN server must still succeed: the certificate it presents is " +
                    "the one in the keystore these settings name, so the pin matches. If this is red, a " +
                    "bind conflict under TLS leaves the MCP server permanently down — the reliability " +
                    "regression the fail-closed branch must never cause in the legitimate case.",
            )

            assertTrue(
                awaitServerStopped(port),
                "A 2xx on the shutdown route is not proof of shutdown — the route responds before it " +
                    "submits the stop. The server must actually stop listening, otherwise the retry that " +
                    "follows a bind conflict hits the same busy port forever.",
            )
        } finally {
            manager.shutdown()
        }
    }

    @Test
    fun aForeignCertificateIsRefusedAndTheServerSurvives() {
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        // A SECOND, unrelated keystore, minted through the same keytool path the server uses. Nothing
        // about it is special except that it is not the certificate the running server presents —
        // which is exactly the position a local process squatting the MCP port is in.
        val foreignDir = Files.createTempDirectory("mcp-pin-foreign-ks")
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            val foreignSettings =
                settings.copy(
                    tlsKeystorePath = foreignDir.resolve("foreign.p12").toString(),
                    tlsKeystorePassword = "foreign-pass",
                )
            McpTls.resolve(foreignSettings)

            assertFalse(
                requestRemoteShutdown(foreignSettings),
                "The takeover must be refused when the pin computed from the client's own keystore does " +
                    "not match the certificate the listener presents. Everything else about this request " +
                    "is valid — same token, same host, same port, so the proof credential is accepted — " +
                    "which is what leaves the certificate as the only thing that can refuse it.",
            )

            // The load-bearing assertion. A false return alone would not distinguish "the pin refused a
            // foreign certificate" from "the test never connected at all", so the server's survival is
            // asserted independently of the return value.
            assertTrue(
                serverAnswersHealth(port),
                "The server must still be running: a refused handshake must not take down the server it " +
                    "was aimed at, which is the whole point of pinning rather than trusting everything",
            )
        } finally {
            manager.shutdown()
            foreignDir.toFile().deleteRecursively()
        }
    }

    @Test
    fun noPinAvailableInstallsNoOverrideAndFailsClosed() {
        val port = McpTestServerSupport.freePort()
        val settings = McpTestServerSupport.localTlsSettings(port, keystoreDir)
        val manager = KtorMcpServerManager(McpTestServerSupport.deepStubApi())
        val missingKeystore = keystoreDir.resolve("does-not-exist.p12").toString()
        try {
            McpTestServerSupport.startAndAwaitRunning(manager, settings)

            assertFalse(
                requestRemoteShutdown(settings.copy(tlsKeystorePath = missingKeystore)),
                "With no readable keystore the client can name no certificate, so it must install no TLS " +
                    "override and fail closed against the JDK defaults — never fall back to trusting " +
                    "whatever the listener presents. A pin-when-available, trust-everything-otherwise " +
                    "fallback would leave the original weakness reachable by deleting one file (T-25-13).",
            )

            assertTrue(
                serverAnswersHealth(port),
                "The server must still be running after a fail-closed takeover attempt",
            )

            assertFalse(
                File(missingKeystore).exists(),
                "Computing a pin must never create key material. This assertion is what pins the " +
                    "'pinnedLeafSha256 never generates' rule to observable behaviour instead of to a code " +
                    "review: McpTls.resolve would have auto-generated this file, which is why the reader " +
                    "is deliberately not implemented in terms of it (T-25-14).",
            )
        } finally {
            manager.shutdown()
        }
    }

    /**
     * Reaches the private shutdown client by reflection, exactly as `McpSupervisorProbeTest.probe`
     * reaches `probeExistingServer`.
     */
    private fun requestRemoteShutdown(settings: McpSettings): Boolean {
        val method = supervisor.javaClass.getDeclaredMethod("requestRemoteShutdown", McpSettings::class.java)
        method.isAccessible = true
        return method.invoke(supervisor, settings) as Boolean
    }

    /** One TLS health request. True when the server answered it. */
    private fun serverAnswersHealth(port: Int): Boolean =
        McpTestServerSupport
            .trustAllClient()
            .newCall(healthRequest(port))
            .execute()
            .use { it.code == HTTP_OK }

    /**
     * Polls the TLS health route until the connection fails, bounded by an ATTEMPT COUNT rather than
     * by a wall-clock deadline. Each attempt performs a real HTTP round trip, which is what paces the
     * loop; there is deliberately no sleep. Returns true once the port stops answering.
     */
    private fun awaitServerStopped(port: Int): Boolean {
        val client = McpTestServerSupport.trustAllClient()
        val request = healthRequest(port)
        repeat(STOP_POLL_ATTEMPTS) {
            val stillListening =
                try {
                    client.newCall(request).execute().use { true }
                } catch (_: Exception) {
                    false
                }
            if (!stillListening) return true
        }
        return false
    }

    private fun healthRequest(port: Int): Request =
        Request
            .Builder()
            .url("${McpTestServerSupport.baseUrl(port, tls = true)}$HEALTH_PATH")
            .get()
            .build()
}
