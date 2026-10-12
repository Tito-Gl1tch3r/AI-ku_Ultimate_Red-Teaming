package com.nccgroup.web3_decoder.abi;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.logging.Logging;
import com.nccgroup.web3decoder.abi.FourByteSignatureProvider;
import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.web3j.abi.FunctionEncoder;
import org.web3j.abi.datatypes.Address;
import org.web3j.abi.datatypes.Function;
import org.web3j.abi.datatypes.generated.Uint256;

import java.math.BigInteger;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class FourByteSignatureProviderTest {

    @Test
    @DisplayName("Builds synthetic ABI that can decode simple selector signatures")
    void testBuildSyntheticAbiSimpleSignature() throws Exception {
        FourByteSignatureProvider provider = newProvider();
        String syntheticAbi = provider.buildSyntheticAbiFromSignature("transfer(address,uint256)");

        String calldata = FunctionEncoder.encode(new Function(
                "transfer",
                List.of(new Address("0x1111111111111111111111111111111111111111"), new Uint256(BigInteger.TEN)),
                List.of()
        ));

        Map<String, Object> decoded = ABIInputDecoder.decodeInput(syntheticAbi, calldata);
        assertEquals("transfer(address,uint256)", decoded.get("function"));
    }

    @Test
    @DisplayName("Builds synthetic ABI with tuple and array parameter types")
    void testBuildSyntheticAbiTupleArraySignature() throws Exception {
        FourByteSignatureProvider provider = newProvider();
        String syntheticAbi = provider.buildSyntheticAbiFromSignature("aggregate((address,bytes)[])");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> abi = new com.fasterxml.jackson.databind.ObjectMapper().readValue(
                syntheticAbi,
                List.class
        );
        Map<String, Object> function = abi.get(0);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> inputs = (List<Map<String, Object>>) function.get("inputs");
        assertEquals("tuple[]", inputs.get(0).get("type"));
    }

    private static FourByteSignatureProvider newProvider() {
        MontoyaApi api = mock(MontoyaApi.class);
        when(api.logging()).thenReturn(mock(Logging.class));
        return new FourByteSignatureProvider(api);
    }
}
