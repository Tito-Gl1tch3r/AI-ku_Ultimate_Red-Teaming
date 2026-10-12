package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JsonSearchEngineTest {

    private final JsonSearchEngine engine = new JsonSearchEngine();

    @Test
    void literalMatchesAllOccurrences() {
        List<Range> r = engine.find("aXaXa", "a", false, false);
        assertEquals(List.of(new Range(0, 1), new Range(2, 3), new Range(4, 5)), r);
    }

    @Test
    void caseInsensitiveByDefault() {
        List<Range> r = engine.find("Amount amount", "amount", false, false);
        assertEquals(List.of(new Range(0, 6), new Range(7, 13)), r);
    }

    @Test
    void caseSensitiveWhenRequested() {
        List<Range> r = engine.find("Amount amount", "amount", true, false);
        assertEquals(List.of(new Range(7, 13)), r);
    }

    @Test
    void regexMatchesAddress() {
        String text = "to=0x1f98431c8ad98523631ae4a59f267346ea31f984;";
        List<Range> r = engine.find(text, "0x[0-9a-f]{40}", false, true);
        assertEquals(1, r.size());
        assertEquals(text.indexOf("0x1f"), r.get(0).start);
        assertEquals(text.indexOf("0x1f") + 42, r.get(0).end);
    }

    @Test
    void caseSensitiveRegexMatchesOnlyExactCase() {
        List<Range> r = engine.find("Foo foo", "Foo", true, true);
        assertEquals(List.of(new Range(0, 3)), r);
    }

    @Test
    void regexFindsMultipleMatches() {
        List<Range> r = engine.find("0xAB 0xCD", "0x[0-9a-fA-F]+", false, true);
        assertEquals(List.of(new Range(0, 4), new Range(5, 9)), r);
    }

    @Test
    void emptyQueryYieldsNoMatches() {
        assertTrue(engine.find("anything", "", false, false).isEmpty());
    }

    @Test
    void invalidRegexYieldsNoMatchesAndNoThrow() {
        assertTrue(engine.find("anything", "[unclosed", false, true).isEmpty());
    }

    @Test
    void noMatchYieldsEmpty() {
        assertTrue(engine.find("hello", "zzz", false, false).isEmpty());
    }
}
