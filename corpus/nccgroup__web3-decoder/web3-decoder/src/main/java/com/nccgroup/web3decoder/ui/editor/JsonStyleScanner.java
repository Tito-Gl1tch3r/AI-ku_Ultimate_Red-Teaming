package com.nccgroup.web3decoder.ui.editor;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.regex.Pattern;

/**
 * A small, resilient single-pass JSON tokenizer that produces styled spans for
 * the editor. It never throws: incomplete/invalid input simply yields best-effort
 * spans. Validity is checked separately by {@link JsonValidator}.
 */
public final class JsonStyleScanner {

    private static final Pattern ADDRESS = Pattern.compile("^0x[0-9a-fA-F]{40}$");
    private static final Pattern HEX = Pattern.compile("^0x[0-9a-fA-F]+$");

    /** One container scope on the parse stack. */
    private static final class Frame {
        final boolean object;
        boolean expectKey;   // true when the next string in an object is a key
        String pendingKey;   // most recent key parsed in this object
        boolean inArgs;      // this container is the "args" value, or nested within it

        Frame(boolean object) {
            this.object = object;
            this.expectKey = object;
        }
    }

    /** A child container is in the args subtree if its parent is, or it is the value of an "args" key. */
    private static boolean childInArgs(Frame parent) {
        if (parent == null) return false;
        return parent.inArgs || (parent.object && "args".equals(parent.pendingKey));
    }

    public List<StyleSpan> scan(String text) {
        List<StyleSpan> spans = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return spans;
        }

        int n = text.length();
        int firstNonWs = 0;
        while (firstNonWs < n && Character.isWhitespace(text.charAt(firstNonWs))) {
            firstNonWs++;
        }
        // Only objects/arrays are treated as JSON; anything else (hex calldata, a plain
        // status message) renders as a single PLAIN span.
        if (firstNonWs >= n || (text.charAt(firstNonWs) != '{' && text.charAt(firstNonWs) != '[')) {
            spans.add(new StyleSpan(0, n, StyleKind.PLAIN));
            return spans;
        }

        Deque<Frame> stack = new ArrayDeque<>();
        int i = 0;
        while (i < n) {
            char c = text.charAt(i);
            if (Character.isWhitespace(c)) {
                i++;
                continue;
            }
            switch (c) {
                case '{': {
                    spans.add(new StyleSpan(i, i + 1, StyleKind.PUNCTUATION));
                    Frame f = new Frame(true);
                    f.inArgs = childInArgs(stack.peek());
                    stack.push(f);
                    i++;
                    break;
                }
                case '[': {
                    spans.add(new StyleSpan(i, i + 1, StyleKind.PUNCTUATION));
                    Frame f = new Frame(false);
                    f.inArgs = childInArgs(stack.peek());
                    stack.push(f);
                    i++;
                    break;
                }
                case '}':
                case ']':
                    spans.add(new StyleSpan(i, i + 1, StyleKind.PUNCTUATION));
                    if (!stack.isEmpty()) stack.pop();
                    i++;
                    break;
                case ':':
                    spans.add(new StyleSpan(i, i + 1, StyleKind.PUNCTUATION));
                    if (!stack.isEmpty() && stack.peek().object) stack.peek().expectKey = false;
                    i++;
                    break;
                case ',':
                    spans.add(new StyleSpan(i, i + 1, StyleKind.PUNCTUATION));
                    if (!stack.isEmpty() && stack.peek().object) {
                        stack.peek().expectKey = true;
                        stack.peek().pendingKey = null;
                    }
                    i++;
                    break;
                case '"': {
                    int end = readString(text, i);
                    String content = text.substring(i + 1, Math.max(i + 1, end - 1));
                    Frame top = stack.peek();
                    boolean bold = top != null && top.inArgs;
                    boolean isKey = top != null && top.object && top.expectKey;
                    if (isKey) {
                        spans.add(new StyleSpan(i, end, StyleKind.KEY, bold));
                        top.pendingKey = content;
                    } else {
                        spans.add(new StyleSpan(i, end, classifyValueString(top, content), bold));
                    }
                    i = end;
                    break;
                }
                default:
                    boolean bold = !stack.isEmpty() && stack.peek().inArgs;
                    if (c == '-' || (c >= '0' && c <= '9')) {
                        int end = readNumber(text, i);
                        spans.add(new StyleSpan(i, end, StyleKind.NUMBER, bold));
                        i = end;
                    } else if (c == 't' || c == 'f' || c == 'n') {
                        int end = readWord(text, i);
                        spans.add(new StyleSpan(i, end, StyleKind.BOOL_NULL, bold));
                        i = end;
                    } else {
                        i++; // unknown character: skip, stay resilient
                    }
            }
        }
        return spans;
    }

    private static StyleKind classifyValueString(Frame top, String content) {
        String key = top != null ? top.pendingKey : null;
        if ("function".equals(key)) return StyleKind.FUNCTION;
        if ("reason".equals(key)) return StyleKind.ERROR;
        if ("status".equals(key)) {
            switch (content) {
                case "decoded": return StyleKind.STATUS_OK;
                case "skipped": return StyleKind.STATUS_SKIPPED;
                case "error":   return StyleKind.ERROR;
                default: break;
            }
        }
        if ("decodeSource".equals(key)) {
            switch (content) {
                case "cache":     return StyleKind.SOURCE_CACHE;
                case "etherscan": return StyleKind.SOURCE_ETHERSCAN;
                case "4byte":     return StyleKind.SOURCE_FOURBYTE;
                case "builtin":   return StyleKind.SOURCE_BUILTIN;
                default: break;
            }
        }
        if (ADDRESS.matcher(content).matches()) return StyleKind.ADDRESS;
        if (HEX.matcher(content).matches()) return StyleKind.HEX;
        return StyleKind.STRING;
    }

    /** Returns the index just past the closing quote, or text length if unterminated. */
    private static int readString(String text, int openQuote) {
        int n = text.length();
        int i = openQuote + 1;
        while (i < n) {
            char c = text.charAt(i);
            if (c == '\\') {
                i += 2;
                continue;
            }
            if (c == '"') return i + 1;
            i++;
        }
        return n;
    }

    private static int readNumber(String text, int start) {
        int n = text.length();
        int i = start;
        if (i < n && text.charAt(i) == '-') i++;
        while (i < n) {
            char c = text.charAt(i);
            if ((c >= '0' && c <= '9') || c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') {
                i++;
            } else {
                break;
            }
        }
        return i;
    }

    private static int readWord(String text, int start) {
        int n = text.length();
        int i = start;
        while (i < n && Character.isLetter(text.charAt(i))) i++;
        return i;
    }
}
