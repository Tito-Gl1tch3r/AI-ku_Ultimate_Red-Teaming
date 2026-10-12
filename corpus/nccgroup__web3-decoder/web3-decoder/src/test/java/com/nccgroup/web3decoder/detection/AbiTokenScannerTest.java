package com.nccgroup.web3decoder.detection;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AbiTokenScannerTest {

    @Test
    void findsUnquotedKeyHit() {
        String body = "var x=42; const W=[{type:\"function\",stateMutability:\"view\"}]; var y=1;";
        List<Integer> hits = AbiTokenScanner.findCandidateOffsets(body);
        assertEquals(1, hits.size());
        // hit points at the start of "stateMutability"
        assertTrue(body.startsWith("stateMutability:\"", hits.get(0)));
    }

    @Test
    void findsQuotedKeyHit() {
        String body = "{\"abi\":[{\"type\":\"function\",\"stateMutability\":\"view\"}]}";
        List<Integer> hits = AbiTokenScanner.findCandidateOffsets(body);
        assertEquals(1, hits.size());
        assertTrue(body.startsWith("\"stateMutability\":\"", hits.get(0)));
    }

    @Test
    void findsInternalTypeHit() {
        String body = "[{name:\"x\",type:\"uint256\",internalType:\"uint256\"}]";
        List<Integer> hits = AbiTokenScanner.findCandidateOffsets(body);
        assertEquals(1, hits.size());
    }

    @Test
    void multipleHitsReturnedInOrder() {
        String body = "stateMutability:\"a\" ... internalType:\"b\" ... stateMutability:\"c\"";
        List<Integer> hits = AbiTokenScanner.findCandidateOffsets(body);
        assertEquals(3, hits.size());
        assertTrue(hits.get(0) < hits.get(1));
        assertTrue(hits.get(1) < hits.get(2));
    }

    @Test
    void emptyBodyReturnsNothing() {
        assertEquals(List.of(), AbiTokenScanner.findCandidateOffsets(""));
    }

    @Test
    void noNeedleReturnsNothing() {
        assertEquals(List.of(), AbiTokenScanner.findCandidateOffsets("just regular code, no abi here"));
    }
}
