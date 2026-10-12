package com.nccgroup.web3decoder.abi;

import org.json.JSONObject;
import org.json.JSONTokener;

import java.util.Locale;

/** Pure mapping of a raw Etherscan HTTP result to an {@link AbiLookupStatus}. No I/O. */
public final class EtherscanResponseClassifier {

    public record Classification(AbiLookupStatus status, String abi, String message) {}

    private EtherscanResponseClassifier() {}

    public static Classification classify(int httpStatus, String body) {
        if (httpStatus == 429) {
            return new Classification(AbiLookupStatus.RATE_LIMITED, null, "HTTP 429 (rate limited)");
        }
        if (httpStatus != 200) {
            return new Classification(AbiLookupStatus.HTTP_ERROR, null, "HTTP " + httpStatus);
        }

        JSONObject json;
        try {
            json = new JSONObject(new JSONTokener(body));
        } catch (Exception e) {
            return new Classification(AbiLookupStatus.ERROR, null, "Unparseable explorer response");
        }

        String status = json.optString("status", "0");
        String result = json.optString("result", "");

        if ("1".equals(status)) {
            return new Classification(AbiLookupStatus.FOUND, result, "OK");
        }

        String lower = result.toLowerCase(Locale.ROOT);
        if (lower.contains("rate limit") || lower.contains("max calls per sec") || lower.contains("max rate")) {
            return new Classification(AbiLookupStatus.RATE_LIMITED, null, result);
        }
        if (lower.contains("api key")) { // "Missing/Invalid API Key", "Invalid API Key"
            return new Classification(AbiLookupStatus.MISSING_API_KEY, null, result);
        }
        if (lower.contains("unsupported chainid")) {
            return new Classification(AbiLookupStatus.UNSUPPORTED_CHAIN, null, result);
        }
        if (lower.contains("not verified") || lower.contains("no abi") || lower.contains("not been verified")) {
            return new Classification(AbiLookupStatus.NOT_VERIFIED, null, result);
        }
        return new Classification(AbiLookupStatus.ERROR, null, result.isEmpty() ? "Explorer returned status 0" : result);
    }
}
