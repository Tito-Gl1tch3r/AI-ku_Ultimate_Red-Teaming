package shardedcache

import (
	"context"
	"time"
)

// Group is a structured namespace handle. Group names and keys are never
// encoded into one string, so every non-empty group remains isolated from the
// ungrouped namespace and every other group.
type Group struct {
	cache *ShardedCache
	name  string
}

func (g Group) entry(key string) EntryKey { return EntryKey{Group: g.name, Key: key} }

// Set stores a value using the cache default expiration.
func (g Group) Set(key string, value any) error {
	return g.cache.setEntry(g.entry(key), value, DefaultExpiration)
}

// SetWithExpiration stores a value with an explicit expiration rule.
func (g Group) SetWithExpiration(key string, value any, expiration time.Duration) error {
	return g.cache.setEntry(g.entry(key), value, expiration)
}

// Get retrieves a live value.
func (g Group) Get(key string) (any, bool) { return g.cache.getEntry(g.entry(key)) }

// GetWithExpiration retrieves a live value and its absolute expiration time.
func (g Group) GetWithExpiration(key string) (any, time.Time, bool) {
	return g.cache.getEntryWithExpiration(g.entry(key))
}

// Has reports whether a live value exists.
func (g Group) Has(key string) bool { return g.cache.hasEntry(g.entry(key)) }

// Touch changes the TTL without changing policy order.
func (g Group) Touch(key string, expiration time.Duration) (bool, error) {
	return g.cache.touchEntry(g.entry(key), expiration)
}

// Persist removes expiration without changing policy order.
func (g Group) Persist(key string) (bool, error) {
	return g.cache.touchEntry(g.entry(key), NoExpiration)
}

// Delete removes a live value. An expired value is reported as not found.
func (g Group) Delete(key string) (bool, error) { return g.cache.deleteEntry(g.entry(key)) }

// DeleteKeys removes the named live values.
func (g Group) DeleteKeys(keys []string) (int, error) {
	entries := make([]EntryKey, len(keys))
	for i, key := range keys {
		entries[i] = g.entry(key)
	}
	return g.cache.deleteEntries(entries)
}

// DeletePrefix removes live values whose raw group key has prefix.
func (g Group) DeletePrefix(prefix string) (int, error) {
	return g.cache.deletePrefix(g.name, prefix)
}

// GetOrSet returns an existing live value or stores value.
func (g Group) GetOrSet(key string, value any) (any, error) {
	return g.cache.getOrSetEntry(g.entry(key), value)
}

// GetOrSetFunc loads a missing value using the cache default expiration.
func (g Group) GetOrSetFunc(ctx context.Context, key string, loader LoaderFunc) (any, error) {
	return g.cache.getOrSetFuncEntry(ctx, g.entry(key), loader, DefaultExpiration)
}

// GetOrSetFuncWithExpiration loads a missing value with an explicit expiration rule.
func (g Group) GetOrSetFuncWithExpiration(ctx context.Context, key string, loader LoaderFunc, expiration time.Duration) (any, error) {
	return g.cache.getOrSetFuncEntry(ctx, g.entry(key), loader, expiration)
}

// Count returns the exact number of live values in this group.
func (g Group) Count() int { return g.cache.countGroup(g.name) }

// Range visits a weakly consistent snapshot one shard at a time. The visitor
// runs without cache locks; returning false stops the whole traversal.
func (g Group) Range(visitor func(key string, value any, expiresAt time.Time) bool) {
	g.cache.rangeGroup(g.name, visitor)
}

// Clear removes every value in this group.
func (g Group) Clear() error { return g.cache.clearGroup(g.name) }
