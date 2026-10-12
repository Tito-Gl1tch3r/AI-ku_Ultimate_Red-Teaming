package com.nccgroup.web3decoder.detection;

import java.util.Optional;

/**
 * Given an offset somewhere inside a candidate ABI literal, find the enclosing
 * "[ ... ]" array (string-aware, depth-aware) and return its contents.
 *
 * <p>Important: the enclosing array is the array that <em>directly</em> contains the
 * hit. Walking left character-by-character with a bracket-depth counter, the first
 * {@code [} we see at depth 0 is the start of that array. Earlier inner arrays
 * (e.g. {@code inputs:[...]}) are crossed at depth ≥ 1 and ignored.
 */
public final class AbiBoundaryExtractor {

    /** Hard upper bound on how far we search outward from the hit. Keeps pathological
     *  bodies cheap. ABIs longer than this are rare and not worth the cost. */
    private static final int MAX_SCAN = 512 * 1024;

    private AbiBoundaryExtractor() {}

    public static Optional<String> extract(String body, int hitOffset) {
        if (body == null || hitOffset < 0 || hitOffset >= body.length()) return Optional.empty();
        return extract(body, hitOffset, computeInStringMap(body));
    }

    /**
     * Same as {@link #extract(String, int)} but takes a precomputed string-awareness
     * bitmap. Callers that process many hits against the same body should compute the
     * map once via {@link #computeInStringMap(String)} and reuse it.
     */
    public static Optional<String> extract(String body, int hitOffset, boolean[] inString) {
        if (body == null || hitOffset < 0 || hitOffset >= body.length()) return Optional.empty();
        int start = findEnclosingArrayStart(body, hitOffset, inString);
        if (start < 0) return Optional.empty();
        int end = findMatchingClose(body, start, inString);
        if (end < 0) return Optional.empty();
        return Optional.of(body.substring(start, end + 1));
    }

    /**
     * Build a parallel {@code boolean[]} marking every byte inside a JS/JSON string
     * literal (string content only, not the surrounding quotes). Single-pass forward
     * scan; respects backslash escapes inside strings.
     */
    public static boolean[] computeInStringMap(String body) {
        boolean[] inStr = new boolean[body.length()];
        boolean inside = false;
        char quote = 0;
        for (int i = 0; i < body.length(); i++) {
            char c = body.charAt(i);
            if (!inside) {
                if (c == '"' || c == '\'') {
                    inside = true;
                    quote = c;
                }
            } else {
                if (c == '\\' && i + 1 < body.length()) {
                    inStr[i] = true;
                    inStr[i + 1] = true;
                    i++;
                    continue;
                }
                if (c == quote) {
                    inside = false;
                } else {
                    inStr[i] = true;
                }
            }
        }
        return inStr;
    }

    /**
     * Walk left from {@code hitOffset} tracking bracket depth (string-aware) and
     * return the start of the OUTERMOST {@code [{...}]} array enclosing the hit.
     *
     * <p>Why outermost: ABIs are nested arrays — function entries contain
     * {@code inputs:[{...}]} / {@code outputs:[{...}]} sub-arrays. Returning the
     * first enclosing {@code [} at depth 0 would pick those sub-arrays instead
     * of the outer ABI array, which would then fail validation because their
     * element {@code type} values are Solidity types ("address", "uint256") not
     * ABI vocabulary ("function", "event", …).
     *
     * <p>So when we find a depth-0 {@code [} that's followed by {@code {} we save
     * it and keep walking — a later (further-left) depth-0 {@code [} that also
     * matches {@code [{} represents an outer container of the previous, and is
     * preferred. The LAST one saved wins.
     */
    private static int findEnclosingArrayStart(String body, int hitOffset, boolean[] inString) {
        int limit = Math.max(0, hitOffset - MAX_SCAN);
        int depth = 0;
        int lastEnclosing = -1;
        for (int i = hitOffset; i >= limit; i--) {
            if (inString[i]) continue;
            char c = body.charAt(i);
            if (c == ']') {
                depth++;
            } else if (c == '[') {
                if (depth == 0) {
                    int j = i + 1;
                    while (j < body.length() && Character.isWhitespace(body.charAt(j))) j++;
                    if (j < body.length() && body.charAt(j) == '{') {
                        lastEnclosing = i;
                    }
                    // Regardless of [{ match, this `[` exited an array we were
                    // inside; keep walking left to find more-outer containers.
                } else {
                    depth--;
                }
            }
        }
        return lastEnclosing;
    }

    /** Forward-scan from {@code start} (which must point at '[') to its matching ']' —
     *  string-aware via the precomputed bitmap. Returns -1 if unbalanced within MAX_SCAN. */
    private static int findMatchingClose(String body, int start, boolean[] inString) {
        int depth = 0;
        int limit = Math.min(body.length(), start + MAX_SCAN);
        for (int i = start; i < limit; i++) {
            if (inString[i]) continue;
            char c = body.charAt(i);
            if (c == '[' || c == '{') depth++;
            else if (c == '}') depth--;
            else if (c == ']') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }
}
