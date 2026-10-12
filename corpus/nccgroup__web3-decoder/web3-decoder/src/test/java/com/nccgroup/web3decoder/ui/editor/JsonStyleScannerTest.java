package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JsonStyleScannerTest {

    private final JsonStyleScanner scanner = new JsonStyleScanner();

    /** Returns the kind of the span that starts exactly at the given offset, or null. */
    private static StyleKind kindAt(List<StyleSpan> spans, int start) {
        for (StyleSpan s : spans) {
            if (s.start == start) return s.kind;
        }
        return null;
    }

    /** Returns the span that starts exactly at the given offset, or null. */
    private static StyleSpan spanAt(List<StyleSpan> spans, int start) {
        for (StyleSpan s : spans) {
            if (s.start == start) return s;
        }
        return null;
    }

    @Test
    void argsKeysAndValuesAreBold() {
        String json = "{\"function\":\"f()\",\"args\":{\"amountIn\":123,"
                + "\"to\":\"0x1f98431c8ad98523631ae4a59f267346ea31f984\"}}";
        List<StyleSpan> spans = scanner.scan(json);
        assertTrue(spanAt(spans, json.indexOf("\"amountIn\"")).bold);          // arg key
        assertTrue(spanAt(spans, json.indexOf("123")).bold);                   // arg number value
        assertTrue(spanAt(spans, json.indexOf("\"0x1f")).bold);               // arg address value
        // members outside args (and the args key itself) are not bold
        assertFalse(spanAt(spans, json.indexOf("\"function\"")).bold);
        assertFalse(spanAt(spans, json.indexOf("\"args\"")).bold);
    }

    @Test
    void nestedArgsValuesAreBold() {
        String json = "{\"args\":{\"path\":[\"0xabc\",1]}}";
        List<StyleSpan> spans = scanner.scan(json);
        assertTrue(spanAt(spans, json.indexOf("\"path\"")).bold);
        assertTrue(spanAt(spans, json.indexOf("\"0xabc\"")).bold);            // nested array element
        assertTrue(spanAt(spans, json.indexOf("1")).bold);
    }

    @Test
    void functionValueIsFunctionKind() {
        String json = "{\"function\":\"swap(uint256,bool)\"}";
        List<StyleSpan> spans = scanner.scan(json);
        assertEquals(StyleKind.KEY, kindAt(spans, json.indexOf("\"function\"")));
        assertEquals(StyleKind.FUNCTION, kindAt(spans, json.indexOf("\"swap")));
    }

    @Test
    void fortyHexValueIsAddress() {
        String json = "{\"to\":\"0x1f98431c8ad98523631ae4a59f267346ea31f984\"}";
        assertEquals(StyleKind.ADDRESS, kindAt(scanner.scan(json), json.indexOf("\"0x1f")));
    }

    @Test
    void otherHexValueIsHex() {
        String json = "{\"data\":\"0x12345678\"}";
        assertEquals(StyleKind.HEX, kindAt(scanner.scan(json), json.indexOf("\"0x12")));
    }

    @Test
    void errorStatusAndReasonAreErrorKind() {
        String json = "{\"status\":\"error\",\"reason\":\"ABI not found\"}";
        List<StyleSpan> spans = scanner.scan(json);
        assertEquals(StyleKind.ERROR, kindAt(spans, json.indexOf("\"error\"")));
        assertEquals(StyleKind.ERROR, kindAt(spans, json.indexOf("\"ABI")));
    }

    @Test
    void skippedStatusIsSkipped() {
        String json = "{\"status\":\"skipped\"}";
        assertEquals(StyleKind.STATUS_SKIPPED,
                kindAt(scanner.scan(json), json.indexOf("\"skipped\"")));
    }

    @Test
    void decodedStatusIsStatusOk() {
        String json = "{\"status\":\"decoded\"}";
        assertEquals(StyleKind.STATUS_OK,
                kindAt(scanner.scan(json), json.indexOf("\"decoded\"")));
    }

    @Test
    void decodeSourceCacheIsSourceCache() {
        String json = "{\"decodeSource\":\"cache\"}";
        assertEquals(StyleKind.SOURCE_CACHE,
                kindAt(scanner.scan(json), json.indexOf("\"cache\"")));
    }

    @Test
    void decodeSourceEtherscanIsSourceEtherscan() {
        String json = "{\"decodeSource\":\"etherscan\"}";
        assertEquals(StyleKind.SOURCE_ETHERSCAN,
                kindAt(scanner.scan(json), json.indexOf("\"etherscan\"")));
    }

    @Test
    void decodeSourceFourbyteIsSourceFourbyte() {
        String json = "{\"decodeSource\":\"4byte\"}";
        assertEquals(StyleKind.SOURCE_FOURBYTE,
                kindAt(scanner.scan(json), json.indexOf("\"4byte\"")));
    }

    @Test
    void decodeSourceBuiltinIsSourceBuiltin() {
        String json = "{\"decodeSource\":\"builtin\"}";
        assertEquals(StyleKind.SOURCE_BUILTIN,
                kindAt(scanner.scan(json), json.indexOf("\"builtin\"")));
    }

    @Test
    void decodeSourceUnknownFallsBackToString() {
        String json = "{\"decodeSource\":\"manual\"}";
        assertEquals(StyleKind.STRING,
                kindAt(scanner.scan(json), json.indexOf("\"manual\"")));
    }

    @Test
    void decodeSourceInsideArgsIsBoldAndKind() {
        String json = "{\"args\":{\"decodeSource\":\"cache\"}}";
        StyleSpan span = spanAt(scanner.scan(json), json.indexOf("\"cache\""));
        assertEquals(StyleKind.SOURCE_CACHE, span.kind);
        assertTrue(span.bold);
    }

    @Test
    void scalarsAndPunctuation() {
        String json = "{\"a\":1,\"b\":true,\"c\":null}";
        List<StyleSpan> spans = scanner.scan(json);
        assertEquals(StyleKind.PUNCTUATION, kindAt(spans, 0)); // '{'
        assertEquals(StyleKind.NUMBER, kindAt(spans, json.indexOf("1")));
        assertEquals(StyleKind.BOOL_NULL, kindAt(spans, json.indexOf("true")));
        assertEquals(StyleKind.BOOL_NULL, kindAt(spans, json.indexOf("null")));
        assertEquals(StyleKind.PUNCTUATION, kindAt(spans, json.indexOf(",")));
        assertEquals(StyleKind.PUNCTUATION, kindAt(spans, json.indexOf(":")));
    }

    @Test
    void arrayOfObjectsKeepsPerObjectContext() {
        String json = "[{\"function\":\"a()\"},{\"function\":\"b()\"}]";
        List<StyleSpan> spans = scanner.scan(json);
        assertEquals(StyleKind.FUNCTION, kindAt(spans, json.indexOf("\"a()\"")));
        assertEquals(StyleKind.FUNCTION, kindAt(spans, json.indexOf("\"b()\"")));
    }

    @Test
    void addressInsideArrayElementIsStillAddress() {
        String json = "{\"targets\":[\"0x1f98431c8ad98523631ae4a59f267346ea31f984\"]}";
        assertEquals(StyleKind.ADDRESS, kindAt(scanner.scan(json), json.indexOf("\"0x1f")));
    }

    @Test
    void unterminatedStringDoesNotThrow() {
        String json = "{\"a\":\"oops";
        List<StyleSpan> spans = scanner.scan(json); // must not throw
        assertFalse(spans.isEmpty());
    }

    @Test
    void nonJsonHexIsSinglePlainSpan() {
        String hex = "0xdeadbeef";
        List<StyleSpan> spans = scanner.scan(hex);
        assertEquals(1, spans.size());
        assertEquals(StyleKind.PLAIN, spans.get(0).kind);
        assertEquals(0, spans.get(0).start);
        assertEquals(hex.length(), spans.get(0).end);
    }

    @Test
    void plainMessageIsSinglePlainSpan() {
        List<StyleSpan> spans = scanner.scan("No result to decode.");
        assertEquals(1, spans.size());
        assertEquals(StyleKind.PLAIN, spans.get(0).kind);
    }

    @Test
    void emptyInputProducesNoSpans() {
        assertTrue(scanner.scan("").isEmpty());
    }
}
