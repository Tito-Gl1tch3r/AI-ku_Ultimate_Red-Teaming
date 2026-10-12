package com.github.chandrakanthrck.cache_project.eviction;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;

import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Logger;

public class TTLEvictionPolicy<K, V> implements EvictionPolicy<K, V> {

    private static final Logger logger = Logger.getLogger(TTLEvictionPolicy.class.getName());
    private final ConcurrentMap<K, Instant> timeMap;  // Use a thread-safe map for time tracking
    private final long ttlMillis;
    private final boolean refreshOnGet;  // Option to refresh the TTL on access
    private final MeterRegistry meterRegistry;  // For recording eviction metrics

    public TTLEvictionPolicy(long ttlMillis, boolean refreshOnGet, MeterRegistry meterRegistry) {
        this.timeMap = new ConcurrentHashMap<>();
        this.ttlMillis = ttlMillis;
        this.refreshOnGet = refreshOnGet;
        this.meterRegistry = meterRegistry;
        registerEvictionMetrics();  // Register TTL-related metrics
    }

    @Override
    public void onPut(K key, V value, ConcurrentMap<K, V> cache) {
        timeMap.put(key, Instant.now());  // Store the current timestamp when the entry is added
        logger.info("TTL onPut: Added " + key + " to TTL tracking.");
        evictEntries(cache);  // Check if eviction is needed
        meterRegistry.counter("cache.put", Tags.of("cache.policy", "TTL")).increment();  // Track put operation
    }

    @Override
    public void onGet(K key, V value) {
        if (refreshOnGet) {
            timeMap.put(key, Instant.now());  // Optionally refresh the timestamp on access
            logger.info("TTL onGet: Accessed " + key + ", TTL refreshed.");
        }
        meterRegistry.counter("cache.get", Tags.of("cache.policy", "TTL")).increment();  // Track get operation
    }

    @Override
    public void evictEntries(ConcurrentMap<K, V> cache) {
        Instant now = Instant.now();

        // Iterate through the time map and remove entries older than TTL
        timeMap.entrySet().removeIf(entry -> {
            K key = entry.getKey();
            Instant timeAdded = entry.getValue();
            if (now.isAfter(timeAdded.plusMillis(ttlMillis))) {
                cache.remove(key);  // Remove expired entry from cache
                logger.info("Evicted TTL: Removed " + key);
                meterRegistry.counter("cache.eviction", Tags.of("cache.policy", "TTL")).increment();  // Track eviction
                return true;  // Remove from the time map
            }
            return false;
        });
    }

    private void registerEvictionMetrics() {
        // Register any custom metrics for TTL cache policy if needed
        // Example: Register a gauge for the size of the TTL timeMap
        meterRegistry.gauge("cache.ttl.timeMap.size", Tags.of("cache.policy", "TTL"), timeMap, ConcurrentMap::size);
    }
}
