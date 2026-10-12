package com.nccgroup.web3decoder.detection;

import com.fasterxml.jackson.core.json.JsonReadFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.util.List;
import java.util.Optional;

/**
 * Parses a candidate ABI source (either strict JSON or a JS-object-literal slice as
 * found in minified dapp bundles) into a strict-JSON canonical form. Canonical form
 * has sorted keys and no extra whitespace, so byte-equal canonical strings represent
 * logically-equal ABIs.
 */
public final class AbiNormalizer {

    private static final ObjectMapper LENIENT = JsonMapper.builder()
            .enable(JsonReadFeature.ALLOW_UNQUOTED_FIELD_NAMES)
            .enable(JsonReadFeature.ALLOW_SINGLE_QUOTES)
            .enable(JsonReadFeature.ALLOW_TRAILING_COMMA)
            .enable(JsonReadFeature.ALLOW_UNESCAPED_CONTROL_CHARS)
            .build();

    private static final ObjectMapper CANONICAL = JsonMapper.builder()
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
            .build();

    private AbiNormalizer() {}

    public static Optional<String> toCanonicalJson(String candidate) {
        if (candidate == null || candidate.isBlank()) return Optional.empty();
        try {
            // Minified bundles often write booleans as !0 / !1 (the standard JS
            // tersification of true/false). Jackson can't parse those even leniently,
            // so we replace them with the JSON keywords first, string-aware so we
            // don't mangle a literal "!0" inside a string value.
            String preprocessed = replaceMinifiedBooleans(candidate);
            // Read as Object (yields List/Map graph) rather than JsonNode so that
            // CANONICAL's ORDER_MAP_ENTRIES_BY_KEYS actually sorts map keys at
            // serialisation time — JsonNode/ObjectNode preserves insertion order
            // and is unaffected by that feature.
            Object tree = LENIENT.readValue(preprocessed, Object.class);
            if (!(tree instanceof List)) return Optional.empty();
            return Optional.of(CANONICAL.writeValueAsString(tree));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    /** Replace {@code !0} → {@code true} and {@code !1} → {@code false} outside string
     *  literals. JS minifiers (Terser, esbuild, …) emit these for {@code true}/{@code false}
     *  in object literals because they're two chars shorter. */
    static String replaceMinifiedBooleans(String src) {
        StringBuilder sb = new StringBuilder(src.length());
        boolean inString = false;
        char quote = 0;
        int i = 0;
        int n = src.length();
        while (i < n) {
            char c = src.charAt(i);
            if (inString) {
                sb.append(c);
                if (c == '\\' && i + 1 < n) {
                    sb.append(src.charAt(i + 1));
                    i += 2;
                    continue;
                }
                if (c == quote) inString = false;
                i++;
                continue;
            }
            if (c == '"' || c == '\'') {
                inString = true;
                quote = c;
                sb.append(c);
                i++;
                continue;
            }
            if (c == '!' && i + 1 < n) {
                char next = src.charAt(i + 1);
                if (next == '0') { sb.append("true"); i += 2; continue; }
                if (next == '1') { sb.append("false"); i += 2; continue; }
            }
            sb.append(c);
            i++;
        }
        return sb.toString();
    }
}
