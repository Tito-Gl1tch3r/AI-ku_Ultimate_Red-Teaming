package com.nccgroup.web3decoder.proxies;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpHeader;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.web3j.utils.Numeric;

import java.util.List;
import java.util.Map;

/**
 * Detects legacy ZeppelinOS/AdminUpgradeabilityProxy implementation slot.
 */
public class ZeppelinOSProxyDetector implements IProxyDetector {

    private static final String IMPLEMENTATION_SLOT =
            "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3";

    private final MontoyaApi montoyaApi;
    private final String jsonRpcUrl;
    private final List<HttpHeader> originHeaders;

    public ZeppelinOSProxyDetector(MontoyaApi montoyaApi, String jsonRpcUrl) {
        this(montoyaApi, jsonRpcUrl, List.of());
    }

    public ZeppelinOSProxyDetector(MontoyaApi montoyaApi, String jsonRpcUrl, List<HttpHeader> originHeaders) {
        this.montoyaApi = montoyaApi;
        this.jsonRpcUrl = jsonRpcUrl;
        this.originHeaders = originHeaders == null ? List.of() : originHeaders;
    }

    @Override
    public String getImplementationAddress(String contractAddress) throws Exception {
        Map<String, Object> jsonRpcRequest = Map.of(
                "jsonrpc", "2.0",
                "method", "eth_getStorageAt",
                "params", new Object[] {contractAddress, IMPLEMENTATION_SLOT, "latest"},
                "id", 1
        );

        ObjectMapper objectMapper = new ObjectMapper();
        String requestBody = objectMapper.writeValueAsString(jsonRpcRequest);

        HttpRequest httpRequest = HttpRequest.httpRequestFromUrl(jsonRpcUrl)
                .withMethod("POST")
                .withHeader("Content-Type", "application/json")
                .withBody(requestBody);
        httpRequest = ProxyDetector.withForwardedHeaders(httpRequest, originHeaders);

        HttpRequestResponse httpRequestResponse = montoyaApi.http().sendRequest(httpRequest);
        HttpResponse httpResponse = httpRequestResponse.response();

        if (httpResponse.statusCode() != 200) {
            throw new Exception("Failed to get implementation address: HTTP " + httpResponse.statusCode());
        }

        Map<String, Object> jsonRpcResponse = objectMapper.readValue(httpResponse.bodyToString(), Map.class);
        if (jsonRpcResponse.containsKey("error")) {
            Map<String, Object> error = (Map<String, Object>) jsonRpcResponse.get("error");
            throw new Exception("Error in JSON-RPC response: " + error.get("message"));
        }

        String result = (String) jsonRpcResponse.get("result");
        if (result == null || result.equals("0x")) {
            throw new Exception("No result from eth_getStorageAt");
        }

        String implementationAddressHex = "0x" + result.substring(result.length() - 40);
        String implementationAddress = Numeric.prependHexPrefix(Numeric.cleanHexPrefix(implementationAddressHex).toLowerCase());

        if (implementationAddress.matches("^0x0+$")) {
            return null;
        }

        return implementationAddress;
    }
}
