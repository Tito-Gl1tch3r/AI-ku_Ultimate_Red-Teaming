package com.nccgroup.web3decoder.proxies;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpHeader;
import burp.api.montoya.http.message.requests.HttpRequest;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;

public class ProxyDetector {

    /** Headers we never replay onto the synthetic eth_getStorageAt request. */
    private static final Set<String> SKIP_HEADERS = Set.of(
            "host", "content-type", "content-length",
            "connection", "keep-alive", "transfer-encoding",
            "upgrade", "proxy-connection", "te", "accept-encoding"
    );

    private final MontoyaApi api;
    private final String jsonRpcUrl;
    private final List<IProxyDetector> detectors = new ArrayList<>();

    /** Shared, process-wide negative/positive cache, keyed by (rpcUrl, address). */
    private static final Map<String, String> implementationCache = new ConcurrentHashMap<>();

    /** Concurrent dedup: in-flight lookups share one detector pass per (rpcUrl, address). */
    private static final ConcurrentHashMap<String, CompletableFuture<String>> inFlight = new ConcurrentHashMap<>();

    public ProxyDetector(MontoyaApi api, String jsonRpcUrl) {
        this(api, jsonRpcUrl, null);
    }

    /**
     * @param originHeaders Headers from the originating proxied request, replayed onto the
     *                      synthetic JSON-RPC calls so they satisfy the RPC's auth/origin
     *                      checks. {@code null} for code paths with no upstream request
     *                      (e.g. manual Calldata Codec input).
     */
    public ProxyDetector(MontoyaApi api, String jsonRpcUrl, List<HttpHeader> originHeaders) {
        this.api = api;
        this.jsonRpcUrl = jsonRpcUrl == null ? "" : jsonRpcUrl.trim().toLowerCase();
        List<HttpHeader> headers = originHeaders == null ? List.of() : List.copyOf(originHeaders);
        registerDetector(new ERC1967ProxyDetector(api, jsonRpcUrl, headers));
        registerDetector(new ZeppelinOSProxyDetector(api, jsonRpcUrl, headers));
    }

    public void registerDetector(IProxyDetector detector) {
        detectors.add(detector);
    }

    /**
     * Attempts to get the implementation address of a proxy contract.
     * Returns null if not a proxy or implementation address is 0x0 or null.
     * Caches the result to avoid redundant network calls.
     *
     * @param contractAddress The address of the contract to check.
     * @return The implementation address or null if not found.
     */
    public String getImplementationAddress(String contractAddress) {
        String normalizedContractAddress = contractAddress == null ? null : contractAddress.toLowerCase();
        if (normalizedContractAddress == null) {
            return null;
        }
        String cacheKey = cacheKey(normalizedContractAddress);

        String cached = implementationCache.get(cacheKey);
        if (cached != null) {
            return cached.equals("0x0") ? null : cached;
        }

        CompletableFuture<String> myFuture = new CompletableFuture<>();
        CompletableFuture<String> existing = inFlight.putIfAbsent(cacheKey, myFuture);
        if (existing != null) {
            // Another thread is already resolving this (rpc, address). Wait for its result.
            try {
                String result = existing.get();
                return "0x0".equals(result) ? null : result;
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return null;
            } catch (ExecutionException ee) {
                return null;
            }
        }

        String resolved = null;
        try {
            for (IProxyDetector detector : detectors) {
                try {
                    String implementationAddress = detector.getImplementationAddress(normalizedContractAddress);
                    if (implementationAddress != null && !implementationAddress.matches("0x0*")) {
                        resolved = implementationAddress;
                        break;
                    }
                } catch (Exception e) {
                    api.logging().logToError("Error getting implementation address for contract "
                            + normalizedContractAddress + ": " + e.getMessage());
                }
            }
            String toCache = resolved == null ? "0x0" : resolved;
            implementationCache.put(cacheKey, toCache);
            myFuture.complete(toCache);
            return resolved;
        } catch (Throwable t) {
            // Defensive: never leave waiters blocked.
            myFuture.completeExceptionally(t);
            throw t;
        } finally {
            inFlight.remove(cacheKey, myFuture);
        }
    }

    private String cacheKey(String contractAddress) {
        return jsonRpcUrl + "|" + contractAddress;
    }

    /**
     * Returns a copy of {@code request} with safe headers from {@code originHeaders}
     * added. Strips {@link #SKIP_HEADERS} and HTTP/2 pseudo-headers so we don't
     * overwrite the body framing we just set.
     */
    static HttpRequest withForwardedHeaders(HttpRequest request, List<HttpHeader> originHeaders) {
        if (originHeaders == null || originHeaders.isEmpty()) {
            return request;
        }
        List<HttpHeader> toAdd = new ArrayList<>();
        for (HttpHeader h : originHeaders) {
            String name = h.name();
            if (name == null || name.isEmpty() || name.startsWith(":")) {
                continue;
            }
            if (SKIP_HEADERS.contains(name.toLowerCase())) {
                continue;
            }
            toAdd.add(h);
        }
        return toAdd.isEmpty() ? request : request.withAddedHeaders(Collections.unmodifiableList(toAdd));
    }
}
