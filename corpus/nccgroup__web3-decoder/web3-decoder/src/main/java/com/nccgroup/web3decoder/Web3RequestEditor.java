package com.nccgroup.web3decoder;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.ui.Selection;
import burp.api.montoya.ui.editor.extension.EditorCreationContext;
import burp.api.montoya.ui.editor.extension.EditorMode;
import burp.api.montoya.ui.editor.extension.ExtensionProvidedHttpRequestEditor;
import burp.api.montoya.logging.Logging;

import java.awt.Component;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.swing.SwingWorker;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.ui.editor.DecodedEditorPanel;

public class Web3RequestEditor implements ExtensionProvidedHttpRequestEditor {
    private static final String STATUS_DECODED = "decoded";

    private final DecodedEditorPanel requestEditor;
    private HttpRequestResponse requestResponse;
    private final Logging logging;
    private final Web3RequestContextDecoder contextDecoder;
    private final ObjectMapper objectMapper;
    private String abiJson;
    private String functionSignature;

    public Web3RequestEditor(MontoyaApi api, ExtensionConfig config, EditorCreationContext creationContext) {
        this(api, config, creationContext, null);
    }

    public Web3RequestEditor(MontoyaApi api, ExtensionConfig config, EditorCreationContext creationContext,
                             DetectedAbiStore detectedAbiStore) {
        this.logging = api.logging();
        this.objectMapper = new ObjectMapper();
        this.contextDecoder = new Web3RequestContextDecoder(api, config, logging, detectedAbiStore);

        boolean editable = creationContext.editorMode() != EditorMode.READ_ONLY;
        this.requestEditor = new DecodedEditorPanel(editable, api.logging());
    }

    @Override
    public HttpRequest getRequest() {
        if (requestResponse == null || requestResponse.request() == null) {
            return null;
        }

        if (!requestEditor.isModified()) {
            return requestResponse.request();
        }

        try {
            String editedContent = requestEditor.getText().trim();
            JsonNode editedRoot = objectMapper.readTree(editedContent);
            JsonNode originalRoot = objectMapper.readTree(requestResponse.request().bodyToString());

            if (editedRoot.isArray()) {
                String updatedRequestBody = applyBatchEdits((ArrayNode) editedRoot, originalRoot);
                return requestResponse.request().withBody(updatedRequestBody);
            }

            if (editedRoot.isObject()) {
                String updatedRequestBody = applySingleEdit(editedRoot, originalRoot);
                return requestResponse.request().withBody(updatedRequestBody);
            }
        } catch (Exception e) {
            logging.logToError("Error re-encoding function: " + e.getMessage());
            logging.logToError(e);
        }

        return requestResponse.request();
    }

    @Override
    public void setRequestResponse(HttpRequestResponse requestResponse) {
        this.requestResponse = requestResponse;
        requestEditor.setChainHint(-1);

        if (requestResponse == null || requestResponse.request() == null) {
            requestEditor.setText("No request context available.");
            return;
        }

        JsonNode requestRoot;
        try {
            requestRoot = objectMapper.readTree(requestResponse.request().bodyToString());
        } catch (Exception e) {
            requestEditor.setText("Invalid JSON-RPC request.");
            return;
        }

        boolean hasRpcItems = !Web3RequestContextDecoder.collectRpcItems(requestRoot).isEmpty();
        if (!hasRpcItems) {
            requestEditor.setText("No JSON-RPC calls found.");
            return;
        }

        String requestKey = generateRequestKey(requestResponse.request());
        if (requestKey == null) {
            requestEditor.setText("Unable to build request context key.");
            return;
        }

        RequestContextStore.clearRequestContext(requestKey);
        // The cache is populated by the decode below; until then surface whatever was
        // resolved on a prior pass through this URL so the chip isn't blank during the
        // SwingWorker round-trip.
        requestEditor.setChainHint(Web3RequestContextDecoder.cachedChainId(requestResponse.request().url()));
        boolean isBatch = requestRoot.isArray();
        decodeBatchAsync(requestResponse, isBatch, requestKey);
    }

    private String applySingleEdit(JsonNode editedRoot, JsonNode originalRoot) throws Exception {
        ObjectNode singleRpc = resolveRpcObject(originalRoot, 0);
        if (isSendRawTransaction(singleRpc)) {
            // A signed raw transaction is read-only: re-encoding would require
            // re-signing (out of scope). Return the request unchanged.
            return objectMapper.writeValueAsString(originalRoot);
        }

        String function = editedRoot.path("function").asText(null);
        JsonNode argsNode = editedRoot.get("args");
        if (function == null || argsNode == null) {
            throw new Exception("Missing function/args in edited request payload.");
        }

        String requestKey = generateRequestKey(requestResponse.request());
        String itemKey = buildItemKey(resolveRpcObject(originalRoot, 0), 0);
        RequestContextStore.ContextEntry context = RequestContextStore.getContext(requestKey, itemKey);
        if (context == null || context.abiJson() == null) {
            throw new Exception("No ABI context available for single request edit.");
        }

        Map<String, Object> args = objectMapper.convertValue(argsNode, new TypeReference<Map<String, Object>>() {});
        String encodedFunction = ABIInputDecoder.encodeInput(context.abiJson(), function, args);

        ObjectNode rpcObject = resolveRpcObject(originalRoot, 0);
        ObjectNode callParams = getCallParamsObject(rpcObject);
        if (callParams == null) {
            throw new Exception("Single request does not contain eth_call params[0] object.");
        }
        callParams.put("data", encodedFunction);
        return objectMapper.writeValueAsString(originalRoot);
    }

    private String applyBatchEdits(ArrayNode editedArray, JsonNode originalRoot) throws Exception {
        String requestKey = generateRequestKey(requestResponse.request());
        if (requestKey == null) {
            throw new Exception("Unable to build request context key.");
        }

        int updated = 0;
        for (JsonNode editedNode : editedArray) {
            if (!editedNode.isObject()) {
                continue;
            }

            if (!STATUS_DECODED.equals(editedNode.path("status").asText())) {
                continue;
            }

            int index = editedNode.path("index").asInt(-1);
            if (index >= 0 && isSendRawTransaction(resolveRpcObject(originalRoot, index))) {
                // Signed raw transaction: read-only, nothing to re-encode.
                continue;
            }

            String function = editedNode.path("function").asText(null);
            JsonNode argsNode = editedNode.get("args");
            if (function == null || argsNode == null || index < 0) {
                throw new Exception("Decoded batch entry is missing index/function/args.");
            }

            String itemKey = buildItemKeyFromEditedNode(editedNode, index);
            RequestContextStore.ContextEntry context = RequestContextStore.getContext(requestKey, itemKey);
            if (context == null || context.abiJson() == null) {
                context = RequestContextStore.getContext(requestKey, "index:" + index);
            }
            if (context == null || context.abiJson() == null) {
                throw new Exception("No ABI context available for batch entry " + index + ".");
            }

            Map<String, Object> args = objectMapper.convertValue(argsNode, new TypeReference<Map<String, Object>>() {});
            String encodedFunction = ABIInputDecoder.encodeInput(context.abiJson(), function, args);

            ObjectNode rpcObject = resolveRpcObject(originalRoot, index);
            ObjectNode callParams = getCallParamsObject(rpcObject);
            if (callParams == null) {
                throw new Exception("Batch entry " + index + " has no editable params[0] object.");
            }

            callParams.put("data", encodedFunction);
            updated++;
        }

        if (updated == 0) {
            throw new Exception("No decoded batch entries found to apply.");
        }

        return objectMapper.writeValueAsString(originalRoot);
    }

    private void decodeBatchAsync(HttpRequestResponse requestResponse, boolean isBatch, String requestKey) {
        new SwingWorker<List<Map<String, Object>>, Void>() {
            @Override
            protected List<Map<String, Object>> doInBackground() {
                return contextDecoder.decodeAndStore(requestResponse, requestKey);
            }

            @Override
            protected void done() {
                try {
                    // The decode itself populates the per-URL chain id cache.
                    requestEditor.setChainHint(
                            Web3RequestContextDecoder.cachedChainId(requestResponse.request().url()));

                    List<Map<String, Object>> outputRows = get();
                    if (outputRows.isEmpty()) {
                        requestEditor.setText("No decodable eth_call entries found.");
                        return;
                    }

                    if (!isBatch && outputRows.size() == 1) {
                        Map<String, Object> single = outputRows.get(0);
                        if (STATUS_DECODED.equals(single.get("status"))) {
                            Map<String, Object> orderedOutput = new LinkedHashMap<>();
                            orderedOutput.put("to", single.get("to"));
                            if (single.get("transaction") != null) {
                                orderedOutput.put("transaction", single.get("transaction"));
                            }
                            if (single.get("function") != null) {
                                orderedOutput.put("function", single.get("function"));
                            }
                            if (single.get("args") != null) {
                                orderedOutput.put("args", single.get("args"));
                            }
                            if (single.get("decodeSource") != null) {
                                orderedOutput.put("decodeSource", single.get("decodeSource"));
                            }
                            if (single.get("proxy") != null) {
                                orderedOutput.put("proxy", single.get("proxy"));
                            }
                            if (single.get("nestedCalls") != null) {
                                orderedOutput.put("nestedCalls", single.get("nestedCalls"));
                            }

                            functionSignature = (String) single.get("function");
                            String requestKey = generateRequestKey(requestResponse.request());
                            RequestContextStore.ContextEntry context = RequestContextStore.getContext(requestKey, "index:0");
                            abiJson = context != null ? context.abiJson() : null;

                            String jsonOutput = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(orderedOutput);
                            requestEditor.setText(jsonOutput);
                            return;
                        }

                        String reason = single.get("reason") != null ? single.get("reason").toString() : "No decoded output.";
                        requestEditor.setText(reason);
                        return;
                    }

                    String jsonOutput = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(outputRows);
                    requestEditor.setText(jsonOutput);
                } catch (Exception e) {
                    logging.logToError("Error decoding input data: " + e.getMessage());
                    requestEditor.setText("Error decoding input data.");
                }
            }
        }.execute();
    }

    private String buildItemKey(JsonNode rpcItem, int index) {
        return Web3RequestContextDecoder.buildItemKey(rpcItem, index);
    }

    private String buildItemKeyFromEditedNode(JsonNode editedNode, int index) {
        if (editedNode.has("id") && !editedNode.get("id").isNull()) {
            return "id:" + editedNode.get("id").asText();
        }
        return "index:" + index;
    }

    private ObjectNode resolveRpcObject(JsonNode root, int index) throws Exception {
        JsonNode rpcNode;
        if (root.isArray()) {
            if (index < 0 || index >= root.size()) {
                throw new Exception("Invalid batch index: " + index);
            }
            rpcNode = root.get(index);
        } else {
            rpcNode = root;
        }

        if (rpcNode == null || !rpcNode.isObject()) {
            throw new Exception("JSON-RPC entry is not an object.");
        }

        return (ObjectNode) rpcNode;
    }

    private ObjectNode getCallParamsObject(ObjectNode rpcObject) {
        JsonNode params = rpcObject.get("params");
        if (params == null || !params.isArray() || params.size() == 0) {
            return null;
        }

        JsonNode first = params.get(0);
        if (first == null || !first.isObject()) {
            return null;
        }

        return (ObjectNode) first;
    }

    private boolean isSendRawTransaction(ObjectNode rpcObject) {
        return rpcObject != null && "eth_sendRawTransaction".equals(rpcObject.path("method").asText());
    }

    /**
     * Generates a unique key for the request based on its URL and body.
     */
    private String generateRequestKey(HttpRequest request) {
        return Web3RequestContextDecoder.requestKey(request);
    }

    @Override
    public boolean isEnabledFor(HttpRequestResponse requestResponse) {
        if (requestResponse == null || requestResponse.request() == null) {
            return false;
        }

        try {
            JsonNode root = objectMapper.readTree(requestResponse.request().bodyToString());
            return Web3RequestContextDecoder.collectRpcItems(root).stream()
                    .anyMatch(item -> item.rpcItem != null && item.rpcItem.isObject()
                            && (item.isEthCall() || item.isSendRawTransaction()));
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    public String caption() {
        return "Web3 Request";
    }

    @Override
    public Component uiComponent() {
        return requestEditor.getComponent();
    }

    DecodedEditorPanel editorForTesting() {
        return requestEditor;
    }

    @Override
    public Selection selectedData() {
        String selected = requestEditor.getSelectedText();
        if (selected == null || selected.isEmpty()) {
            return null;
        }
        return Selection.selection(burp.api.montoya.core.ByteArray.byteArray(
                selected.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }

    @Override
    public boolean isModified() {
        return requestEditor.isModified();
    }
}
