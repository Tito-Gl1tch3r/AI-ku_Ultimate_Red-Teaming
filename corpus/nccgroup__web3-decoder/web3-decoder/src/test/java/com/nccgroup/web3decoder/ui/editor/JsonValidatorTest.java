package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JsonValidatorTest {

    private final JsonValidator validator = new JsonValidator();

    @Test
    void validObjectIsOk() {
        assertTrue(validator.validate("{\"a\":1}").isEmpty());
    }

    @Test
    void validArrayIsOk() {
        assertTrue(validator.validate("[1,2,3]").isEmpty());
    }

    @Test
    void invalidJsonReportsError() {
        Optional<JsonValidator.ParseError> err = validator.validate("{\"a\":}");
        assertTrue(err.isPresent());
        assertFalse(err.get().message.isBlank());
        assertTrue(err.get().offset <= "{\"a\":}".length());
    }

    @Test
    void truncatedJsonReportsError() {
        assertTrue(validator.validate("{\"a\":1").isPresent());
    }

    @Test
    void nonJsonHexIsNotValidated() {
        assertTrue(validator.validate("0xdeadbeef").isEmpty());
    }

    @Test
    void plainMessageIsNotValidated() {
        assertTrue(validator.validate("No result to decode.").isEmpty());
    }
}
