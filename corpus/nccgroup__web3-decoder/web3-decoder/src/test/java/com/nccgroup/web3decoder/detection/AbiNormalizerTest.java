package com.nccgroup.web3decoder.detection;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AbiNormalizerTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void normalisesJsObjectLiteralToJson() throws Exception {
        String input = "[{type:\"function\",name:\"foo\",inputs:[],outputs:[],stateMutability:\"view\"}]";
        Optional<String> normalised = AbiNormalizer.toCanonicalJson(input);
        assertTrue(normalised.isPresent());
        // strict-JSON-parseable
        JsonNode tree = mapper.readTree(normalised.get());
        assertEquals("function", tree.get(0).get("type").asText());
        assertEquals("foo", tree.get(0).get("name").asText());
    }

    @Test
    void normalisesPlainJsonUntouched() throws Exception {
        String input = "[{\"type\":\"function\",\"name\":\"bar\",\"inputs\":[],\"outputs\":[],\"stateMutability\":\"pure\"}]";
        Optional<String> normalised = AbiNormalizer.toCanonicalJson(input);
        assertTrue(normalised.isPresent());
        JsonNode tree = mapper.readTree(normalised.get());
        assertEquals("bar", tree.get(0).get("name").asText());
    }

    @Test
    void canonicalFormSortsKeysSoSameContentSameOutput() {
        String a = "[{type:\"function\",name:\"foo\",stateMutability:\"view\",inputs:[],outputs:[]}]";
        String b = "[{name:\"foo\",type:\"function\",inputs:[],outputs:[],stateMutability:\"view\"}]";
        Optional<String> normA = AbiNormalizer.toCanonicalJson(a);
        Optional<String> normB = AbiNormalizer.toCanonicalJson(b);
        assertTrue(normA.isPresent());
        assertTrue(normB.isPresent());
        assertEquals(normA.get(), normB.get());
    }

    @Test
    void rejectsNonsense() {
        assertEquals(Optional.empty(), AbiNormalizer.toCanonicalJson("this is not json or js"));
    }

    @Test
    void rejectsNonArray() {
        // Single object — ABIs must be arrays
        assertEquals(Optional.empty(), AbiNormalizer.toCanonicalJson("{type:\"function\",name:\"foo\"}"));
    }
}
