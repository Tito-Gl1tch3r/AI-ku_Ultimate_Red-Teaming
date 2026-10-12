package com.github.chandrakanthrck.cache_project.factory;

import com.github.chandrakanthrck.cache_project.eviction.*;
import java.util.concurrent.TimeUnit;
import java.util.logging.Logger;
import io.micrometer.core.instrument.MeterRegistry;

public class EvictionPolicyFactory<K, V> {

    private static final Logger logger = Logger.getLogger(EvictionPolicyFactory.class.getName());

    public enum EvictionType {
        TTL, LRU, LFU
    }

    /**
     * Returns an eviction policy based on the provided eviction type, cache size, and TTL parameters.
     *
     * @param evictionType  the type of eviction policy (TTL, LRU, LFU)
     * @param cacheSize     the maximum size of the cache (only relevant for LRU and LFU)
     * @param ttlMillis     the TTL in milliseconds (only relevant for TTL eviction)
     * @param refreshOnGet  whether the TTL should be refreshed on access (only relevant for TTL eviction)
     * @param meterRegistry the MeterRegistry for tracking metrics
     * @return an EvictionPolicy based on the input parameters
     */
    public EvictionPolicy<K, V> getEvictionPolicy(EvictionType evictionType, int cacheSize, long ttlMillis, boolean refreshOnGet, MeterRegistry meterRegistry) {
        try {
            switch (evictionType) {
                case TTL:
                    validateTtl(ttlMillis);
                    logger.info("Creating TTL eviction policy with TTL: " + ttlMillis + " ms and refreshOnGet: " + refreshOnGet);
                    return new TTLEvictionPolicy<>(ttlMillis, refreshOnGet, meterRegistry);
                case LRU:
                    validateCacheSize(cacheSize);
                    logger.info("Creating LRU eviction policy with max size: " + cacheSize);
                    return new LRUEvictionPolicy<>(cacheSize, meterRegistry);
                case LFU:
                    validateCacheSize(cacheSize);
                    logger.info("Creating LFU eviction policy with max size: " + cacheSize);
                    return new LFUEvictionPolicy<>(meterRegistry);  // LFU eviction with meter registry
                default:
                    throw new IllegalArgumentException("Unknown eviction type: " + evictionType);
            }
        } catch (IllegalArgumentException e) {
            logger.severe("Error creating eviction policy: " + e.getMessage());
            throw e; // Rethrow or handle it as needed
        } catch (Exception e) {
            logger.severe("Unexpected error while creating eviction policy: " + e.getMessage());
            throw new RuntimeException("Failed to create eviction policy", e); // Rethrow as a runtime exception
        }
    }

    /**
     * Returns an eviction policy with default values.
     *
     * @param evictionType the type of eviction policy (TTL, LRU, LFU)
     * @param meterRegistry the MeterRegistry for tracking metrics
     * @return an EvictionPolicy based on the default parameters
     */
    public EvictionPolicy<K, V> getEvictionPolicy(EvictionType evictionType, MeterRegistry meterRegistry) {
        logger.info("Creating eviction policy with default values for eviction type: " + evictionType);
        return getEvictionPolicy(evictionType, 100, TimeUnit.SECONDS.toMillis(10), false, meterRegistry);  // Default values
    }

    // Helper method to validate cache size
    private void validateCacheSize(int cacheSize) {
        if (cacheSize <= 0) {
            throw new IllegalArgumentException("Cache size must be greater than 0");
        }
    }

    // Helper method to validate TTL duration
    private void validateTtl(long ttlMillis) {
        if (ttlMillis <= 0) {
            throw new IllegalArgumentException("TTL must be greater than 0 milliseconds");
        }
    }
}