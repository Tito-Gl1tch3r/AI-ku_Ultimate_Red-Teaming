package com.github.chandrakanthrck.cache_project.service;

import com.github.chandrakanthrck.cache_project.metrics.CacheMetrics;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;
import jakarta.transaction.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class SynchronizedCacheService {

    private static final Logger logger = LoggerFactory.getLogger(SynchronizedCacheService.class);

    private final InMemoryCacheService<String, String> inMemoryCacheService;
    private final PersistentCacheService persistentCacheService; // Added generics for type safety
    private final CacheMetrics cacheMetrics;
    private final MeterRegistry meterRegistry;

    public SynchronizedCacheService(InMemoryCacheService<String, String> inMemoryCacheService,
                                    PersistentCacheService persistentCacheService,
                                    CacheMetrics cacheMetrics,
                                    MeterRegistry meterRegistry) {
        this.inMemoryCacheService = inMemoryCacheService;
        this.persistentCacheService = persistentCacheService;
        this.cacheMetrics = cacheMetrics;
        this.meterRegistry = meterRegistry;
        registerMetrics();  // Register cache synchronization-related metrics
    }

    public void put(String key, String value) {
        try {
            logger.info("Putting key: {} into in-memory cache.", key);
            inMemoryCacheService.put(key, value);
            syncToPersistentStore(key, value);  // Async sync to persistent store
            cacheMetrics.recordHit();
            meterRegistry.counter("cache.put", Tags.of("cache", "synchronized")).increment();
        } catch (Exception e) {
            logger.error("Error while putting key: {}. Error: {}", key, e.getMessage());
            // Optionally, handle the error (e.g., alerting, fallback logic)
        }
    }

    public String get(String key) {
        try {
            logger.info("Getting key: {} from in-memory cache.", key);
            String value = inMemoryCacheService.get(key);
            if (value == null) {
                logger.info("Cache miss for key: {}. Fetching from persistent store.", key);
                value = persistentCacheService.get(key);
                if (value != null) {
                    logger.info("Putting key: {} into in-memory cache after fetch from persistent store.", key);
                    inMemoryCacheService.put(key, value);
                }
                cacheMetrics.recordMiss();
                meterRegistry.counter("cache.miss", Tags.of("cache", "synchronized")).increment();
            } else {
                logger.info("Cache hit for key: {}.", key);
                cacheMetrics.recordHit();
            }
            return value;
        } catch (Exception e) {
            logger.error("Error while getting key: {}. Error: {}", key, e.getMessage());
            return null; // Or throw a custom exception if necessary
        }
    }

    public void remove(String key) {
        try {
            logger.info("Removing key: {} from both in-memory and persistent caches.", key);
            inMemoryCacheService.remove(key);
            persistentCacheService.remove(key);
            meterRegistry.counter("cache.remove", Tags.of("cache", "synchronized")).increment();
        } catch (Exception e) {
            logger.error("Error while removing key: {}. Error: {}", key, e.getMessage());
        }
    }

    public void clear() {
        try {
            logger.info("Clearing all entries from both in-memory and persistent caches.");
            inMemoryCacheService.clear();
            persistentCacheService.clear();
            meterRegistry.counter("cache.clear", Tags.of("cache", "synchronized")).increment();
        } catch (Exception e) {
            logger.error("Error while clearing caches. Error: {}", e.getMessage());
        }
    }

    @Async
    @Transactional
    public void syncToPersistentStore(String key, String value) {
        logger.info("Synchronizing key: {} to persistent store.", key);
        int retryCount = 3;  // Number of retries
        while (retryCount > 0) {
            try {
                persistentCacheService.put(key, value);
                meterRegistry.counter("cache.sync", Tags.of("cache", "synchronized")).increment();
                logger.info("Successfully synchronized key: {} to persistent store.", key);
                return;  // Exit if successful
            } catch (Exception e) {
                retryCount--;
                logger.error("Failed to synchronize key: {} to persistent store. Error: {}. Retries left: {}", key, e.getMessage(), retryCount);
                meterRegistry.counter("cache.sync.failure", Tags.of("cache", "synchronized")).increment();
                // Optionally, add a delay before retrying
                try {
                    Thread.sleep(1000);  // Delay for 1 second before retrying
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();  // Restore interrupted state
                }
            }
        }
        logger.warn("All retries exhausted for key: {}. Could not synchronize to persistent store.", key);
    }

    public CacheMetrics getMetrics() {
        return cacheMetrics;
    }

    public int size() {
        try {
            int totalSize = inMemoryCacheService.size() + persistentCacheService.size();
            logger.info("Total cache size: {}", totalSize);
            meterRegistry.gauge("cache.size.total", Tags.of("cache", "synchronized"), totalSize);
            return totalSize;
        } catch (Exception e) {
            logger.error("Error while getting total cache size. Error: {}", e.getMessage());
            return 0; // Or throw a custom exception if necessary
        }
    }

    public int getInMemoryCacheSize() {
        try {
            int inMemorySize = inMemoryCacheService.size();
            logger.info("In-memory cache size: {}", inMemorySize);
            meterRegistry.gauge("cache.size.memory", Tags.of("cache", "synchronized"), inMemorySize);
            return inMemorySize;
        } catch (Exception e) {
            logger.error("Error while getting in-memory cache size. Error: {}", e.getMessage());
            return 0; // Or throw a custom exception if necessary
        }
    }

    public int getPersistentCacheSize() {
        try {
            int persistentSize = persistentCacheService.size();
            logger.info("Persistent cache size: {}", persistentSize);
            meterRegistry.gauge("cache.size.persistent", Tags.of("cache", "synchronized"), persistentSize);
            return persistentSize;
        } catch (Exception e) {
            logger.error("Error while getting persistent cache size. Error: {}", e.getMessage());
            return 0; // Or throw a custom exception if necessary
        }
    }

    private void registerMetrics() {
        meterRegistry.gauge("cache.size.memory", Tags.of("cache", "synchronized"), this, SynchronizedCacheService::getInMemoryCacheSize);
        meterRegistry.gauge("cache.size.persistent", Tags.of("cache", "synchronized"), this, SynchronizedCacheService::getPersistentCacheSize);
        meterRegistry.gauge("cache.size.total", Tags.of("cache", "synchronized"), this, SynchronizedCacheService::size);
    }
}