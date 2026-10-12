package com.nccgroup.web3_decoder.decoder;

import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.web3j.crypto.Hash;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ABIInputDecoderRealTransactionsTest {

    private static JSONArray realCases;

    @BeforeAll
    static void setup() throws Exception {
        realCases = new JSONArray(readResource("real_transactions_decoder_cases.json"));
    }

    @Test
    @DisplayName("Fixture calldata selectors match function signatures")
    void testFixtureSelectorsMatchSignatures() {
        for (int i = 0; i < realCases.length(); i++) {
            JSONObject txCase = realCases.getJSONObject(i);
            String calldata = txCase.getString("calldata");
            String functionSignature = txCase.getString("functionSignature");

            String expectedSelector = selectorFromSignature(functionSignature);
            assertEquals(
                    expectedSelector,
                    calldata.substring(0, 10),
                    "Selector mismatch for case " + txCase.getString("name") + " (" + txCase.getString("txHash") + ")"
            );
        }
    }

    @Test
    @DisplayName("Decodes real transaction calldata from Mainnet")
    void testDecodeRealTransactionCalldata() throws Exception {
        for (int i = 0; i < realCases.length(); i++) {
            JSONObject txCase = realCases.getJSONObject(i);
            String abiJson = txCase.getJSONArray("minimalAbi").toString();
            String calldata = txCase.getString("calldata");
            String expectedSignature = txCase.getString("functionSignature");
            String caseName = txCase.getString("name");
            String txHash = txCase.getString("txHash");

            Map<String, Object> decoded = ABIInputDecoder.decodeInput(abiJson, calldata);
            assertEquals(
                    expectedSignature,
                    decoded.get("function"),
                    "Function signature mismatch for case " + caseName + " (" + txHash + ")"
            );

            Map<String, Object> args = castMap(decoded.get("args"));
            assertCaseSpecificValues(caseName, args);
        }
    }

    private static void assertCaseSpecificValues(String caseName, Map<String, Object> args) {
        switch (caseName) {
            case "usdt_transfer":
                assertEquals("0x3b6dcfde35e53fb7dca8571f23286631b5123c5b", args.get("_to"));
                assertEquals(BigInteger.TEN, args.get("_value"));
                break;

            case "uniswap_v2_swap_exact_eth_for_tokens":
                assertEquals(BigInteger.valueOf(80522L), args.get("amountOutMin"));
                assertEquals("0xb557ba13d1681ca32416981a79ceb837858f2cae", args.get("to"));
                assertEquals(BigInteger.valueOf(1755462889L), args.get("deadline"));
                assertInstanceOf(List.class, args.get("path"));
                List<?> path = (List<?>) args.get("path");
                assertEquals(2, path.size());
                assertEquals("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", path.get(0));
                assertEquals("0x4ff23cf2804e777c233890119b881cab7fd60652", path.get(1));
                break;

            case "multicall3_aggregate3":
                assertInstanceOf(List.class, args.get("calls"));
                List<?> calls = (List<?>) args.get("calls");
                assertEquals(1, calls.size());
                assertInstanceOf(Map.class, calls.get(0));
                Map<?, ?> call0 = (Map<?, ?>) calls.get(0);
                assertEquals("0x06ef1dcf87e419c48b94a331b252819fadbd63ef", call0.get("target"));
                assertEquals(true, call0.get("allowFailure"));
                assertInstanceOf(String.class, call0.get("callData"));
                assertTrue(((String) call0.get("callData")).startsWith("0xb2406d94"));
                break;

            case "usdc_permit":
                assertEquals("0x81573929c0618545d686210b3b8e678f18ee1350", args.get("owner"));
                assertEquals("0x36e36c2df35331a515b81d6dcdd2a957d91937af", args.get("spender"));
                assertEquals(BigInteger.valueOf(239407881L), args.get("value"));
                assertEquals(BigInteger.valueOf(1772737469L), args.get("deadline"));
                assertEquals(BigInteger.valueOf(27L), args.get("v"));
                assertInstanceOf(String.class, args.get("r"));
                assertInstanceOf(String.class, args.get("s"));
                assertEquals(66, ((String) args.get("r")).length());
                assertEquals(66, ((String) args.get("s")).length());
                break;

            default:
                throw new IllegalArgumentException("Unhandled case: " + caseName);
        }
    }

    private static String selectorFromSignature(String functionSignature) {
        String hash = Hash.sha3String(functionSignature);
        return "0x" + hash.substring(2, 10);
    }

    private static String readResource(String name) throws IOException {
        try (InputStream inputStream = ABIInputDecoderRealTransactionsTest.class.getClassLoader().getResourceAsStream(name)) {
            if (inputStream == null) {
                throw new IOException("Missing resource " + name);
            }
            return new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        return (Map<String, Object>) value;
    }
}
