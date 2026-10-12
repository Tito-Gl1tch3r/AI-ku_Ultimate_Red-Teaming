package com.nccgroup.web3_decoder.abi;

import com.nccgroup.web3decoder.abi.AbiLookupStatus;
import com.nccgroup.web3decoder.abi.EtherscanResponseClassifier;
import com.nccgroup.web3decoder.abi.EtherscanResponseClassifier.Classification;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class EtherscanResponseClassifierTest {

    @Test
    void httpErrorWhenNot200() {
        Classification c = EtherscanResponseClassifier.classify(500, "");
        assertEquals(AbiLookupStatus.HTTP_ERROR, c.status());
        assertNull(c.abi());
    }

    @Test
    void rateLimitedOn429() {
        Classification c = EtherscanResponseClassifier.classify(429, "");
        assertEquals(AbiLookupStatus.RATE_LIMITED, c.status());
    }

    @Test
    void foundReturnsAbi() {
        String body = "{\"status\":\"1\",\"message\":\"OK\",\"result\":\"[{\\\"type\\\":\\\"function\\\"}]\"}";
        Classification c = EtherscanResponseClassifier.classify(200, body);
        assertEquals(AbiLookupStatus.FOUND, c.status());
        assertEquals("[{\"type\":\"function\"}]", c.abi());
    }

    @Test
    void rateLimitedFromBodyMessage() {
        String body = "{\"status\":\"0\",\"message\":\"NOTOK\",\"result\":\"Max calls per sec rate limit reached (5/sec)\"}";
        Classification c = EtherscanResponseClassifier.classify(200, body);
        assertEquals(AbiLookupStatus.RATE_LIMITED, c.status());
    }

    @Test
    void missingApiKeyFromBody() {
        String body = "{\"status\":\"0\",\"message\":\"NOTOK\",\"result\":\"Missing/Invalid API Key\"}";
        Classification c = EtherscanResponseClassifier.classify(200, body);
        assertEquals(AbiLookupStatus.MISSING_API_KEY, c.status());
    }

    @Test
    void notVerifiedFromBody() {
        String body = "{\"status\":\"0\",\"message\":\"NOTOK\",\"result\":\"Contract source code not verified\"}";
        Classification c = EtherscanResponseClassifier.classify(200, body);
        assertEquals(AbiLookupStatus.NOT_VERIFIED, c.status());
    }

    @Test
    void unsupportedChainFromBody() {
        String body = "{\"status\":\"0\",\"message\":\"NOTOK\",\"result\":\"Error! Unsupported chainid\"}";
        Classification c = EtherscanResponseClassifier.classify(200, body);
        assertEquals(AbiLookupStatus.UNSUPPORTED_CHAIN, c.status());
    }

    @Test
    void unparseableBodyIsError() {
        Classification c = EtherscanResponseClassifier.classify(200, "not json");
        assertEquals(AbiLookupStatus.ERROR, c.status());
    }
}
