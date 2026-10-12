package com.nccgroup.web3_decoder.annotation;

import com.nccgroup.web3decoder.annotation.AnnotationNoteBuilder;
import com.nccgroup.web3decoder.annotation.AnnotationNoteBuilder.Result;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AnnotationNoteBuilderTest {

    private static Map<String, Object> row(Object... kv) {
        java.util.LinkedHashMap<String, Object> m = new java.util.LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    @Test
    void simpleCallShowsFunctionName() {
        Result r = AnnotationNoteBuilder.build(List.of(
                row("method", "eth_call", "status", "decoded", "function", "transfer(address,uint256)")));
        assertEquals("web3: transfer", r.notes());
        assertFalse(r.isRawTransaction());
    }

    @Test
    void multicallShowsInnerCallsNotWrapper() {
        Map<String, Object> mc = row(
                "method", "eth_call", "status", "decoded", "function", "aggregate3((address,bool,bytes)[])",
                "nestedCalls", List.of(
                        row("function", "transfer(address,uint256)"),
                        row("function", "approve(address,uint256)")));
        Result r = AnnotationNoteBuilder.build(List.of(mc));
        assertEquals("web3 mc: transfer, approve", r.notes());
    }

    @Test
    void nestedMulticallFlattensToLeaves() {
        Map<String, Object> inner = row("function", "aggregate((address,bytes)[])",
                "nestedCalls", List.of(row("function", "swap(uint256)")));
        Map<String, Object> mc = row("method", "eth_call", "function", "aggregate3((address,bool,bytes)[])",
                "nestedCalls", List.of(row("function", "transfer(address,uint256)"), inner));
        Result r = AnnotationNoteBuilder.build(List.of(mc));
        assertEquals("web3 mc: transfer, swap", r.notes());
    }

    @Test
    void truncatesLongLists() {
        Map<String, Object> mc = row("method", "eth_call", "function", "aggregate((address,bytes)[])",
                "nestedCalls", List.of(
                        row("function", "a()"), row("function", "b()"), row("function", "c()"),
                        row("function", "d()"), row("function", "e()"), row("function", "f()")));
        Result r = AnnotationNoteBuilder.build(List.of(mc));
        assertEquals("web3 mc: a, b, c, d (+2 more)", r.notes());
    }

    @Test
    void rawTransactionSetsFlag() {
        Result r = AnnotationNoteBuilder.build(List.of(
                row("method", "eth_sendRawTransaction", "status", "decoded", "function", "transfer(address,uint256)")));
        assertEquals("web3: transfer", r.notes());
        assertTrue(r.isRawTransaction());
    }

    @Test
    void undecodedNestedCallUsesSelectorFromRawCallData() {
        Map<String, Object> mc = row("method", "eth_call", "function", "aggregate((address,bytes)[])",
                "nestedCalls", List.of(row("status", "error", "rawCallData", "0xa9059cbb0000")));
        Result r = AnnotationNoteBuilder.build(List.of(mc));
        assertEquals("web3 mc: 0xa9059cbb", r.notes());
    }

    @Test
    void allUnresolvedYieldsGenericNote() {
        Result r = AnnotationNoteBuilder.build(List.of(
                row("method", "eth_call", "status", "error", "reason", "no abi")));
        assertEquals("web3: (unresolved)", r.notes());
    }
}
