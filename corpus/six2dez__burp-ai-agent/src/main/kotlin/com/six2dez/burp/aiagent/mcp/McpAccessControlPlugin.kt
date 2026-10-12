// The file's primary export is the `McpAccessControl` plugin val, not the config class that happens
// to be its only top-level CLASS declaration — detekt's MatchingDeclarationName only looks at
// classes. Suppressed at file level rather than added to detekt-baseline.xml, which QUAL-07 forbids
// from growing.
@file:Suppress("MatchingDeclarationName")

package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.config.McpSettings
import io.ktor.server.application.ApplicationCall
import io.ktor.server.application.createApplicationPlugin
import io.ktor.server.request.httpMethod
import io.ktor.server.request.path
import io.ktor.server.response.respond

// SEC-04 / F1: the Ktor half of the MCP access-control gate. This file is the FIX for the bypass —
// the previous checks lived in an `intercept(ApplicationCallPipeline.Call)` block registered after
// `routing {}`, which put them behind RoutingRoot's own Call-phase interceptor, so every resolved
// route (including the SDK's /sse and /message) was served before they ran.
//
// `PluginBuilder.onCall` attaches to `ApplicationCallPipeline.ApplicationPhase.Plugins`, and
// `ApplicationCallPipeline` is constructed with the phases Setup, Monitoring, Plugins, Call,
// Fallback in that literal order. Both facts are fixed at pipeline construction, so this gate runs
// before routing REGARDLESS of where `install(McpAccessControl)` sits in the module lambda — the
// class of bug being fixed cannot recur through a future re-ordering of that lambda.
//
// All security logic lives in McpAccessControlDecision.kt and all observability lives behind
// [McpAccessControlConfig.onBlocked]; this file only adapts an ApplicationCall to RequestFacts.

/**
 * Configuration for [McpAccessControl].
 *
 * [settings] is passed through the plugin config rather than captured from an enclosing closure so
 * that the immutability of the snapshot is explicit and the gate is configurable from a test.
 *
 * [onBlocked] receives the whole [GateDecision.Deny]; the caller supplies the mode flag and the
 * clock, which keeps time-reading out of both this plugin and [McpBlockedRequestReporter]. It is
 * `lateinit` rather than defaulted to an empty lambda ON PURPOSE: a default no-op would let a caller
 * silently drop the D-06 audit event, the D-07 sanitization, the D-09 rate-limited Output line and
 * the D-10 hashing while every compile-time and static check still passed. `lateinit` turns that
 * omission into a startup crash instead. Do not give it a default value.
 */
internal class McpAccessControlConfig {
    lateinit var settings: McpSettings
    lateinit var onBlocked: (GateDecision.Deny) -> Unit
}

/**
 * SC3. Values are byte-identical to the four headers the deleted Call-phase interceptor appended.
 */
private val SECURITY_HEADERS: List<Pair<String, String>> =
    listOf(
        "X-Frame-Options" to "DENY",
        "X-Content-Type-Options" to "nosniff",
        "Referrer-Policy" to "same-origin",
        "Content-Security-Policy" to "default-src 'none'",
    )

/**
 * The MCP access-control gate. Evaluates every inbound call in the `Plugins` phase, denies with a
 * bare status (D-08), and appends the four security headers on the allow path.
 *
 * Runs on Netty event-loop threads, so there is deliberately no blocking I/O, no monitor lock, no
 * Swing access and no file write anywhere in this file.
 */
internal val McpAccessControl =
    createApplicationPlugin("McpAccessControl", ::McpAccessControlConfig) {
        val settings = pluginConfig.settings
        val onBlocked = pluginConfig.onBlocked

        onCall { call ->
            // SEC-04 / RESEARCH pitfall P4 — LOAD-BEARING, do not remove.
            // Ktor's CORS plugin is also a Plugins-phase plugin (it too registers through
            // PluginBuilder.onCall), so it shares this phase with the gate and runs first because it
            // is installed first. It was verified by execution that when a first same-phase
            // interceptor responds, the SECOND ONE STILL EXECUTES — responding does not cancel the
            // rest of the phase. Without this guard the gate would respond a second time after CORS
            // had already answered a preflight or rejected a foreign origin.
            if (!call.response.isCommitted) {
                when (val decision = evaluate(requestFacts(call), settings)) {
                    is GateDecision.Deny -> {
                        // D-06/D-07/D-09/D-10 all hang off this single call. An empty lambda here
                        // would compile, pass detekt and leave blocked requests invisible.
                        onBlocked(decision)
                        // D-08: bare status, no body, no WWW-Authenticate. The pipeline is NOT
                        // explicitly finished here, and does not need to be:
                        // RoutingNode.buildPipeline wraps every registered handle{} body in
                        // `if (call.isHandled) return`, and isHandled == response.isCommitted, so
                        // responding here provably skips the handler (verified: a route-side flag
                        // was still false 700 ms after the client had received the 401). The
                        // CallContext method that would end the pipeline early also carries
                        // Kotlin's internal name-mangling suffix and is not callable from here.
                        call.respond(decision.status)
                    }
                    // SC3: appended from the pre-routing Plugins phase, which is what makes the
                    // headers deterministic — they land on matched-route 200s and on the
                    // text/event-stream SSE response over both HTTP/1.1 and HTTP/2. Appending after
                    // a handler had committed was measured to work over TLS/HTTP-2 and silently fail
                    // over cleartext HTTP/1.1 on the same code path (RESEARCH pitfall P3). The
                    // respond-side plugin hook is the wrong seam: it attaches to
                    // ApplicationSendPipeline.Transform and would also fire for the 401/403.
                    GateDecision.Allow -> appendSecurityHeaders(call)
                }
            }
        }
    }

/**
 * The literal `RequestConnectionPoint.version` value that identifies an HTTP/2 request. Measured, not
 * assumed: a probe against this build's `ktor-server-netty-jvm` observed exactly `HTTP/2` on a TLS
 * connector and `HTTP/1.1` on a cleartext one.
 */
private const val HTTP_2_VERSION = "HTTP/2"

/**
 * Resolved as the request authority when the HTTP/2 connection point cannot be read. Deliberately
 * contains `<` and `>`, which are outside the host character class of the shared authority parser in
 * McpAccessControlDecision.kt, so it is REJECTED and the request is denied. Pinned by
 * `McpLocalTlsAuthorityPipelineTest.unresolvableAuthoritySentinel_isRejectedByTheSharedPredicate` —
 * were this ever accepted as loopback, a malformed authority would turn into an allow.
 */
private const val UNRESOLVABLE_AUTHORITY = "<unresolved-authority>"

/**
 * Lifts the attacker-controlled inputs out of the call. Values are kept RAW here: `evaluate` must
 * see what the client actually sent, and sanitization belongs to the log boundary (D-07).
 *
 * Uses `path()` and not `uri`, so a query string cannot change the [HEALTH_PATH] comparison.
 *
 * ## Why `host` is not just the `Host` header
 *
 * Reading only `headers["Host"]` made the whole local-mode DNS-rebinding branch dead code over
 * HTTP/2, in a user-reachable configuration: local mode with the independent "Enable TLS" option on
 * binds an `sslConnector`, Netty advertises `h2` over ALPN, and a foreign authority was measured
 * reaching `200` on `/__mcp/health` and `200` on `/sse` while the identical HTTP/1.1 request got
 * `403`. Two engine behaviours combine to cause it: Ktor 3.1.3 does not synthesise a `Host` header
 * from HTTP/2's `:authority`, and its Netty h2 request implementation builds the Ktor headers map by
 * iterating Netty's `Http2Headers` while SKIPPING any name whose first character is `:` — so every
 * pseudo-header is filtered out and `headers[":authority"]` is ALWAYS null. Reading the pseudo-header
 * from the headers map cannot work; the raw `Http2Headers` is not reachable either, because the class
 * holding it is declared `internal` in the Ktor module. The connection point is the only public seam
 * that surfaces `:authority` at all.
 *
 * The connection point is read through `local` rather than `origin` on purpose. `origin` resolves to
 * `attributes.getOrNull(MutableOriginConnectionPointKey) ?: local`, which means it becomes
 * client-controllable through `X-Forwarded-Host` the moment anyone installs `ForwardedHeaders` or
 * `XForwardedHeaders`. A DNS-rebinding gate must never read a client-overridable authority. The two
 * are the same object today (`KtorMcpServerManager` installs no forwarded-headers plugin); `local`
 * keeps that from silently becoming a bypass later.
 *
 * The fallback is gated to HTTP/2 and MUST STAY THAT WAY — do not "simplify" it by dropping the
 * version test. On HTTP/1.1 the connection point coalesces an ABSENT `Host` header into the server's
 * OWN listening socket, which is loopback: a raw HTTP/1.1 request carrying no `Host` at all was
 * measured yielding `serverHost = localhost` plus the bound port. Applying the fallback there would
 * hand the gate the server's own authority, pass the loopback check, and re-open the exact fail-open
 * being closed — a Host-less HTTP/1.1 request would go from denied to allowed.
 *
 * The port read is guarded because it can THROW rather than fail: the HTTP/2 connection point's port
 * getter calls `Integer.parseInt` on the substring after the first `:` with no exception handler, so
 * an attacker-supplied `:authority` such as `evil.example:abc` would raise `NumberFormatException` on
 * a Netty event-loop thread and surface as a `500` instead of a denial. On a guarded failure the
 * authority resolves to [UNRESOLVABLE_AUTHORITY], which the shared parser rejects — so the outcome is
 * a denial, and the audit payload plus the Output line get a diagnosable marker instead of a silent
 * allow.
 *
 * ## Residuals (accepted, all fail-closed except residual 1)
 *
 * 1. An HTTP/2 request with `:authority` ABSENT coalesces to the server's own socket and is therefore
 *    ALLOWED. This is not closable with Ktor's public API, because the raw `Http2Headers` sits behind
 *    a class the Ktor module declares `internal`, so absent and loopback-valued authorities are
 *    indistinguishable from here. RFC 9113 makes a request carrying neither `:authority` nor `host`
 *    malformed, so a conforming client and intermediary will not produce one.
 * 2. A bracketed IPv6 `:authority` is split on its FIRST colon by the HTTP/2 connection point, so
 *    `[::1]:9876` yields `[` and the original authority cannot be reconstructed — the request is
 *    DENIED. (The HTTP/1.1 connection point splits on the LAST colon and is bracket-safe, which is
 *    why this asymmetry exists at all.) `McpSettings.host` defaults to `127.0.0.1`, so this is
 *    reachable only for an operator who binds MCP to `::1` AND enables TLS AND uses an h2 client; the
 *    outcome is fail-closed.
 * 3. A PORTLESS `:authority` acquires the scheme's default port from the connection point, whose port
 *    getter falls back through `substringAfter(":", <defaultPort>)`. So HTTP/2 DENIES
 *    `:authority: localhost` — resolved as `localhost:443` over TLS, a port mismatch — where HTTP/1.1
 *    ALLOWS `Host: localhost` (empty port capture, null port, comparison skipped). Fail-closed, and a
 *    behavioural asymmetry between the two transports rather than a defect in either.
 */
private fun requestFacts(call: ApplicationCall): RequestFacts =
    RequestFacts(
        method = call.request.httpMethod.value,
        path = call.request.path(),
        origin = call.request.headers["Origin"],
        host = call.request.headers["Host"] ?: http2Authority(call),
        referer = call.request.headers["Referer"],
        userAgent = call.request.headers["User-Agent"],
        authorization = call.request.headers["Authorization"],
        takeoverProof = call.request.headers[McpTakeoverProof.HEADER],
        // The ONLY clock read on the gate path, and it lives here rather than in `evaluate` so the
        // decision core stays pure by contract (SEC-07).
        epochMillis = System.currentTimeMillis(),
    )

/**
 * Reconstructs `host:port` from the HTTP/2 connection point, or null when the request is not HTTP/2.
 *
 * Expression-bodied with zero `return` statements on purpose: detekt.yml overrides only `LongMethod`,
 * `LongParameterList`, `MaxLineLength` and `FunctionNaming`, so `ReturnCount` runs at its default max
 * of 2, and QUAL-07 forbids growing `detekt-baseline.xml` to work around a rule this code can satisfy.
 *
 * See [requestFacts] for why the HTTP/2 gate, the `local` read and the catch are each load-bearing.
 * `RuntimeException` rather than `Exception` keeps an `Error` propagating, and the `_` binding is what
 * detekt's `SwallowedException` / `TooGenericExceptionCaught` allowed-name regex accepts.
 */
private fun http2Authority(call: ApplicationCall): String? =
    if (call.request.local.version != HTTP_2_VERSION) {
        null
    } else {
        try {
            "${call.request.local.serverHost}:${call.request.local.serverPort}"
        } catch (_: RuntimeException) {
            UNRESOLVABLE_AUTHORITY
        }
    }

/**
 * `ResponseHeaders.append` does not deduplicate, so each header is appended only when absent. That
 * keeps a future route which sets one of these itself from producing a doubled header.
 */
private fun appendSecurityHeaders(call: ApplicationCall) {
    SECURITY_HEADERS.forEach { (name, value) ->
        if (call.response.headers[name] == null) {
            call.response.headers.append(name, value)
        }
    }
}
