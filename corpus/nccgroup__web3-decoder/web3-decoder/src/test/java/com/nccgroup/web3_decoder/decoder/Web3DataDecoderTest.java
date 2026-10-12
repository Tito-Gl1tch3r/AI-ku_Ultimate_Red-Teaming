package com.nccgroup.web3_decoder.decoder;

import burp.api.montoya.logging.Logging;
import com.nccgroup.web3decoder.abi.AbiProvider;
import com.nccgroup.web3decoder.abi.FourByteSignatureProvider;
import com.nccgroup.web3decoder.decoder.Web3DataDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbi;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.proxies.ProxyDetector;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Address;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.generated.Uint256;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class Web3DataDecoderTest {

    private static final String CONTRACT = "0x1111111111111111111111111111111111111111";
    private static final String IMPLEMENTATION = "0x2222222222222222222222222222222222222222";
    private static final String OWNER = "0x6e2cb485076ebc5f5fdf7be66ad750bee385cf7a";

    private static String tokenAbiJson;

    @BeforeAll
    static void setup() throws Exception {
        tokenAbiJson = readResource("abi_0x3f382dbd960e3a9bbceae22651e88158d2791550.json");
    }

    @Test
    @DisplayName("Uses the direct contract ABI when no proxy implementation is found")
    void testDecodeInputWithoutProxy() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        Logging logging = mock(Logging.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(tokenAbiJson);
        when(abiProvider.getLastAbiSource()).thenReturn("cache");

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, logging);
        Map<String, Object> decoded = decoder.decodeInput(CONTRACT, balanceOfInput());

        assertEquals("balanceOf(address)", decoded.get("function"));
        assertEquals("cache", decoded.get("decodeSource"));
        assertEquals(tokenAbiJson, decoder.getLastAbi());
        verify(abiProvider).getAbi(CONTRACT);
    }

    @Test
    @DisplayName("Uses the implementation ABI when the target contract is a proxy")
    void testDecodeInputWithProxy() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        Logging logging = mock(Logging.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(IMPLEMENTATION);
        when(abiProvider.getAbi(IMPLEMENTATION)).thenReturn(tokenAbiJson);
        when(abiProvider.getLastAbiSource()).thenReturn("etherscan");

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, logging);
        Map<String, Object> decoded = decoder.decodeInput(CONTRACT, balanceOfInput());

        assertEquals("balanceOf(address)", decoded.get("function"));
        assertEquals(true, decoded.get("isProxy"));
        assertEquals(CONTRACT, decoded.get("proxyTarget"));
        assertEquals(IMPLEMENTATION, decoded.get("implementationAddress"));
        assertEquals(IMPLEMENTATION, decoded.get("decodedUsing"));
        assertEquals("etherscan", decoded.get("decodeSource"));
        assertEquals(tokenAbiJson, decoder.getLastAbi());
        verify(abiProvider).getAbi(IMPLEMENTATION);
    }

    @Test
    @DisplayName("Falls back to 4byte selector lookup when ABI is not available")
    void testDecodeInputFallsBackTo4Byte() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        Logging logging = mock(Logging.class);
        FourByteSignatureProvider fourByte = mock(FourByteSignatureProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);
        when(fourByte.lookupFunctionSignatures("0x70a08231")).thenReturn(List.of("balanceOf(address)"));
        when(fourByte.buildSyntheticAbiFromSignature("balanceOf(address)")).thenReturn(tokenAbiJson);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, logging, fourByte);
        Map<String, Object> decoded = decoder.decodeInput(CONTRACT, balanceOfInput());

        assertEquals("balanceOf(address)", decoded.get("function"));
        assertEquals("4byte", decoded.get("decodeSource"));
        assertEquals(tokenAbiJson, decoder.getLastAbi());
    }

    @Test
    @DisplayName("Uses detected ABI pool before 4byte when provider returns null")
    void usesDetectedAbiPoolWhenProviderReturnsNull() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        Logging logging = mock(Logging.class);
        FourByteSignatureProvider fourByte = mock(FourByteSignatureProvider.class);

        when(proxyDetector.getImplementationAddress(anyString())).thenReturn(null);
        when(abiProvider.getAbi(anyString())).thenReturn(null);
        when(abiProvider.getLastLookupMessage()).thenReturn("");

        String balanceOfAbi = "[{\"inputs\":[{\"name\":\"owner\",\"type\":\"address\"}],"
                + "\"name\":\"balanceOf\",\"outputs\":[{\"name\":\"\",\"type\":\"uint256\"}],"
                + "\"stateMutability\":\"view\",\"type\":\"function\"}]";
        DetectedAbiStore store = mock(DetectedAbiStore.class);
        DetectedAbi detected = new DetectedAbi(
                "fp-test", balanceOfAbi, java.util.List.of("0x70a08231"));
        when(store.findBySelector("0x70a08231")).thenReturn(java.util.List.of(detected));

        Web3DataDecoder decoder = new Web3DataDecoder(
                proxyDetector, abiProvider, logging, fourByte, store);

        String calldata = "0x70a08231"
                + "000000000000000000000000abcdefabcdefabcdefabcdefabcdefabcdefabcd";
        Map<String, Object> result = decoder.decodeInput("0xcontract", calldata);

        assertEquals("detected", result.get("decodeSource"));
        assertEquals("balanceOf(address)", result.get("function"));
        verify(fourByte, never()).lookupFunctionSignatures(anyString());
    }

    @Test
    @DisplayName("Fails when the implementation ABI cannot be retrieved")
    void testDecodeInputFailsWhenImplementationAbiMissing() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(IMPLEMENTATION);
        when(abiProvider.getAbi(IMPLEMENTATION)).thenReturn(null);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class));

        Exception exception = assertThrows(Exception.class, () -> decoder.decodeInput(CONTRACT, balanceOfInput()));
        assertTrue(exception.getMessage().contains("implementation contract"));
    }

    @Test
    @DisplayName("Fails when the direct contract ABI cannot be retrieved")
    void testDecodeInputFailsWhenDirectAbiMissing() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class));

        Exception exception = assertThrows(Exception.class, () -> decoder.decodeInput(CONTRACT, balanceOfInput()));
        assertTrue(exception.getMessage().contains("Failed to retrieve ABI for contract"));
    }

    @Test
    @DisplayName("Decodes output using the ABI captured by a prior input decode")
    void testDecodeOutputAfterDecodeInput() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(tokenAbiJson);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class));
        decoder.decodeInput(CONTRACT, balanceOfInput());

        String outputData = FunctionEncoder.encodeConstructor(List.of(new Uint256(BigInteger.valueOf(99))));
        Map<String, Object> decoded = decoder.decodeOutput("balanceOf(address)", outputData);

        assertEquals(BigInteger.valueOf(99), castMap(decoded.get("output")).get("balance"));
    }

    @Test
    @DisplayName("Rejects output decoding before any ABI is loaded")
    void testDecodeOutputWithoutAbi() {
        Web3DataDecoder decoder = new Web3DataDecoder(mock(ProxyDetector.class), mock(AbiProvider.class), mock(Logging.class));

        Exception exception = assertThrows(Exception.class, () -> decoder.decodeOutput("balanceOf(address)", "0x"));
        assertTrue(exception.getMessage().contains("No ABI JSON available"));
    }

    @Test
    @DisplayName("Surfaces the missing-key reason in output when falling back to 4byte")
    void testSurfacesLookupNoteOn4ByteFallback() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        Logging logging = mock(Logging.class);
        FourByteSignatureProvider fourByte = mock(FourByteSignatureProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);
        when(abiProvider.getLastLookupMessage()).thenReturn("Etherscan API key not set for chain 1 — add it under the \"Web3\" tab → Chains.");
        when(fourByte.lookupFunctionSignatures("0x70a08231")).thenReturn(List.of("balanceOf(address)"));
        when(fourByte.buildSyntheticAbiFromSignature("balanceOf(address)")).thenReturn(tokenAbiJson);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, logging, fourByte);
        Map<String, Object> decoded = decoder.decodeInput(CONTRACT, balanceOfInput());

        assertEquals("balanceOf(address)", decoded.get("function"));
        assertEquals("4byte", decoded.get("decodeSource"));
        assertTrue(((String) decoded.get("abiLookupNote")).contains("API key not set"));
    }

    @Test
    @DisplayName("Skips 4byte and fails when config flag disables 4byte lookup")
    void testFourByteGateBlocksLookupWhenDisabled() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        FourByteSignatureProvider fourByte = mock(FourByteSignatureProvider.class);
        ExtensionConfig config = mock(ExtensionConfig.class);
        when(config.isFourByteLookupEnabled()).thenReturn(false);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);
        when(abiProvider.getLastLookupMessage()).thenReturn("");

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class),
                fourByte, null, config);

        Exception exception = assertThrows(Exception.class,
                () -> decoder.decodeInput(CONTRACT, balanceOfInput()));
        assertTrue(exception.getMessage().contains("4byte selector lookup disabled"));
        verify(fourByte, never()).lookupFunctionSignatures(anyString());
    }

    @Test
    @DisplayName("Calls 4byte when config flag enables 4byte lookup")
    void testFourByteGateAllowsLookupWhenEnabled() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);
        FourByteSignatureProvider fourByte = mock(FourByteSignatureProvider.class);
        ExtensionConfig config = mock(ExtensionConfig.class);
        when(config.isFourByteLookupEnabled()).thenReturn(true);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);
        when(fourByte.lookupFunctionSignatures("0x70a08231")).thenReturn(List.of("balanceOf(address)"));
        when(fourByte.buildSyntheticAbiFromSignature("balanceOf(address)")).thenReturn(tokenAbiJson);

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class),
                fourByte, null, config);
        Map<String, Object> decoded = decoder.decodeInput(CONTRACT, balanceOfInput());

        assertEquals("4byte", decoded.get("decodeSource"));
        verify(fourByte).lookupFunctionSignatures("0x70a08231");
    }

    @Test
    @DisplayName("Total failure exception carries the specific lookup reason")
    void testFailureExceptionCarriesReason() throws Exception {
        ProxyDetector proxyDetector = mock(ProxyDetector.class);
        AbiProvider abiProvider = mock(AbiProvider.class);

        when(proxyDetector.getImplementationAddress(CONTRACT)).thenReturn(null);
        when(abiProvider.getAbi(CONTRACT)).thenReturn(null);
        when(abiProvider.getLastLookupMessage()).thenReturn("Rate limited by Etherscan for chain 1; try again shortly.");

        Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, mock(Logging.class));

        Exception exception = assertThrows(Exception.class, () -> decoder.decodeInput(CONTRACT, balanceOfInput()));
        assertTrue(exception.getMessage().contains("Rate limited"));
    }

    private static String balanceOfInput() {
        return FunctionEncoder.encode(new Function("balanceOf", List.of(new Address(OWNER)), List.of()));
    }

    private static String readResource(String name) throws IOException {
        try (InputStream inputStream = Web3DataDecoderTest.class.getClassLoader().getResourceAsStream(name)) {
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
