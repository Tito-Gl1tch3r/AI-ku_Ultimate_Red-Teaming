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

public class ERC1967ProxyDetector implements IProxyDetector {

    private final MontoyaApi montoyaApi;
    private final String jsonRpcUrl; // Ethereum node endpoint (e.g., Infura)
    private final List<HttpHeader> originHeaders;

    public ERC1967ProxyDetector(MontoyaApi montoyaApi, String jsonRpcUrl) {
        this(montoyaApi, jsonRpcUrl, List.of());
    }

    public ERC1967ProxyDetector(MontoyaApi montoyaApi, String jsonRpcUrl, List<HttpHeader> originHeaders) {
        this.montoyaApi = montoyaApi;
        this.jsonRpcUrl = jsonRpcUrl;
        this.originHeaders = originHeaders == null ? List.of() : originHeaders;
    }

    // @Override
    // public boolean isProxy(String contractAddress) {
    //     try {
    //         String implementationAddress = getImplementationAddress(contractAddress);
    //         return implementationAddress != null && !implementationAddress.equals("0x0000000000000000000000000000000000000000");
    //     } catch (Exception e) {
    //         // If an exception occurs, it might not be a proxy
    //         return false;
    //     }
    // }

    @Override
    public String getImplementationAddress(String contractAddress) throws Exception {
        // EIP-1967 implementation slot
        String implementationSlot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";

        // Build the JSON-RPC request
        Map<String, Object> jsonRpcRequest = Map.of(
                "jsonrpc", "2.0",
                "method", "eth_getStorageAt",
                "params", new Object[] {
                        contractAddress,
                        implementationSlot,
                        "latest"
                },
                "id", 1
        );

        // Serialize the request to JSON
        ObjectMapper objectMapper = new ObjectMapper();
        String requestBody = objectMapper.writeValueAsString(jsonRpcRequest);

        // Build the HTTP request using MontoyaApi, replaying origin headers so the
        // RPC's auth/origin/key checks pass (the dApp's request had them, ours wouldn't).
        HttpRequest httpRequest = HttpRequest.httpRequestFromUrl(jsonRpcUrl)
                .withMethod("POST")
                .withHeader("Content-Type", "application/json")
                .withBody(requestBody);
        httpRequest = ProxyDetector.withForwardedHeaders(httpRequest, originHeaders);

        // Send the request and get the response
        HttpRequestResponse httpRequestResponse = montoyaApi.http().sendRequest(httpRequest);
        HttpResponse httpResponse = httpRequestResponse.response();

        // Check the response status code
        if (httpResponse.statusCode() != 200) {
            throw new Exception("Failed to get implementation address: HTTP " + httpResponse.statusCode());
        }

        // Parse the response
        String responseBody = httpResponse.bodyToString();
        Map<String, Object> jsonRpcResponse = objectMapper.readValue(responseBody, Map.class);

        if (jsonRpcResponse.containsKey("error")) {
            Map<String, Object> error = (Map<String, Object>) jsonRpcResponse.get("error");
            String errorMessage = (String) error.get("message");
            throw new Exception("Error in JSON-RPC response: " + errorMessage);
        }

        // Get the result
        String result = (String) jsonRpcResponse.get("result");

        if (result == null || result.equals("0x")) {
            // No result, possibly not a proxy
            throw new Exception("No result from eth_getStorageAt");
        }

        // The result is the storage value at the implementation slot
        // The implementation address is the last 20 bytes of the 32-byte value
        String implementationAddressHex = "0x" + result.substring(result.length() - 40);

        // Normalize the address
        String implementationAddress = Numeric.prependHexPrefix(Numeric.cleanHexPrefix(implementationAddressHex).toLowerCase());
        // Check if implementation address is different from 0x and a number of zeros with a regex
        if (implementationAddress == null || implementationAddress.matches("^0x0+$")) {
            return null;
        } else
            return implementationAddress;
    }
}