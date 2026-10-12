package com.six2dez.burp.aiagent.mcp

import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * SEC-07 / SC1 — the credential the bind-conflict takeover client presents to whatever holds the MCP
 * port.
 *
 * ## Why this exists
 *
 * Until Phase 25 the takeover client sent `Authorization: Bearer <token>` to the port holder
 * (Finding 7). That token grants full MCP tool access to the operator's Burp — proxy history,
 * repeater, intruder, scanner — and any local process able to bind `127.0.0.1:<mcp port>` before Burp
 * does could simply collect it. The probe cannot prevent that, because **listener identity cannot be
 * established on a loopback port**: in local mode the `X-Burp-AI-Agent: mcp` response header is
 * trivially echoed by any squatter, and in external mode it is deliberately not emitted at all so an
 * unauthenticated scan cannot fingerprint the port (D-02).
 *
 * The answer chosen at execution time (recorded in `25-01-SUMMARY.md` under `## SC1 decision`) is to
 * stop having a secret to leak rather than to keep trying to identify the listener first. The client
 * proves it *possesses* the token instead of disclosing it. A non-holder learns nothing usable from
 * the value; a holder validates it in constant time.
 *
 * ## The three rules a future editor must not break
 *
 *  1. **The token is the HMAC KEY.** It is never the message, and it is never a header value. If you
 *     ever find yourself putting `settings.token` into a request property, Finding 7 has been
 *     reopened — `McpTakeoverSquatterTest` asserts structurally against exactly that.
 *  2. **The window bounds replay; it does not establish identity.** Nothing here tells you who is
 *     listening. It tells you that whoever receives the proof gains nothing durable from it. Real
 *     listener identity for TLS configurations is restored separately by certificate pinning; this
 *     scheme is what covers cleartext local mode, which is the default and which pinning cannot
 *     reach.
 *  3. **Both halves must mint the same message.** [forTarget] runs in the client
 *     (`McpSupervisor.requestRemoteShutdown`) and [accepts] runs in the server (the
 *     `POST /__mcp/shutdown` route in `KtorMcpServerManager`). If the message construction or the
 *     window arithmetic drifts between them, the legitimate takeover silently stops working and the
 *     MCP server stays down after every bind conflict — a reliability regression with a green suite,
 *     unless `McpTakeoverPipelineTest` is kept honest.
 *
 * ## Accepted residual (T-25-04, disposition `accept`)
 *
 * The squatter *does* receive the proof and can replay it within its window — 10 seconds, plus one
 * fallback window, so 20 seconds worst case — to shut down the freshly-bound server. That is a denial
 * of service by a process which is already denying the service by holding the port. A single-use
 * server-side nonce cache was considered and rejected as disproportionate.
 */
object McpTakeoverProof {
    /** Request header carrying the proof. Deliberately not `Authorization`: this is not a bearer secret. */
    const val HEADER = "X-Mcp-Takeover-Proof"

    /**
     * Mints the proof a client presents for `host:port` at `epochMillis`.
     *
     * Deterministic for every instant inside one window, which is what lets the server recompute it
     * without any shared state. The encoder shape (Base64-URL, no padding) matches
     * `McpSettings.generateToken`, so the value is safe in a header without further escaping.
     *
     * `token` must not be blank — a blank key cannot produce a meaningful proof and `SecretKeySpec`
     * rejects an empty key outright. Callers guard first: [accepts] returns false before reaching
     * here, and `McpSupervisor.requestRemoteShutdown` refuses to issue the request at all.
     */
    fun forTarget(
        token: String,
        host: String,
        port: Int,
        epochMillis: Long,
    ): String {
        val mac = Mac.getInstance(HMAC_ALGORITHM)
        mac.init(SecretKeySpec(token.toByteArray(Charsets.UTF_8), HMAC_ALGORITHM))
        val message = "$MESSAGE_PREFIX${host.trim().lowercase()}:$port|${epochMillis / WINDOW_MS}"
        return Base64
            .getUrlEncoder()
            .withoutPadding()
            .encodeToString(mac.doFinal(message.toByteArray(Charsets.UTF_8)))
    }

    /**
     * Server-side acceptance. True when `presented` is the proof for this exact host, port and token
     * in the current window OR in the immediately preceding one.
     *
     * The one-window fallback is not slack for a clock skew — client and holder are always the same
     * machine reading the same `System.currentTimeMillis()`, so no skew is possible (A-25-04). It
     * exists so a legitimate takeover that happens to straddle a window boundary is not rejected
     * milliseconds after it was minted.
     *
     * The blank-token guard mirrors `isAuthorizedBearer`'s SEC-05 5c rule: a blank configured token
     * can never authenticate anything, so it is checked BEFORE any value is computed.
     */
    fun accepts(
        token: String,
        host: String,
        port: Int,
        epochMillis: Long,
        presented: String,
    ): Boolean {
        if (token.isBlank() || presented.isBlank()) return false
        val current = forTarget(token, host, port, epochMillis)
        val previous = forTarget(token, host, port, epochMillis - WINDOW_MS)
        // constantTimeCompare, not a hand-rolled loop: McpAccessControlDecision.kt says so explicitly
        // and the rule is inherited here. Both branches are evaluated as written; short-circuiting on
        // the current window only leaks which of two equally-valid windows matched, which is not a
        // secret.
        return constantTimeCompare(presented, current) || constantTimeCompare(presented, previous)
    }

    /**
     * Window width. Deliberately a file-private constant and NOT an entry in `config/Defaults.kt`:
     * it is one protocol's internal parameter, meaningful only to the two functions above, and it must
     * change in both halves at once or not at all.
     */
    private const val WINDOW_MS = 10_000L
    private const val HMAC_ALGORITHM = "HmacSHA256"

    /**
     * Domain separation. The `v1` segment is a wire-protocol version between two independently
     * installed copies of this extension: bump it only with a deliberate compatibility decision, since
     * there is no negotiation step to fall back on.
     */
    private const val MESSAGE_PREFIX = "burp-ai-agent/mcp-takeover|v1|"
}
