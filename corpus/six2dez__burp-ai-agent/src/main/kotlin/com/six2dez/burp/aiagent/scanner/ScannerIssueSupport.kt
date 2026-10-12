package com.six2dez.burp.aiagent.scanner

import burp.api.montoya.scanner.audit.issues.AuditIssueSeverity
import com.six2dez.burp.aiagent.redact.RedactionPolicy

object ScannerIssueSupport {
    /**
     * (PRIV-05) 28-01 / D-28-01 — the truncation bound applied to an injection point's original
     * value before it is written into the issue detail.
     *
     * Named rather than left as the bare `100` it was at `ActiveAiScanner.kt:1239` because standing
     * rule (vi) requires a source-derivable bound to be DERIVABLE BY A TEST. A literal buried in a
     * string template is not.
     */
    internal const val ORIGINAL_VALUE_MAX_CHARS = 100

    /**
     * (PRIV-05) 28-01 — the marker written in place of a stripped cookie value.
     *
     * The text is READ FROM the marker `McpToolHelpers.sanitizeParameters` and `sanitizeHeaders`
     * already write for a stripped cookie (`McpToolHelpers.kt:393`), not invented here, so a reader
     * meets ONE vocabulary across every cookie control in the product.
     */
    internal const val INJECTION_VALUE_STRIPPED_MARKER = "[STRIPPED]"

    /**
     * (PRIV-05) 28-01 — the truncation bound on the payload rendered into the issue detail.
     *
     * Carried over unchanged in VALUE from the bare `500` at the old write site. It is NAMED here
     * only because moving the line changed its detekt baseline ID from
     * `MagicNumber:ActiveAiScanner.kt$ActiveAiScanner$500` to a `ScannerIssueSupport` one, and
     * QUAL-07 forbids growing `detekt-baseline.xml` to re-suppress it. This constant is NOT part of
     * the privacy control: the payload is agent-authored, not operator traffic.
     *
     * SUPERSEDED IN PART — 2026-08-27, phase 28 plan 28-04 (`CR-01`, D-28-08 first site). The
     * paragraph above is KEPT VERBATIM as the historical record. Its last sentence is the FALSE
     * PREMISE that caused the `Payload Used:` line to be passed over in round 1, and deleting it
     * would leave a later reader unable to tell what was believed from what was overlooked.
     *
     * WHAT WAS MEASURED. The payload is NOT unconditionally agent-authored. For a context-aware
     * payload it is built by INTERPOLATING operator traffic: `ActiveAiScanner.kt:511-515` passes
     * `target.injectionPoint.originalValue` into `PayloadGenerator.generateContextAwarePayloads`,
     * which interpolates it at `PayloadGenerator.kt:762`, `:771`, `:782` and `:791` with NO
     * injection-type filter. For a COOKIE-typed point the rendered payload therefore carried the
     * exact bytes [sanitizeInjectionPointValue] had stripped one line above — the whole control's
     * span was one line short of its own subject.
     *
     * WHAT THIS CONSTANT IS NOW. The bound on the PASS-THROUGH branch of [sanitizeRenderedPayload],
     * a function that IS part of the privacy control. Its VALUE is unchanged; only the claim made
     * about it is.
     */
    internal const val PAYLOAD_VALUE_MAX_CHARS = 500

    /**
     * (PRIV-05) 28-01 / `AR-27-08` — the cookie control on the ISSUE-DETAIL carrier, one hop
     * downstream of the parameter carrier `McpToolHelpers.sanitizeParameters` guards.
     *
     * TYPE-KEYED, never shape-keyed. The decision is taken on [InjectionType.COOKIE], a member of a
     * closed enum, so no reformatting of the detail line can defeat it. That discipline is not a
     * preference: phase 27 MEASURED `Redaction.cookieTypedParamRegex` as blind to this route
     * precisely because it keys on the passive scanner's `name=value (COOKIE)` rendering, while
     * this route renders `Original Value: <value>`. A control placed anywhere downstream of the
     * write site would have only a rendered string to key on and would inherit that same blindness.
     *
     * The substitution is a `when` over the classification rather than a single `if`, so the
     * extension point stays visible in the code exactly as `sanitizeParameters` keeps it visible.
     * The else branch is a DELIBERATE pass-through: URL_PARAM-, BODY_PARAM-, HEADER-,
     * PATH_SEGMENT-, JSON_FIELD- and XML_ELEMENT-typed points carry their value verbatim in every
     * mode, exactly as before this function existed. PRIV-05's wording is about cookie values;
     * whether a URL- or BODY-typed point named `access_token` survives this blob is a DIFFERENT
     * requirement class, it is NOT assumed either way here, and `AR-27-07` is the separate finding
     * that covers it.
     *
     * Truncation to [ORIGINAL_VALUE_MAX_CHARS] is preserved on the pass-through branch — it is the
     * pre-existing behaviour of `ActiveAiScanner.kt:1239` and this function changes nothing about
     * it.
     */
    internal fun sanitizeInjectionPointValue(
        point: InjectionPoint,
        policy: RedactionPolicy,
    ): String =
        when {
            // The cookie carrier. Same marker sanitizeParameters and sanitizeHeaders write for a
            // stripped cookie, so one vocabulary is met across every cookie control in the product.
            policy.stripCookies && point.type == InjectionType.COOKIE -> INJECTION_VALUE_STRIPPED_MARKER
            // D-28-01: every other type passes through, truncated exactly as before. Deliberate.
            else -> point.originalValue.take(ORIGINAL_VALUE_MAX_CHARS)
        }

    /**
     * (PRIV-05) 28-04 / `CR-01` / D-28-07 — the SIBLING gate for the `Payload Used:` line, one line
     * below the one [sanitizeInjectionPointValue] guards.
     *
     * WHY A SECOND GATE WAS NEEDED. `28-VERIFICATION.md` measured SC1 FALSE after round 1: the
     * control's MECHANISM was sound and its SPAN was one line short. For a COOKIE-typed point the
     * payload is OPERATOR TRAFFIC, not agent text — `ActiveAiScanner.kt:511-515` passes
     * `target.injectionPoint.originalValue` into `PayloadGenerator.generateContextAwarePayloads`,
     * which interpolates it at `PayloadGenerator.kt:762`, `:771`, `:782` and `:791` with NO
     * injection-type filter — so the rendered payload re-leaked the exact bytes the line above had
     * just stripped.
     *
     * THE DISCIPLINE IS THE SIBLING'S, QUOTED RATHER THAN RESTATED (`sanitizeInjectionPointValue`,
     * verbatim):
     *
     * > TYPE-KEYED, never shape-keyed. The decision is taken on [InjectionType.COOKIE], a member of
     * > a closed enum, so no reformatting of the detail line can defeat it.
     *
     * D-28-07 binds this function to that sentence and REJECTED the alternative: excising the
     * embedded `originalValue` substring from inside `payload.value` to preserve a partially useful
     * diagnostic. That is shape-keying — it reads the value's TEXT — and any payload that encodes or
     * otherwise transforms the value defeats it. This gate reads [InjectionPoint.type] and
     * `policy.stripCookies` and NOTHING ELSE. There is deliberately no emptiness guard either: a
     * COOKIE point whose value is the empty string must still render the marker, or the point's TYPE
     * becomes observable as a difference in the rendered line.
     *
     * ACCEPTED TRADE, RECORDED RATHER THAN HIDDEN. Under STRICT and BALANCED a cookie point's
     * payload diagnostics are GIVEN UP — the operator can no longer read which probe string was
     * sent from this issue's detail blob. That cost is deliberate and D-28-07 locked it. It is
     * accepted for the same reason its sibling's is: the operator retains the raw attack request
     * byte-for-byte in the SAME issue's `requestResponses` pane, which Burp renders directly and
     * never passes through `Redaction.apply`. This control does not touch that list — a checked
     * invariant, not a claim; see `theRequestResponsesListIsNotAlteredByTheControl`.
     *
     * The marker is [INJECTION_VALUE_STRIPPED_MARKER], REFERENCED and never retyped: D-28-05's
     * one-vocabulary rule forbids a second payload-specific marker constant.
     */
    internal fun sanitizeRenderedPayload(
        point: InjectionPoint,
        payload: Payload,
        policy: RedactionPolicy,
    ): String =
        when {
            // The cookie carrier's SECOND line. Same gate shape and same marker as the sibling one
            // line up, so a reader meets ONE control applied twice rather than two mechanisms.
            policy.stripCookies && point.type == InjectionType.COOKIE -> INJECTION_VALUE_STRIPPED_MARKER
            // D-28-07: every other type passes through, truncated exactly as before. Deliberate —
            // sanitising all types would reopen D-28-01's pass-through, which was itself deliberate.
            else -> payload.value.take(PAYLOAD_VALUE_MAX_CHARS)
        }

    /**
     * (PRIV-05) 28-01 / D-28-01 — THE ONLY PRODUCER OF THE ACTIVE-SCAN ISSUE DETAIL LINES IN THE
     * REPOSITORY.
     *
     * That is not a stylistic preference: a second producer is how this control gets bypassed
     * without anyone editing [sanitizeInjectionPointValue]. `IssueDetailCookieCarrierTest`'s
     * single-producer gate fails if a detail-line accumulator reappears inline in
     * `ActiveAiScanner`.
     *
     * WHY THE CONTROL SITS HERE AND NOT DOWNSTREAM. This is the last point in the route that still
     * holds the [InjectionType]. `IssueUtils.formatIssueDetailHtml` receives `List<String>` and has
     * neither a privacy mode nor any knowledge of which line came from which type;
     * `Serialization.kt`'s `detail = detail()` is later still, with the type discarded and the value
     * already inside an HTML-escaped, `<br>`-joined blob. A control at either site would have to
     * re-parse its own `Original Value: ` prefix to locate the value — shape-keyed, the mechanism
     * phase 27 measured as structurally blind.
     *
     * ACCEPTED TRADE, RECORDED RATHER THAN HIDDEN. Under STRICT and BALANCED the operator's own
     * Burp UI issue detail now shows the marker instead of the value, because `AuditIssue.detail` is
     * stored in Burp's site map as well as emitted over MCP. It is accepted because the operator
     * retains the raw value byte-for-byte in the SAME issue's request pane: Burp renders
     * `requestResponses` directly and does not pass it through `Redaction.apply`. That is a checked
     * invariant, not a claim — see `theRequestResponsesListIsNotAlteredByTheControl`.
     *
     * SIX PARAMETERS IS A DESIGN BOUND, NOT A TOOL THRESHOLD. Detekt's own `functionThreshold` is
     * 10 (`detekt.yml:9`) and would accept more without comment, so it is NOT the reason. The bound
     * is six because the seventh parameter this function could plausibly grow is the supervisor's
     * backend info, and admitting it would drag a Montoya-dependent collaborator into a function
     * whose entire value is that it has none. A collaborator-free function is one a mocks-free test
     * can drive end to end, and that is what makes this control's probe cheap enough that a future
     * round keeps it rather than deleting it. The metadata section is therefore passed IN, already
     * built. If a seventh parameter looks necessary, that is a signal to re-read D-28-01.
     *
     * SUPERSEDED IN PART — 2026-08-27, phase 28 plan 28-05 (`CR-02`, D-28-08 second site). Every
     * paragraph above is KEPT VERBATIM as the historical record. The heading's claim and its
     * supporting sentence were FALSE WHEN WRITTEN, and deleting them would leave a later reader
     * unable to tell what was believed from what was overlooked. Three corrections, stated plainly.
     *
     * (a) THERE ARE TWO PRODUCERS, not one. The second is
     * [com.six2dez.burp.aiagent.scanner.AiScanCheck.buildDetail], a separate active scan check
     * live-registered `PER_INSERTION_POINT` at `App.kt:214-215`, whose `AuditIssue.detail()` reaches
     * the same `scanner_issues` MCP tool result through `api.siteMap()`. `WR-01` measured it:
     * `grep -rn "Original Value" src/main/kotlin/` returns two write sites, not one. It is NOW
     * controlled, by its own type-keyed gate — but that gate keys on a DIFFERENT closed enum,
     * Montoya's `AuditInsertionPointType.PARAM_COOKIE`, because the predicate spelling used here
     * cannot see an insertion-point type. The two controls are siblings in shape and share this
     * file's [INJECTION_VALUE_STRIPPED_MARKER]; they are not the same predicate.
     *
     * (b) THE SINGLE-PRODUCER GATE NAMED ABOVE DOES NOT EXIST. `IssueDetailCookieCarrierTest`'s
     * assertion filters the `List<String>` THIS FUNCTION ITSELF RETURNED and counts the lines
     * carrying the prefix. It is structurally incapable of seeing another file, so it would not have
     * failed when `AiScanCheck` reappeared as a second producer — and it did not. The sentence
     * "a second producer is how this control gets bypassed without anyone editing
     * [sanitizeInjectionPointValue]" remains TRUE as a statement of risk; only the claim that a gate
     * catches it was false.
     *
     * (c) NO REPOSITORY-WIDE ENFORCEMENT IS ADDED BY THIS ROUND, and this clause must not be read as
     * implying otherwise. D-28-06 records the repo-wide single-producer gate as CONSIDERED AND NOT
     * TAKEN — a named residual, not an oversight. After plan 28-05 there are TWO CONTROLLED
     * PRODUCERS and STILL NO GATE THAT WOULD CATCH A THIRD. The tripwire plan 28-05 did build,
     * `CookieRouteDispositionTest.exactlyOneInsertionPointCookieTypePredicateExistsInMainSource`,
     * is a DIFFERENT mechanism over a DIFFERENT population: it counts cookie-type PREDICATES in main
     * source, not issue-detail PRODUCERS. It does not close `WR-01` and must not be cited as doing
     * so.
     */
    internal fun buildActiveIssueDetailLines(
        point: InjectionPoint,
        vulnClassName: String,
        payload: Payload,
        evidence: String,
        metadataSection: String,
        policy: RedactionPolicy,
    ): List<String> {
        val detailLines = mutableListOf<String>()
        detailLines.add("Vulnerability confirmed via active testing")
        detailLines.add("")
        detailLines.add("Type:")
        detailLines.add("  $vulnClassName")
        detailLines.add("  Injection Point: ${point.type} - ${point.name}")
        detailLines.add("  Original Value: ${sanitizeInjectionPointValue(point, policy)}")
        detailLines.add("  Payload Used: ${sanitizeRenderedPayload(point, payload, policy)}")
        detailLines.add("  Detection Method: ${payload.detectionMethod}")
        detailLines.add("  Evidence: $evidence")
        detailLines.add("")
        detailLines.addAll(metadataSection.split("\r\n"))
        return detailLines
    }

    fun mapSeverity(vulnClass: VulnClass): AuditIssueSeverity =
        when (vulnClass) {
            VulnClass.SQLI, VulnClass.CMDI, VulnClass.SSTI, VulnClass.XXE,
            VulnClass.DESERIALIZATION, VulnClass.REQUEST_SMUGGLING, VulnClass.RFI, VulnClass.LDAP_INJECTION,
            VulnClass.XPATH_INJECTION, VulnClass.NOSQL_INJECTION,
            VulnClass.ACCOUNT_TAKEOVER, VulnClass.MFA_BYPASS, VulnClass.OAUTH_MISCONFIGURATION,
            VulnClass.GIT_EXPOSURE, VulnClass.SUBDOMAIN_TAKEOVER, VulnClass.HOST_HEADER_INJECTION,
            VulnClass.CACHE_POISONING,
            -> AuditIssueSeverity.HIGH

            VulnClass.ACCESS_CONTROL_BYPASS,
            VulnClass.XSS_REFLECTED, VulnClass.XSS_STORED, VulnClass.XSS_DOM,
            VulnClass.LFI, VulnClass.SSRF, VulnClass.IDOR, VulnClass.PATH_TRAVERSAL,
            VulnClass.BOLA, VulnClass.BFLA, VulnClass.BAC_HORIZONTAL, VulnClass.BAC_VERTICAL,
            VulnClass.MASS_ASSIGNMENT, VulnClass.AUTH_BYPASS, VulnClass.SESSION_FIXATION,
            VulnClass.GRAPHQL_INJECTION, VulnClass.STACK_TRACE_EXPOSURE,
            VulnClass.SOURCEMAP_DISCLOSURE, VulnClass.BACKUP_DISCLOSURE,
            VulnClass.DEBUG_EXPOSURE, VulnClass.S3_MISCONFIGURATION, VulnClass.CACHE_DECEPTION,
            VulnClass.PRICE_MANIPULATION, VulnClass.RACE_CONDITION_TOCTOU, VulnClass.EMAIL_HEADER_INJECTION,
            VulnClass.API_VERSION_BYPASS, VulnClass.UNRESTRICTED_FILE_UPLOAD,
            -> AuditIssueSeverity.MEDIUM

            VulnClass.OPEN_REDIRECT, VulnClass.HEADER_INJECTION, VulnClass.CRLF_INJECTION,
            VulnClass.JWT_WEAKNESS, VulnClass.BUSINESS_LOGIC,
            VulnClass.CORS_MISCONFIGURATION, VulnClass.DIRECTORY_LISTING, VulnClass.DEBUG_ENDPOINT,
            VulnClass.VERSION_DISCLOSURE, VulnClass.MISSING_SECURITY_HEADERS, VulnClass.VERBOSE_ERROR,
            VulnClass.INSECURE_COOKIE, VulnClass.SENSITIVE_DATA_URL, VulnClass.WEAK_CRYPTO,
            VulnClass.LOG_INJECTION, VulnClass.CSRF, VulnClass.RATE_LIMIT_BYPASS,
            VulnClass.WEAK_SESSION_TOKEN,
            -> AuditIssueSeverity.LOW
        }

    fun remediation(vulnClass: VulnClass): String =
        when (vulnClass) {
            VulnClass.SQLI -> "Use parameterized queries or prepared statements. Never concatenate user input into SQL queries."
            VulnClass.XSS_REFLECTED, VulnClass.XSS_STORED, VulnClass.XSS_DOM -> "Encode all user input before rendering in HTML. Use Content-Security-Policy headers."
            VulnClass.LFI, VulnClass.PATH_TRAVERSAL -> "Validate and sanitize file paths. Use allowlists for permitted files. Avoid user input in file operations."
            VulnClass.RFI -> "Disable remote file inclusion in PHP. Validate URLs against allowlist."
            VulnClass.SSTI -> "Use logic-less templates or sandbox template execution. Never pass user input directly to template engines."
            VulnClass.CMDI -> "Avoid system commands with user input. If necessary, use strict allowlists and proper escaping."
            VulnClass.SSRF -> "Validate and allowlist destination URLs. Block requests to internal networks and cloud metadata endpoints."
            VulnClass.IDOR, VulnClass.BOLA -> "Implement proper authorization checks. Don't rely on obscurity of IDs."
            VulnClass.BFLA, VulnClass.BAC_HORIZONTAL, VulnClass.BAC_VERTICAL -> "Implement role-based access control. Verify user permissions for each action."
            VulnClass.MASS_ASSIGNMENT -> "Use allowlists for permitted fields in object binding. Never trust client-provided field names."
            VulnClass.OPEN_REDIRECT -> "Validate redirect URLs against an allowlist. Use relative URLs where possible."
            VulnClass.XXE -> "Disable external entity processing in XML parsers. Use JSON instead of XML where possible."
            VulnClass.HEADER_INJECTION, VulnClass.CRLF_INJECTION -> "Strip or encode CR/LF characters from user input used in HTTP headers."
            VulnClass.DESERIALIZATION -> "Avoid deserializing untrusted data. Use allowlists for permitted classes."
            VulnClass.REQUEST_SMUGGLING -> "Normalize or reject conflicting Content-Length/Transfer-Encoding headers. Use a single HTTP parser across all tiers."
            VulnClass.CSRF -> "Implement anti-CSRF tokens. Use SameSite cookies and verify Origin/Referer on state-changing requests."
            VulnClass.UNRESTRICTED_FILE_UPLOAD -> "Restrict file types, validate content, store outside web root, and enforce random names."
            VulnClass.JWT_WEAKNESS -> "Use strong algorithms (RS256). Validate all JWT claims. Don't accept 'none' algorithm."
            VulnClass.LDAP_INJECTION -> "Use parameterized LDAP queries. Escape special LDAP characters in user input."
            VulnClass.XPATH_INJECTION -> "Use parameterized XPath queries. Validate and sanitize user input."
            VulnClass.AUTH_BYPASS -> "Implement proper authentication checks on all protected resources."
            VulnClass.BUSINESS_LOGIC -> "Review business logic for edge cases. Implement proper validation and state management."
            VulnClass.NOSQL_INJECTION -> "Use parameterized queries. Sanitize user input. Disable server-side JavaScript."
            VulnClass.GRAPHQL_INJECTION -> "Disable introspection in production. Implement query depth/complexity limits."
            VulnClass.LOG_INJECTION -> "Sanitize log entries. Encode CRLF characters. Use structured logging."
            VulnClass.CORS_MISCONFIGURATION -> "Use explicit allowlist for origins. Never reflect arbitrary origins. Avoid wildcard with credentials."
            VulnClass.DIRECTORY_LISTING -> "Disable directory listing in web server config. Add index files."
            VulnClass.DEBUG_ENDPOINT -> "Disable debug mode in production. Remove debug endpoints and tools."
            VulnClass.STACK_TRACE_EXPOSURE -> "Configure custom error pages. Never expose stack traces to users."
            VulnClass.VERSION_DISCLOSURE -> "Remove or obfuscate version headers. Configure server to hide version info."
            VulnClass.MISSING_SECURITY_HEADERS -> "Add security headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS."
            VulnClass.VERBOSE_ERROR -> "Use generic error messages. Log details server-side only."
            VulnClass.INSECURE_COOKIE -> "Set Secure, HttpOnly, SameSite flags on cookies. Use proper cookie scope."
            VulnClass.SENSITIVE_DATA_URL -> "Never put passwords/tokens in URLs. Use POST body or headers."
            VulnClass.WEAK_CRYPTO -> "Use strong, modern algorithms. Avoid MD5, SHA1, DES. Use TLS 1.2+."
            VulnClass.SESSION_FIXATION -> "Regenerate session ID after login. Invalidate old sessions."
            VulnClass.WEAK_SESSION_TOKEN -> "Use cryptographically secure random session tokens. Use sufficient entropy."
            VulnClass.RATE_LIMIT_BYPASS -> "Implement robust rate limiting. Don't rely on client-side controls."
            VulnClass.ACCOUNT_TAKEOVER -> "Implement secure password reset flows with short-lived tokens. Require email verification for email changes. Use rate limiting on auth endpoints."
            VulnClass.HOST_HEADER_INJECTION -> "Validate Host header against allowlist. Don't use Host header in password reset URLs or cache keys. Use absolute URLs with hardcoded domains."
            VulnClass.EMAIL_HEADER_INJECTION -> "Sanitize all email header inputs. Strip newlines and carriage returns. Use email libraries that handle escaping."
            VulnClass.OAUTH_MISCONFIGURATION -> "Strictly validate redirect_uri against exact match allowlist. Use state parameter with unpredictable values. Don't expose tokens in URLs."
            VulnClass.MFA_BYPASS -> "Implement rate limiting on MFA verification. Don't expose backup codes in responses. Ensure MFA cannot be skipped via direct navigation."
            VulnClass.PRICE_MANIPULATION -> "Validate all price/quantity calculations server-side. Never trust client-provided prices. Use signed carts or recalculate totals."
            VulnClass.RACE_CONDITION_TOCTOU -> "Use database-level locking for critical operations. Implement idempotency keys. Use atomic operations for balance/inventory changes."
            VulnClass.CACHE_POISONING -> "Don't use unkeyed headers in cached responses. Validate all header inputs. Use separate caches for authenticated/unauthenticated content."
            VulnClass.CACHE_DECEPTION -> "Don't cache responses based on URL extension alone. Use Cache-Control headers. Validate authentication before serving cached content."
            VulnClass.SOURCEMAP_DISCLOSURE -> "Don't deploy source maps to production. If needed, restrict access to authenticated users only. Remove sourceMappingURL comments."
            VulnClass.GIT_EXPOSURE -> "Block access to .git directories in web server config. Don't deploy version control directories. Use .gitignore and verify deployment scripts."
            VulnClass.BACKUP_DISCLOSURE -> "Don't store backup files in web-accessible directories. Configure web server to block common backup extensions. Use secure backup storage."
            VulnClass.DEBUG_EXPOSURE -> "Disable debug endpoints in production. Use environment-based configuration. Protect actuator endpoints with authentication."
            VulnClass.S3_MISCONFIGURATION -> "Use private bucket policies by default. Enable S3 Block Public Access. Audit bucket policies regularly. Use presigned URLs for temporary access."
            VulnClass.SUBDOMAIN_TAKEOVER -> "Remove dangling DNS records. Monitor for unclaimed resources. Use CNAME verification before DNS changes."
            VulnClass.API_VERSION_BYPASS -> "Deprecate old API versions completely. Don't leave deprecated versions accessible. Use consistent security across all versions."
            VulnClass.ACCESS_CONTROL_BYPASS -> "Don't rely on client IP headers for access control. Implement proper authentication and authorization. Use consistent access control across path variations and HTTP methods."
        }
}
