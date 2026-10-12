package com.nccgroup.web3decoder.annotation;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.HighlightColor;
import burp.api.montoya.core.ToolType;
import burp.api.montoya.http.handler.HttpHandler;
import burp.api.montoya.http.handler.HttpRequestToBeSent;
import burp.api.montoya.http.handler.HttpResponseReceived;
import burp.api.montoya.http.handler.RequestToBeSentAction;
import burp.api.montoya.http.handler.ResponseReceivedAction;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.proxy.ProxyHttpRequestResponse;

import com.nccgroup.web3decoder.Web3RequestContextDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * Annotates Proxy history rows with the decoded Web3 function name. The handler
 * method itself does no slow work; the decode (which may hit the network for
 * chain id, Etherscan ABI, 4byte signature, or proxy implementation slots) runs
 * on a background executor. Once the decode is done, the annotator finds the
 * matching {@link ProxyHttpRequestResponse} in {@code proxy().history()} and
 * mutates its live {@code Annotations} — the same path the GUI uses when a user
 * edits a row's note by hand, so the change persists.
 *
 * <p>Annotations returned via {@code continueWith(..., annotations)} are
 * snapshotted at handler return, which is why this class uses the history-row
 * mutation route instead.
 */
public class Web3HistoryAnnotator implements HttpHandler {

    private static final int NOTE_CACHE_LIMIT = 5000;
    private static final int WORKER_QUEUE_CAPACITY = 1024;
    private static final int HISTORY_LOOKUP_ATTEMPTS = 6;
    private static final long HISTORY_LOOKUP_BACKOFF_MS = 50L;
    private static final long SHUTDOWN_TIMEOUT_SECONDS = 2L;

    private final MontoyaApi api;
    private final ExtensionConfig config;
    private final Logging logging;
    private final Web3RequestContextDecoder decoder;
    private final Map<String, AnnotationNoteBuilder.Result> noteCache = new ConcurrentHashMap<>();
    private final ExecutorService executor;

    public Web3HistoryAnnotator(MontoyaApi api, ExtensionConfig config) {
        this(api, config, null);
    }

    public Web3HistoryAnnotator(MontoyaApi api, ExtensionConfig config, DetectedAbiStore detectedAbiStore) {
        this.api = api;
        this.config = config;
        this.logging = api.logging();
        this.decoder = new Web3RequestContextDecoder(api, config, api.logging(), detectedAbiStore);
        this.executor = newDecodeExecutor();
    }

    private static ExecutorService newDecodeExecutor() {
        ThreadPoolExecutor exec = new ThreadPoolExecutor(
                1, 2, 30L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(WORKER_QUEUE_CAPACITY),
                r -> {
                    Thread t = new Thread(r, "web3-decoder-annotator");
                    t.setDaemon(true);
                    return t;
                },
                new ThreadPoolExecutor.DiscardOldestPolicy());
        exec.allowCoreThreadTimeOut(true);
        return exec;
    }

    @Override
    public RequestToBeSentAction handleHttpRequestToBeSent(HttpRequestToBeSent requestToBeSent) {
        return RequestToBeSentAction.continueWith(requestToBeSent);
    }

    @Override
    public ResponseReceivedAction handleHttpResponseReceived(HttpResponseReceived responseReceived) {
        if (!config.isHistoryAnnotationEnabled()
                || responseReceived.toolSource().isFromTool(ToolType.EXTENSIONS)
                || !responseReceived.toolSource().isFromTool(ToolType.PROXY)) {
            return ResponseReceivedAction.continueWith(responseReceived);
        }
        HttpRequest request = responseReceived.initiatingRequest();
        if (request == null || !Web3RequestSniffer.isCandidate(request.bodyToString())) {
            return ResponseReceivedAction.continueWith(responseReceived);
        }
        try {
            executor.submit(() -> annotateAsync(request));
        } catch (RejectedExecutionException ignored) {
            // Executor shut down (extension unloading) — drop this annotation request.
        }
        return ResponseReceivedAction.continueWith(responseReceived);
    }

    private void annotateAsync(HttpRequest request) {
        try {
            // Sniff the raw body up-front: if it unambiguously identifies the method as
            // eth_sendRawTransaction, the row deserves the yellow highlight regardless of
            // whether the JSON parse / RLP decode that follows produces a useful row. That
            // covers requests where decodeAndStore returns an empty list (malformed JSON,
            // unexpected envelope, decoder I/O failure) — without it the highlight silently
            // disappears even though the method is obvious from the body.
            String bodyText = request.bodyToString();
            boolean bodyMentionsRawTx = bodyText != null && bodyText.contains("eth_sendRawTransaction");

            String key = Web3RequestContextDecoder.requestKey(request);
            AnnotationNoteBuilder.Result result = (key == null) ? null : noteCache.get(key);
            if (result == null) {
                HttpRequestResponse rr = HttpRequestResponse.httpRequestResponse(request, HttpResponse.httpResponse());
                List<Map<String, Object>> rows = decoder.decodeAndStore(rr, key);
                result = AnnotationNoteBuilder.build(rows);
                if (key != null) {
                    if (noteCache.size() >= NOTE_CACHE_LIMIT) {
                        noteCache.clear();
                    }
                    noteCache.put(key, result);
                }
            }

            ProxyHttpRequestResponse row = findHistoryRow(request);
            if (row == null) {
                return;
            }
            row.annotations().setNotes(result.notes());
            if (result.isRawTransaction() || bodyMentionsRawTx) {
                row.annotations().setHighlightColor(HighlightColor.YELLOW);
            }
        } catch (Exception e) {
            logging.logToError("Async annotation failed: " + e.getMessage());
        }
    }

    /**
     * Finds the {@link ProxyHttpRequestResponse} that corresponds to {@code request}.
     *
     * <p>We deliberately do <em>not</em> match by {@link HttpResponseReceived#messageId()}
     * against {@link ProxyHttpRequestResponse#id()}: those come from different counters.
     * {@code messageId} is Burp's global HTTP message counter (bumped by every tool —
     * Proxy, Scanner, Repeater, Live Audit, and our own {@code api.http().sendRequest()}
     * chain-id / Etherscan / 4byte probes). {@code id()} is the index within proxy
     * history — it only advances when proxy actually records a row. They drift apart
     * fast and {@code row.id() == messageId} silently lands on whatever unrelated row
     * happens to share that number.
     *
     * <p>URL + body uniquely identifies the JSON-RPC call we want to annotate. If
     * several identical requests are in history (polling endpoints), we annotate the
     * most recent — each earlier one was annotated by its own handler invocation.
     */
    private ProxyHttpRequestResponse findHistoryRow(HttpRequest request) {
        String url = request.url();
        String body = request.bodyToString();
        for (int attempt = 0; attempt < HISTORY_LOOKUP_ATTEMPTS; attempt++) {
            ProxyHttpRequestResponse latest = null;
            for (ProxyHttpRequestResponse row : api.proxy().history(r -> {
                HttpRequest fr = r.finalRequest();
                return fr != null && url.equals(fr.url()) && body.equals(fr.bodyToString());
            })) {
                if (latest == null || row.id() > latest.id()) {
                    latest = row;
                }
            }
            if (latest != null) {
                return latest;
            }
            try {
                Thread.sleep(HISTORY_LOOKUP_BACKOFF_MS);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return null;
            }
        }
        return null;
    }

    public void shutdown() {
        executor.shutdownNow();
        try {
            executor.awaitTermination(SHUTDOWN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }
}
