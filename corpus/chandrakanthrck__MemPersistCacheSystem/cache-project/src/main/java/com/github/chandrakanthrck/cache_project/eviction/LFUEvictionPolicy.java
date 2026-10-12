package com.github.chandrakanthrck.cache_project.eviction;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Logger;

public class LFUEvictionPolicy<K, V> implements EvictionPolicy<K, V> {

    private static final Logger logger = Logger.getLogger(LFUEvictionPolicy.class.getName());
    private final ConcurrentMap<K, Integer> accessCounts;
    private final MeterRegistry meterRegistry;  // For recording eviction metrics

    public LFUEvictionPolicy(MeterRegistry meterRegistry) {
        this.accessCounts = new ConcurrentHashMap<>();
        this.meterRegistry = meterRegistry;
        registerEvictionMetrics();  // Register the eviction metrics
    }

    @Override
    public void onPut(K key, V value, ConcurrentMap<K, V> cache) {
        accessCounts.put(key, 1);  // Initialize the access count to 1 when a new entry is added
        logger.info("LFU onPut: Added " + key + " to LFU tracking.");
        evictEntries(cache);  // Check if eviction is needed
        meterRegistry.counter("cache.put", Tags.of("cache.policy", "LFU")).increment();  // Track put operation
    }

    @Override
    public void onGet(K key, V value) {
        accessCounts.compute(key, (k, count) -> (count == null) ? 1 : count + 1);  // Increment access count
        logger.info("LFU onGet: Accessed " + key + ", access count updated.");
        meterRegistry.counter("cache.get", Tags.of("cache.policy", "LFU")).increment();  // Track get operation
    }

    @Override
    public void evictEntries(ConcurrentMap<K, V> cache) {
        K leastFrequentKey = accessCounts.entrySet().stream()
                .min(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse(null);

        if (leastFrequentKey != null) {
            cache.remove(leastFrequentKey);  // Remove from actual cache
            accessCounts.remove(leastFrequentKey);  // Remove from access count tracking
            logger.info("Evicted LFU: Removed " + leastFrequentKey);
            meterRegistry.counter("cache.eviction", Tags.of("cache.policy", "LFU")).increment();  // Track eviction
        }
    }

    private void registerEvictionMetrics() {
        // Register any custom metrics for LFU cache policy if needed
        // Example: Register a gauge for the size of the LFU access count map
        meterRegistry.gauge("cache.lfu.accessCount.size", Tags.of("cache.policy", "LFU"), accessCounts, Map::size);
    }
}
