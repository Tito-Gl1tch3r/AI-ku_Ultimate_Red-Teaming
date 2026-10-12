package com.nccgroup.web3decoder.detection;

import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.assertEquals;

class AbiSelectorBuilderTest {

    @Test
    void buildsBalanceOfSelector() {
        Map<String, Object> fn = Map.of(
                "name", "balanceOf",
                "inputs", List.of(Map.of("name", "owner", "type", "address"))
        );
        // balanceOf(address) -> 0x70a08231
        assertEquals("0x70a08231", AbiSelectorBuilder.selectorFor(fn));
    }

    @Test
    void buildsTransferSelector() {
        Map<String, Object> fn = Map.of(
                "name", "transfer",
                "inputs", List.of(
                        Map.of("name", "to", "type", "address"),
                        Map.of("name", "value", "type", "uint256")
                )
        );
        // transfer(address,uint256) -> 0xa9059cbb
        assertEquals("0xa9059cbb", AbiSelectorBuilder.selectorFor(fn));
    }

    @Test
    void buildsCanonicalSignatureForTuple() {
        Map<String, Object> fn = Map.of(
                "name", "multicall",
                "inputs", List.of(Map.of(
                        "name", "calls",
                        "type", "tuple[]",
                        "components", List.of(
                                Map.of("name", "target", "type", "address"),
                                Map.of("name", "callData", "type", "bytes")
                        )
                ))
        );
        // multicall((address,bytes)[]) -> 0xcaa5c23f (keccak-verified)
        assertEquals("0xcaa5c23f", AbiSelectorBuilder.selectorFor(fn));
    }
}
