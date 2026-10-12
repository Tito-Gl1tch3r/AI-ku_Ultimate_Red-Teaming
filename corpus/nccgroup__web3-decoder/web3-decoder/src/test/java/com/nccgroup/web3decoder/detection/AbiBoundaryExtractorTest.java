package com.nccgroup.web3decoder.detection;

import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AbiBoundaryExtractorTest {

    @Test
    void extractsSimpleJsObjectArray() {
        String body = "const W=[{type:\"function\",stateMutability:\"view\"}]; tail";
        int hit = body.indexOf("stateMutability");
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, hit);
        assertTrue(extracted.isPresent());
        assertEquals("[{type:\"function\",stateMutability:\"view\"}]", extracted.get());
    }

    @Test
    void extractsNestedBracketsCorrectly() {
        String body = "x=[{a:[1,2,3],stateMutability:\"view\"}];";
        int hit = body.indexOf("stateMutability");
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, hit);
        assertTrue(extracted.isPresent());
        assertEquals("[{a:[1,2,3],stateMutability:\"view\"}]", extracted.get());
    }

    @Test
    void ignoresBracketsInStrings() {
        // The "]" inside the string must NOT close the array.
        String body = "x=[{name:\"weird]name\",stateMutability:\"view\"}];";
        int hit = body.indexOf("stateMutability");
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, hit);
        assertTrue(extracted.isPresent());
        assertEquals("[{name:\"weird]name\",stateMutability:\"view\"}]", extracted.get());
    }

    @Test
    void handlesEscapedQuotesInsideStrings() {
        String body = "x=[{name:\"a\\\"b\",stateMutability:\"view\"}];";
        int hit = body.indexOf("stateMutability");
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, hit);
        assertTrue(extracted.isPresent());
    }

    @Test
    void returnsEmptyWhenNoOpeningBracket() {
        String body = "just stateMutability:\"view\" floating with no brackets";
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, body.indexOf("stateMutability"));
        assertEquals(Optional.empty(), extracted);
    }

    @Test
    void returnsEmptyWhenUnbalanced() {
        String body = "x=[{stateMutability:\"view\"}"; // missing closing ]
        Optional<String> extracted = AbiBoundaryExtractor.extract(body, body.indexOf("stateMutability"));
        assertEquals(Optional.empty(), extracted);
    }
}
