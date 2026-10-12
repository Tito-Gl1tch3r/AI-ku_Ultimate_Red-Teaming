package com.nccgroup.web3decoder.detection;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.Annotations;
import burp.api.montoya.core.ToolType;
import burp.api.montoya.http.handler.HttpHandler;
import burp.api.montoya.http.handler.HttpRequestToBeSent;
import burp.api.montoya.http.handler.HttpResponseReceived;
import burp.api.montoya.http.handler.RequestToBeSentAction;
import burp.api.montoya.http.handler.ResponseReceivedAction;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.scanner.audit.issues.AuditIssue;

import java.util.ArrayList;
import java.util.List;

/**
 * Runs ABI detection on every HTTP response that passes through Burp, independent
 * of {@link AbiDetectionScanCheck}. Burp Pro's Live Audit deduplicates identical
 * requests and will skip the passive scan check on a JS asset it has already seen,
 * which means after the user manually deletes a detected ABI from the panel,
 * reloading the dApp would never re-populate the {@link DetectedAbiStore}. This
 * handler closes that gap by re-running detection on every response.
 *
 * <p>The scan check stays registered for its other job: raising the audit issue
 * that surfaces newly-discovered ABIs in Burp's Issues view.
 */
public final class AbiDetectionHttpHandler implements HttpHandler {

    private final MontoyaApi api;
    private final DetectedAbiStore store;
    private final Logging logging;

    public AbiDetectionHttpHandler(MontoyaApi api, DetectedAbiStore store) {
        this.api = api;
        this.store = store;
        this.logging = api.logging();
    }

    @Override
    public RequestToBeSentAction handleHttpRequestToBeSent(HttpRequestToBeSent requestToBeSent) {
        return RequestToBeSentAction.continueWith(requestToBeSent);
    }

    @Override
    public ResponseReceivedAction handleHttpResponseReceived(HttpResponseReceived responseReceived) {
        try {
            if (store == null
                    || responseReceived == null
                    || responseReceived.toolSource().isFromTool(ToolType.EXTENSIONS)) {
                return ResponseReceivedAction.continueWith(responseReceived);
            }
            String body = responseReceived.bodyToString();
            if (body == null || body.isEmpty()) {
                return ResponseReceivedAction.continueWith(responseReceived);
            }
            List<DetectedAbi> found = AbiDetectionPipeline.detect(body);
            if (found.isEmpty()) {
                return ResponseReceivedAction.continueWith(responseReceived);
            }

            // Annotate the history row so the user can see at a glance which responses
            // carry ABIs. Annotate on every detection (even duplicates), since each
            // response is its own history row and the visual signal is per-row.
            Annotations annotations = responseReceived.annotations();
            String detectedNote = "web3: " + found.size() + " ABI" + (found.size() == 1 ? "" : "s") + " detected";
            String existing = annotations.notes();
            annotations.setNotes((existing == null || existing.isEmpty())
                    ? detectedNote
                    : existing + " | " + detectedNote);

            HttpRequest initiating = responseReceived.initiatingRequest();
            String url = initiating != null ? initiating.url() : "";
            List<DetectedAbi> newlyAdded = new ArrayList<>();
            for (DetectedAbi abi : found) {
                if (store.saveIfNew(abi, url)) newlyAdded.add(abi);
            }
            if (!newlyAdded.isEmpty()) {
                logging.logToOutput("Web3 Decoder: detected " + newlyAdded.size()
                        + " new ABI(s) via HTTP handler from " + url);

                // Raise the same informational issue the passive scan check would have raised.
                // Burp's Live Audit may have deduplicated the request and skipped the scan
                // check entirely, so the handler has to put the issue on the site map itself.
                if (initiating != null) {
                    try {
                        HttpRequestResponse rr = HttpRequestResponse.httpRequestResponse(initiating, responseReceived);
                        AuditIssue issue = AbiDetectionScanCheck.buildAuditIssue(newlyAdded, url, rr);
                        api.siteMap().add(issue);
                    } catch (Exception e) {
                        logging.logToError("AbiDetectionHttpHandler: failed to raise audit issue: " + e.getMessage());
                    }
                }
            }

            return ResponseReceivedAction.continueWith(responseReceived, annotations);
        } catch (Exception e) {
            // Detection must never break the HTTP flow.
            logging.logToError("AbiDetectionHttpHandler error: " + e.getMessage());
        }
        return ResponseReceivedAction.continueWith(responseReceived);
    }
}
