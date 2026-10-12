package com.nccgroup.web3_decoder.decoder;

import com.nccgroup.web3decoder.decoder.MulticallRecursiveDecoder;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigInteger;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MulticallRecursiveDecoderTest {

    private static final String MULTICALL = "0xca11bde05977b3631167028862be2a173976ca11";

    @Test
    @DisplayName("Extracts nested calls for all supported multicall signatures")
    void testExtractSupportedMulticallMethods() {
        assertExtracts("aggregate((address,bytes)[])", List.of(List.of("0x111", "0xaaa")));
        assertExtracts("tryAggregate(bool,(address,bytes)[])", List.of(List.of("0x111", "0xbbb")));
        assertExtracts("blockAndAggregate(bool,(address,bytes)[])", List.of(List.of("0x111", "0xccc")));
        assertExtracts("tryBlockAndAggregate(bool,(address,bytes)[])", List.of(List.of("0x111", "0xddd")));

        List<Map<String, Object>> aggregate3 = decode(
                "aggregate3((address,bool,bytes)[])",
                List.of(List.of("0x222", true, "0xeee")),
                (target, callData) -> decoded("transfer(address,uint256)", Map.of("to", "0xaaa", "value", BigInteger.ONE))
        );
        assertEquals(true, aggregate3.get(0).get("allowFailure"));

        List<Map<String, Object>> aggregate3Value = decode(
                "aggregate3Value((address,bool,uint256,bytes)[])",
                List.of(List.of("0x333", false, BigInteger.TEN, "0xfff")),
                (target, callData) -> decoded("approve(address,uint256)", Map.of("spender", "0xbbb", "value", BigInteger.TEN))
        );
        assertEquals(false, aggregate3Value.get(0).get("allowFailure"));
        assertEquals(BigInteger.TEN, aggregate3Value.get(0).get("value"));
    }

    @Test
    @DisplayName("Recurses and stops when reaching maximum depth")
    void testRecursionDepthLimit() {
        List<List<Object>> topCalls = List.of(List.of(MULTICALL, true, "0xmc1"));

        List<Map<String, Object>> nested = decode(
                "aggregate3((address,bool,bytes)[])",
                topCalls,
                (target, callData) -> {
                    if ("0xmc1".equals(callData)) {
                        return decoded("aggregate3((address,bool,bytes)[])", Map.of("calls", List.of(List.of(MULTICALL, true, "0xmc2"))));
                    }
                    if ("0xmc2".equals(callData)) {
                        return decoded("aggregate3((address,bool,bytes)[])", Map.of("calls", List.of(List.of(MULTICALL, true, "0xmc3"))));
                    }
                    if ("0xmc3".equals(callData)) {
                        return decoded("aggregate3((address,bool,bytes)[])", Map.of("calls", List.of(List.of(MULTICALL, true, "0xleaf"))));
                    }
                    return decoded("transfer(address,uint256)", Map.of("to", "0xabc", "value", BigInteger.ONE));
                }
        );

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> depth2 = (List<Map<String, Object>>) nested.get(0).get("nestedCalls");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> depth3 = (List<Map<String, Object>>) depth2.get(0).get("nestedCalls");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> depth4 = (List<Map<String, Object>>) depth3.get(0).get("nestedCalls");

        assertEquals("decoded", nested.get(0).get("status"));
        assertEquals("decoded", depth2.get(0).get("status"));
        assertEquals("decoded", depth3.get(0).get("status"));
        assertEquals("skipped", depth4.get(0).get("status"));
        assertTrue(depth4.get(0).get("reason").toString().contains("depth limit"));
        assertEquals("0xleaf", depth4.get(0).get("rawCallData"));
    }

    @Test
    @DisplayName("Keeps raw calldata and error when nested decode fails")
    void testFallbackWhenNestedDecodeFails() {
        List<Map<String, Object>> nested = decode(
                "aggregate3((address,bool,bytes)[])",
                List.of(List.of("0xdead", true, "0xbad")),
                (target, callData) -> {
                    throw new Exception("ABI not found for target " + target);
                }
        );

        Map<String, Object> node = nested.get(0);
        assertEquals("error", node.get("status"));
        assertEquals("0xbad", node.get("rawCallData"));
        assertTrue(node.get("reason").toString().contains("ABI not found"));
    }

    @Test
    @DisplayName("Decodes supported multicall signatures regardless of target address")
    void testNonMulticallTarget() {
        List<Map<String, Object>> nested = MulticallRecursiveDecoder.decodeNestedCalls(
                "0x1234",
                "aggregate3((address,bool,bytes)[])",
                Map.of("calls", List.of(List.of("0x111", true, "0xaaa"))),
                3,
                (target, callData) -> decoded("foo()", Map.of())
        );

        assertEquals(1, nested.size());
        assertTrue(MulticallRecursiveDecoder.isSupportedMulticall("0x1234", "aggregate3((address,bool,bytes)[])"));
    }

    private static void assertExtracts(String signature, List<List<Object>> calls) {
        List<Map<String, Object>> nested = decode(
                signature,
                calls,
                (target, callData) -> decoded("balanceOf(address)", Map.of("owner", "0xabc"))
        );

        assertEquals(1, nested.size());
        assertEquals("decoded", nested.get(0).get("status"));
        assertEquals(calls.get(0).get(0), nested.get(0).get("target"));
    }

    private static List<Map<String, Object>> decode(
            String functionSignature,
            List<List<Object>> calls,
            MulticallRecursiveDecoder.NestedCallDecoder decoder
    ) {
        Map<String, Object> args = new LinkedHashMap<>();
        args.put("calls", calls);
        return MulticallRecursiveDecoder.decodeNestedCalls(MULTICALL, functionSignature, args, 3, decoder);
    }

    private static Map<String, Object> decoded(String function, Map<String, Object> args) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("function", function);
        result.put("args", args);
        return result;
    }
}
