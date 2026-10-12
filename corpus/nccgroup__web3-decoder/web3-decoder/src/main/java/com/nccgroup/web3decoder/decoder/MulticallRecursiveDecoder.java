package com.nccgroup.web3decoder.decoder;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class MulticallRecursiveDecoder {
    public static final String MULTICALL3_ADDRESS = "0xca11bde05977b3631167028862be2a173976ca11";

    private static final String STATUS_DECODED = "decoded";
    private static final String STATUS_SKIPPED = "skipped";
    private static final String STATUS_ERROR = "error";

    private static final Set<String> SUPPORTED_MULTICALL_FUNCTIONS = Set.of(
            "aggregate((address,bytes)[])",
            "tryAggregate(bool,(address,bytes)[])",
            "aggregate3((address,bool,bytes)[])",
            "aggregate3Value((address,bool,uint256,bytes)[])",
            "blockAndAggregate(bool,(address,bytes)[])",
            "tryBlockAndAggregate(bool,(address,bytes)[])"
    );

    @FunctionalInterface
    public interface NestedCallDecoder {
        Map<String, Object> decode(String target, String callData) throws Exception;
    }

    /**
     * Receives per-nested-call decode context. The path is hierarchical and
     * stable across the request/response pair (e.g. "index:0/nested:3").
     */
    @FunctionalInterface
    public interface NestedContextRecorder {
        void record(String path, String function, String abiJson);
    }

    /**
     * Stash key the {@link NestedCallDecoder} can use to hand the ABI used for
     * a nested decode back to this class. The key is removed before the node
     * is returned so it never appears in the user-facing JSON output.
     */
    public static final String ABI_STASH_KEY = "__abiJson";

    private static final class NestedCallDescriptor {
        private final String target;
        private final String callData;
        private final Object allowFailure;
        private final Object value;

        private NestedCallDescriptor(String target, String callData, Object allowFailure, Object value) {
            this.target = target;
            this.callData = callData;
            this.allowFailure = allowFailure;
            this.value = value;
        }
    }

    private MulticallRecursiveDecoder() {
    }

    public static boolean isSupportedMulticall(String target, String functionSignature) {
        if (functionSignature == null) {
            return false;
        }
        return SUPPORTED_MULTICALL_FUNCTIONS.contains(functionSignature);
    }

    public static List<Map<String, Object>> decodeNestedCalls(
            String target,
            String functionSignature,
            Map<String, Object> args,
            int maxDepth,
            NestedCallDecoder decoder
    ) {
        return decodeNestedCalls(target, functionSignature, args, maxDepth, decoder, null, null);
    }

    public static List<Map<String, Object>> decodeNestedCalls(
            String target,
            String functionSignature,
            Map<String, Object> args,
            int maxDepth,
            NestedCallDecoder decoder,
            String basePath,
            NestedContextRecorder recorder
    ) {
        if (!isSupportedMulticall(target, functionSignature) || args == null || decoder == null || maxDepth < 1) {
            return Collections.emptyList();
        }

        List<NestedCallDescriptor> descriptors = extractDescriptors(functionSignature, args);
        if (descriptors.isEmpty()) {
            return Collections.emptyList();
        }

        return decodeDescriptors(descriptors, 1, maxDepth, decoder, basePath, recorder);
    }

    private static List<Map<String, Object>> decodeDescriptors(
            List<NestedCallDescriptor> descriptors,
            int depth,
            int maxDepth,
            NestedCallDecoder decoder,
            String basePath,
            NestedContextRecorder recorder
    ) {
        List<Map<String, Object>> output = new ArrayList<>();

        for (int i = 0; i < descriptors.size(); i++) {
            NestedCallDescriptor descriptor = descriptors.get(i);
            String currentPath = basePath == null ? null : basePath + "/nested:" + i;
            Map<String, Object> node = new LinkedHashMap<>();
            node.put("depth", depth);
            node.put("target", descriptor.target);

            if (descriptor.allowFailure != null) {
                node.put("allowFailure", descriptor.allowFailure);
            }
            if (descriptor.value != null) {
                node.put("value", descriptor.value);
            }

            if (descriptor.target == null || descriptor.callData == null || descriptor.callData.isEmpty()) {
                node.put("status", STATUS_SKIPPED);
                node.put("reason", "Missing nested target or callData.");
                node.put("rawCallData", descriptor.callData);
                output.add(node);
                continue;
            }

            if (depth > maxDepth) {
                node.put("status", STATUS_SKIPPED);
                node.put("reason", "Reached recursion depth limit.");
                node.put("rawCallData", descriptor.callData);
                output.add(node);
                continue;
            }

            try {
                Map<String, Object> decoded = decoder.decode(descriptor.target, descriptor.callData);
                String function = decoded == null ? null : (String) decoded.get("function");
                @SuppressWarnings("unchecked")
                Map<String, Object> args = decoded == null ? null : (Map<String, Object>) decoded.get("args");
                Object abiStash = decoded == null ? null : decoded.remove(ABI_STASH_KEY);
                String abiJson = abiStash instanceof String ? (String) abiStash : null;

                if (function == null || args == null) {
                    node.put("status", STATUS_ERROR);
                    node.put("reason", "Nested decode returned invalid payload.");
                    node.put("rawCallData", descriptor.callData);
                    output.add(node);
                    continue;
                }

                node.put("status", STATUS_DECODED);
                node.put("function", function);
                node.put("args", args);
                if (decoded.get("decodeSource") != null) {
                    node.put("decodeSource", decoded.get("decodeSource"));
                }
                if (Boolean.TRUE.equals(decoded.get("isProxy"))) {
                    Map<String, Object> proxyInfo = new LinkedHashMap<>();
                    proxyInfo.put("isProxy", true);
                    proxyInfo.put("proxyTarget", decoded.get("proxyTarget"));
                    proxyInfo.put("implementationAddress", decoded.get("implementationAddress"));
                    proxyInfo.put("decodedUsing", decoded.get("decodedUsing"));
                    node.put("proxy", proxyInfo);
                }

                if (recorder != null && currentPath != null && abiJson != null) {
                    recorder.record(currentPath, function, abiJson);
                }

                if (isSupportedMulticall(descriptor.target, function)) {
                    List<NestedCallDescriptor> nestedDescriptors = extractDescriptors(function, args);
                    if (!nestedDescriptors.isEmpty()) {
                        List<Map<String, Object>> nested = decodeDescriptors(
                                nestedDescriptors, depth + 1, maxDepth, decoder, currentPath, recorder);
                        node.put("nestedCalls", nested);
                    }
                }
            } catch (Exception e) {
                node.put("status", STATUS_ERROR);
                node.put("reason", e.getMessage());
                node.put("rawCallData", descriptor.callData);
            }

            output.add(node);
        }

        return output;
    }

    @SuppressWarnings("unchecked")
    private static List<NestedCallDescriptor> extractDescriptors(String functionSignature, Map<String, Object> args) {
        Object callsObject = args.get("calls");
        if (!(callsObject instanceof List<?>)) {
            // Fallback for synthetic 4byte-derived ABIs whose parameter names are
            // generic (param0, param1, ...). All supported multicall signatures
            // have exactly one tuple-array argument, so the first List value is it.
            callsObject = null;
            for (Object value : args.values()) {
                if (value instanceof List<?>) {
                    callsObject = value;
                    break;
                }
            }
            if (callsObject == null) {
                return Collections.emptyList();
            }
        }

        List<?> calls = (List<?>) callsObject;
        List<NestedCallDescriptor> descriptors = new ArrayList<>();

        for (Object call : calls) {
            // A call tuple may be a positional list ([target, ...]) or, when the
            // ABI carries component names, a map ({target, callData, ...}).
            if (!(call instanceof List<?>) && !(call instanceof Map<?, ?>)) {
                continue;
            }

            NestedCallDescriptor descriptor = buildDescriptor(functionSignature, call);
            if (descriptor != null) {
                descriptors.add(descriptor);
            }
        }

        return descriptors;
    }

    private static NestedCallDescriptor buildDescriptor(String functionSignature, Object call) {
        switch (functionSignature) {
            case "aggregate((address,bytes)[])":
            case "tryAggregate(bool,(address,bytes)[])":
            case "blockAndAggregate(bool,(address,bytes)[])":
            case "tryBlockAndAggregate(bool,(address,bytes)[])": {
                String target = asString(field(call, 0, "target"));
                Object callData = field(call, 1, "callData");
                if (target == null || callData == null) {
                    return null;
                }
                return new NestedCallDescriptor(target, asString(callData), null, null);
            }

            case "aggregate3((address,bool,bytes)[])": {
                String target = asString(field(call, 0, "target"));
                Object allowFailure = field(call, 1, "allowFailure");
                Object callData = field(call, 2, "callData");
                if (target == null || callData == null) {
                    return null;
                }
                return new NestedCallDescriptor(target, asString(callData), allowFailure, null);
            }

            case "aggregate3Value((address,bool,uint256,bytes)[])": {
                String target = asString(field(call, 0, "target"));
                Object allowFailure = field(call, 1, "allowFailure");
                Object value = field(call, 2, "value");
                Object callData = field(call, 3, "callData");
                if (target == null || callData == null) {
                    return null;
                }
                return new NestedCallDescriptor(target, asString(callData), allowFailure, value);
            }

            default:
                return null;
        }
    }

    /**
     * Reads a call-tuple field either by name (named-map decode) or by position
     * (positional-list decode / synthetic 4byte ABIs without component names).
     */
    private static Object field(Object call, int index, String name) {
        if (call instanceof Map<?, ?>) {
            return ((Map<?, ?>) call).get(name);
        }
        if (call instanceof List<?>) {
            List<?> list = (List<?>) call;
            return index < list.size() ? list.get(index) : null;
        }
        return null;
    }

    private static String asString(Object value) {
        return value == null ? null : value.toString();
    }
}
