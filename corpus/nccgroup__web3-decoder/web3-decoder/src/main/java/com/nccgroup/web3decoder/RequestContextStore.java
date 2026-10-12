package com.nccgroup.web3decoder;

import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import java.util.Collections;

public class RequestContextStore {
    public static class ContextEntry {
        private final String functionSignature;
        private final String abiJson;

        public ContextEntry(String functionSignature, String abiJson) {
            this.functionSignature = functionSignature;
            this.abiJson = abiJson;
        }

        public String functionSignature() {
            return functionSignature;
        }

        public String abiJson() {
            return abiJson;
        }
    }

    private static final Map<String, Map<String, ContextEntry>> requestContexts = new ConcurrentHashMap<>();
    private static final String DEFAULT_ITEM_KEY = "index:0";

    public static void clearRequestContext(String requestKey) {
        requestContexts.remove(requestKey);
    }

    public static void storeContext(String requestKey, String itemKey, String functionSignature, String abiJson) {
        if (requestKey == null || itemKey == null || functionSignature == null || abiJson == null) {
            return;
        }
        requestContexts.computeIfAbsent(requestKey, ignored -> new ConcurrentHashMap<>())
                .put(itemKey, new ContextEntry(functionSignature, abiJson));
    }

    public static ContextEntry getContext(String requestKey, String itemKey) {
        if (requestKey == null || itemKey == null) {
            return null;
        }
        Map<String, ContextEntry> contexts = requestContexts.get(requestKey);
        if (contexts == null) {
            return null;
        }
        return contexts.get(itemKey);
    }

    public static ContextEntry getLegacyContext(String requestKey) {
        return getContext(requestKey, DEFAULT_ITEM_KEY);
    }

    public static Map<String, ContextEntry> getContexts(String requestKey) {
        if (requestKey == null) {
            return Collections.emptyMap();
        }
        Map<String, ContextEntry> contexts = requestContexts.get(requestKey);
        if (contexts == null) {
            return Collections.emptyMap();
        }
        return Collections.unmodifiableMap(contexts);
    }

    public static boolean hasAnyContext(String requestKey) {
        Map<String, ContextEntry> contexts = requestContexts.get(requestKey);
        return contexts != null && !contexts.isEmpty();
    }

    public static void storeFunctionSignature(String requestKey, String functionSignature) {
        if (requestKey == null || functionSignature == null) {
            return;
        }
        ContextEntry existing = getLegacyContext(requestKey);
        String abi = existing != null ? existing.abiJson() : "";
        requestContexts.computeIfAbsent(requestKey, ignored -> new ConcurrentHashMap<>())
                .put(DEFAULT_ITEM_KEY, new ContextEntry(functionSignature, abi));
    }

    public static String getFunctionSignature(String requestKey) {
        ContextEntry legacyContext = getLegacyContext(requestKey);
        return legacyContext != null ? legacyContext.functionSignature() : null;
    }

    public static void storeAbiJson(String requestKey, String abiJson) {
        if (requestKey == null || abiJson == null) {
            return;
        }
        ContextEntry existing = getLegacyContext(requestKey);
        String function = existing != null ? existing.functionSignature() : "";
        requestContexts.computeIfAbsent(requestKey, ignored -> new ConcurrentHashMap<>())
                .put(DEFAULT_ITEM_KEY, new ContextEntry(function, abiJson));
    }

    public static String getAbiJson(String requestKey) {
        ContextEntry legacyContext = getLegacyContext(requestKey);
        return legacyContext != null ? legacyContext.abiJson() : null;
    }
}
