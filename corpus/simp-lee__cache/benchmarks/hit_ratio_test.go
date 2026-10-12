package benchmarks

import (
	"fmt"
	"math/rand"
	"testing"

	cache "github.com/simp-lee/cache"

	"github.com/dgraph-io/ristretto/v2"
	"github.com/maypok86/otter/v2"
)

const (
	hitRatioCapacity = 1_024
	hitRatioWarmup   = 10_000
	hitRatioRequests = 100_000
)

type hitRatioCache struct {
	get   func(string) bool
	set   func(string)
	size  func() int
	close func()
}

type hitRatioWorkload struct {
	name  string
	trace []int
}

// TestHitRatioComparison compares bounded-cache eviction behavior. It uses one
// ShardedCache shard so MaxEntriesPerShard is the same logical capacity used by the global
// limits in Ristretto and Otter. go-cache and sync.Map are excluded because they
// do not provide capacity eviction; BigCache is byte-capacity based.
func TestHitRatioComparison(t *testing.T) {
	workloads, keys := newHitRatioWorkloads()
	factories := []struct {
		name string
		new  func(*testing.T) hitRatioCache
	}{
		{name: "ShardedCache-FIFO", new: newShardedFIFOHitRatioCache},
		{name: "ShardedCache-LRU", new: newShardedLRUHitRatioCache},
		{name: "Ristretto-TinyLFU-SampledLFU", new: newRistrettoHitRatioCache},
		{name: "Otter-W-TinyLFU", new: newOtterHitRatioCache},
	}

	for _, workload := range workloads {
		t.Run(workload.name, func(t *testing.T) {
			if measured := len(workload.trace) - hitRatioWarmup; measured != hitRatioRequests {
				t.Fatalf("workload has %d measured requests, want %d", measured, hitRatioRequests)
			}
			for _, factory := range factories {
				t.Run(factory.name, func(t *testing.T) {
					cache := factory.new(t)
					defer cache.close()

					hits := 0
					for i, keyIndex := range workload.trace {
						key := keys[keyIndex]
						if cache.get(key) {
							if i >= hitRatioWarmup {
								hits++
							}
							continue
						}
						cache.set(key)
					}

					if size := cache.size(); size > hitRatioCapacity {
						t.Fatalf("cache retained %d entries, capacity is %d", size, hitRatioCapacity)
					}
					ratio := float64(hits) * 100 / hitRatioRequests
					t.Logf("hit ratio: %.2f%% (%d/%d)", ratio, hits, hitRatioRequests)
				})
			}
		})
	}
}

func TestPolicyOrderBaselineTrace(t *testing.T) {
	workloads, keys := newHitRatioWorkloads()
	expected := map[string]map[cache.EvictionPolicy]int{
		"Zipfian":        {cache.FIFO: 74_266, cache.LRU: 78_113},
		"ScanResistance": {cache.FIFO: 57_585, cache.LRU: 57_585},
	}
	for _, workload := range workloads {
		for _, policy := range []cache.EvictionPolicy{cache.FIFO, cache.LRU} {
			t.Run(workload.name+"/"+policy.String(), func(t *testing.T) {
				candidate := newShardedHitRatioCache(t, policy)
				defer candidate.close()
				hits := 0
				for index, keyIndex := range workload.trace {
					key := keys[keyIndex]
					if candidate.get(key) {
						if index >= hitRatioWarmup {
							hits++
						}
						continue
					}
					candidate.set(key)
				}
				if hits != expected[workload.name][policy] {
					t.Fatalf("measured hits = %d, want baseline %d", hits, expected[workload.name][policy])
				}
				if size := candidate.size(); size > hitRatioCapacity {
					t.Fatalf("cache retained %d entries, capacity is %d", size, hitRatioCapacity)
				}
			})
		}
	}
}

func newHitRatioWorkloads() ([]hitRatioWorkload, []string) {
	const universe = hitRatioCapacity * 10
	total := hitRatioWarmup + hitRatioRequests

	keys := make([]string, universe)
	for i := range keys {
		keys[i] = fmt.Sprintf("key-%05d", i)
	}

	zipfTrace := make([]int, total)
	zipf := rand.NewZipf(rand.New(rand.NewSource(1)), 1.1, 1, universe-1)
	for i := range zipfTrace {
		zipfTrace[i] = int(zipf.Uint64())
	}

	// Alternate a frequently reused hot set with scans larger than the cache.
	// Admission policies can reject one-time scan entries instead of displacing
	// the hot set, while FIFO admits every scanned entry.
	scanTrace := make([]int, 0, total)
	hotRand := rand.New(rand.NewSource(2))
	const hotSet = hitRatioCapacity / 2
	scanIndex := hotSet
	for len(scanTrace) < total {
		for range 4_096 {
			scanTrace = append(scanTrace, hotRand.Intn(hotSet))
			if len(scanTrace) == total {
				break
			}
		}
		if len(scanTrace) == total {
			break
		}
		for range 2_048 {
			scanTrace = append(scanTrace, scanIndex)
			scanIndex++
			if scanIndex == universe {
				scanIndex = hotSet
			}
			if len(scanTrace) == total {
				break
			}
		}
	}

	return []hitRatioWorkload{
		{name: "Zipfian", trace: zipfTrace},
		{name: "ScanResistance", trace: scanTrace},
	}, keys
}

func newShardedFIFOHitRatioCache(t *testing.T) hitRatioCache {
	return newShardedHitRatioCache(t, cache.FIFO)
}

func newShardedLRUHitRatioCache(t *testing.T) hitRatioCache {
	return newShardedHitRatioCache(t, cache.LRU)
}

func newShardedHitRatioCache(t *testing.T, policy cache.EvictionPolicy) hitRatioCache {
	options := cache.DefaultOptions()
	options.ShardCount = 1
	options.MaxEntriesPerShard = hitRatioCapacity
	options.CleanupEnabled = false
	options.EvictionPolicy = policy
	candidate, err := cache.New(options)
	if err != nil {
		t.Fatal(err)
	}
	return hitRatioCache{
		get: func(key string) bool {
			_, ok := candidate.Get(key)
			return ok
		},
		set: func(key string) {
			if err := candidate.Set(key, key); err != nil {
				t.Fatal(err)
			}
		},
		size:  candidate.Count,
		close: func() { _ = candidate.Close() },
	}
}

func newRistrettoHitRatioCache(t *testing.T) hitRatioCache {
	cache, err := ristretto.NewCache(&ristretto.Config[string, string]{
		NumCounters:        int64(hitRatioCapacity * 10),
		MaxCost:            hitRatioCapacity,
		BufferItems:        64,
		IgnoreInternalCost: true,
	})
	if err != nil {
		t.Fatal(err)
	}
	return hitRatioCache{
		get: func(key string) bool {
			_, ok := cache.Get(key)
			return ok
		},
		set: func(key string) {
			for !cache.Set(key, key, 1) {
				cache.Wait()
			}
			cache.Wait()
		},
		size: func() int {
			cache.Wait()
			count := 0
			cache.IterValues(func(string) bool {
				count++
				return false
			})
			return count
		},
		close: cache.Close,
	}
}

func newOtterHitRatioCache(t *testing.T) hitRatioCache {
	cache, err := otter.New(&otter.Options[string, string]{
		MaximumSize:     hitRatioCapacity,
		InitialCapacity: hitRatioCapacity,
	})
	if err != nil {
		t.Fatal(err)
	}
	return hitRatioCache{
		get: func(key string) bool {
			_, ok := cache.GetIfPresent(key)
			return ok
		},
		set: func(key string) {
			cache.Set(key, key)
			cache.CleanUp()
		},
		size: func() int {
			cache.CleanUp()
			return cache.EstimatedSize()
		},
		close: func() { cache.StopAllGoroutines() },
	}
}
