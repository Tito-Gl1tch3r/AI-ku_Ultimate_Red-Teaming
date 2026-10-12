package com.github.chandrakanthrck.cache_project.metrics;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

@Component
public class CacheMetrics {
    private final Counter hitCounter;
    private final Counter missCounter;
    private final Counter evictionCounter;

    public CacheMetrics(MeterRegistry meterRegistry) {
        this.hitCounter = meterRegistry.counter("cache.hit", "type", "cache");
        this.missCounter = meterRegistry.counter("cache.miss", "type", "cache");
        this.evictionCounter = meterRegistry.counter("cache.eviction", "type", "cache");
    }

    public void recordHit() {
        hitCounter.increment();
    }

    public void recordMiss() {
        missCounter.increment();
    }

    public void recordEviction() {
        evictionCounter.increment();
    }

    public double getHitCount() {
        return hitCounter.count();
    }

    public double getMissCount() {
        return missCounter.count();
    }

    public double getEvictionCount() {
        return evictionCounter.count();
    }

    public double getHitRate() {
        double totalRequests = hitCounter.count() + missCounter.count();
        return totalRequests == 0 ? 0 : hitCounter.count() / totalRequests;
    }

    public double getMissRate() {
        double totalRequests = hitCounter.count() + missCounter.count();
        return totalRequests == 0 ? 0 : missCounter.count() / totalRequests;
    }
}
