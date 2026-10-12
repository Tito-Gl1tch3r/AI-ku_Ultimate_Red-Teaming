package com.nccgroup.web3decoder.detection;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Locates byte offsets in a response body that may mark the inside of a Solidity ABI.
 * Uses a small set of fixed needles that are present in either JS-object-literal or
 * strict-JSON forms of an ABI — both with very low false-positive rates outside
 * Solidity output.
 */
public final class AbiTokenScanner {

    private static final List<String> NEEDLES = Arrays.asList(
            "stateMutability:\"",
            "\"stateMutability\":\"",
            "internalType:\"",
            "\"internalType\":\""
    );

    private AbiTokenScanner() {}

    /** @return ascending list of offsets in {@code body} where any needle starts. */
    public static List<Integer> findCandidateOffsets(String body) {
        List<Integer> hits = new ArrayList<>();
        if (body == null || body.isEmpty()) return hits;
        for (String needle : NEEDLES) {
            int idx = 0;
            while ((idx = body.indexOf(needle, idx)) >= 0) {
                hits.add(idx);
                idx += needle.length();
            }
        }
        hits.sort(Integer::compareTo);
        return hits;
    }
}
