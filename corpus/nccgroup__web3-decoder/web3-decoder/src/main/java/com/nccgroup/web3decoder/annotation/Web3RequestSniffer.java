package com.nccgroup.web3decoder.annotation;

/**
 * Cheap, allocation-light check for whether a request body is a JSON-RPC call worth
 * decoding for annotation. Deliberately a substring scan (no JSON parse) so it can run
 * inline on the traffic path; the real parse happens later on a background thread.
 */
public final class Web3RequestSniffer {

    private Web3RequestSniffer() {}

    public static boolean isCandidate(String body) {
        if (body == null || body.isEmpty()) {
            return false;
        }
        return body.contains("eth_call") || body.contains("eth_sendRawTransaction");
    }
}
