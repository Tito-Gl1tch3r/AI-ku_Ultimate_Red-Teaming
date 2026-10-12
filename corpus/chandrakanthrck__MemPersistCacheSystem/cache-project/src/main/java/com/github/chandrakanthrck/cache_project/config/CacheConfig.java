package com.github.chandrakanthrck.cache_project.config;

import com.github.chandrakanthrck.cache_project.factory.EvictionPolicyFactory;
import com.github.chandrakanthrck.cache_project.service.InMemoryCacheService;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.logging.Logger;

@Configuration
public class CacheConfig {

    private static final Logger logger = Logger.getLogger(CacheConfig.class.getName());

    @Value("${cache.max.size:100}")  // Default max cache size is 100, can be customized
    private int maxCacheSize;

    @Value("${cache.eviction.policy:LRU}")  // Default eviction policy is LRU, can be configured
    private String evictionPolicyType;

    @Bean
    public EvictionPolicyFactory<String, String> evictionPolicyFactory() {
        logger.info("Creating EvictionPolicyFactory bean");
        return new EvictionPolicyFactory<>();
    }

    @Bean
    public InMemoryCacheService<String, String> inMemoryCacheService(
            EvictionPolicyFactory<String, String> evictionPolicyFactory,
            MeterRegistry meterRegistry) {

        EvictionPolicyFactory.EvictionType evictionType;
        try {
            evictionType = EvictionPolicyFactory.EvictionType.valueOf(evictionPolicyType.toUpperCase());
        } catch (IllegalArgumentException e) {
            logger.severe("Invalid eviction policy type: " + evictionPolicyType);
            throw e; // Rethrow or handle as needed
        }

        logger.info("Configuring InMemoryCacheService with eviction policy: " + evictionType + " and max cache size: " + maxCacheSize);

        return new InMemoryCacheService<>(
                evictionPolicyFactory.getEvictionPolicy(evictionType, maxCacheSize, 10000L, false, meterRegistry),
                meterRegistry,
                maxCacheSize
        );
    }
}
