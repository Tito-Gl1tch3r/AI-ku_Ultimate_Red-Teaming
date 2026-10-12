package com.nccgroup.web3decoder.ui.editor;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Deque;

/**
 * Finds the bracket matching the one immediately before or after a caret.
 * Brackets inside string literals are ignored. Pure; no Swing.
 */
public final class BracketMatcher {

    /** Returns the matching bracket offset, or -1 if the caret is not beside a matched bracket. */
    public int match(String text, int caret) {
        int pos = selectedBracketIndex(text, caret);
        if (pos < 0) return -1;
        return computePartners(text)[pos];
    }

    /**
     * Returns the index of the bracket the caret is considered to be "on" — the bracket
     * whose partner {@link #match} returns — or -1 if the caret is not beside a bracket.
     * When both neighbours are brackets, the open bracket is preferred so a caret sitting
     * between an open and its close highlights the open and its partner.
     */
    public int selectedBracketIndex(String text, int caret) {
        if (text == null) return -1;
        int n = text.length();
        boolean caretValid = caret >= 0 && caret < n && isBracket(text.charAt(caret));
        boolean leftValid = caret - 1 >= 0 && caret - 1 < n && isBracket(text.charAt(caret - 1));
        if (caretValid && leftValid) {
            return isOpen(text.charAt(caret)) ? caret : caret - 1;
        } else if (caretValid) {
            return caret;
        } else if (leftValid) {
            return caret - 1;
        }
        return -1;
    }

    private static boolean isBracket(char c) {
        return c == '{' || c == '}' || c == '[' || c == ']' || c == '(' || c == ')';
    }

    private static boolean isOpen(char c) {
        return c == '{' || c == '[' || c == '(';
    }

    private static char closeOf(char c) {
        return c == '{' ? '}' : c == '[' ? ']' : ')';
    }

    private static int[] computePartners(String text) {
        int n = text.length();
        int[] partner = new int[n];
        Arrays.fill(partner, -1);
        Deque<Integer> stack = new ArrayDeque<>();
        boolean inStr = false;
        for (int i = 0; i < n; i++) {
            char c = text.charAt(i);
            if (inStr) {
                if (c == '\\') {
                    i++;
                    continue;
                }
                if (c == '"') inStr = false;
                continue;
            }
            if (c == '"') {
                inStr = true;
                continue;
            }
            if (isOpen(c)) {
                stack.push(i);
            } else if (c == '}' || c == ']' || c == ')') {
                if (!stack.isEmpty()) {
                    int openPos = stack.peek();
                    if (closeOf(text.charAt(openPos)) == c) {
                        stack.pop();
                        partner[openPos] = i;
                        partner[i] = i == openPos ? -1 : openPos;
                    } else {
                        stack.pop(); // mismatched: leave both unmatched
                    }
                }
            }
        }
        return partner;
    }
}
