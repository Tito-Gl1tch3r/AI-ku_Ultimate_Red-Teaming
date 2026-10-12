package com.nccgroup.web3decoder.annotation;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Builds a short history-row note from {@code decodeAndStore} rows. For a multicall it
 * lists the inner leaf functions (e.g. {@code transfer, approve}) and never the wrapper
 * (e.g. {@code aggregate3}). Pure: no I/O, no Burp types.
 */
public final class AnnotationNoteBuilder {

    public record Result(String notes, boolean isRawTransaction) {}

    private static final int MAX_NAMES = 4;

    private AnnotationNoteBuilder() {}

    @SuppressWarnings("unchecked")
    public static Result build(List<Map<String, Object>> rows) {
        List<String> names = new ArrayList<>();
        boolean rawTx = false;
        boolean anyMulticall = false;

        if (rows != null) {
            for (Map<String, Object> row : rows) {
                if ("eth_sendRawTransaction".equals(row.get("method"))) {
                    rawTx = true;
                }
                List<Map<String, Object>> nested = (List<Map<String, Object>>) row.get("nestedCalls");
                if (nested != null && !nested.isEmpty()) {
                    anyMulticall = true;
                    collectLeaves(nested, names);
                } else {
                    String n = shortName(row);
                    if (n != null) {
                        names.add(n);
                    }
                }
            }
        }

        if (names.isEmpty()) {
            return new Result("web3: (unresolved)", rawTx);
        }

        String prefix = anyMulticall ? "web3 mc: " : "web3: ";
        StringBuilder sb = new StringBuilder(prefix);
        int shown = Math.min(names.size(), MAX_NAMES);
        for (int i = 0; i < shown; i++) {
            if (i > 0) sb.append(", ");
            sb.append(names.get(i));
        }
        if (names.size() > MAX_NAMES) {
            sb.append(" (+").append(names.size() - MAX_NAMES).append(" more)");
        }
        return new Result(sb.toString(), rawTx);
    }

    @SuppressWarnings("unchecked")
    private static void collectLeaves(List<Map<String, Object>> nodes, List<String> out) {
        for (Map<String, Object> node : nodes) {
            List<Map<String, Object>> deeper = (List<Map<String, Object>>) node.get("nestedCalls");
            if (deeper != null && !deeper.isEmpty()) {
                collectLeaves(deeper, out); // descend; skip the inner wrapper's own name
            } else {
                String n = shortName(node);
                if (n != null) {
                    out.add(n);
                }
            }
        }
    }

    /** Bare function name (drops the parameter list), or the 4-byte selector as a fallback. */
    private static String shortName(Map<String, Object> node) {
        Object fn = node.get("function");
        if (fn instanceof String s && !s.isBlank()) {
            int paren = s.indexOf('(');
            return paren > 0 ? s.substring(0, paren) : s;
        }
        Object raw = node.get("rawCallData");
        if (raw instanceof String r && r.startsWith("0x") && r.length() >= 10) {
            return r.substring(0, 10);
        }
        return null;
    }
}
