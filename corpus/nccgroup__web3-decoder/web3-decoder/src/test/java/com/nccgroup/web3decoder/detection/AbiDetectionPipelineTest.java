package com.nccgroup.web3decoder.detection;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AbiDetectionPipelineTest {

    @Test
    void emptyBodyYieldsEmptyList() {
        assertEquals(List.of(), AbiDetectionPipeline.detect(""));
    }

    @Test
    void irrelevantBodyYieldsEmptyList() {
        String body = "var x=1; function foo(){} const y='hello';";
        assertEquals(List.of(), AbiDetectionPipeline.detect(body));
    }

    @Test
    void detectsOneAbiInJsObjectLiteral() {
        String body = "junk const W=[{type:\"function\",name:\"foo\"," +
                "inputs:[],outputs:[],stateMutability:\"view\"}]; more junk";
        List<DetectedAbi> result = AbiDetectionPipeline.detect(body);
        assertEquals(1, result.size());
    }

    @Test
    void detectsMultipleDistinctAbis() {
        String body =
                "const A=[{type:\"function\",name:\"foo\",inputs:[],outputs:[],stateMutability:\"view\"}];" +
                "const B=[{type:\"function\",name:\"bar\",inputs:[],outputs:[],stateMutability:\"view\"}];";
        List<DetectedAbi> result = AbiDetectionPipeline.detect(body);
        assertEquals(2, result.size());
    }

    @Test
    void dedupesIdenticalAbisInSameResponse() {
        String fragment = "[{type:\"function\",name:\"foo\",inputs:[],outputs:[],stateMutability:\"view\"}]";
        String body = "const A=" + fragment + "; const B=" + fragment + ";";
        List<DetectedAbi> result = AbiDetectionPipeline.detect(body);
        assertEquals(1, result.size());
    }

    @Test
    void detectsHiveAuthSvelteFixture() throws IOException {
        String body;
        try (InputStream in = AbiDetectionPipelineTest.class
                .getResourceAsStream("/abi-detection/hive-auth-svelte-excerpt.js")) {
            assertNotNull(in, "fixture resource missing from classpath");
            body = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
        List<DetectedAbi> result = AbiDetectionPipeline.detect(body);
        assertTrue(result.size() >= 1,
                "expected at least one ABI detected in Hive excerpt");
        assertTrue(result.get(0).selectors().size() > 0,
                "expected at least one function selector");
    }
}
