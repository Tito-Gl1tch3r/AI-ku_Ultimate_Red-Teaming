package com.github.chandrakanthrck.cache_project.eviction;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Logger;

public class LRUEvictionPolicy<K, V> implements EvictionPolicy<K, V> {

    private static final Logger logger = Logger.getLogger(LRUEvictionPolicy.class.getName());
    private final LinkedHashMap<K, V> lruCache;
    private final int maxSize;
    private final MeterRegistry meterRegistry;  // To record eviction metrics

    public LRUEvictionPolicy(int maxSize, MeterRegistry meterRegistry) {
        this.maxSize = maxSize;
        this.meterRegistry = meterRegistry;
        this.lruCache = new LinkedHashMap<>(maxSize, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                return size() > maxSize;
            }
        };
        registerEvictionMetrics();  // Register the eviction metrics
    }

    @Override
    public void onPut(K key, V value, ConcurrentMap<K, V> cache) {
        lruCache.put(key, value);  // Track access in LRU map
        logger.info("LRU onPut: Added " + key + " to LRU tracking.");
        evictEntries(cache);  // Evict if needed
        meterRegistry.counter("cache.put", Tags.of("cache.policy", "LRU")).increment();
    }

    @Override
    public void onGet(K key, V value) {
        lruCache.get(key);  // Access the item, reordering it in the LRU cache
        logger.info("LRU onGet: Accessed " + key);
        meterRegistry.counter("cache.get", Tags.of("cache.policy", "LRU")).increment();
    }

    @Override
    public void evictEntries(ConcurrentMap<K, V> cache) {
        if (lruCache.size() > maxSize) {
            K eldestKey = lruCache.keySet().iterator().next();  // Get the eldest (LRU) key
            cache.remove(eldestKey);  // Remove from actual cache
            lruCache.remove(eldestKey);  // Remove from LRU tracking
            logger.info("Evicted LRU: Removed " + eldestKey);
            meterRegistry.counter("cache.eviction", Tags.of("cache.policy", "LRU")).increment();
        }
    }

    private void registerEvictionMetrics() {
        // Register the metrics for cache size and eviction count
        meterRegistry.gauge("cache.size", Tags.of("cache.policy", "LRU"), lruCache, Map::size);
    }
}
