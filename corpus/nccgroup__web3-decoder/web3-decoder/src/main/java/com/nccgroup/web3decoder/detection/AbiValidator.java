package com.nccgroup.web3decoder.detection;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Confirms a canonical-JSON candidate is a real Solidity ABI, computes its content
 * fingerprint, and extracts the 4-byte selectors of all function entries.
 */
public final class AbiValidator {

    private static final Set<String> VALID_TYPES = Set.of(
            "function", "constructor", "event", "fallback", "receive", "error"
    );

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private AbiValidator() {}

    public static Optional<DetectedAbi> validate(String canonicalJson) {
        if (canonicalJson == null || canonicalJson.isBlank()) return Optional.empty();
        JsonNode tree;
        try {
            tree = MAPPER.readTree(canonicalJson);
        } catch (Exception e) {
            return Optional.empty();
        }
        if (tree == null || !tree.isArray() || tree.isEmpty()) return Optional.empty();

        Set<String> selectorSet = new LinkedHashSet<>();
        for (JsonNode entry : tree) {
            if (!entry.isObject()) return Optional.empty();
            JsonNode type = entry.get("type");
            if (type == null || !type.isTextual()) return Optional.empty();
            String typeName = type.asText();
            if (!VALID_TYPES.contains(typeName)) return Optional.empty();
            if ("function".equals(typeName)) {
                Map<String, Object> fnMap = treeToFunctionMap(entry);
                if (fnMap == null) return Optional.empty();
                try {
                    selectorSet.add(AbiSelectorBuilder.selectorFor(fnMap));
                } catch (RuntimeException e) {
                    return Optional.empty();
                }
            }
        }

        return Optional.of(new DetectedAbi(
                sha256Hex(canonicalJson),
                canonicalJson,
                new ArrayList<>(selectorSet)
        ));
    }

    /** Convert a function JsonNode to the Map<String,Object> shape AbiSelectorBuilder expects. */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> treeToFunctionMap(JsonNode fn) {
        try {
            return MAPPER.convertValue(fn, Map.class);
        } catch (Exception e) {
            return null;
        }
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException("SHA-256 unavailable", e);
        }
    }
}
