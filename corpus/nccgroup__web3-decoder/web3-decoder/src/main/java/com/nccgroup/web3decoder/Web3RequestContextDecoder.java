package com.nccgroup.web3decoder;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.logging.Logging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nccgroup.web3decoder.abi.AbiProvider;
import com.nccgroup.web3decoder.abi.FourByteSignatureProvider;
import com.nccgroup.web3decoder.decoder.MulticallRecursiveDecoder;
import com.nccgroup.web3decoder.decoder.RawTransactionDecoder;
import com.nccgroup.web3decoder.decoder.Web3DataDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ChainInfo;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.proxies.ProxyDetector;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Headless decoding of a JSON-RPC request's {@code eth_call} entries into the
 * shared {@link RequestContextStore}. Both the Web3 Request and Web3 Response
 * editors funnel through this so the response side can decode after a single
 * send without first opening the request tab. Decoding is the only way to learn
 * which function/ABI a response's {@code result} bytes belong to — that identity
 * lives in the request, not the response.
 *
 * <p>The decode performs network I/O (chain id lookup, ABI fetch) and must run
 * off the EDT.
 */
public class Web3RequestContextDecoder {
    private static final int MULTICALL_MAX_DEPTH = 3;
    private static final String STATUS_DECODED = "decoded";
    private static final String STATUS_SKIPPED = "skipped";
    private static final String STATUS_ERROR = "error";

    // Actionable reasons surfaced when the decoder can't be initialized, kept here
    // so the distinct causes don't collapse into one opaque message.
    static String chainNotConfiguredReason(int chainId) {
        return "Chain ID " + chainId + " is not in your configured chains. Add it under the \"Web3\" tab → "
                + "\"Chains Management\" to enable ABI-based decoding.";
    }

    // URL -> chainId, shared across editor instances to avoid redundant lookups.
    private static final Map<String, Integer> chainIdCache = new ConcurrentHashMap<>();

    /**
     * Lookup-only accessor for the per-URL chain id cache. Returns -1 if no chain id
     * has been resolved yet for the URL. Used by the editor wrapper to populate its
     * chain hint after a decode without triggering another eth_chainId probe.
     */
    public static int cachedChainId(String url) {
        if (url == null) return -1;
        Integer cached = chainIdCache.get(url);
        return cached != null ? cached : -1;
    }

    private final MontoyaApi api;
    private final ExtensionConfig config;
    private final Logging logging;
    private final ObjectMapper objectMapper;
    private final DetectedAbiStore detectedAbiStore;

    public Web3RequestContextDecoder(MontoyaApi api, ExtensionConfig config, Logging logging) {
        this(api, config, logging, null);
    }

    public Web3RequestContextDecoder(MontoyaApi api, ExtensionConfig config, Logging logging,
                                     DetectedAbiStore detectedAbiStore) {
        this.api = api;
        this.config = config;
        this.logging = logging;
        this.objectMapper = new ObjectMapper();
        this.detectedAbiStore = detectedAbiStore;
    }

    static final class RpcBatchItem {
        final int index;
        final JsonNode rpcItem;
        final String itemKey;
        final String method;
        final String id;
        final String contractAddress;
        final String inputData;
        final String rawTxHex;

        private RpcBatchItem(int index, JsonNode rpcItem, String itemKey, String method, String id,
                             String contractAddress, String inputData, String rawTxHex) {
            this.index = index;
            this.rpcItem = rpcItem;
            this.itemKey = itemKey;
            this.method = method;
            this.id = id;
            this.contractAddress = contractAddress;
            this.inputData = inputData;
            this.rawTxHex = rawTxHex;
        }

        boolean isEthCall() {
            return "eth_call".equals(method);
        }

        boolean isSendRawTransaction() {
            return "eth_sendRawTransaction".equals(method);
        }

        boolean hasDecodeInputs() {
            return contractAddress != null && !contractAddress.isEmpty() && inputData != null && !inputData.isEmpty();
        }
    }

    /** Stable per-request key shared by both editors (URL + body hash). */
    public static String requestKey(HttpRequest request) {
        if (request == null) {
            return null;
        }
        String keyData = request.url() + request.bodyToString();
        return Integer.toString(keyData.hashCode());
    }

    static List<RpcBatchItem> collectRpcItems(JsonNode requestRoot) {
        List<RpcBatchItem> items = new ArrayList<>();
        if (requestRoot == null) {
            return items;
        }
        if (requestRoot.isObject()) {
            items.add(buildRpcItem(0, requestRoot));
            return items;
        }
        if (requestRoot.isArray()) {
            int index = 0;
            for (JsonNode item : requestRoot) {
                items.add(buildRpcItem(index, item));
                index++;
            }
        }
        return items;
    }

    private static RpcBatchItem buildRpcItem(int index, JsonNode rpcItem) {
        if (rpcItem == null || !rpcItem.isObject()) {
            return new RpcBatchItem(index, rpcItem, "index:" + index, null, null, null, null, null);
        }

        String id = rpcItem.has("id") && !rpcItem.get("id").isNull() ? rpcItem.get("id").asText() : null;
        String method = rpcItem.has("method") && !rpcItem.get("method").isNull() ? rpcItem.get("method").asText() : null;

        String to = null;
        String data = null;
        JsonNode params = rpcItem.get("params");
        if (params != null && params.isArray() && params.size() > 0) {
            JsonNode first = params.get(0);
            if (first != null && first.isObject()) {
                to = first.has("to") && !first.get("to").isNull() ? first.get("to").asText() : null;
                data = first.has("data") && !first.get("data").isNull() ? first.get("data").asText() : null;
            }
        }

        String rawTxHex = null;
        if ("eth_sendRawTransaction".equals(method) && params != null && params.isArray() && params.size() > 0) {
            JsonNode firstParam = params.get(0);
            if (firstParam != null && firstParam.isTextual()) {
                rawTxHex = firstParam.asText();
            }
        }

        return new RpcBatchItem(index, rpcItem, buildItemKey(rpcItem, index), method, id, to, data, rawTxHex);
    }

    static String buildItemKey(JsonNode rpcItem, int index) {
        if (rpcItem != null && rpcItem.isObject() && rpcItem.has("id") && !rpcItem.get("id").isNull()) {
            return "id:" + rpcItem.get("id").asText();
        }
        return "index:" + index;
    }

    /**
     * Decodes each {@code eth_call} in the request and stores its
     * function/ABI (and any nested multicall context) in {@link RequestContextStore}
     * under {@code requestKey}. Returns one display row per JSON-RPC entry (used by
     * the request editor; the response editor calls this only for its side effect).
     */
    public List<Map<String, Object>> decodeAndStore(HttpRequestResponse requestResponse, String requestKey) {
        List<Map<String, Object>> output = new ArrayList<>();

        JsonNode requestRoot;
        try {
            requestRoot = objectMapper.readTree(requestResponse.request().bodyToString());
        } catch (Exception e) {
            return output;
        }

        List<RpcBatchItem> items = collectRpcItems(requestRoot);
        if (items.isEmpty()) {
            return output;
        }

        // Decoders are built lazily per chain id and memoized for this request.
        // eth_call items resolve the endpoint's chain id (eth_chainId probe).
        Map<Integer, DecoderResult> decoderCache = new HashMap<>();

        for (RpcBatchItem item : items) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("index", item.index);
            if (item.id != null) {
                row.put("id", item.id);
            }
            row.put("method", item.method);

            if (item.rpcItem == null || !item.rpcItem.isObject()) {
                row.put("status", STATUS_SKIPPED);
                row.put("reason", "Entry is not a JSON object.");
                output.add(row);
                continue;
            }

            if (item.isEthCall()) {
                if (!item.hasDecodeInputs()) {
                    row.put("status", STATUS_SKIPPED);
                    row.put("reason", "Missing eth_call params[0].to or params[0].data.");
                    output.add(row);
                    continue;
                }
                DecoderResult dr = getOrBuildDecoder(chainId(requestResponse), requestResponse, decoderCache);
                if (dr.decoder == null) {
                    row.put("status", STATUS_ERROR);
                    row.put("reason", dr.unavailableReason);
                    output.add(row);
                    continue;
                }
                try {
                    decodeCallInto(row, dr.decoder, item.contractAddress, item.inputData, item.itemKey, requestKey);
                } catch (Exception e) {
                    row.put("status", STATUS_ERROR);
                    row.put("reason", e.getMessage());
                }
                output.add(row);
                continue;
            }

            if (item.isSendRawTransaction()) {
                decodeRawTransactionInto(row, item, requestResponse, requestKey, decoderCache);
                output.add(row);
                continue;
            }

            row.put("status", STATUS_SKIPPED);
            row.put("reason", "Method is not eth_call.");
            output.add(row);
        }

        return output;
    }

    /**
     * Decodes an {@code eth_sendRawTransaction} entry: RLP-decode the signed
     * transaction into an envelope (surfaced under {@code transaction}), then decode
     * the inner calldata through the shared call path. The chain id embedded in the
     * signed transaction is preferred; only a transaction that carries none (pre-155
     * legacy) falls back to the endpoint's eth_chainId probe.
     */
    private void decodeRawTransactionInto(Map<String, Object> row, RpcBatchItem item,
                                          HttpRequestResponse requestResponse, String requestKey,
                                          Map<Integer, DecoderResult> decoderCache) {
        if (item.rawTxHex == null || item.rawTxHex.isEmpty()) {
            row.put("status", STATUS_SKIPPED);
            row.put("reason", "Missing eth_sendRawTransaction raw transaction (params[0]).");
            return;
        }

        Map<String, Object> envelope;
        try {
            envelope = RawTransactionDecoder.decode(item.rawTxHex);
        } catch (Exception e) {
            row.put("status", STATUS_ERROR);
            row.put("reason", "Failed to decode raw transaction: " + e.getMessage());
            return;
        }

        String to = (String) envelope.get("to");
        String data = (String) envelope.get("data");

        // Surface the envelope (minus the raw inner calldata blob) to the analyst.
        Map<String, Object> envelopeForDisplay = new LinkedHashMap<>(envelope);
        envelopeForDisplay.remove("data");
        row.put("transaction", envelopeForDisplay);

        if (to == null || data == null || data.length() <= 2) {
            // Contract creation (no `to`) or a plain value transfer (no calldata):
            // the envelope is the whole story; there is no inner function to decode.
            row.put("status", STATUS_DECODED);
            row.put("to", to);
            return;
        }

        Object embeddedChainId = envelope.get("chainId");
        int chainId = embeddedChainId instanceof Long
                ? ((Long) embeddedChainId).intValue()
                : chainId(requestResponse);
        DecoderResult dr = getOrBuildDecoder(chainId, requestResponse, decoderCache);
        if (dr.decoder == null) {
            row.put("status", STATUS_ERROR);
            row.put("reason", dr.unavailableReason);
            return;
        }

        try {
            decodeCallInto(row, dr.decoder, to, data, item.itemKey, requestKey);
        } catch (Exception e) {
            row.put("status", STATUS_ERROR);
            row.put("reason", e.getMessage());
        }
    }

    /**
     * Decodes one call's {@code (to, data)} into {@code row}, stores its
     * function/ABI context, and expands any nested multicall. Shared by the
     * {@code eth_call} and {@code eth_sendRawTransaction} paths.
     */
    private void decodeCallInto(Map<String, Object> row, Web3DataDecoder decoder, String to, String data,
                                String itemKey, String requestKey) throws Exception {
        Map<String, Object> decodedData = decoder.decodeInput(to, data);
        String decodedFunction = (String) decodedData.get("function");
        String decodedAbi = decoder.getLastAbi();
        if (decodedFunction != null && decodedAbi != null) {
            RequestContextStore.storeContext(requestKey, itemKey, decodedFunction, decodedAbi);
        }

        row.put("status", STATUS_DECODED);
        row.put("to", to);
        row.put("function", decodedFunction);
        row.put("args", decodedData.get("args"));
        if (decodedData.get("decodeSource") != null) {
            row.put("decodeSource", decodedData.get("decodeSource"));
        }
        if (Boolean.TRUE.equals(decodedData.get("isProxy"))) {
            Map<String, Object> proxyInfo = new LinkedHashMap<>();
            proxyInfo.put("isProxy", true);
            proxyInfo.put("proxyTarget", decodedData.get("proxyTarget"));
            proxyInfo.put("implementationAddress", decodedData.get("implementationAddress"));
            proxyInfo.put("decodedUsing", decodedData.get("decodedUsing"));
            row.put("proxy", proxyInfo);
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> decodedArgs = (Map<String, Object>) decodedData.get("args");
        if (decodedFunction != null && decodedArgs != null) {
            final Web3DataDecoder nestedDecoderRef = decoder;
            MulticallRecursiveDecoder.NestedCallDecoder wrappedNestedDecoder = (target, callData) -> {
                Map<String, Object> result = nestedDecoderRef.decodeInput(target, callData);
                String innerAbi = nestedDecoderRef.getLastAbi();
                if (result != null && innerAbi != null) {
                    result.put(MulticallRecursiveDecoder.ABI_STASH_KEY, innerAbi);
                }
                return result;
            };
            final String capturedRequestKey = requestKey;
            MulticallRecursiveDecoder.NestedContextRecorder contextRecorder =
                    (path, fn, abi) -> RequestContextStore.storeContext(capturedRequestKey, path, fn, abi);
            List<Map<String, Object>> nestedCalls = MulticallRecursiveDecoder.decodeNestedCalls(
                    to,
                    decodedFunction,
                    decodedArgs,
                    MULTICALL_MAX_DEPTH,
                    wrappedNestedDecoder,
                    itemKey,
                    contextRecorder
            );
            if (!nestedCalls.isEmpty()) {
                row.put("nestedCalls", nestedCalls);
            }
        }
    }

    /**
     * Returns a decoder for {@code chainId}, memoized in {@code cache}. When the
     * chain id is unresolved (-1) or not configured, returns a result carrying the
     * specific, actionable reason to surface on the row instead.
     */
    private DecoderResult getOrBuildDecoder(int chainId, HttpRequestResponse requestResponse,
                                            Map<Integer, DecoderResult> cache) {
        DecoderResult cached = cache.get(chainId);
        if (cached != null) {
            return cached;
        }

        DecoderResult result;
        if (chainId == -1) {
            // No chain context (eth_chainId probe failed). Build a decoder with a
            // null AbiProvider so cache/builtin/etherscan are skipped, and rely on
            // the chain-agnostic fallbacks (detected pool, then 4byte). Better
            // than refusing to decode at all.
            ProxyDetector proxyDetector = new ProxyDetector(api, requestResponse.request().url(),
                    requestResponse.request().headers());
            result = DecoderResult.available(new Web3DataDecoder(proxyDetector, null, logging,
                    new FourByteSignatureProvider(api), detectedAbiStore, config));
        } else {
            ChainInfo chainInfo = config.getChain(chainId);
            if (chainInfo == null) {
                logging.logToError("No chain configuration found for chainId " + chainId);
                result = DecoderResult.unavailable(chainNotConfiguredReason(chainId));
            } else {
                AbiProvider abiProvider = new AbiProvider(api, chainId, chainInfo.getExplorer(),
                        config.resolveExplorerAPIKey(chainInfo), config);
                ProxyDetector proxyDetector = new ProxyDetector(api, requestResponse.request().url(),
                    requestResponse.request().headers());
                result = DecoderResult.available(new Web3DataDecoder(proxyDetector, abiProvider, logging,
                        new FourByteSignatureProvider(api), detectedAbiStore, config));
            }
        }
        cache.put(chainId, result);
        return result;
    }

    /** A built decoder, or the reason one could not be built for a chain id. */
    private static final class DecoderResult {
        final Web3DataDecoder decoder;
        final String unavailableReason;

        private DecoderResult(Web3DataDecoder decoder, String unavailableReason) {
            this.decoder = decoder;
            this.unavailableReason = unavailableReason;
        }

        static DecoderResult available(Web3DataDecoder decoder) {
            return new DecoderResult(decoder, null);
        }

        static DecoderResult unavailable(String reason) {
            return new DecoderResult(null, reason);
        }
    }

    /**
     * Resolves the chain id for the endpoint via an {@code eth_chainId} call,
     * caching per URL.
     */
    private int chainId(HttpRequestResponse requestResponse) {
        HttpRequest request = requestResponse.request();
        String url = request.url();

        if (chainIdCache.containsKey(url)) {
            return chainIdCache.get(url);
        }

        HttpRequest chainRequest = request.withBody("{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"id\":1}");

        HttpRequestResponse chainRequestResponse;
        try {
            chainRequestResponse = api.http().sendRequest(chainRequest);
        } catch (Exception e) {
            logging.logToError("Failed to send eth_chainId request for URL " + url + ": " + e.getMessage());
            return -1;
        }

        String responseBody = chainRequestResponse.response().bodyToString();

        JsonNode jsonResponse;
        try {
            jsonResponse = objectMapper.readTree(responseBody);
        } catch (Exception e) {
            logging.logToError("Invalid JSON-RPC response for URL " + url + ": " + e.getMessage());
            return -1;
        }

        if (jsonResponse.has("result")) {
            String hexChainId = jsonResponse.get("result").asText();
            try {
                if (hexChainId.length() < 3 || !hexChainId.startsWith("0x")) {
                    logging.logToError("Unexpected chain ID format for URL " + url + ": " + hexChainId);
                    return -1;
                }
                int chainId = Integer.parseInt(hexChainId.substring(2), 16);
                chainIdCache.put(url, chainId);
                return chainId;
            } catch (NumberFormatException | StringIndexOutOfBoundsException ex) {
                logging.logToError("Error parsing chain ID for URL " + url + ": " + ex.getMessage());
                return -1;
            }
        }

        logging.logToError("Chain ID not found in response for URL " + url + ": " + responseBody);
        return -1;
    }
}
