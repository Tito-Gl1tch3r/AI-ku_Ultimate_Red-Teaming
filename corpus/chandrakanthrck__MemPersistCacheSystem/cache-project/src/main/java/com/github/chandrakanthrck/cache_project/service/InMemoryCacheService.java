package com.github.chandrakanthrck.cache_project.service;

import com.github.chandrakanthrck.cache_project.eviction.EvictionPolicy;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.logging.Logger;

public class InMemoryCacheService<K, V> implements CacheService<K, V> {

    private static final Logger logger = Logger.getLogger(InMemoryCacheService.class.getName());

    private final ConcurrentMap<K, V> cache;
    private final EvictionPolicy<K, V> evictionPolicy;
    private final MeterRegistry meterRegistry;
    private final int maxCacheSize;

    public InMemoryCacheService(EvictionPolicy<K, V> evictionPolicy, MeterRegistry meterRegistry, int maxCacheSize) {
        this.cache = new ConcurrentHashMap<>();
        this.evictionPolicy = evictionPolicy;
        this.meterRegistry = meterRegistry;
        this.maxCacheSize = maxCacheSize;
        registerCacheMetrics();  // Register cache-related metrics
    }

    @Override
    public void put(K key, V value) {
        logger.info("Cache size before put: " + cache.size());

        try {
            // Add key-value pair to the cache
            cache.put(key, value);
            logger.info("Inserted key: " + key + ". Cache size after put: " + cache.size());

            // After inserting, enforce eviction to ensure the size limit
            enforceEvictionPolicy();

            // Log cache size after enforcing eviction
            logger.info("Cache size after eviction enforcement: " + cache.size());

            // Update cache size metric
            updateCacheSizeMetric();
        } catch (Exception e) {
            logger.severe("Error occurred while putting key: " + key + " into cache. Error: " + e.getMessage());
            // Optionally, handle the error (e.g., alerting, fallback logic)
        }
    }

    @Override
    public V get(K key) {
        try {
            V value = cache.get(key);

            if (value != null) {
                // Cache hit
                meterRegistry.counter("cache.hit", Tags.of("cache", "inMemoryCache")).increment();
                evictionPolicy.onGet(key, value);  // Notify eviction policy about access
                logger.info("Cache hit for key: " + key);
            } else {
                // Cache miss
                meterRegistry.counter("cache.miss", Tags.of("cache", "inMemoryCache")).increment();
                logger.info("Cache miss for key: " + key);
            }

            return value;
        } catch (Exception e) {
            logger.severe("Error occurred while getting key: " + key + " from cache. Error: " + e.getMessage());
            return null; // Or throw a custom exception if necessary
        }
    }

    @Override
    public void remove(K key) {
        try {
            cache.remove(key);
            updateCacheSizeMetric();
            logger.info("Removed key: " + key + ". Cache size is now: " + cache.size());
        } catch (Exception e) {
            logger.severe("Error occurred while removing key: " + key + " from cache. Error: " + e.getMessage());
        }
    }

    @Override
    public void clear() {
        try {
            cache.clear();
            updateCacheSizeMetric();
            logger.info("Cache cleared.");
        } catch (Exception e) {
            logger.severe("Error occurred while clearing cache. Error: " + e.getMessage());
        }
    }

    @Override
    public int size() {
        try {
            return cache.size();
        } catch (Exception e) {
            logger.severe("Error occurred while getting cache size. Error: " + e.getMessage());
            return 0; // Or throw a custom exception if necessary
        }
    }

    public void evictEntries() {
        try {
            evictionPolicy.evictEntries(cache);
            updateCacheSizeMetric();
        } catch (Exception e) {
            logger.severe("Error occurred while evicting entries from cache. Error: " + e.getMessage());
        }
    }

    private void enforceEvictionPolicy() {
        // Continue evicting until the cache size is within the max limit
        while (cache.size() > maxCacheSize) {
            logger.info("Cache size exceeds maxCacheSize, performing eviction...");
            evictionPolicy.evictEntries(cache);  // Evict entries
        }
    }

    private void updateCacheSizeMetric() {
        meterRegistry.gauge("cache.size", Tags.of("cache", "inMemoryCache"), cache.size());
    }

    private void registerCacheMetrics() {
        meterRegistry.gauge("cache.size", Tags.of("cache", "inMemoryCache"), cache, ConcurrentMap::size);
    }
}
