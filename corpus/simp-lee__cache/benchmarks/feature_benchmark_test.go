package benchmarks

import (
	"fmt"
	"strings"
	"testing"
	"time"

	cache "github.com/simp-lee/cache"

	"github.com/dgraph-io/ristretto/v2"
	"github.com/maypok86/otter/v2"
)

// BenchmarkFeatureComparisonV2 covers behavior dimensions that are not
// interchangeable across libraries. Sub-benchmark names state visibility,
// capacity, TTL, namespace, and value-size semantics. Ristretto and Otter
// writes are reported separately as submission and drain-inclusive costs.
func BenchmarkFeatureComparisonV2(b *testing.B) {
	initComparisonKeys()
	for _, policy := range []cache.EvictionPolicy{cache.FIFO, cache.LRU} {
		b.Run("ShardedCache/"+policy.String(), func(b *testing.B) {
			b.Run("CapacityTurnover/SyncVisible/Capacity1024/NoTTL/Ungrouped/Value16B", func(b *testing.B) {
				benchmarkShardedDistinctInsert(b, policy, 1024, strings.Repeat("v", 16))
			})
			b.Run("Lookup/SyncVisible/Unbounded/NoTTL/Ungrouped/Value16B", func(b *testing.B) {
				benchmarkShardedLookup(b, policy, 0)
			})
			b.Run("Lookup/SyncVisible/Unbounded/TTL1h/Ungrouped/Value16B", func(b *testing.B) {
				benchmarkShardedLookup(b, policy, time.Hour)
			})
			b.Run("ExpiredLookupCleanup/SyncVisible/Unbounded/TTL1ns/Ungrouped/Value16B", func(b *testing.B) {
				benchmarkShardedExpiredCleanup(b, policy)
			})
			b.Run("Replacement/SyncVisible/Unbounded/NoTTL/CallbackOff/Value16B", func(b *testing.B) {
				benchmarkShardedCallback(b, policy, false)
			})
			b.Run("Replacement/SyncVisible/Unbounded/NoTTL/CallbackOn/Value16B", func(b *testing.B) {
				benchmarkShardedCallback(b, policy, true)
			})
			b.Run("Lookup/SyncVisible/Unbounded/NoTTL/Group/Value16B", func(b *testing.B) {
				benchmarkShardedGroupLookup(b, policy)
			})
			for _, size := range []int{16, 1024, 64 * 1024} {
				b.Run(fmt.Sprintf("NewKeyInsert/SyncVisible/Unbounded/NoTTL/Ungrouped/Value%dB", size), func(b *testing.B) {
					benchmarkShardedDistinctInsert(b, policy, 0, strings.Repeat("v", size))
				})
			}
		})
	}

	b.Run("Ristretto/WriteExisting/Submit/DeferredPolicy/Capacity131072/NoTTL", func(b *testing.B) {
		benchmarkRistrettoDrain(b, false)
	})
	b.Run("Ristretto/WriteExisting/EndToEnd/DeferredPolicy/Capacity131072/NoTTL", func(b *testing.B) {
		benchmarkRistrettoDrain(b, true)
	})
	b.Run("Otter/WriteExisting/Submit/DeferredPolicy/Capacity131072/NoTTL", func(b *testing.B) {
		benchmarkOtterDrain(b, false)
	})
	b.Run("Otter/WriteExisting/EndToEnd/DeferredPolicy/Capacity131072/NoTTL", func(b *testing.B) {
		benchmarkOtterDrain(b, true)
	})
}

func benchmarkShardedDistinctInsert(b *testing.B, policy cache.EvictionPolicy, capacity int, value string) {
	keys := make([]string, b.N)
	for index := range keys {
		keys[index] = fmt.Sprintf("feature-%012d", index)
	}
	options := cache.DefaultOptions()
	options.ShardCount = 1
	options.MaxEntriesPerShard = capacity
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = candidate.Close() })
	if capacity > 0 {
		warmKeys := make([]string, capacity)
		for index := range capacity {
			warmKeys[index] = fmt.Sprintf("warm-%012d", index)
			if err := candidate.Set(warmKeys[index], value); err != nil {
				b.Fatal(err)
			}
		}
		if count := candidate.Count(); count != capacity {
			b.Fatalf("capacity warm-up retained %d entries, want %d", count, capacity)
		}
		for _, key := range warmKeys {
			if _, found := candidate.Get(key); !found {
				b.Fatalf("capacity warm-up missed %q", key)
			}
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := range b.N {
		if err := candidate.Set(keys[index], value); err != nil {
			b.Fatal(err)
		}
	}
}

func benchmarkShardedLookup(b *testing.B, policy cache.EvictionPolicy, ttl time.Duration) {
	options := cache.DefaultOptions()
	options.ShardCount = 32
	options.MaxEntriesPerShard = 0
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = candidate.Close() })
	value := strings.Repeat("v", 16)
	for _, key := range comparisonKeys {
		if err := candidate.SetWithExpiration(key, value, expirationForBenchmark(ttl)); err != nil {
			b.Fatal(err)
		}
	}
	if count := candidate.Count(); count != comparisonKeyCount {
		b.Fatalf("lookup warm-up retained %d entries, want %d", count, comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := candidate.Get(key); !found {
			b.Fatalf("lookup warm-up missed %q", key)
		}
	}
	benchmarkGets(b, func(key string) bool {
		_, found := candidate.Get(key)
		return found
	}, comparisonKeys[:])
}

func benchmarkShardedExpiredCleanup(b *testing.B, policy cache.EvictionPolicy) {
	keys := make([]string, b.N)
	for index := range keys {
		keys[index] = fmt.Sprintf("expired-%012d", index)
	}
	options := cache.DefaultOptions()
	options.ShardCount = 1
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = candidate.Close() })
	value := strings.Repeat("v", 16)
	b.ReportAllocs()
	b.ResetTimer()
	for _, key := range keys {
		if err := candidate.SetWithExpiration(key, value, time.Nanosecond); err != nil {
			b.Fatal(err)
		}
		for {
			if _, found := candidate.Get(key); !found {
				break
			}
		}
	}
}

func benchmarkShardedCallback(b *testing.B, policy cache.EvictionPolicy, enabled bool) {
	options := cache.DefaultOptions()
	options.ShardCount = 32
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = candidate.Close() })
	value := strings.Repeat("v", 16)
	for _, key := range comparisonKeys {
		if err := candidate.Set(key, value); err != nil {
			b.Fatal(err)
		}
	}
	if count := candidate.Count(); count != comparisonKeyCount {
		b.Fatalf("callback warm-up retained %d entries, want %d", count, comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := candidate.Get(key); !found {
			b.Fatalf("callback warm-up missed %q", key)
		}
	}
	if enabled {
		if err := candidate.OnEvicted(func(cache.EntryKey, any, cache.EvictionReason) {}); err != nil {
			b.Fatal(err)
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := range b.N {
		if err := candidate.Set(comparisonKeys[index&(comparisonKeyCount-1)], value); err != nil {
			b.Fatal(err)
		}
	}
}

func benchmarkShardedGroupLookup(b *testing.B, policy cache.EvictionPolicy) {
	options := cache.DefaultOptions()
	options.ShardCount = 32
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = candidate.Close() })
	group, err := candidate.Group("feature")
	if err != nil {
		b.Fatal(err)
	}
	value := strings.Repeat("v", 16)
	for _, key := range comparisonKeys {
		if err := group.Set(key, value); err != nil {
			b.Fatal(err)
		}
	}
	if count := group.Count(); count != comparisonKeyCount || candidate.Count() != comparisonKeyCount {
		b.Fatalf("group warm-up counts = %d/%d, want %d", count, candidate.Count(), comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := group.Get(key); !found {
			b.Fatalf("group warm-up missed %q", key)
		}
	}
	benchmarkGets(b, func(key string) bool {
		_, found := group.Get(key)
		return found
	}, comparisonKeys[:])
}

func benchmarkRistrettoDrain(b *testing.B, drain bool) {
	candidate, err := ristretto.NewCache(&ristretto.Config[string, string]{
		NumCounters:        comparisonKeyCount * 10,
		MaxCost:            comparisonKeyCount * 2,
		BufferItems:        64,
		IgnoreInternalCost: true,
	})
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(candidate.Close)
	for _, key := range comparisonKeys {
		for !candidate.Set(key, "value", 1) {
			candidate.Wait()
		}
	}
	candidate.Wait()
	count := 0
	candidate.IterValues(func(string) bool {
		count++
		return false
	})
	if count != comparisonKeyCount {
		b.Fatalf("Ristretto warm-up retained %d entries, want %d", count, comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := candidate.Get(key); !found {
			b.Fatalf("Ristretto warm-up missed %q", key)
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := range b.N {
		if !candidate.Set(comparisonKeys[index&(comparisonKeyCount-1)], "value", 1) {
			b.Fatal("Ristretto rejected an existing-key submission")
		}
	}
	if drain {
		candidate.Wait()
	}
}

func benchmarkOtterDrain(b *testing.B, drain bool) {
	candidate, err := otter.New(&otter.Options[string, string]{
		MaximumSize:     comparisonKeyCount * 2,
		InitialCapacity: comparisonKeyCount,
	})
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { candidate.StopAllGoroutines() })
	for _, key := range comparisonKeys {
		candidate.Set(key, "value")
	}
	candidate.CleanUp()
	if count := candidate.EstimatedSize(); count != comparisonKeyCount {
		b.Fatalf("Otter warm-up retained %d entries, want %d", count, comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := candidate.GetIfPresent(key); !found {
			b.Fatalf("Otter warm-up missed %q", key)
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := range b.N {
		candidate.Set(comparisonKeys[index&(comparisonKeyCount-1)], "value")
	}
	if drain {
		candidate.CleanUp()
	}
}
