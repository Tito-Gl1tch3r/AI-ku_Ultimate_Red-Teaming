package com.nccgroup.web3_decoder.decoder;

import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Address;
import org.web3j.abi.datatypes.Bool;
import org.web3j.abi.datatypes.DynamicArray;
import org.web3j.abi.datatypes.DynamicBytes;
import org.web3j.abi.datatypes.DynamicStruct;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.Type;
import org.web3j.abi.datatypes.Utf8String;
import org.web3j.abi.datatypes.generated.Bytes9;
import org.web3j.abi.datatypes.generated.StaticArray2;
import org.web3j.abi.datatypes.generated.Uint256;
import org.web3j.abi.datatypes.generated.Int256;
import org.web3j.utils.Numeric;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ABIInputDecoderTest {

    private static final String ADDRESS = "0x6e2cb485076ebc5f5fdf7be66ad750bee385cf7a";

    private static String simpleAbiJson;
    private static String tokenAbiJson;
    private static String edgeCaseAbiJson;

    @BeforeAll
    static void setup() throws Exception {
        simpleAbiJson = readResource("simple_contract_abi.json");
        tokenAbiJson = readResource("abi_0x3f382dbd960e3a9bbceae22651e88158d2791550.json");
        edgeCaseAbiJson = readResource("decoder_edge_cases_abi.json");
    }

    @Test
    @DisplayName("Decodes and re-encodes the existing ENS reverse lookup fixture")
    void testDecodeAndReencodeSimpleFunction() throws Exception {
        String inputData = "0xec11c8230000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000003728366532636234383530373665626335663566646637626536366164373530626565333835636637610461646472077265766572736500000000000000000000";

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(simpleAbiJson, inputData);

        assertEquals("reverse(bytes)", decoded.get("function"));

        Map<String, Object> args = castMap(decoded.get("args"));
        String reverseNameHex = (String) args.get("reverseName");
        byte[] reverseNameBytes = Numeric.hexStringToByteArray(reverseNameHex);
        String actualBase64 = Base64.getEncoder().encodeToString(reverseNameBytes);
        assertEquals("KDZlMmNiNDg1MDc2ZWJjNWY1ZmRmN2JlNjZhZDc1MGJlZTM4NWNmN2EEYWRkcgdyZXZlcnNlAA==", actualBase64);

        Map<String, Object> argsForEncoding = new HashMap<>();
        argsForEncoding.put("reverseName", reverseNameHex);
        String reEncodedInputData = ABIInputDecoder.encodeInput(simpleAbiJson, "reverse(bytes)", argsForEncoding);

        assertEquals(inputData, reEncodedInputData);
    }

    @Test
    @DisplayName("Decodes and re-encodes an ERC20 balanceOf call")
    void testDecodeAndReencodeBalanceOfFunction() throws Exception {
        String inputData = "0x70a082310000000000000000000000006e2cb485076ebc5f5fdf7be66ad750bee385cf7a";

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(tokenAbiJson, inputData);

        assertEquals("balanceOf(address)", decoded.get("function"));

        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(ADDRESS, args.get("_owner"));

        Map<String, Object> argsForEncoding = new HashMap<>();
        argsForEncoding.put("_owner", args.get("_owner"));

        String reEncodedInputData = ABIInputDecoder.encodeInput(tokenAbiJson, "balanceOf(address)", argsForEncoding);

        assertEquals(inputData, reEncodedInputData);
    }

    @Test
    @DisplayName("Round-trips mixed scalar types including dynamic bytes, fixed bytes, and signed ints")
    void testRoundTripMixedScalars() throws Exception {
        Function function = new Function(
                "roundTripMixed",
                List.of(
                        new Address(ADDRESS),
                        new Bool(true),
                        new Utf8String("hello world"),
                        new DynamicBytes(Numeric.hexStringToByteArray("0x1234abcd")),
                        new Bytes9(Numeric.hexStringToByteArray("0x010203040506070809")),
                        new Uint256(BigInteger.valueOf(123456789L)),
                        new Int256(BigInteger.valueOf(-42))
                ),
                List.of()
        );
        String inputData = FunctionEncoder.encode(function);

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        assertEquals("roundTripMixed(address,bool,string,bytes,bytes9,uint256,int256)", decoded.get("function"));

        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(ADDRESS, args.get("target"));
        assertEquals(true, args.get("enabled"));
        assertEquals("hello world", args.get("note"));
        assertEquals("0x1234abcd", args.get("payload"));
        assertEquals("0x010203040506070809", args.get("salt"));
        assertEquals(BigInteger.valueOf(123456789L), args.get("amount"));
        assertEquals(BigInteger.valueOf(-42), args.get("delta"));

        String reEncoded = ABIInputDecoder.encodeInput(edgeCaseAbiJson, (String) decoded.get("function"), args);
        assertEquals(inputData, reEncoded);
    }

    @Test
    @DisplayName("Uses canonical uint256 and int256 signatures for uint and int aliases")
    void testAliasTypesUseCanonicalSignature() throws Exception {
        Function function = new Function(
                "aliasNumbers",
                List.of(new Uint256(BigInteger.valueOf(7)), new Int256(BigInteger.valueOf(-3))),
                List.of()
        );
        String inputData = FunctionEncoder.encode(function);

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        assertEquals("aliasNumbers(uint256,int256)", decoded.get("function"));

        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(BigInteger.valueOf(7), args.get("value"));
        assertEquals(BigInteger.valueOf(-3), args.get("delta"));

        String reEncoded = ABIInputDecoder.encodeInput(edgeCaseAbiJson, "aliasNumbers(uint256,int256)", args);
        assertEquals(inputData, reEncoded);
    }

    @Test
    @DisplayName("Assigns default names for unnamed inputs and outputs")
    void testUnnamedInputAndOutputKeys() throws Exception {
        Function function = new Function(
                "unnamedThings",
                List.of(new Uint256(BigInteger.TEN), new Address(ADDRESS)),
                List.of()
        );
        String inputData = FunctionEncoder.encode(function);

        Map<String, Object> decodedInput = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        Map<String, Object> args = castMap(decodedInput.get("args"));
        assertEquals(BigInteger.TEN, args.get("param0"));
        assertEquals(ADDRESS, args.get("param1"));

        String outputData = FunctionEncoder.encodeConstructor(List.of(
                new DynamicBytes(Numeric.hexStringToByteArray("0xcafe")),
                new Bool(true)
        ));

        Map<String, Object> decodedOutput = ABIInputDecoder.decodeOutput(edgeCaseAbiJson, "unnamedThings(uint256,address)", outputData);
        Map<String, Object> outputs = castMap(decodedOutput.get("output"));
        assertEquals("0xcafe", outputs.get("output0"));
        assertEquals(true, outputs.get("output1"));
    }

    @Test
    @DisplayName("Decodes and re-encodes fixed arrays and rejects wrong fixed-array lengths")
    void testFixedArrayHandling() throws Exception {
        Function function = new Function(
                "setFixedArray",
                List.of(new StaticArray2<>(Uint256.class, new Uint256(BigInteger.ONE), new Uint256(BigInteger.TWO))),
                List.of()
        );
        String inputData = FunctionEncoder.encode(function);

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(List.of(BigInteger.ONE, BigInteger.TWO), args.get("values"));

        String reEncoded = ABIInputDecoder.encodeInput(edgeCaseAbiJson, "setFixedArray(uint256[2])", args);
        assertEquals(inputData, reEncoded);

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> ABIInputDecoder.encodeInput(edgeCaseAbiJson, "setFixedArray(uint256[2])", Map.of("values", List.of("1")))
        );
        assertTrue(exception.getMessage().contains("Expected array of size 2"));
    }

    @Test
    @DisplayName("Decodes and re-encodes dynamic arrays")
    void testDynamicArrayHandling() throws Exception {
        Function function = new Function(
                "setDynamicArray",
                List.of(new DynamicArray<>(Utf8String.class, new Utf8String("alpha"), new Utf8String("beta"))),
                List.of()
        );
        String inputData = FunctionEncoder.encode(function);

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(List.of("alpha", "beta"), args.get("values"));

        String reEncoded = ABIInputDecoder.encodeInput(edgeCaseAbiJson, "setDynamicArray(string[])", args);
        assertEquals(inputData, reEncoded);
    }

    @Test
    @DisplayName("Decodes and re-encodes standard tuple inputs")
    void testTupleInputHandling() throws Exception {
        Map<String, Object> orderArg = new HashMap<>();
        orderArg.put("owner", ADDRESS);
        orderArg.put("amount", BigInteger.valueOf(99));
        String inputData = ABIInputDecoder.encodeInput(edgeCaseAbiJson, "setTuple((address,uint256))", Map.of("order", orderArg));

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(edgeCaseAbiJson, inputData);
        assertEquals("setTuple((address,uint256))", decoded.get("function"));

        Map<String, Object> args = castMap(decoded.get("args"));
        assertEquals(Map.of("owner", ADDRESS, "amount", BigInteger.valueOf(99)), args.get("order"));

        String reEncoded = ABIInputDecoder.encodeInput(edgeCaseAbiJson, "setTuple((address,uint256))", Map.of("order", orderArg));
        assertEquals(inputData, reEncoded);
    }

    @Test
    @DisplayName("Decodes nested tuple arrays in outputs")
    void testTupleArrayOutputHandling() throws Exception {
        DynamicStruct first = tuple(new Bool(true), new DynamicBytes(Numeric.hexStringToByteArray("0x1234")));
        DynamicStruct second = tuple(new Bool(false), new DynamicBytes(Numeric.hexStringToByteArray("0xabcd")));

        String outputData = FunctionEncoder.encodeConstructor(List.of(
                new DynamicArray<>(DynamicStruct.class, first, second)
        ));

        Map<String, Object> decoded = ABIInputDecoder.decodeOutput(edgeCaseAbiJson, "setTupleArray((bool,bytes)[])", outputData);
        Map<String, Object> output = castMap(decoded.get("output"));

        Object echoed = output.get("echoed");
        assertInstanceOf(List.class, echoed);
        assertEquals(
                List.of(
                        Map.of("success", true, "returnData", "0x1234"),
                        Map.of("success", false, "returnData", "0xabcd")
                ),
                echoed
        );
    }

    @Test
    @DisplayName("Decodes outputs for existing and custom ABIs")
    void testDecodeOutput() throws Exception {
        String erc20Output = FunctionEncoder.encodeConstructor(List.of(new Uint256(BigInteger.valueOf(55))));
        Map<String, Object> tokenDecoded = ABIInputDecoder.decodeOutput(tokenAbiJson, "balanceOf(address)", erc20Output);
        assertEquals(BigInteger.valueOf(55), castMap(tokenDecoded.get("output")).get("balance"));

        String mixedOutput = FunctionEncoder.encodeConstructor(List.of(
                new Bool(true),
                new Bytes9(Numeric.hexStringToByteArray("0x010203040506070809"))
        ));
        Map<String, Object> mixedDecoded = ABIInputDecoder.decodeOutput(edgeCaseAbiJson, "roundTripMixed(address,bool,string,bytes,bytes9,uint256,int256)", mixedOutput);
        Map<String, Object> outputs = castMap(mixedDecoded.get("output"));
        assertEquals(true, outputs.get("accepted"));
        assertEquals("0x010203040506070809", outputs.get("ticket"));
    }

    @Test
    @DisplayName("Rejects malformed payloads and unknown selectors")
    void testMalformedPayloadAndUnknownSelector() {
        IllegalArgumentException shortPayload = assertThrows(
                IllegalArgumentException.class,
                () -> ABIInputDecoder.decodeInput(simpleAbiJson, "0x1234")
        );
        assertTrue(shortPayload.getMessage().contains("4-byte selector"));

        IllegalArgumentException unknownSelector = assertThrows(
                IllegalArgumentException.class,
                () -> ABIInputDecoder.decodeInput(simpleAbiJson, "0xdeadbeef")
        );
        assertTrue(unknownSelector.getMessage().contains("No matching function for selector"));
    }

    @Test
    @DisplayName("Rejects missing arguments, unsupported fixed bytes, and missing functions")
    void testEncodingFailures() {
        IllegalArgumentException missingArgument = assertThrows(
                IllegalArgumentException.class,
                () -> ABIInputDecoder.encodeInput(edgeCaseAbiJson, "roundTripMixed(address,bool,string,bytes,bytes9,uint256,int256)", Map.of())
        );
        assertTrue(missingArgument.getMessage().contains("Argument target is missing"));

        Exception unsupportedType = assertThrows(
                Exception.class,
                () -> ABIInputDecoder.encodeInput(edgeCaseAbiJson, "badBytes(bytes33)", Map.of("value", "0x01"))
        );
        assertTrue(unsupportedType.getMessage().contains("Bytes33 not supported"));

        IllegalArgumentException functionNotFound = assertThrows(
                IllegalArgumentException.class,
                () -> ABIInputDecoder.decodeOutput(edgeCaseAbiJson, "missing()", "0x")
        );
        assertTrue(functionNotFound.getMessage().contains("not found in ABI"));
    }

    private static DynamicStruct tuple(Type... values) {
        return new DynamicStruct(values) {};
    }

    private static String readResource(String name) throws IOException {
        try (InputStream inputStream = ABIInputDecoderTest.class.getClassLoader().getResourceAsStream(name)) {
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
