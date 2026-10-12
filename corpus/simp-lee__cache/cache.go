// Package shardedcache provides a concurrent sharded in-memory cache with
// structured namespaces, FIFO or LRU eviction, expiration, and optional
// recoverable snapshot persistence.
package shardedcache

import (
	"context"
	"errors"
	"fmt"
	"math"
	"time"
)

const (
	// NoExpiration makes an entry persistent in memory.
	NoExpiration time.Duration = -1
	// DefaultExpiration applies Options.DefaultExpiration to an entry.
	DefaultExpiration time.Duration = 0

	maxShardCount = 1 << 16
)

var (
	// ErrCacheClosed is returned by mutations, loaders, and Flush after Close starts.
	ErrCacheClosed = errors.New("cache is closed")
	// ErrPersistenceDisabled is returned by Flush when persistence is disabled.
	ErrPersistenceDisabled = errors.New("cache persistence is disabled")
	// ErrEmptyGroup is returned when a group name is empty.
	ErrEmptyGroup = errors.New("cache group name is empty")
	// ErrUnsupportedFormat reports a recognized persistence format that this version cannot read.
	ErrUnsupportedFormat = errors.New("unsupported cache persistence format")
	// ErrPersistenceLocked reports that another active cache owns the persistence directory.
	ErrPersistenceLocked = errors.New("cache persistence directory is locked")
)

// LoaderFunc computes a value for a missing key. It is called outside cache locks.
type LoaderFunc func(context.Context) (any, error)

// EntryKey is the public, structured identity of an entry. An empty Group means
// the ungrouped cache namespace.
type EntryKey struct {
	Group string
	Key   string
}

// EvictionReason identifies why an entry was removed.
type EvictionReason uint8

const (
	EvictionReasonDeleted EvictionReason = iota + 1
	EvictionReasonReplaced
	EvictionReasonExpired
	EvictionReasonCapacity
	EvictionReasonCleared
)

// EvictionPolicy controls the per-shard capacity order.
type EvictionPolicy uint8

const (
	// FIFO evicts the entry with the oldest write or replacement.
	FIFO EvictionPolicy = iota + 1
	// LRU evicts the least recently used entry.
	LRU
)

func (p EvictionPolicy) String() string {
	switch p {
	case FIFO:
		return "FIFO"
	case LRU:
		return "LRU"
	default:
		return fmt.Sprintf("EvictionPolicy(%d)", p)
	}
}

// PersistenceOptions enables manifest-based snapshot persistence when non-nil.
type PersistenceOptions struct {
	Path      string
	Interval  time.Duration
	Threshold int
}

// Options configures a cache. Options are strict: use DefaultOptions and
// modify it rather than relying on zero-value coercion.
type Options struct {
	// ShardCount must be a positive power of two no greater than 65,536.
	ShardCount         int
	MaxEntriesPerShard int
	DefaultExpiration  time.Duration
	CleanupEnabled     bool
	EvictionPolicy     EvictionPolicy
	Persistence        *PersistenceOptions
}

// DefaultOptions returns the documented default cache configuration.
func DefaultOptions() Options {
	return Options{
		ShardCount:         32,
		MaxEntriesPerShard: 0,
		DefaultExpiration:  0,
		CleanupEnabled:     true,
		EvictionPolicy:     FIFO,
		Persistence:        nil,
	}
}

// Validate checks every option without applying defaults.
func (o Options) Validate() error {
	if o.ShardCount <= 0 {
		return fmt.Errorf("ShardCount must be positive: %d", o.ShardCount)
	}
	if o.ShardCount&(o.ShardCount-1) != 0 {
		return fmt.Errorf("ShardCount must be a power of two: %d", o.ShardCount)
	}
	if o.ShardCount > maxShardCount {
		return fmt.Errorf("ShardCount must not exceed %d: %d", maxShardCount, o.ShardCount)
	}
	if o.MaxEntriesPerShard < 0 {
		return fmt.Errorf("MaxEntriesPerShard must not be negative: %d", o.MaxEntriesPerShard)
	}
	if o.DefaultExpiration < 0 {
		return fmt.Errorf("DefaultExpiration must not be negative: %s", o.DefaultExpiration)
	}
	if o.EvictionPolicy != FIFO && o.EvictionPolicy != LRU {
		return fmt.Errorf("EvictionPolicy is unknown: %d", o.EvictionPolicy)
	}
	if o.MaxEntriesPerShard > 0 && o.ShardCount > math.MaxInt/o.MaxEntriesPerShard {
		return fmt.Errorf("MaxEntriesPerShard * ShardCount overflows int")
	}
	if o.Persistence != nil {
		if o.Persistence.Path == "" {
			return errors.New("Persistence.Path is required")
		}
		if o.Persistence.Interval < 0 {
			return fmt.Errorf("Persistence.Interval must not be negative: %s", o.Persistence.Interval)
		}
		if o.Persistence.Threshold < 0 {
			return fmt.Errorf("Persistence.Threshold must not be negative: %d", o.Persistence.Threshold)
		}
	}
	return nil
}

func validateExpiration(expiration time.Duration) error {
	if expiration == DefaultExpiration || expiration == NoExpiration || expiration > 0 {
		return nil
	}
	return fmt.Errorf("expiration must be DefaultExpiration (0), NoExpiration (-1), or positive: %s", expiration)
}

// PersistenceStatus describes the current persistence state.
type PersistenceStatus struct {
	Enabled     bool
	DirtyShards int
	LastSuccess time.Time
	LastError   error
}

// Stats is a strongly typed cache statistics snapshot.
type Stats struct {
	TotalCount          int
	Hits                uint64
	Misses              uint64
	HitRate             float64
	MaxEntriesPerShard  int
	EffectiveMaxEntries int
	DefaultExpiration   time.Duration
	ShardCount          int
	EvictionPolicy      EvictionPolicy
	PersistenceStatus   PersistenceStatus
	Closed              bool
}

// GetTyped returns the cache value when it has the requested type.
func GetTyped[T any](c *ShardedCache, key string) (T, bool) {
	var zero T
	value, found := c.Get(key)
	if !found {
		return zero, false
	}
	typed, ok := value.(T)
	if !ok {
		return zero, false
	}
	return typed, true
}
