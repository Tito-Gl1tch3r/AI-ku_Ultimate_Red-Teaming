package com.github.chandrakanthrck.cache_project.controller;

import com.github.chandrakanthrck.cache_project.service.SynchronizedCacheService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
@RequestMapping("/cache")
public class CacheController {

    private static final Logger logger = LoggerFactory.getLogger(CacheController.class);
    private final SynchronizedCacheService cacheService;

    @Autowired
    public CacheController(SynchronizedCacheService cacheService) {
        this.cacheService = cacheService;
    }

    @PostMapping("/put")
    public ResponseEntity<String> put(@RequestParam String key, @RequestParam String value) {
        try {
            cacheService.put(key, value);
            return new ResponseEntity<>("Cached " + key, HttpStatus.CREATED);
        } catch (Exception e) {
            logger.error("Error caching key: {}. Error: {}", key, e.getMessage());
            return new ResponseEntity<>("Error caching key: " + key, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/get")
    public ResponseEntity<Object> get(@RequestParam String key) {
        try {
            String value = cacheService.get(key);
            if (value != null) {
                return new ResponseEntity<>(value, HttpStatus.OK);
            } else {
                return new ResponseEntity<>("Key not found", HttpStatus.NOT_FOUND);
            }
        } catch (Exception e) {
            logger.error("Error retrieving key: {}. Error: {}", key, e.getMessage());
            return new ResponseEntity<>("Error retrieving key: " + key, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @DeleteMapping("/remove")
    public ResponseEntity<String> remove(@RequestParam String key) {
        try {
            cacheService.remove(key);
            return new ResponseEntity<>("Removed " + key, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error removing key: {}. Error: {}", key, e.getMessage());
            return new ResponseEntity<>("Error removing key: " + key, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @DeleteMapping("/clear")
    public ResponseEntity<String> clear() {
        try {
            cacheService.clear();
            return new ResponseEntity<>("Cache cleared", HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error clearing cache. Error: {}", e.getMessage());
            return new ResponseEntity<>("Error clearing cache", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/size")
    public ResponseEntity<Integer> totalSize() {
        try {
            int size = cacheService.size();
            return new ResponseEntity<>(size, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error getting total cache size. Error: {}", e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/size/in-memory")
    public ResponseEntity<Integer> inMemorySize() {
        try {
            int inMemorySize = cacheService.getInMemoryCacheSize();
            return new ResponseEntity<>(inMemorySize, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error getting in-memory cache size. Error: {}", e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/size/persistent")
    public ResponseEntity<Integer> persistentSize() {
        try {
            int persistentSize = cacheService.getPersistentCacheSize();
            return new ResponseEntity<>(persistentSize, HttpStatus.OK);
        } catch (Exception e) {
            logger.error("Error getting persistent cache size. Error: {}", e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
