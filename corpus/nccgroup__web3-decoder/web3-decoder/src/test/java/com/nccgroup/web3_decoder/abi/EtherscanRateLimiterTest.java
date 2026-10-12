package com.nccgroup.web3_decoder.abi;

import com.nccgroup.web3decoder.abi.EtherscanRateLimiter;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EtherscanRateLimiterTest {

    @Test
    void enforcesMinIntervalBetweenAcquires() throws InterruptedException {
        // 50 calls/sec -> 20ms min interval. 5 acquires => >= ~4*20ms = 80ms.
        EtherscanRateLimiter limiter = new EtherscanRateLimiter(50);
        long start = System.nanoTime();
        for (int i = 0; i < 5; i++) {
            limiter.acquire();
        }
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;
        assertTrue(elapsedMs >= 70, "Expected >=70ms for 5 acquires at 50/sec, got " + elapsedMs + "ms");
    }

    @Test
    void singletonIsStableAcrossCalls() {
        assertNotNull(EtherscanRateLimiter.getInstance());
        assertSame(EtherscanRateLimiter.getInstance(), EtherscanRateLimiter.getInstance());
    }
}
