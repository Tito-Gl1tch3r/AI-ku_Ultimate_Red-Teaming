package com.nccgroup.web3decoder.detection;

import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.scanner.AuditResult;
import burp.api.montoya.scanner.ConsolidationAction;
import burp.api.montoya.scanner.audit.issues.AuditIssue;
import burp.api.montoya.scanner.audit.issues.AuditIssueConfidence;
import burp.api.montoya.scanner.audit.issues.AuditIssueSeverity;
import burp.api.montoya.scanner.scancheck.PassiveScanCheck;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Function;

/**
 * Passive scan check that detects Solidity ABIs embedded in HTTP response bodies,
 * stores them, and raises one informational audit issue per response that introduces
 * a new ABI. Identical ABIs seen in later responses do not re-raise.
 *
 * <p>The constructor accepts a pluggable {@code AuditIssue} factory so tests can
 * avoid the real {@link AuditIssue#auditIssue} static method (which is backed by
 * a Montoya internal {@code ObjectFactoryLocator} that is not initialised outside
 * a running Burp — same hazard as {@code PersistedObject.persistedObject} from
 * Task 6).
 */
public final class AbiDetectionScanCheck implements PassiveScanCheck {

    private static final String CHECK_NAME = "Web3 Decoder — ABI Detection";
    private static final String ISSUE_NAME = "Solidity contract ABI detected";
    private static final String ISSUE_BACKGROUND =
            "Web3 Decoder detected one or more Solidity contract ABIs embedded in this response. "
                    + "They are now usable for decoding calldata.";

    private final DetectedAbiStore store;
    private final BiFunction<List<DetectedAbi>, IssueContext, AuditIssue> issueFactory;
    private final Function<List<AuditIssue>, AuditResult> resultFactory;
    private final Logging logging;

    public AbiDetectionScanCheck(DetectedAbiStore store) {
        this(store, (Logging) null);
    }

    /** Production constructor with logging — fires a single line when new ABIs are added. */
    public AbiDetectionScanCheck(DetectedAbiStore store, Logging logging) {
        this(store, AbiDetectionScanCheck::defaultIssueFactory, AuditResult::auditResult, logging);
    }

    /**
     * Test-friendly constructor that allows injecting an alternative AuditIssue
     * factory. Production code should use the single-arg ctor, which delegates
     * to the real Montoya factory.
     */
    public AbiDetectionScanCheck(DetectedAbiStore store,
                                 BiFunction<List<DetectedAbi>, IssueContext, AuditIssue> issueFactory) {
        this(store, issueFactory, AuditResult::auditResult, null);
    }

    /**
     * Fully-injectable constructor for tests. Both the {@link AuditIssue} and
     * {@link AuditResult} Montoya factories crash outside a running Burp (their
     * {@code ObjectFactoryLocator.FACTORY} is null), so unit tests inject
     * plain mock-returning lambdas here.
     */
    public AbiDetectionScanCheck(DetectedAbiStore store,
                                 BiFunction<List<DetectedAbi>, IssueContext, AuditIssue> issueFactory,
                                 Function<List<AuditIssue>, AuditResult> resultFactory) {
        this(store, issueFactory, resultFactory, null);
    }

    public AbiDetectionScanCheck(DetectedAbiStore store,
                                 BiFunction<List<DetectedAbi>, IssueContext, AuditIssue> issueFactory,
                                 Function<List<AuditIssue>, AuditResult> resultFactory,
                                 Logging logging) {
        this.store = store;
        this.issueFactory = issueFactory;
        this.resultFactory = resultFactory;
        this.logging = logging;
    }

    @Override
    public String checkName() {
        return CHECK_NAME;
    }

    @Override
    public AuditResult doCheck(HttpRequestResponse baseRequestResponse) {
        if (baseRequestResponse == null || baseRequestResponse.response() == null) {
            return resultFactory.apply(List.of());
        }
        String body = baseRequestResponse.response().bodyToString();
        if (body == null || body.isEmpty()) {
            return resultFactory.apply(List.of());
        }

        List<DetectedAbi> found = AbiDetectionPipeline.detect(body);
        if (found.isEmpty()) return resultFactory.apply(List.of());

        String sourceUrl = baseRequestResponse.request() != null
                ? baseRequestResponse.request().url() : "";
        List<DetectedAbi> newlyAdded = new ArrayList<>();
        for (DetectedAbi abi : found) {
            if (store.saveIfNew(abi, sourceUrl)) newlyAdded.add(abi);
        }
        if (newlyAdded.isEmpty()) return resultFactory.apply(List.of());

        if (logging != null) {
            logging.logToOutput("Web3 Decoder: detected " + newlyAdded.size()
                    + " new ABI(s) in " + sourceUrl);
        }

        IssueContext ctx = new IssueContext(
                ISSUE_NAME,
                buildDetail(newlyAdded),
                "",
                sourceUrl,
                AuditIssueSeverity.INFORMATION,
                AuditIssueConfidence.CERTAIN,
                ISSUE_BACKGROUND,
                "",
                AuditIssueSeverity.INFORMATION,
                baseRequestResponse);
        AuditIssue issue = issueFactory.apply(newlyAdded, ctx);
        return resultFactory.apply(List.of(issue));
    }

    @Override
    public ConsolidationAction consolidateIssues(AuditIssue existingIssue, AuditIssue newIssue) {
        return ConsolidationAction.KEEP_EXISTING;
    }

    private static final ObjectMapper MAPPER = new ObjectMapper();

    static String buildDetail(List<DetectedAbi> newlyAdded) {
        StringBuilder sb = new StringBuilder();
        sb.append("<p>Detected <b>").append(newlyAdded.size())
                .append("</b> new Solidity contract ABI(s) in this response. ")
                .append("They are now available to decode matching JSON-RPC traffic ")
                .append("(<code>decodeSource: \"detected\"</code>).</p>");

        int idx = 1;
        for (DetectedAbi abi : newlyAdded) {
            renderAbi(sb, idx++, abi);
        }
        return sb.toString();
    }

    /** Render a single ABI as an HTML section: header with counts, then grouped
     *  lists of functions/events/errors with canonical signature → selector. */
    @SuppressWarnings("unchecked")
    private static void renderAbi(StringBuilder sb, int idx, DetectedAbi abi) {
        List<Map<String, Object>> entries;
        try {
            entries = MAPPER.readValue(abi.canonicalJson(), List.class);
        } catch (Exception e) {
            // Canonical JSON is produced by the validator and should always parse;
            // fall back to fingerprint-only on the off-chance it doesn't.
            sb.append("<h4>ABI ").append(idx).append("</h4>");
            sb.append("<p><small>Fingerprint: <code>").append(abi.fingerprint()).append("</code></small></p>");
            return;
        }

        List<Map<String, Object>> functions = new ArrayList<>();
        List<Map<String, Object>> events = new ArrayList<>();
        List<Map<String, Object>> errors = new ArrayList<>();
        int constructors = 0;
        int fallbacks = 0;
        int receives = 0;
        for (Map<String, Object> entry : entries) {
            String type = String.valueOf(entry.get("type"));
            switch (type) {
                case "function" -> functions.add(entry);
                case "event" -> events.add(entry);
                case "error" -> errors.add(entry);
                case "constructor" -> constructors++;
                case "fallback" -> fallbacks++;
                case "receive" -> receives++;
                default -> { /* ignored */ }
            }
        }

        sb.append("<h4>ABI ").append(idx).append(" — ");
        List<String> counts = new ArrayList<>();
        if (!functions.isEmpty()) counts.add(functions.size() + " function" + (functions.size() == 1 ? "" : "s"));
        if (!events.isEmpty())    counts.add(events.size()    + " event"    + (events.size()    == 1 ? "" : "s"));
        if (!errors.isEmpty())    counts.add(errors.size()    + " error"    + (errors.size()    == 1 ? "" : "s"));
        if (constructors > 0)     counts.add(constructors     + " constructor" + (constructors == 1 ? "" : "s"));
        if (fallbacks > 0)        counts.add(fallbacks        + " fallback");
        if (receives > 0)         counts.add(receives         + " receive");
        sb.append(String.join(", ", counts)).append("</h4>");

        sb.append("<p><small>Fingerprint: <code>").append(abi.fingerprint()).append("</code></small></p>");

        renderEntryList(sb, "Functions", functions, true);
        renderEntryList(sb, "Events",    events,    false);
        renderEntryList(sb, "Errors",    errors,    true);
    }

    private static void renderEntryList(StringBuilder sb, String title,
                                        List<Map<String, Object>> entries, boolean withSelector) {
        if (entries.isEmpty()) return;
        sb.append("<p><b>").append(title).append("</b></p><ul>");
        for (Map<String, Object> entry : entries) {
            String signature;
            try {
                signature = AbiSelectorBuilder.canonicalSignature(entry);
            } catch (Exception e) {
                signature = String.valueOf(entry.get("name")) + "(?)";
            }
            sb.append("<li><code>").append(escapeHtml(signature)).append("</code>");
            if (withSelector) {
                try {
                    String selector = AbiSelectorBuilder.selectorFor(entry);
                    sb.append(" &rarr; <code>").append(selector).append("</code>");
                } catch (Exception ignored) {
                    // skip selector if computation fails
                }
            }
            sb.append("</li>");
        }
        sb.append("</ul>");
    }

    private static String escapeHtml(String s) {
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;");
    }

    /**
     * Builds the canonical "Solidity contract ABI detected" audit issue for a set of
     * newly-stored ABIs. Exposed so detection paths outside the scanner (e.g. the
     * {@link AbiDetectionHttpHandler}) can raise the same issue via
     * {@code api.siteMap().add(issue)}.
     */
    public static AuditIssue buildAuditIssue(List<DetectedAbi> newlyAdded, String sourceUrl,
                                             HttpRequestResponse baseRequestResponse) {
        IssueContext ctx = new IssueContext(
                ISSUE_NAME,
                buildDetail(newlyAdded),
                "",
                sourceUrl,
                AuditIssueSeverity.INFORMATION,
                AuditIssueConfidence.CERTAIN,
                ISSUE_BACKGROUND,
                "",
                AuditIssueSeverity.INFORMATION,
                baseRequestResponse);
        return defaultIssueFactory(newlyAdded, ctx);
    }

    private static AuditIssue defaultIssueFactory(List<DetectedAbi> abis, IssueContext ctx) {
        return AuditIssue.auditIssue(
                ctx.name(),
                ctx.detail(),
                ctx.remediation(),
                ctx.baseUrl(),
                ctx.severity(),
                ctx.confidence(),
                ctx.background(),
                ctx.remediationBackground(),
                ctx.typicalSeverity(),
                ctx.requestResponse());
    }

    /** Inputs forwarded to the AuditIssue factory; exposed so tests can assert on them. */
    public static final class IssueContext {
        private final String name;
        private final String detail;
        private final String remediation;
        private final String baseUrl;
        private final AuditIssueSeverity severity;
        private final AuditIssueConfidence confidence;
        private final String background;
        private final String remediationBackground;
        private final AuditIssueSeverity typicalSeverity;
        private final HttpRequestResponse requestResponse;

        IssueContext(String name, String detail, String remediation, String baseUrl,
                     AuditIssueSeverity severity, AuditIssueConfidence confidence,
                     String background, String remediationBackground,
                     AuditIssueSeverity typicalSeverity, HttpRequestResponse requestResponse) {
            this.name = name;
            this.detail = detail;
            this.remediation = remediation;
            this.baseUrl = baseUrl;
            this.severity = severity;
            this.confidence = confidence;
            this.background = background;
            this.remediationBackground = remediationBackground;
            this.typicalSeverity = typicalSeverity;
            this.requestResponse = requestResponse;
        }

        public String name() { return name; }
        public String detail() { return detail; }
        public String remediation() { return remediation; }
        public String baseUrl() { return baseUrl; }
        public AuditIssueSeverity severity() { return severity; }
        public AuditIssueConfidence confidence() { return confidence; }
        public String background() { return background; }
        public String remediationBackground() { return remediationBackground; }
        public AuditIssueSeverity typicalSeverity() { return typicalSeverity; }
        public HttpRequestResponse requestResponse() { return requestResponse; }
    }
}
