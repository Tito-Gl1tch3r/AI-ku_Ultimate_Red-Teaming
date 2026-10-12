package com.github.chandrakanthrck.cache_project.controller;

import com.github.chandrakanthrck.cache_project.metrics.CacheMetrics;
import com.github.chandrakanthrck.cache_project.service.SynchronizedCacheService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
@RequestMapping("/cache/metrics")
public class CacheMetricsController {

    private static final Logger logger = LoggerFactory.getLogger(CacheMetricsController.class);
    private final SynchronizedCacheService cacheService; // Use the generic version

    @Autowired
    public CacheMetricsController(SynchronizedCacheService cacheService) {
        this.cacheService = cacheService;
    }

    @GetMapping
    public ResponseEntity<CacheMetrics> getCacheMetrics() {
        try {
            CacheMetrics metrics = cacheService.getMetrics();
            logger.info("Metrics retrieved successfully.");
            return new ResponseEntity<>(metrics, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error retrieving cache metrics: {}", e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
