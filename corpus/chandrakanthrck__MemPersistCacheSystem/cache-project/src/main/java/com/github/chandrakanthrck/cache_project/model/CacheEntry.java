package com.github.chandrakanthrck.cache_project.model;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "cache_entry")  // This ensures the entity maps to the cache_entry table
public class CacheEntry {

    @Id
    private String cacheKey;  // Use 'cacheKey' instead of 'key' to avoid reserved keyword conflicts in SQL

    private String cacheValue;

    // Constructors
    public CacheEntry() {
    }

    public CacheEntry(String cacheKey, String cacheValue) {
        this.cacheKey = cacheKey;
        this.cacheValue = cacheValue;
    }

    // Getters and Setters
    public String getCacheKey() {
        return cacheKey;
    }

    public void setCacheKey(String cacheKey) {
        this.cacheKey = cacheKey;
    }

    public String getCacheValue() {
        return cacheValue;
    }

    public void setCacheValue(String cacheValue) {
        this.cacheValue = cacheValue;
    }
}
