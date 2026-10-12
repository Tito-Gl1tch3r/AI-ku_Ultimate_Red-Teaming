package com.nccgroup.web3decoder.abi;

import java.util.concurrent.TimeUnit;

/**
 * Process-wide gate that spaces Etherscan calls to at most {@code maxCallsPerSecond}.
 * Etherscan's free tier allows 5 calls/sec shared across all chains for a key, and a
 * fresh provider is created per request, so this must be a singleton. {@link #acquire()}
 * blocks the calling (background) thread until the next slot is due.
 */
public class EtherscanRateLimiter {

    /** Etherscan free-tier limit (calls/sec). Tune here if a paid tier raises it. */
    public static final int DEFAULT_MAX_CALLS_PER_SECOND = 5;

    private static final EtherscanRateLimiter INSTANCE = new EtherscanRateLimiter(DEFAULT_MAX_CALLS_PER_SECOND);

    public static EtherscanRateLimiter getInstance() {
        return INSTANCE;
    }

    private final long minIntervalNanos;
    private long lastAcquireNanos = Long.MIN_VALUE;

    /** Build a limiter with a custom rate (the singleton uses the default). Used by tests. */
    public EtherscanRateLimiter(int maxCallsPerSecond) {
        this.minIntervalNanos = 1_000_000_000L / Math.max(1, maxCallsPerSecond);
    }

    public synchronized void acquire() throws InterruptedException {
        long now = System.nanoTime();
        long earliest = lastAcquireNanos + minIntervalNanos;
        if (lastAcquireNanos != Long.MIN_VALUE && now < earliest) {
            TimeUnit.NANOSECONDS.sleep(earliest - now);
            now = System.nanoTime();
        }
        lastAcquireNanos = now;
    }
}
