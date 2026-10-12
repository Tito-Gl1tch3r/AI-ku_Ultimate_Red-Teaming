package benchmarks

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"runtime/debug"
	"sort"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	cache "github.com/simp-lee/cache"

	"github.com/allegro/bigcache/v3"
	"github.com/dgraph-io/ristretto/v2"
	"github.com/maypok86/otter/v2"
	gocache "github.com/patrickmn/go-cache"
)

const (
	memoryEntryCount = 1_000_000
	memoryTTL        = 24 * time.Hour
	memoryJSONPrefix = "MEMJSON "
)

type memorySnapshot struct {
	HeapAlloc   uint64 `json:"heapAlloc"`
	HeapInuse   uint64 `json:"heapInuse"`
	HeapObjects uint64 `json:"heapObjects"`
	HeapSys     uint64 `json:"heapSys"`
	Sys         uint64 `json:"sys"`
	TotalAlloc  uint64 `json:"totalAlloc"`
	Mallocs     uint64 `json:"mallocs"`
	RSS         uint64 `json:"rss"`
	PSS         uint64 `json:"pss"`
	Private     uint64 `json:"private"`
	VmHWM       uint64 `json:"vmHWM"`
}

type memoryResult struct {
	Implementation string `json:"implementation"`
	Mode           string `json:"mode"`
	Version        string `json:"version"`
	Entries        int    `json:"entries"`
	PayloadBytes   int64  `json:"payloadBytes"`

	FixedHeapAlloc int64 `json:"fixedHeapAlloc"`
	EntryHeapAlloc int64 `json:"entryHeapAlloc"`
	TotalHeapAlloc int64 `json:"totalHeapAlloc"`
	TotalHeapInuse int64 `json:"totalHeapInuse"`
	HeapObjects    int64 `json:"heapObjects"`
	TotalRSS       int64 `json:"totalRSS"`
	TotalPSS       int64 `json:"totalPSS"`
	TotalPrivate   int64 `json:"totalPrivate"`
	PeakRSS        int64 `json:"peakRSS"`

	InsertionAllocBytes uint64 `json:"insertionAllocBytes"`
	InsertionMallocs    uint64 `json:"insertionMallocs"`
	InsertionNanos      int64  `json:"insertionNanos"`
	PostCloseHeapAlloc  int64  `json:"postCloseHeapAlloc"`
	ExtraCapacity       int64  `json:"extraCapacity,omitempty"`
}

type memoryCacheHandle struct {
	set        func(string, string) error
	get        func(string) (string, bool)
	count      func() int
	ttlValid   func(string) bool
	expiration func(string) (time.Time, bool)
	settle     func()
	close      func()
	extra      func() int64
	keepAlive  any
}

var memoryComparisonSink any

// TestMemoryComparison is intentionally opt-in because it starts isolated
// million-entry subprocesses. Run it with CACHE_RUN_MEMORY_COMPARISON=1.
func TestMemoryComparison(t *testing.T) {
	if os.Getenv("CACHE_RUN_MEMORY_COMPARISON") != "1" {
		t.Skip("set CACHE_RUN_MEMORY_COMPARISON=1 to run the isolated memory suite")
	}

	repetitions := 5
	if value := os.Getenv("CACHE_MEMORY_REPETITIONS"); value != "" {
		parsed, err := strconv.Atoi(value)
		if err != nil || parsed < 1 {
			t.Fatalf("invalid CACHE_MEMORY_REPETITIONS %q", value)
		}
		repetitions = parsed
	}
	if os.Getenv("CACHE_REQUIRE_CANONICAL_HOST") == "1" && repetitions < 5 {
		t.Fatalf("canonical memory comparison requires at least 5 repetitions, got %d", repetitions)
	}
	requireCanonicalHost(t, 0)

	cases := []struct{ implementation, mode string }{
		{"shardedcache", "none"},
		{"shardedcache", "ttl"},
		{"go-cache", "none"},
		{"go-cache", "ttl"},
		{"bigcache", "none"},
		{"bigcache", "ttl"},
		{"ristretto", "none"},
		{"ristretto", "ttl"},
		{"otter", "none"},
		{"otter", "ttl"},
		{"sync.Map", "none"},
	}

	all := make(map[string][]memoryResult, len(cases))
	for repetition := range repetitions {
		for offset := range len(cases) {
			current := cases[(offset+repetition)%len(cases)]
			result := runMemoryWorker(t, current.implementation, current.mode)
			key := current.implementation + "/" + current.mode
			all[key] = append(all[key], result)
			encoded, err := json.Marshal(result)
			if err != nil {
				t.Fatal(err)
			}
			t.Logf("MEMRAW repetition=%d %s", repetition+1, encoded)
		}
	}

	t.Log("retained-memory medians (MiB); total = fixed empty-cache overhead + retained entries")
	t.Log("implementation mode totalHeap fixedHeap entryHeap heapInuse RSS PSS private objects bytes/entry insertAlloc insertTime postCloseDelta")
	for _, current := range cases {
		key := current.implementation + "/" + current.mode
		result := medianMemoryResult(all[key])
		t.Logf("%s %s %.2f %.2f %.2f %.2f %.2f %.2f %.2f %d %.1f %.2f %.2fs %.2f",
			result.Implementation,
			result.Mode,
			mib(result.TotalHeapAlloc),
			mib(result.FixedHeapAlloc),
			mib(result.EntryHeapAlloc),
			mib(result.TotalHeapInuse),
			mib(result.TotalRSS),
			mib(result.TotalPSS),
			mib(result.TotalPrivate),
			result.HeapObjects,
			float64(result.TotalHeapAlloc)/float64(result.Entries),
			mib(int64(result.InsertionAllocBytes)),
			float64(result.InsertionNanos)/float64(time.Second),
			mib(result.PostCloseHeapAlloc),
		)
		encoded, err := json.Marshal(result)
		if err != nil {
			t.Fatal(err)
		}
		t.Logf("MEMSUMMARY %s", encoded)
		if result.Implementation == "shardedcache" {
			limit := int64(220 << 20)
			if result.Mode == "ttl" {
				limit = 230 << 20
			}
			if result.TotalHeapAlloc > limit {
				t.Errorf("%s TotalHeapAlloc = %.2f MiB, limit %.2f MiB", key, mib(result.TotalHeapAlloc), mib(limit))
			}
			if result.PostCloseHeapAlloc > 20<<20 {
				t.Errorf("%s post-Close HeapAlloc growth = %.2f MiB, limit 20 MiB", key, mib(result.PostCloseHeapAlloc))
			}
		}
	}
}

func TestMemoryComparisonWorker(t *testing.T) {
	implementation := os.Getenv("CACHE_MEMORY_IMPL")
	mode := os.Getenv("CACHE_MEMORY_MODE")
	if implementation == "" || mode == "" {
		t.Skip("memory worker is only run by TestMemoryComparison")
	}
	if mode != "none" && mode != "ttl" {
		t.Fatalf("unsupported memory mode %q", mode)
	}
	if implementation == "sync.Map" && mode == "ttl" {
		t.Fatal("sync.Map TTL is intentionally excluded: it has no TTL contract")
	}
	requireCanonicalHost(t, 1)

	settleMemory()
	baseline := readMemorySnapshot(t)
	handle, version := newMemoryCache(t, implementation, mode)
	settleMemory()
	empty := readMemorySnapshot(t)

	var beforeInsertion runtime.MemStats
	runtime.ReadMemStats(&beforeInsertion)
	started := time.Now()
	for i := range memoryEntryCount {
		key, value := memoryKeyValue(i)
		if err := handle.set(key, value); err != nil {
			t.Fatalf("set item %d: %v", i, err)
		}
	}
	inserted := time.Now()
	handle.settle()
	insertionNanos := time.Since(started).Nanoseconds()
	var afterInsertion runtime.MemStats
	runtime.ReadMemStats(&afterInsertion)

	if count := handle.count(); count != memoryEntryCount {
		t.Fatalf("retained %d entries, want %d", count, memoryEntryCount)
	}
	for i := range memoryEntryCount {
		key, expected := memoryKeyValue(i)
		actual, ok := handle.get(key)
		if !ok || actual != expected {
			t.Fatalf("lookup %d: value=%q found=%v, want %q", i, actual, ok, expected)
		}
	}
	if implementation == "shardedcache" {
		for i := range memoryEntryCount {
			key, _ := memoryKeyValue(i)
			expiresAt, ok := handle.expiration(key)
			if !ok {
				t.Fatalf("expiration lookup %d missed", i)
			}
			if mode == "none" {
				if !expiresAt.IsZero() {
					t.Fatalf("no-TTL entry %d expires at %v", i, expiresAt)
				}
			} else if expiresAt.Before(started.Add(memoryTTL)) || expiresAt.After(inserted.Add(memoryTTL)) {
				t.Fatalf("TTL entry %d expires at %v, outside [%v, %v]", i, expiresAt, started.Add(memoryTTL), inserted.Add(memoryTTL))
			}
		}
	} else if mode == "ttl" {
		key, _ := memoryKeyValue(memoryEntryCount / 2)
		if !handle.ttlValid(key) {
			t.Fatalf("TTL metadata is not valid for %q", key)
		}
	}

	settleMemory()
	loaded := readMemorySnapshot(t)
	memoryComparisonSink = handle.keepAlive
	runtime.KeepAlive(handle.keepAlive)

	result := memoryResult{
		Implementation:      implementation,
		Mode:                mode,
		Version:             version,
		Entries:             memoryEntryCount,
		PayloadBytes:        int64(memoryEntryCount * (14 + 16)),
		FixedHeapAlloc:      signedDelta(empty.HeapAlloc, baseline.HeapAlloc),
		EntryHeapAlloc:      signedDelta(loaded.HeapAlloc, empty.HeapAlloc),
		TotalHeapAlloc:      signedDelta(loaded.HeapAlloc, baseline.HeapAlloc),
		TotalHeapInuse:      signedDelta(loaded.HeapInuse, baseline.HeapInuse),
		HeapObjects:         signedDelta(loaded.HeapObjects, baseline.HeapObjects),
		TotalRSS:            signedDelta(loaded.RSS, baseline.RSS),
		TotalPSS:            signedDelta(loaded.PSS, baseline.PSS),
		TotalPrivate:        signedDelta(loaded.Private, baseline.Private),
		PeakRSS:             signedDelta(loaded.VmHWM, baseline.VmHWM),
		InsertionAllocBytes: afterInsertion.TotalAlloc - beforeInsertion.TotalAlloc,
		InsertionMallocs:    afterInsertion.Mallocs - beforeInsertion.Mallocs,
		InsertionNanos:      insertionNanos,
		ExtraCapacity:       handle.extra(),
	}
	closed := false
	if implementation == "shardedcache" {
		handle.close()
		closed = true
		settleMemory()
		postClose := readMemorySnapshot(t)
		memoryComparisonSink = handle.keepAlive
		runtime.KeepAlive(handle.keepAlive)
		result.PostCloseHeapAlloc = signedDelta(postClose.HeapAlloc, loaded.HeapAlloc)
		if count := handle.count(); count != memoryEntryCount {
			t.Fatalf("post-Close count = %d, want %d", count, memoryEntryCount)
		}
	}

	encoded, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	fmt.Printf("%s%s\n", memoryJSONPrefix, encoded)
	if !closed {
		handle.close()
	}
}

func newMemoryCache(t *testing.T, implementation, mode string) (memoryCacheHandle, string) {
	t.Helper()
	ttl := mode == "ttl"
	switch implementation {
	case "shardedcache":
		options := cache.DefaultOptions()
		options.ShardCount = 32
		options.CleanupEnabled = false
		candidate, err := cache.New(options)
		if err != nil {
			t.Fatal(err)
		}
		return memoryCacheHandle{
			set: func(key, value string) error {
				expiration := cache.NoExpiration
				if ttl {
					expiration = memoryTTL
				}
				return candidate.SetWithExpiration(key, value, expiration)
			},
			get: func(key string) (string, bool) {
				value, ok := candidate.Get(key)
				if !ok {
					return "", false
				}
				return value.(string), true
			},
			count: candidate.Count,
			ttlValid: func(key string) bool {
				_, expiresAt, ok := candidate.GetWithExpiration(key)
				return ok && expiresAt.After(time.Now())
			},
			expiration: func(key string) (time.Time, bool) {
				_, expiresAt, ok := candidate.GetWithExpiration(key)
				return expiresAt, ok
			},
			settle:    func() {},
			close:     func() { _ = candidate.Close() },
			extra:     func() int64 { return 0 },
			keepAlive: candidate,
		}, "v2"

	case "go-cache":
		cache := gocache.New(gocache.NoExpiration, 0)
		return memoryCacheHandle{
			set: func(key, value string) error {
				expiration := gocache.NoExpiration
				if ttl {
					expiration = memoryTTL
				}
				cache.Set(key, value, expiration)
				return nil
			},
			get: func(key string) (string, bool) {
				value, ok := cache.Get(key)
				if !ok {
					return "", false
				}
				return value.(string), true
			},
			count: cache.ItemCount,
			ttlValid: func(key string) bool {
				_, expiresAt, ok := cache.GetWithExpiration(key)
				return ok && expiresAt.After(time.Now())
			},
			settle:    func() {},
			close:     func() {},
			extra:     func() int64 { return 0 },
			keepAlive: cache,
		}, "v2.1.0+incompatible"

	case "bigcache":
		lifeWindow := 100 * 365 * 24 * time.Hour
		if ttl {
			lifeWindow = memoryTTL
		}
		config := bigcache.DefaultConfig(lifeWindow)
		config.Shards = 32
		config.CleanWindow = 0
		config.MaxEntriesInWindow = 1_002_624
		config.MaxEntrySize = 64
		config.HardMaxCacheSize = 0
		config.StatsEnabled = false
		config.Verbose = false
		cache, err := bigcache.New(context.Background(), config)
		if err != nil {
			t.Fatal(err)
		}
		return memoryCacheHandle{
			set: func(key, value string) error {
				return cache.Set(key, []byte(value))
			},
			get: func(key string) (string, bool) {
				value, err := cache.Get(key)
				return string(value), err == nil
			},
			count: cache.Len,
			ttlValid: func(key string) bool {
				_, response, err := cache.GetWithInfo(key)
				return err == nil && response.EntryStatus != bigcache.Expired
			},
			settle:    func() {},
			close:     func() { _ = cache.Close() },
			extra:     func() int64 { return int64(cache.Capacity()) },
			keepAlive: cache,
		}, "v3.2.0"

	case "ristretto":
		cache, err := ristretto.NewCache(&ristretto.Config[string, string]{
			NumCounters:        memoryEntryCount * 10,
			MaxCost:            memoryEntryCount * 2,
			BufferItems:        64,
			IgnoreInternalCost: true,
		})
		if err != nil {
			t.Fatal(err)
		}
		return memoryCacheHandle{
			set: func(key, value string) error {
				duration := time.Duration(0)
				if ttl {
					duration = memoryTTL
				}
				for !cache.SetWithTTL(key, value, 1, duration) {
					cache.Wait()
				}
				return nil
			},
			get: cache.Get,
			count: func() int {
				cache.Wait()
				count := 0
				cache.IterValues(func(string) bool {
					count++
					return false
				})
				return count
			},
			ttlValid: func(key string) bool {
				cache.Wait()
				remaining, ok := cache.GetTTL(key)
				return ok && remaining > 0
			},
			settle:    cache.Wait,
			close:     cache.Close,
			extra:     func() int64 { return memoryEntryCount * 10 },
			keepAlive: cache,
		}, "v2.4.2"

	case "otter":
		options := &otter.Options[string, string]{}
		if ttl {
			options.ExpiryCalculator = otter.ExpiryWriting[string, string](memoryTTL)
		}
		cache, err := otter.New(options)
		if err != nil {
			t.Fatal(err)
		}
		return memoryCacheHandle{
			set: func(key, value string) error {
				cache.Set(key, value)
				return nil
			},
			get: cache.GetIfPresent,
			count: func() int {
				cache.CleanUp()
				return cache.EstimatedSize()
			},
			ttlValid: func(key string) bool {
				entry, ok := cache.GetEntryQuietly(key)
				return ok && entry.ExpiresAt().After(time.Now())
			},
			settle:    cache.CleanUp,
			close:     func() { cache.StopAllGoroutines() },
			extra:     func() int64 { return 0 },
			keepAlive: cache,
		}, "v2.3.0"

	case "sync.Map":
		cache := new(syncMapString)
		return memoryCacheHandle{
			set: func(key, value string) error {
				cache.values.Store(key, value)
				return nil
			},
			get: func(key string) (string, bool) {
				value, ok := cache.values.Load(key)
				if !ok {
					return "", false
				}
				return value.(string), true
			},
			count:     cache.count,
			ttlValid:  func(string) bool { return false },
			settle:    func() {},
			close:     func() {},
			extra:     func() int64 { return 0 },
			keepAlive: cache,
		}, "Go 1.26.0"
	default:
		t.Fatalf("unsupported memory implementation %q", implementation)
		return memoryCacheHandle{}, ""
	}
}

type syncMapString struct {
	values sync.Map
}

func (m *syncMapString) count() int {
	count := 0
	m.values.Range(func(_, _ any) bool {
		count++
		return true
	})
	return count
}

func runMemoryWorker(t *testing.T, implementation, mode string) memoryResult {
	t.Helper()
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	command := exec.Command(executable,
		"-test.run=^TestMemoryComparisonWorker$",
		"-test.count=1",
		"-test.timeout=20m",
		"-test.v",
	)
	command.Env = append(filteredMemoryEnvironment(),
		"GOMAXPROCS=1",
		"GOGC=100",
		"GOMEMLIMIT=off",
		"CACHE_MEMORY_IMPL="+implementation,
		"CACHE_MEMORY_MODE="+mode,
	)
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("memory worker %s/%s failed: %v\n%s", implementation, mode, err, output)
	}
	for _, line := range bytes.Split(output, []byte{'\n'}) {
		if !bytes.HasPrefix(line, []byte(memoryJSONPrefix)) {
			continue
		}
		var result memoryResult
		if err := json.Unmarshal(bytes.TrimPrefix(line, []byte(memoryJSONPrefix)), &result); err != nil {
			t.Fatalf("decode memory result: %v", err)
		}
		return result
	}
	t.Fatalf("memory worker %s/%s returned no result:\n%s", implementation, mode, output)
	return memoryResult{}
}

func filteredMemoryEnvironment() []string {
	environment := make([]string, 0, len(os.Environ()))
	for _, value := range os.Environ() {
		if strings.HasPrefix(value, "CACHE_MEMORY_") || strings.HasPrefix(value, "CACHE_RUN_MEMORY_") ||
			strings.HasPrefix(value, "GOMAXPROCS=") || strings.HasPrefix(value, "GOGC=") ||
			strings.HasPrefix(value, "GOMEMLIMIT=") {
			continue
		}
		environment = append(environment, value)
	}
	return environment
}

func settleMemory() {
	runtime.GC()
	debug.FreeOSMemory()
	runtime.GC()
}

func readMemorySnapshot(t *testing.T) memorySnapshot {
	t.Helper()
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	process := readProcessMemory(t)
	return memorySnapshot{
		HeapAlloc:   stats.HeapAlloc,
		HeapInuse:   stats.HeapInuse,
		HeapObjects: stats.HeapObjects,
		HeapSys:     stats.HeapSys,
		Sys:         stats.Sys,
		TotalAlloc:  stats.TotalAlloc,
		Mallocs:     stats.Mallocs,
		RSS:         process.RSS,
		PSS:         process.PSS,
		Private:     process.Private,
		VmHWM:       process.VmHWM,
	}
}

func readProcessMemory(t *testing.T) memorySnapshot {
	t.Helper()
	var snapshot memorySnapshot
	rollup, err := os.Open("/proc/self/smaps_rollup")
	if err == nil {
		scanner := bufio.NewScanner(rollup)
		for scanner.Scan() {
			fields := strings.Fields(scanner.Text())
			if len(fields) < 2 {
				continue
			}
			value, parseErr := strconv.ParseUint(fields[1], 10, 64)
			if parseErr != nil {
				continue
			}
			value *= 1024
			switch strings.TrimSuffix(fields[0], ":") {
			case "Rss":
				snapshot.RSS = value
			case "Pss":
				snapshot.PSS = value
			case "Private_Clean", "Private_Dirty":
				snapshot.Private += value
			}
		}
		if err := scanner.Err(); err != nil {
			t.Fatal(err)
		}
		if err := rollup.Close(); err != nil {
			t.Fatal(err)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		t.Fatal(err)
	}

	status, err := os.Open("/proc/self/status")
	if err == nil {
		scanner := bufio.NewScanner(status)
		for scanner.Scan() {
			fields := strings.Fields(scanner.Text())
			if len(fields) >= 2 && fields[0] == "VmHWM:" {
				value, parseErr := strconv.ParseUint(fields[1], 10, 64)
				if parseErr == nil {
					snapshot.VmHWM = value * 1024
				}
			}
		}
		if err := scanner.Err(); err != nil {
			t.Fatal(err)
		}
		if err := status.Close(); err != nil {
			t.Fatal(err)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		t.Fatal(err)
	}
	return snapshot
}

func memoryKeyValue(index int) (string, string) {
	return fmt.Sprintf("key-%010d", index), fmt.Sprintf("value-%010d", index)
}

func signedDelta(after, before uint64) int64 {
	if after >= before {
		return int64(after - before)
	}
	return -int64(before - after)
}

func medianMemoryResult(results []memoryResult) memoryResult {
	if len(results) == 0 {
		return memoryResult{}
	}
	medianInt64 := func(value func(memoryResult) int64) int64 {
		values := make([]int64, len(results))
		for i, result := range results {
			values[i] = value(result)
		}
		sort.Slice(values, func(i, j int) bool { return values[i] < values[j] })
		return values[len(values)/2]
	}
	medianUint64 := func(value func(memoryResult) uint64) uint64 {
		values := make([]uint64, len(results))
		for i, result := range results {
			values[i] = value(result)
		}
		sort.Slice(values, func(i, j int) bool { return values[i] < values[j] })
		return values[len(values)/2]
	}
	result := results[0]
	result.FixedHeapAlloc = medianInt64(func(v memoryResult) int64 { return v.FixedHeapAlloc })
	result.EntryHeapAlloc = medianInt64(func(v memoryResult) int64 { return v.EntryHeapAlloc })
	result.TotalHeapAlloc = medianInt64(func(v memoryResult) int64 { return v.TotalHeapAlloc })
	result.TotalHeapInuse = medianInt64(func(v memoryResult) int64 { return v.TotalHeapInuse })
	result.HeapObjects = medianInt64(func(v memoryResult) int64 { return v.HeapObjects })
	result.TotalRSS = medianInt64(func(v memoryResult) int64 { return v.TotalRSS })
	result.TotalPSS = medianInt64(func(v memoryResult) int64 { return v.TotalPSS })
	result.TotalPrivate = medianInt64(func(v memoryResult) int64 { return v.TotalPrivate })
	result.PeakRSS = medianInt64(func(v memoryResult) int64 { return v.PeakRSS })
	result.InsertionAllocBytes = medianUint64(func(v memoryResult) uint64 { return v.InsertionAllocBytes })
	result.InsertionMallocs = medianUint64(func(v memoryResult) uint64 { return v.InsertionMallocs })
	result.InsertionNanos = medianInt64(func(v memoryResult) int64 { return v.InsertionNanos })
	result.PostCloseHeapAlloc = medianInt64(func(v memoryResult) int64 { return v.PostCloseHeapAlloc })
	result.ExtraCapacity = medianInt64(func(v memoryResult) int64 { return v.ExtraCapacity })
	return result
}

func mib(value int64) float64 {
	return float64(value) / (1024 * 1024)
}
