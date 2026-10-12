package benchmarks

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	cache "github.com/simp-lee/cache"

	"github.com/allegro/bigcache/v3"
	"github.com/dgraph-io/ristretto/v2"
	"github.com/maypok86/otter/v2"
	gocache "github.com/patrickmn/go-cache"
)

const comparisonKeyCount = 1 << 16

var (
	comparisonKeys     [comparisonKeyCount]string
	comparisonMissKeys [comparisonKeyCount]string
	comparisonKeysOnce sync.Once
)

type benchmarkCache struct {
	get func(string) bool
	set func(string)
}

func initComparisonKeys() {
	comparisonKeysOnce.Do(func() {
		for i := range comparisonKeyCount {
			comparisonKeys[i] = fmt.Sprintf("key-%d", i)
			comparisonMissKeys[i] = fmt.Sprintf("missing-%d", i)
		}
	})
}

// BenchmarkCacheComparisonV2 compares steady-state mapping API operations.
// Keys are prepared outside timed sections so formatting and random-number locks
// do not dominate cache costs. BigCache necessarily stores []byte while the
// other implementations store a string. Ristretto and Otter defer policy work.
func BenchmarkCacheComparisonV2(b *testing.B) {
	requireCanonicalHost(b, 8)
	initComparisonKeys()

	factories := []struct {
		name   string
		new    func(*testing.B) benchmarkCache
		newSet func(*testing.B) benchmarkCache
	}{
		{name: "ShardedCache/FIFO", new: newShardedBenchmarkCache},
		{name: "ShardedCache/LRU", new: newShardedLRUBenchmarkCache},
		{name: "GoCache", new: newGoCacheBenchmarkCache},
		{name: "BigCache", new: newBigCacheBenchmarkCache, newSet: newBigCacheReplacementBenchmarkCache},
		{name: "Ristretto", new: newRistrettoBenchmarkCache},
		{name: "Otter", new: newOtterBenchmarkCache},
		{name: "SyncMap", new: newSyncMapBenchmarkCache},
	}

	for _, factory := range factories {
		b.Run(factory.name, func(b *testing.B) {
			b.Run("GetHit", func(b *testing.B) {
				cache := factory.new(b)
				benchmarkGets(b, cache.get, comparisonKeys[:])
			})
			b.Run("GetMiss", func(b *testing.B) {
				cache := factory.new(b)
				benchmarkGets(b, cache.get, comparisonMissKeys[:])
			})
			b.Run("SetExisting", func(b *testing.B) {
				constructor := factory.new
				if factory.newSet != nil {
					constructor = factory.newSet
				}
				cache := constructor(b)
				benchmarkSets(b, cache.set)
				b.StopTimer()
				verifyBenchmarkCacheResident(b, factory.name, cache)
			})
			b.Run("Mixed80Get20Set", func(b *testing.B) {
				cache := factory.new(b)
				benchmarkMixed(b, cache)
			})
		})
	}
}

// BenchmarkTTLUpdateComparisonV2 compares existing-key updates with a fixed
// one-hour TTL. sync.Map is intentionally excluded because it has no TTL API.
func BenchmarkTTLUpdateComparisonV2(b *testing.B) {
	requireCanonicalHost(b, 8)
	initComparisonKeys()
	factories := []struct {
		name string
		new  func(*testing.B) benchmarkCache
	}{
		{name: "ShardedCache/FIFO", new: newShardedTTLBenchmarkCache},
		{name: "ShardedCache/LRU", new: newShardedLRUTTLBenchmarkCache},
		{name: "GoCache", new: newGoCacheTTLBenchmarkCache},
		{name: "Ristretto", new: newRistrettoTTLBenchmarkCache},
		{name: "Otter", new: newOtterTTLBenchmarkCache},
	}
	for _, factory := range factories {
		b.Run(factory.name, func(b *testing.B) {
			cache := factory.new(b)
			benchmarkSets(b, cache.set)
		})
	}
}

// BenchmarkShardedScaling reports the canonical operations across CPU and
// shard-count matrices. Run it with -cpu=1,4,8. Every configuration retains
// the same 131,072-entry effective capacity and verifies all warm-up hits.
func BenchmarkShardedScaling(b *testing.B) {
	requireCanonicalHost(b, 0)
	initComparisonKeys()
	for _, policy := range []cache.EvictionPolicy{cache.FIFO, cache.LRU} {
		for _, shards := range []int{1, 8, 32, 128} {
			name := fmt.Sprintf("%s/Shards%d", policy, shards)
			b.Run(name, func(b *testing.B) {
				b.Run("GetHit", func(b *testing.B) {
					candidate := newShardedBenchmarkCacheConfigured(b, 0, policy, shards)
					benchmarkGets(b, candidate.get, comparisonKeys[:])
				})
				b.Run("GetMiss", func(b *testing.B) {
					candidate := newShardedBenchmarkCacheConfigured(b, 0, policy, shards)
					benchmarkGets(b, candidate.get, comparisonMissKeys[:])
				})
				b.Run("SetExisting", func(b *testing.B) {
					candidate := newShardedBenchmarkCacheConfigured(b, 0, policy, shards)
					benchmarkSets(b, candidate.set)
				})
				b.Run("Mixed80Get20Set", func(b *testing.B) {
					candidate := newShardedBenchmarkCacheConfigured(b, 0, policy, shards)
					benchmarkMixed(b, candidate)
				})
				b.Run("TTLUpdate1h", func(b *testing.B) {
					candidate := newShardedBenchmarkCacheConfigured(b, time.Hour, policy, shards)
					benchmarkSets(b, candidate.set)
				})
			})
		}
	}
}

// BenchmarkCapacityTurnoverV2 measures insertion while a bounded shard is
// continuously full. It exposes the difference between linear eviction scans
// and the current O(1) FIFO queue.
func BenchmarkCapacityTurnoverV2(b *testing.B) {
	initComparisonKeys()
	const capacity = 1024
	options := cache.DefaultOptions()
	options.ShardCount = 1
	options.MaxEntriesPerShard = capacity
	options.CleanupEnabled = false
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	defer candidate.Close()
	for i := range capacity {
		_ = candidate.Set(comparisonKeys[i], "value")
	}

	b.ReportAllocs()
	b.ResetTimer()
	for i := range b.N {
		_ = candidate.Set(comparisonKeys[(i+capacity)&(comparisonKeyCount-1)], "value")
	}
}

// BenchmarkBigCacheCapacityTurnoverV2 measures replacement attempts after
// BigCache's append-only byte queues have reached their configured hard limit.
// Missing keys are expected here and reported as the final resident percentage.
func BenchmarkBigCacheCapacityTurnoverV2(b *testing.B) {
	initComparisonKeys()
	candidate := newBigCacheTurnoverBenchmarkCache(b)
	benchmarkSets(b, candidate.set)
	b.StopTimer()

	resident := 0
	for _, key := range comparisonKeys {
		if candidate.get(key) {
			resident++
		}
	}
	b.ReportMetric(float64(resident)*100/comparisonKeyCount, "resident%")
}

func newShardedBenchmarkCache(b *testing.B) benchmarkCache {
	return newShardedBenchmarkCacheWithTTL(b, 0, cache.FIFO)
}

func newShardedLRUBenchmarkCache(b *testing.B) benchmarkCache {
	return newShardedBenchmarkCacheWithTTL(b, 0, cache.LRU)
}

func newShardedTTLBenchmarkCache(b *testing.B) benchmarkCache {
	return newShardedBenchmarkCacheWithTTL(b, time.Hour, cache.FIFO)
}

func newShardedLRUTTLBenchmarkCache(b *testing.B) benchmarkCache {
	return newShardedBenchmarkCacheWithTTL(b, time.Hour, cache.LRU)
}

func newShardedBenchmarkCacheWithTTL(b *testing.B, ttl time.Duration, policy cache.EvictionPolicy) benchmarkCache {
	return newShardedBenchmarkCacheConfigured(b, ttl, policy, 32)
}

func newShardedBenchmarkCacheConfigured(b *testing.B, ttl time.Duration, policy cache.EvictionPolicy, shards int) benchmarkCache {
	options := cache.DefaultOptions()
	options.ShardCount = shards
	options.MaxEntriesPerShard = comparisonKeyCount * 2 / shards
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		b.Fatal(err)
	}
	for _, key := range comparisonKeys {
		if err := candidate.SetWithExpiration(key, "value", expirationForBenchmark(ttl)); err != nil {
			b.Fatal(err)
		}
	}
	if count := candidate.Count(); count != comparisonKeyCount {
		b.Fatalf("ShardedCache warm-up retained %d entries, want %d", count, comparisonKeyCount)
	}
	for _, key := range comparisonKeys {
		if _, found := candidate.Get(key); !found {
			b.Fatalf("ShardedCache warm-up did not retain %q", key)
		}
	}
	b.Cleanup(func() { _ = candidate.Close() })
	return benchmarkCache{
		get: func(key string) bool {
			_, ok := candidate.Get(key)
			return ok
		},
		set: func(key string) {
			if err := candidate.SetWithExpiration(key, "value", expirationForBenchmark(ttl)); err != nil {
				panic(err)
			}
		},
	}
}

func newGoCacheBenchmarkCache(b *testing.B) benchmarkCache {
	return newGoCacheBenchmarkCacheWithTTL(b, gocache.NoExpiration)
}

func newGoCacheTTLBenchmarkCache(b *testing.B) benchmarkCache {
	return newGoCacheBenchmarkCacheWithTTL(b, time.Hour)
}

func newGoCacheBenchmarkCacheWithTTL(_ *testing.B, ttl time.Duration) benchmarkCache {
	cache := gocache.New(gocache.NoExpiration, 0)
	for _, key := range comparisonKeys {
		cache.Set(key, "value", ttl)
	}
	return benchmarkCache{
		get: func(key string) bool {
			_, ok := cache.Get(key)
			return ok
		},
		set: func(key string) {
			cache.Set(key, "value", ttl)
		},
	}
}

func newBigCacheBenchmarkCache(b *testing.B) benchmarkCache {
	return newBigCacheBenchmarkCacheConfigured(b, 64, false)
}

func newBigCacheReplacementBenchmarkCache(b *testing.B) benchmarkCache {
	// BigCache appends replacements to its byte queues. Leave the hard maximum
	// unlimited so timed existing-key writes cannot evict the working set.
	return newBigCacheBenchmarkCacheConfigured(b, 0, false)
}

func newBigCacheTurnoverBenchmarkCache(b *testing.B) benchmarkCache {
	return newBigCacheBenchmarkCacheConfigured(b, 8, true)
}

func newBigCacheBenchmarkCacheConfigured(b *testing.B, hardMaxMiB int, primeTurnover bool) benchmarkCache {
	config := bigcache.DefaultConfig(time.Hour)
	config.Shards = 32
	config.CleanWindow = 0
	config.MaxEntriesInWindow = comparisonKeyCount
	config.MaxEntrySize = 64
	config.HardMaxCacheSize = hardMaxMiB
	config.Verbose = false
	cache, err := bigcache.New(context.Background(), config)
	if err != nil {
		b.Fatal(err)
	}
	value := []byte("value")
	for _, key := range comparisonKeys {
		if err := cache.Set(key, value); err != nil {
			b.Fatal(err)
		}
	}
	if primeTurnover {
		// BigCache appends updates to its byte queue. Prime the write-only
		// benchmark to its hard limit so it measures steady turnover rather
		// than cold queue growth.
		for i := range comparisonKeyCount * 4 {
			if err := cache.Set(comparisonKeys[i&(comparisonKeyCount-1)], value); err != nil {
				b.Fatal(err)
			}
		}
		for _, key := range comparisonKeys {
			if err := cache.Set(key, value); err != nil {
				b.Fatal(err)
			}
		}
	}
	for _, key := range comparisonKeys {
		if _, err := cache.Get(key); err != nil {
			b.Fatalf("BigCache steady-state warm-up did not retain %q: %v", key, err)
		}
	}
	b.Cleanup(func() {
		if err := cache.Close(); err != nil {
			b.Error(err)
		}
	})
	return benchmarkCache{
		get: func(key string) bool {
			_, err := cache.Get(key)
			return err == nil
		},
		set: func(key string) {
			if err := cache.Set(key, value); err != nil {
				panic(err)
			}
		},
	}
}

func newRistrettoBenchmarkCache(b *testing.B) benchmarkCache {
	return newRistrettoBenchmarkCacheWithTTL(b, 0)
}

func newRistrettoTTLBenchmarkCache(b *testing.B) benchmarkCache {
	return newRistrettoBenchmarkCacheWithTTL(b, time.Hour)
}

func newRistrettoBenchmarkCacheWithTTL(b *testing.B, ttl time.Duration) benchmarkCache {
	cache, err := ristretto.NewCache(&ristretto.Config[string, string]{
		NumCounters:        comparisonKeyCount * 10,
		MaxCost:            comparisonKeyCount * 2,
		BufferItems:        64,
		IgnoreInternalCost: true,
	})
	if err != nil {
		b.Fatal(err)
	}
	for _, key := range comparisonKeys {
		for !cache.SetWithTTL(key, "value", 1, ttl) {
			cache.Wait()
		}
	}
	cache.Wait()
	for _, key := range comparisonKeys {
		if _, ok := cache.Get(key); !ok {
			b.Fatalf("Ristretto warm-up did not retain %q", key)
		}
	}
	b.Cleanup(cache.Close)
	return benchmarkCache{
		get: func(key string) bool {
			_, ok := cache.Get(key)
			return ok
		},
		set: func(key string) {
			if !cache.SetWithTTL(key, "value", 1, ttl) {
				panic("Ristretto dropped an existing-key update")
			}
		},
	}
}

func newOtterBenchmarkCache(b *testing.B) benchmarkCache {
	return newOtterBenchmarkCacheWithTTL(b, 0)
}

func newOtterTTLBenchmarkCache(b *testing.B) benchmarkCache {
	return newOtterBenchmarkCacheWithTTL(b, time.Hour)
}

func newOtterBenchmarkCacheWithTTL(b *testing.B, ttl time.Duration) benchmarkCache {
	options := &otter.Options[string, string]{
		MaximumSize:     comparisonKeyCount * 2,
		InitialCapacity: comparisonKeyCount,
	}
	if ttl > 0 {
		options.ExpiryCalculator = otter.ExpiryWriting[string, string](ttl)
	}
	cache, err := otter.New(options)
	if err != nil {
		b.Fatal(err)
	}
	for _, key := range comparisonKeys {
		cache.Set(key, "value")
	}
	cache.CleanUp()
	if size := cache.EstimatedSize(); size != comparisonKeyCount {
		b.Fatalf("Otter warm-up retained %d entries, want %d", size, comparisonKeyCount)
	}
	b.Cleanup(func() { cache.StopAllGoroutines() })
	return benchmarkCache{
		get: func(key string) bool {
			_, ok := cache.GetIfPresent(key)
			return ok
		},
		set: func(key string) {
			cache.Set(key, "value")
		},
	}
}

func expirationForBenchmark(ttl time.Duration) time.Duration {
	if ttl == 0 {
		return cache.NoExpiration
	}
	return ttl
}

func newSyncMapBenchmarkCache(*testing.B) benchmarkCache {
	cache := new(sync.Map)
	for _, key := range comparisonKeys {
		cache.Store(key, "value")
	}
	return benchmarkCache{
		get: func(key string) bool {
			_, ok := cache.Load(key)
			return ok
		},
		set: func(key string) {
			cache.Store(key, "value")
		},
	}
}

func benchmarkGets(b *testing.B, get func(string) bool, keys []string) {
	b.ReportAllocs()
	b.ResetTimer()
	var seedCounter atomic.Uint64
	var hits atomic.Uint64
	b.RunParallel(func(pb *testing.PB) {
		seed := seedCounter.Add(0x9e3779b97f4a7c15)
		localHits := uint64(0)
		for pb.Next() {
			seed = nextBenchmarkSeed(seed)
			if get(keys[seed&(comparisonKeyCount-1)]) {
				localHits++
			}
		}
		hits.Add(localHits)
	})
	b.ReportMetric(float64(hits.Load())*100/float64(b.N), "hit%")
}

func verifyBenchmarkCacheResident(b *testing.B, name string, candidate benchmarkCache) {
	b.Helper()
	for _, key := range comparisonKeys {
		if !candidate.get(key) {
			b.Fatalf("%s existing-key updates did not retain %q", name, key)
		}
	}
}

func benchmarkSets(b *testing.B, set func(string)) {
	b.ReportAllocs()
	b.ResetTimer()
	var seedCounter atomic.Uint64
	b.RunParallel(func(pb *testing.PB) {
		seed := seedCounter.Add(0x9e3779b97f4a7c15)
		for pb.Next() {
			seed = nextBenchmarkSeed(seed)
			set(comparisonKeys[seed&(comparisonKeyCount-1)])
		}
	})
}

func benchmarkMixed(b *testing.B, cache benchmarkCache) {
	b.ReportAllocs()
	b.ResetTimer()
	var seedCounter atomic.Uint64
	var hits atomic.Uint64
	b.RunParallel(func(pb *testing.PB) {
		seed := seedCounter.Add(0x9e3779b97f4a7c15)
		localHits := uint64(0)
		for pb.Next() {
			seed = nextBenchmarkSeed(seed)
			key := comparisonKeys[seed&(comparisonKeyCount-1)]
			if seed%5 == 0 {
				cache.set(key)
			} else if cache.get(key) {
				localHits++
			}
		}
		hits.Add(localHits)
	})
	b.ReportMetric(float64(hits.Load())*100/float64(b.N), "hit%")
}

func nextBenchmarkSeed(seed uint64) uint64 {
	seed ^= seed << 13
	seed ^= seed >> 7
	seed ^= seed << 17
	return seed
}
