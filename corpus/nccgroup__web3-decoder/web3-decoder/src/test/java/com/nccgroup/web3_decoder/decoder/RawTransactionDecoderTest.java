package com.nccgroup.web3_decoder.decoder;

import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import com.nccgroup.web3decoder.decoder.RawTransactionDecoder;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RawTransactionDecoderTest {

    // Real samples from the feature request: Uniswap V2 swapExactETHForTokens,
    // signer 0x2105…2e6, chainId 1337, nonce 0, value 1 ETH, gasLimit 300000.
    private static final String EIP1559_TX =
            "0x02f9015b820539808459682f00850df8475800830493e0947a250d5630b4cf539739df2c5dacb4c659f2488d880de0b6b3a7640000b8e47ff36ab500000000000000000000000000000000000000000000009e0950598867d8000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000002105eaa660ff62b14a5e093fc348e13ab63af2e600000000000000000000000000000000000000000000000000000000623b16570000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000006b175474e89094c44da98b954eedeac495271d0fc001a005cfdf9ff11dea2d3e8781cb6ba140ae6e86a0922bfa75938b6f2456f513e24ca057f02b3f7125edb59e22651d503bc296153860e3843f9d495ad21d898c8e20c3";

    private static final String LEGACY_TX =
            "0xf9015480850ba43b7400830493e0947a250d5630b4cf539739df2c5dacb4c659f2488d880de0b6b3a7640000b8e47ff36ab500000000000000000000000000000000000000000000009e0950598867d8000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000002105eaa660ff62b14a5e093fc348e13ab63af2e600000000000000000000000000000000000000000000000000000000623b0bc30000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000006b175474e89094c44da98b954eedeac495271d0f820a95a00cdf02a5c6f37fe05ea5678dd6708e8d34a1c2801c1965a1083e8df6d081863aa008a9ed313db94339015c366786b30cc304d74d6a0b1d74cd77673ec43200f72f";

    private static final String UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d";
    private static final String SIGNER = "0x2105eaa660ff62b14a5e093fc348e13ab63af2e6";

    private static final String SWAP_ABI = "[{\"name\":\"swapExactETHForTokens\",\"type\":\"function\","
            + "\"inputs\":[{\"name\":\"amountOutMin\",\"type\":\"uint256\"},"
            + "{\"name\":\"path\",\"type\":\"address[]\"},"
            + "{\"name\":\"to\",\"type\":\"address\"},"
            + "{\"name\":\"deadline\",\"type\":\"uint256\"}],"
            + "\"outputs\":[{\"name\":\"amounts\",\"type\":\"uint256[]\"}]}]";

    @Test
    @DisplayName("Decodes an EIP-1559 raw transaction envelope")
    void decodesEip1559Envelope() {
        Map<String, Object> env = RawTransactionDecoder.decode(EIP1559_TX);
        assertEquals("eip1559", env.get("txType"));
        assertEquals(1337L, env.get("chainId"));
        assertEquals(SIGNER, env.get("from"));
        assertEquals(UNISWAP_V2_ROUTER, env.get("to"));
        assertEquals("0", env.get("nonce"));
        assertEquals("1000000000000000000", env.get("value"));
        assertEquals("60000000000", env.get("maxFeePerGas"));
        assertEquals("1500000000", env.get("maxPriorityFeePerGas"));
        assertEquals("300000", env.get("gasLimit"));
        assertNull(env.get("gasPrice"));
        assertTrue(((String) env.get("data")).startsWith("0x7ff36ab5"));
    }

    @Test
    @DisplayName("Decodes a legacy (EIP-155) raw transaction envelope")
    void decodesLegacyEnvelope() {
        Map<String, Object> env = RawTransactionDecoder.decode(LEGACY_TX);
        assertEquals("legacy", env.get("txType"));
        assertEquals(1337L, env.get("chainId"));
        assertEquals(SIGNER, env.get("from"));
        assertEquals(UNISWAP_V2_ROUTER, env.get("to"));
        assertEquals("0", env.get("nonce"));
        assertEquals("1000000000000000000", env.get("value"));
        assertEquals("50000000000", env.get("gasPrice"));
        assertEquals("300000", env.get("gasLimit"));
        assertNull(env.get("maxFeePerGas"));
        assertTrue(((String) env.get("data")).startsWith("0x7ff36ab5"));
    }

    @Test
    @DisplayName("Extracted calldata decodes through the existing ABI pipeline")
    void innerCalldataDecodes() throws Exception {
        Map<String, Object> env = RawTransactionDecoder.decode(EIP1559_TX);
        String data = (String) env.get("data");
        Map<String, Object> decoded = ABIInputDecoder.decodeInput(SWAP_ABI, data);
        assertEquals("swapExactETHForTokens(uint256,address[],address,uint256)", decoded.get("function"));
    }

    @Test
    @DisplayName("Rejects empty raw transaction hex")
    void rejectsEmpty() {
        assertThrows(IllegalArgumentException.class, () -> RawTransactionDecoder.decode("0x"));
    }
}
