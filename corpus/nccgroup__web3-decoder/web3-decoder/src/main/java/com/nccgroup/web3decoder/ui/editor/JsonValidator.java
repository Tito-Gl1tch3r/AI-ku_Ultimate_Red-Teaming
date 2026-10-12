package com.nccgroup.web3decoder.ui.editor;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Optional;

/**
 * Authoritative JSON-validity check for the live error indicator. Only JSON
 * (objects/arrays) is validated; hex calldata and plain status messages are skipped,
 * mirroring {@link JsonStyleScanner}'s {@code { / [} gate.
 */
public final class JsonValidator {

    /** A parse error with a best-effort document offset (-1 if unavailable). */
    public static final class ParseError {
        public final int offset;
        public final String message;

        public ParseError(int offset, String message) {
            this.offset = offset;
            this.message = message;
        }
    }

    private final ObjectMapper mapper = new ObjectMapper();

    public Optional<ParseError> validate(String text) {
        if (text == null) return Optional.empty();
        String trimmed = text.trim();
        if (trimmed.isEmpty()) return Optional.empty();
        char c = trimmed.charAt(0);
        if (c != '{' && c != '[') return Optional.empty();

        try {
            mapper.readTree(text);
            return Optional.empty();
        } catch (JsonProcessingException e) {
            int offset = -1;
            if (e.getLocation() != null) {
                long off = e.getLocation().getCharOffset();
                if (off >= 0) offset = (int) off;
            }
            String msg = e.getOriginalMessage() != null ? e.getOriginalMessage() : e.getMessage();
            return Optional.of(new ParseError(offset, msg != null ? msg : "Invalid JSON"));
        }
    }
}
