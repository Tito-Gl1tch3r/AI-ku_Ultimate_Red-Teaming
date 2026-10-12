package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.config.McpSettings
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.mockito.kotlin.argumentCaptor
import org.mockito.kotlin.atLeast
import org.mockito.kotlin.verify
import java.lang.reflect.Method
import java.net.URL
import java.net.URLConnection
import java.net.URLStreamHandler
import java.nio.file.Files
import java.nio.file.Path
import java.security.Principal
import java.security.cert.Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLSocketFactory

/** Declared once so the fixture's host and the diagnostic predicate cannot drift apart. */
private const val NON_LOOPBACK_HOST = McpTestServerSupport.DEFAULT_NON_LOOPBACK_HOST

/**
 * SEC-07 / SC5 — the truth table of `McpSupervisor.openConnection`'s loopback TLS branch, asserted
 * through a fake connection so these stay fast and network-free. The handshake itself is proven
 * against a real server in `McpTakeoverCertificatePinTest`; wiring and handshake are different
 * questions and both need answering.
 *
 * The keystore is generated once into a temp directory through `McpTls.resolve`, never at the
 * extension's real certificate directory under the user's home — `resolve` auto-generates into
 * whatever path it is handed.
 */
@Suppress("DEPRECATION")
class McpSupervisorConnectionTest {
    companion object {
        private lateinit var keystoreDir: Path

        @JvmStatic
        @BeforeAll
        fun createKeystore() {
            keystoreDir = Files.createTempDirectory("mcp-conn-ks")
            // Generates the PKCS12 the pin is later computed from.
            McpTls.resolve(tlsSettings())
        }

        @JvmStatic
        @AfterAll
        fun deleteKeystoreDir() {
            keystoreDir.toFile().deleteRecursively()
        }

        private fun tlsSettings(): McpSettings = McpTestServerSupport.localTlsSettings(port = 8443, keystoreDir = keystoreDir)

        /**
         * 25-REVIEW WR-03. The keystore is the SAME readable one the loopback rows use, which is the
         * whole point: the non-loopback limb must be taken because of the HOST, not because no pin
         * could be read. A fixture with an absent keystore would pass for the wrong reason.
         */
        private fun nonLoopbackTlsSettings(): McpSettings =
            McpTestServerSupport
                .nonLoopbackTlsSettings(port = 8443, keystoreDir = keystoreDir)
                .copy(tlsKeystorePassword = "test-pass")
    }

    // Deep-stubbed rather than a bare mock: the fail-closed branch logs one Output line naming the
    // keystore path, and a bare mock returns null from api.logging(). Held as a field so the Output
    // lines can be captured — what a branch LOGS is the operator-visible half of its behaviour, and
    // 25-REVIEW WR-03 is precisely a case where the wiring was right and the log line was wrong.
    private val api = McpTestServerSupport.deepStubApi()
    private val supervisor = McpSupervisor(api)

    @Test
    fun openConnection_loopbackTls_setsCustomTrustAndHostnameVerifier() {
        val url = URL(null, "https://localhost:8443/test", connectionHandler())
        val connection = invokeOpenConnection(url, tlsSettings()) as FakeHttpsURLConnection

        assertNotNull(connection.assignedSslSocketFactory)
        assertNotNull(connection.assignedHostnameVerifier)
    }

    @Test
    fun openConnection_loopbackTlsWithoutAPin_installsNoOverrideAtAll() {
        // T-25-13, and the row that would silently regress if somebody reintroduced a trust-all
        // fallback: the other three rows all still pass under one. No readable keystore means no
        // certificate can be named, so nothing is installed and the JDK defaults refuse the
        // self-signed listener.
        val url = URL(null, "https://localhost:8443/test", connectionHandler())
        val noKeystore = tlsSettings().copy(tlsKeystorePath = keystoreDir.resolve("absent.p12").toString())
        val connection = invokeOpenConnection(url, noKeystore) as FakeHttpsURLConnection

        assertNull(
            connection.assignedSslSocketFactory,
            "A missing keystore must leave the JDK's own socket factory in place, not a permissive one",
        )
        assertNull(
            connection.assignedHostnameVerifier,
            "A missing keystore must leave the JDK's own hostname verifier in place",
        )
    }

    @Test
    fun openConnection_nonLoopbackTls_doesNotOverrideTlsVerifier() {
        val url = URL(null, "https://example.com:8443/test", connectionHandler())
        val connection = invokeOpenConnection(url, tlsSettings()) as FakeHttpsURLConnection

        assertNull(connection.assignedSslSocketFactory)
        assertNull(connection.assignedHostnameVerifier)
    }

    @Test
    fun openConnection_loopbackWithoutTls_doesNotOverrideTlsVerifier() {
        val url = URL(null, "https://localhost:8443/test", connectionHandler())
        val connection = invokeOpenConnection(url, tlsSettings().copy(tlsEnabled = false)) as FakeHttpsURLConnection

        assertNull(connection.assignedSslSocketFactory)
        assertNull(connection.assignedHostnameVerifier)
    }

    @Test
    fun openConnection_nonLoopbackTls_saysWhyTheTakeoverWasNotAttempted() {
        // 25-REVIEW WR-03. Before this, a non-loopback bind fell silently out of the TLS branch, the
        // JDK default trust store refused this extension's own CN=burp-mcp certificate, and
        // handleBindFailure told the operator "no compatible MCP server was detected" — the opposite
        // of what happened, with no retry scheduled. The wiring assertion above cannot catch that:
        // installing nothing is CORRECT here. What was wrong was the silence.
        val url = URL(null, "https://$NON_LOOPBACK_HOST:8443/test", connectionHandler())
        val connection = invokeOpenConnection(url, nonLoopbackTlsSettings()) as FakeHttpsURLConnection

        assertNull(connection.assignedSslSocketFactory, "The host gate is unchanged: still no override off loopback")
        assertNull(connection.assignedHostnameVerifier, "The host gate is unchanged: still no override off loopback")

        val diagnostics = outputLines().filter(::isNonLoopbackTlsDiagnostic)
        assertEquals(
            1,
            diagnostics.size,
            "Exactly one non-loopback TLS diagnostic must be emitted. Lines seen: ${outputLines()}",
        )
    }

    @Test
    fun openConnection_loopbackTls_doesNotEmitTheNonLoopbackDiagnostic() {
        // The diagnostic must be specific to the branch it describes. A message that also fires on a
        // loopback bind would send the operator to free a port that is not the problem.
        invokeOpenConnection(URL(null, "https://localhost:8443/test", connectionHandler()), tlsSettings())

        assertTrue(
            outputLines().none(::isNonLoopbackTlsDiagnostic),
            "A loopback bind with a readable pin must emit no non-loopback diagnostic. Lines seen: ${outputLines()}",
        )
    }

    @Test
    fun openConnection_loopbackTlsWithoutAPin_stillEmitsItsOwnFailClosedLineAndNotTheNewOne() {
        // T-25-16's line is the one an operator acts on when the keystore has moved. It must survive
        // the restructuring, and it must stay distinguishable from the new one: the remedies differ —
        // fix the keystore path there, free the port manually here.
        val noKeystore = tlsSettings().copy(tlsKeystorePath = keystoreDir.resolve("absent.p12").toString())
        invokeOpenConnection(URL(null, "https://localhost:8443/test", connectionHandler()), noKeystore)

        val lines = outputLines()
        assertTrue(
            lines.any { it.contains("no pinned certificate could be read") },
            "The fail-closed keystore diagnostic must still be emitted. Lines seen: $lines",
        )
        assertTrue(
            lines.none(::isNonLoopbackTlsDiagnostic),
            "A loopback bind must never be reported as a non-loopback one. Lines seen: $lines",
        )
    }

    @Test
    fun openConnection_nonLoopbackWithoutTls_emitsNoTlsDiagnosticAtAll() {
        // Nothing about TLS applies when TLS is off, so neither TLS diagnostic belongs here. This is
        // the row that catches a future edit hoisting the host check out of the `tlsEnabled` guard.
        val url = URL(null, "https://$NON_LOOPBACK_HOST:8443/test", connectionHandler())
        val connection =
            invokeOpenConnection(url, nonLoopbackTlsSettings().copy(tlsEnabled = false)) as FakeHttpsURLConnection

        assertNull(connection.assignedSslSocketFactory)
        assertNull(connection.assignedHostnameVerifier)
        val lines = outputLines()
        assertTrue(
            lines.none(::isNonLoopbackTlsDiagnostic) && lines.none { it.contains("no pinned certificate could be read") },
            "TLS off means no TLS diagnostic of either kind. Lines seen: $lines",
        )
    }

    /**
     * Matched on MEANING rather than on a whole hard-coded sentence: the line must name the host the
     * operator configured and must say that pinning is loopback-scoped. Rewording it stays green;
     * dropping either fact — which is what would leave the operator misinformed — turns it red.
     */
    private fun isNonLoopbackTlsDiagnostic(line: String): Boolean =
        line.contains("takeover", ignoreCase = true) &&
            line.contains("loopback", ignoreCase = true) &&
            line.contains(NON_LOOPBACK_HOST)

    /** Every `logToOutput` argument this test's supervisor emitted, in order. */
    private fun outputLines(): List<String> {
        val captor = argumentCaptor<String>()
        verify(api.logging(), atLeast(0)).logToOutput(captor.capture())
        return captor.allValues
    }

    private fun invokeOpenConnection(
        url: URL,
        settings: McpSettings,
    ): URLConnection {
        val method: Method =
            supervisor.javaClass.getDeclaredMethod(
                "openConnection",
                URL::class.java,
                McpSettings::class.java,
            )
        method.isAccessible = true
        return method.invoke(supervisor, url, settings) as URLConnection
    }

    private fun connectionHandler(): URLStreamHandler =
        object : URLStreamHandler() {
            override fun openConnection(url: URL): URLConnection = FakeHttpsURLConnection(url)
        }

    private class FakeHttpsURLConnection(
        url: URL,
    ) : HttpsURLConnection(url) {
        var assignedSslSocketFactory: SSLSocketFactory? = null
        var assignedHostnameVerifier: HostnameVerifier? = null

        override fun connect() = Unit

        override fun disconnect() = Unit

        override fun usingProxy(): Boolean = false

        override fun setSSLSocketFactory(sf: SSLSocketFactory?) {
            assignedSslSocketFactory = sf
        }

        override fun getSSLSocketFactory(): SSLSocketFactory? = assignedSslSocketFactory

        override fun setHostnameVerifier(v: HostnameVerifier?) {
            assignedHostnameVerifier = v
        }

        override fun getHostnameVerifier(): HostnameVerifier? = assignedHostnameVerifier

        override fun getCipherSuite(): String = "TLS_FAKE"

        override fun getLocalCertificates(): Array<Certificate>? = null

        override fun getServerCertificates(): Array<Certificate>? = null

        override fun getPeerPrincipal(): Principal? = null

        override fun getLocalPrincipal(): Principal? = null
    }
}
