package com.nccgroup.web3decoder.detection;

import org.web3j.crypto.Hash;

import java.util.List;
import java.util.Map;

/**
 * Computes 4-byte function selectors and canonical signatures from ABI
 * function objects in their Map representation (as produced by Jackson when
 * parsing an ABI JSON array).
 *
 * <p>The Map shape matches what {@code ABIInputDecoder} feeds through Jackson:
 * a function entry has {@code name}, {@code inputs} (a list of parameter maps
 * each carrying {@code type} and optionally {@code components} for tuples).
 */
public final class AbiSelectorBuilder {

    private static final String TYPE_TUPLE = "tuple";

    private AbiSelectorBuilder() {}

    /** {@code "0x"} + first 8 hex chars of {@code keccak256(canonicalSignature(fn))}. */
    public static String selectorFor(Map<String, Object> functionDefinition) {
        String signature = canonicalSignature(functionDefinition);
        String hash = Hash.sha3String(signature);
        return "0x" + hash.substring(2, 10);
    }

    /** e.g. {@code "transfer(address,uint256)"} or {@code "multicall((address,bytes)[])"}. */
    public static String canonicalSignature(Map<String, Object> functionDefinition) {
        StringBuilder sb = new StringBuilder();
        sb.append(functionDefinition.get("name")).append("(");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> inputs =
                (List<Map<String, Object>>) functionDefinition.get("inputs");
        if (inputs != null) {
            for (int i = 0; i < inputs.size(); i++) {
                sb.append(canonicalType(inputs.get(i)));
                if (i < inputs.size() - 1) sb.append(",");
            }
        }
        sb.append(")");
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static String canonicalType(Map<String, Object> parameterDefinition) {
        String type = normalizeSolidityType((String) parameterDefinition.get("type"));
        if (type == null) return "";
        if (type.startsWith(TYPE_TUPLE)) {
            String suffix = type.substring(TYPE_TUPLE.length());
            List<Map<String, Object>> components =
                    (List<Map<String, Object>>) parameterDefinition.get("components");
            if (components == null || components.isEmpty()) {
                throw new IllegalArgumentException("Tuple type is missing components.");
            }

            StringBuilder builder = new StringBuilder("(");
            for (int i = 0; i < components.size(); i++) {
                builder.append(canonicalType(components.get(i)));
                if (i < components.size() - 1) {
                    builder.append(",");
                }
            }
            builder.append(")");
            builder.append(suffix);
            return builder.toString();
        }
        return type;
    }

    private static String normalizeSolidityType(String solidityType) {
        if ("uint".equals(solidityType)) {
            return "uint256";
        }
        if ("int".equals(solidityType)) {
            return "int256";
        }
        return solidityType;
    }
}
