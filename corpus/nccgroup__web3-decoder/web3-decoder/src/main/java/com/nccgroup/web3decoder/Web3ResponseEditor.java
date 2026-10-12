package com.nccgroup.web3decoder;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.ui.Selection;
import burp.api.montoya.ui.editor.extension.EditorCreationContext;
import burp.api.montoya.ui.editor.extension.ExtensionProvidedHttpResponseEditor;
import burp.api.montoya.logging.Logging;

import java.awt.Component;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.swing.SwingWorker;

import com.fasterxml.jackson.core.util.DefaultIndenter;
import com.fasterxml.jackson.core.util.DefaultPrettyPrinter;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import com.nccgroup.web3decoder.decoder.MulticallRecursiveDecoder;
import com.nccgroup.web3decoder.decoder.Web3DataDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.ui.editor.DecodedEditorPanel;

public class Web3ResponseEditor implements ExtensionProvidedHttpResponseEditor {
    private static final String STATUS_DECODED = "decoded";
    private static final String STATUS_SKIPPED = "skipped";
    private static final String STATUS_ERROR = "error";

    private static final DefaultPrettyPrinter PRETTY_PRINTER = buildPrettyPrinter();

    private final DecodedEditorPanel responseEditor;
    private final Logging logging;
    private final ObjectMapper objectMapper;
    private final Web3RequestContextDecoder contextDecoder;
    private final DetectedAbiStore detectedAbiStore;
    private HttpRequestResponse requestResponse;

    private static DefaultPrettyPrinter buildPrettyPrinter() {
        DefaultIndenter indenter = new DefaultIndenter("  ", DefaultIndenter.SYS_LF);
        DefaultPrettyPrinter pp = new DefaultPrettyPrinter();
        pp.indentObjectsWith(indenter);
        pp.indentArraysWith(indenter);
        return pp;
    }

    public Web3ResponseEditor(MontoyaApi api, ExtensionConfig config, EditorCreationContext creationContext) {
        this(api, config, creationContext, null);
    }

    public Web3ResponseEditor(MontoyaApi api, ExtensionConfig config, EditorCreationContext creationContext,
                              DetectedAbiStore detectedAbiStore) {
        this.logging = api.logging();
        this.objectMapper = new ObjectMapper();
        this.detectedAbiStore = detectedAbiStore;
        this.contextDecoder = new Web3RequestContextDecoder(api, config, logging, detectedAbiStore);
        this.responseEditor = new DecodedEditorPanel(false, api.logging());
    }

    @Override
    public HttpResponse getResponse() {
        return requestResponse != null ? requestResponse.response() : null;
    }

    @Override
    public void setRequestResponse(HttpRequestResponse requestResponse) {
        this.requestResponse = requestResponse;
        responseEditor.setChainHint(-1);

        if (requestResponse == null || requestResponse.request() == null || requestResponse.response() == null) {
            responseEditor.setText("No request/response context available for decoding.");
            return;
        }

        String requestKey = generateRequestKey(requestResponse.request());
        if (requestKey == null) {
            responseEditor.setText("Unable to build request context key.");
            return;
        }

        responseEditor.setChainHint(Web3RequestContextDecoder.cachedChainId(requestResponse.request().url()));
        decodeResponseAsync(requestKey);
    }

    private void decodeResponseAsync(String requestKey) {
        new SwingWorker<Object, Void>() {
            @Override
            protected Object doInBackground() throws Exception {
                // A response only carries the raw result bytes; decoding them needs
                // the request's function/ABI. If the Web3 Request tab hasn't already
                // populated that context, decode the request here so a single send is
                // enough. Runs off the EDT and may hit the network (chain id / ABI).
                if (!RequestContextStore.hasAnyContext(requestKey)) {
                    contextDecoder.decodeAndStore(requestResponse, requestKey);
                }

                String responseBody = requestResponse.response().bodyToString();
                JsonNode responseRoot = objectMapper.readTree(responseBody);

                if (responseRoot == null) {
                    return null;
                }

                if (responseRoot.isArray()) {
                    return decodeBatchResponse(responseRoot, requestKey);
                }

                if (!responseRoot.isObject()) {
                    return null;
                }

                ResolvedContext resolved = resolveContextWithKey(requestKey, responseRoot, 0);
                if (resolved == null || !responseRoot.has("result")) {
                    return null;
                }

                String resultData = responseRoot.get("result").asText();
                if (resultData == null || resultData.isEmpty()) {
                    return null;
                }

                Web3DataDecoder decoder = new Web3DataDecoder(null, null, logging);
                decoder.setLastAbiJson(resolved.entry.abiJson());
                Map<String, Object> decoded = decoder.decodeOutput(resolved.entry.functionSignature(), resultData);
                enrichMulticallReturnData(requestKey, resolved.itemKey, resolved.entry.functionSignature(), decoded);
                return decoded;
            }

            @Override
            protected void done() {
                try {
                    responseEditor.setChainHint(
                            Web3RequestContextDecoder.cachedChainId(requestResponse.request().url()));
                    Object decoded = get();
                    if (decoded == null) {
                        responseEditor.setText("No result to decode.");
                        return;
                    }

                    String jsonOutput = objectMapper.writer(PRETTY_PRINTER).writeValueAsString(decoded);
                    responseEditor.setText(jsonOutput);
                } catch (Exception e) {
                    logging.logToError("Error decoding response: " + e.getMessage());
                    responseEditor.setText("Error decoding response");
                }
            }
        }.execute();
    }

    private List<Map<String, Object>> decodeBatchResponse(JsonNode responseArray, String requestKey) {
        List<Map<String, Object>> rows = new ArrayList<>();
        int index = 0;

        for (JsonNode item : responseArray) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("index", index);

            if (item != null && item.has("id") && !item.get("id").isNull()) {
                row.put("id", item.get("id").asText());
            }

            if (item == null || !item.isObject()) {
                row.put("status", STATUS_SKIPPED);
                row.put("reason", "Entry is not a JSON object.");
                rows.add(row);
                index++;
                continue;
            }

            if (!item.has("result")) {
                row.put("status", STATUS_SKIPPED);
                row.put("reason", "JSON-RPC response does not include result.");
                rows.add(row);
                index++;
                continue;
            }

            ResolvedContext resolved = resolveContextWithKey(requestKey, item, index);
            if (resolved == null) {
                row.put("status", STATUS_SKIPPED);
                row.put("reason", "No decode context found for this response item.");
                rows.add(row);
                index++;
                continue;
            }

            String resultData = item.get("result").asText();
            if (resultData == null || resultData.isEmpty()) {
                row.put("status", STATUS_SKIPPED);
                row.put("reason", "Empty result field.");
                rows.add(row);
                index++;
                continue;
            }

            try {
                Web3DataDecoder decoder = new Web3DataDecoder(null, null, logging);
                decoder.setLastAbiJson(resolved.entry.abiJson());
                Map<String, Object> decoded = decoder.decodeOutput(resolved.entry.functionSignature(), resultData);
                enrichMulticallReturnData(requestKey, resolved.itemKey, resolved.entry.functionSignature(), decoded);
                row.put("status", STATUS_DECODED);
                row.put("function", resolved.entry.functionSignature());
                row.put("output", decoded.get("output"));
            } catch (Exception e) {
                row.put("status", STATUS_ERROR);
                row.put("reason", e.getMessage());
            }

            rows.add(row);
            index++;
        }

        return rows;
    }

    private ResolvedContext resolveContextWithKey(String requestKey, JsonNode responseItem, int index) {
        if (responseItem != null && responseItem.has("id") && !responseItem.get("id").isNull()) {
            String idKey = "id:" + responseItem.get("id").asText();
            RequestContextStore.ContextEntry byId = RequestContextStore.getContext(requestKey, idKey);
            if (byId != null) {
                return new ResolvedContext(idKey, byId);
            }
        }

        String indexKey = "index:" + index;
        RequestContextStore.ContextEntry byIndex = RequestContextStore.getContext(requestKey, indexKey);
        if (byIndex != null) {
            return new ResolvedContext(indexKey, byIndex);
        }

        RequestContextStore.ContextEntry legacy = RequestContextStore.getLegacyContext(requestKey);
        if (legacy != null) {
            return new ResolvedContext(null, legacy);
        }
        return null;
    }

    private static final class ResolvedContext {
        final String itemKey;
        final RequestContextStore.ContextEntry entry;

        ResolvedContext(String itemKey, RequestContextStore.ContextEntry entry) {
            this.itemKey = itemKey;
            this.entry = entry;
        }
    }

    /**
     * Walk a decoded multicall output and decode each inner {@code returnData}
     * against the per-call context stashed during request decoding. Mutates
     * {@code decodedTopLevel} in place. Recurses for nested multicalls.
     */
    static void enrichMulticallReturnData(
            String requestKey,
            String parentItemKey,
            String parentFunction,
            Map<String, Object> decodedTopLevel
    ) {
        if (requestKey == null || parentItemKey == null) {
            return;
        }
        if (!MulticallRecursiveDecoder.isSupportedMulticall(null, parentFunction)) {
            return;
        }
        Object outputObj = decodedTopLevel.get("output");
        if (!(outputObj instanceof Map)) {
            return;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> output = (Map<String, Object>) outputObj;
        Object returnDataObj = output.get("returnData");
        if (!(returnDataObj instanceof List)) {
            return;
        }
        List<?> entries = (List<?>) returnDataObj;
        List<Object> enriched = new ArrayList<>(entries.size());
        for (int i = 0; i < entries.size(); i++) {
            String childPath = parentItemKey + "/nested:" + i;
            enriched.add(decodeNestedReturnEntry(requestKey, childPath, entries.get(i)));
        }
        output.put("returnData", enriched);
    }

    private static Object decodeNestedReturnEntry(String requestKey, String childPath, Object entry) {
        String hex;
        boolean success = true;
        Map<String, Object> base = new LinkedHashMap<>();

        if (entry instanceof String) {
            // aggregate(...) — entries are raw bytes hex.
            hex = (String) entry;
            base.put("returnData", hex);
        } else if (entry instanceof List<?>) {
            // aggregate3 / tryAggregate / *blockAndAggregate — each entry is a
            // (bool success, bytes returnData) tuple, returned positionally.
            List<?> tuple = (List<?>) entry;
            if (tuple.size() < 2) {
                return entry;
            }
            Object successObj = tuple.get(0);
            Object hexObj = tuple.get(1);
            if (successObj instanceof Boolean) {
                success = (Boolean) successObj;
            }
            hex = hexObj instanceof String ? (String) hexObj : null;
            base.put("success", success);
            base.put("returnData", hex);
        } else if (entry instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) entry;
            base.putAll(map);
            Object hexObj = map.get("returnData");
            hex = hexObj instanceof String ? (String) hexObj : null;
            Object successObj = map.get("success");
            if (successObj instanceof Boolean) {
                success = (Boolean) successObj;
            }
        } else {
            return entry;
        }

        RequestContextStore.ContextEntry ctx = RequestContextStore.getContext(requestKey, childPath);
        if (ctx == null) {
            return base;
        }
        if (!success || hex == null || hex.isEmpty() || "0x".equalsIgnoreCase(hex)) {
            // Nothing to decode — preserve the raw entry but note the function we'd have used.
            base.put("function", ctx.functionSignature());
            return base;
        }

        try {
            Map<String, Object> decoded = ABIInputDecoder.decodeOutput(ctx.abiJson(), ctx.functionSignature(), hex);
            if (MulticallRecursiveDecoder.isSupportedMulticall(null, ctx.functionSignature())) {
                enrichMulticallReturnData(requestKey, childPath, ctx.functionSignature(), decoded);
            }
            base.put("decoded", decoded);
        } catch (Exception e) {
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("function", ctx.functionSignature());
            error.put("status", STATUS_ERROR);
            error.put("reason", e.getMessage());
            base.put("decoded", error);
        }
        return base;
    }

    @Override
    public boolean isEnabledFor(HttpRequestResponse requestResponse) {
        if (requestResponse == null || requestResponse.request() == null || requestResponse.response() == null) {
            return false;
        }

        // Cheap, network-free gate: enable the tab whenever the request carries a
        // decodable eth_call and the response is a JSON-RPC result. The decode
        // context no longer needs to exist yet — setRequestResponse builds it off
        // the EDT (decoding the request first if the Web3 Request tab hasn't).
        try {
            JsonNode requestRoot = objectMapper.readTree(requestResponse.request().bodyToString());
            boolean hasDecodableCall = Web3RequestContextDecoder.collectRpcItems(requestRoot).stream()
                    .anyMatch(item -> item.isEthCall() && item.hasDecodeInputs());
            if (!hasDecodableCall) {
                return false;
            }

            JsonNode jsonResponse = objectMapper.readTree(requestResponse.response().bodyToString());
            if (jsonResponse == null) {
                return false;
            }
            if (jsonResponse.isObject()) {
                return jsonResponse.has("result");
            }
            if (jsonResponse.isArray()) {
                for (JsonNode item : jsonResponse) {
                    if (item != null && item.isObject() && item.has("result")) {
                        return true;
                    }
                }
            }
        } catch (Exception e) {
            return false;
        }

        return false;
    }

    @Override
    public String caption() {
        return "Web3 Response";
    }

    @Override
    public Component uiComponent() {
        return responseEditor.getComponent();
    }

    DecodedEditorPanel editorForTesting() {
        return responseEditor;
    }

    @Override
    public Selection selectedData() {
        String selected = responseEditor.getSelectedText();
        if (selected == null || selected.isEmpty()) {
            return null;
        }
        return Selection.selection(burp.api.montoya.core.ByteArray.byteArray(
                selected.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }

    private String generateRequestKey(HttpRequest request) {
        return Web3RequestContextDecoder.requestKey(request);
    }

    @Override
    public boolean isModified() {
        return responseEditor.isModified();
    }
}
