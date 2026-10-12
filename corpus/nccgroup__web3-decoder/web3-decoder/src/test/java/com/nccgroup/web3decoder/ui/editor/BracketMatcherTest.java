package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class BracketMatcherTest {

    private final BracketMatcher matcher = new BracketMatcher();

    @Test
    void caretBeforeOpenBraceFindsClose() {
        String t = "{\"a\":[1,2]}"; // '{'@0 ... '}'@10
        assertEquals(10, matcher.match(t, 0));
    }

    @Test
    void caretAfterCloseBraceFindsOpen() {
        String t = "{\"a\":[1,2]}";
        assertEquals(0, matcher.match(t, t.length())); // caret after final '}'
    }

    @Test
    void nestedBracketPicksCorrectPartner() {
        String t = "[{}]"; // '['@0 '{'@1 '}'@2 ']'@3
        assertEquals(3, matcher.match(t, 0));
        assertEquals(2, matcher.match(t, 2)); // before '{' -> caret 1? use caret on '{'
        assertEquals(2, matcher.match(t, 1)); // caret at index 1 = on '{'
    }

    @Test
    void bracketsInsideStringsAreIgnored() {
        String t = "{\"a\":\"}\"}"; // real closing brace is the last char
        assertEquals(t.length() - 1, matcher.match(t, 0));
    }

    @Test
    void unbalancedReturnsMinusOne() {
        assertEquals(-1, matcher.match("{", 0));
    }

    @Test
    void caretNotBesideBracketReturnsMinusOne() {
        String t = "{\"a\":1}";
        assertEquals(-1, matcher.match(t, 3)); // inside "a"
    }
}
