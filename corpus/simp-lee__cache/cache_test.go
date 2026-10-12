package shardedcache

import (
	"container/heap"
	"context"
	"errors"
	"math"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type manualClock struct {
	mu  sync.Mutex
	now time.Time
}

func newManualClock() *manualClock {
	return &manualClock{now: time.Date(2030, 1, 2, 3, 4, 5, 0, time.UTC)}
}

func (clock *manualClock) Now() time.Time {
	clock.mu.Lock()
	now := clock.now
	clock.mu.Unlock()
	return now
}

func (clock *manualClock) Advance(duration time.Duration) {
	clock.mu.Lock()
	clock.now = clock.now.Add(duration)
	clock.mu.Unlock()
}

type countingClock struct {
	base  clock
	calls int
}

func (clock *countingClock) Now() time.Time {
	clock.calls++
	return clock.base.Now()
}

func (clock *countingClock) reset() { clock.calls = 0 }

type gatedSampleClock struct {
	base    *manualClock
	sampled chan struct{}
	release chan struct{}
	once    sync.Once
}

func (clock *gatedSampleClock) Now() time.Time {
	now := clock.base.Now()
	clock.once.Do(func() { close(clock.sampled) })
	<-clock.release
	return now
}

func testCache(t *testing.T, modify func(*Options)) (*ShardedCache, *manualClock) {
	t.Helper()
	options := DefaultOptions()
	options.ShardCount = 1
	options.CleanupEnabled = false
	if modify != nil {
		modify(&options)
	}
	clock := newManualClock()
	cache, err := newWithClock(options, clock)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := cache.Close(); err != nil {
			t.Errorf("Close: %v", err)
		}
	})
	return cache, clock
}

func TestDefaultOptions(t *testing.T) {
	options := DefaultOptions()
	if options.ShardCount != 32 || options.MaxEntriesPerShard != 0 || options.DefaultExpiration != 0 || !options.CleanupEnabled || options.EvictionPolicy != FIFO || options.Persistence != nil {
		t.Fatalf("unexpected defaults: %+v", options)
	}
	if err := options.Validate(); err != nil {
		t.Fatal(err)
	}
}

func TestOptionsValidation(t *testing.T) {
	valid := DefaultOptions()
	cases := []struct {
		name   string
		change func(*Options)
		field  string
	}{
		{"zero shards", func(o *Options) { o.ShardCount = 0 }, "ShardCount"},
		{"non power of two", func(o *Options) { o.ShardCount = 3 }, "ShardCount"},
		{"excessive shard count", func(o *Options) { o.ShardCount = maxShardCount * 2 }, "ShardCount"},
		{"negative capacity", func(o *Options) { o.MaxEntriesPerShard = -1 }, "MaxEntriesPerShard"},
		{"negative default ttl", func(o *Options) { o.DefaultExpiration = -1 }, "DefaultExpiration"},
		{"unknown policy", func(o *Options) { o.EvictionPolicy = 99 }, "EvictionPolicy"},
		{"missing path", func(o *Options) { o.Persistence = &PersistenceOptions{} }, "Persistence.Path"},
		{"negative interval", func(o *Options) { o.Persistence = &PersistenceOptions{Path: t.TempDir(), Interval: -1} }, "Persistence.Interval"},
		{"negative threshold", func(o *Options) { o.Persistence = &PersistenceOptions{Path: t.TempDir(), Threshold: -1} }, "Persistence.Threshold"},
		{"capacity overflow", func(o *Options) { o.ShardCount = 2; o.MaxEntriesPerShard = math.MaxInt }, "MaxEntriesPerShard"},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			options := valid
			test.change(&options)
			err := options.Validate()
			if err == nil || !strings.Contains(err.Error(), test.field) {
				t.Fatalf("Validate() = %v, want field %s", err, test.field)
			}
		})
	}
	if _, err := New(Options{}); err == nil {
		t.Fatal("Options{} was silently accepted")
	}
	tooLarge := valid
	tooLarge.ShardCount = maxShardCount * 2
	if _, err := New(tooLarge); err == nil || !strings.Contains(err.Error(), "ShardCount") {
		t.Fatalf("New with excessive ShardCount = %v", err)
	}
}

func TestExpirationValidation(t *testing.T) {
	cache, _ := testCache(t, nil)
	for _, expiration := range []time.Duration{DefaultExpiration, NoExpiration, time.Nanosecond} {
		if err := cache.SetWithExpiration("ok", 1, expiration); err != nil {
			t.Fatalf("expiration %s: %v", expiration, err)
		}
	}
	for _, expiration := range []time.Duration{-2, -time.Hour} {
		if err := cache.SetWithExpiration("bad", 1, expiration); err == nil || !strings.Contains(err.Error(), "expiration") {
			t.Fatalf("expiration %s accepted: %v", expiration, err)
		}
	}
}

func TestPublicAPIContract(t *testing.T) {
	var constructor func(Options) (*ShardedCache, error) = New
	cache, err := constructor(DefaultOptions())
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	var set func(string, any) error = cache.Set
	var touch func(string, time.Duration) (bool, error) = cache.Touch
	var remove func(string) (bool, error) = cache.Delete
	var group func(string) (Group, error) = cache.Group
	var callback func(func(EntryKey, any, EvictionReason)) error = cache.OnEvicted
	_ = []any{set, touch, remove, group, callback}
	if _, err := cache.Group(""); !errors.Is(err, ErrEmptyGroup) {
		t.Fatalf("Group empty error = %v", err)
	}
	if status := cache.PersistenceStatus(); status.Enabled {
		t.Fatalf("disabled persistence status = %+v", status)
	}
	if err := cache.Flush(); !errors.Is(err, ErrPersistenceDisabled) {
		t.Fatalf("Flush = %v", err)
	}
}

func TestShardHashBaselineVectors(t *testing.T) {
	tests := []struct {
		key         EntryKey
		hash        uint64
		shards8     int
		shards32    int
		shards128   int
		shards65536 int
	}{
		{key: EntryKey{}, hash: 0xead94efae26536e1, shards8: 1, shards32: 1, shards128: 97, shards65536: 14049},
		{key: EntryKey{Key: "shared"}, hash: 0xb1b4d1127dbfa902, shards8: 2, shards32: 2, shards128: 2, shards65536: 43266},
		{key: EntryKey{Group: "group", Key: "shared"}, hash: 0x2708d08adca228b9, shards8: 1, shards32: 25, shards128: 57, shards65536: 10425},
		{key: EntryKey{Group: "other", Key: "shared"}, hash: 0x6ed526cf8a8122c1, shards8: 1, shards32: 1, shards128: 65, shards65536: 8897},
		{key: EntryKey{Group: "group", Key: "x\x00:y"}, hash: 0x79d644a1192a452d, shards8: 5, shards32: 13, shards128: 45, shards65536: 17709},
		{key: EntryKey{Group: "group\x00:key", Key: "x"}, hash: 0x9277646f484e605d, shards8: 5, shards32: 29, shards128: 93, shards65536: 24669},
		{key: EntryKey{Group: "团队", Key: "clé/🙂"}, hash: 0xcd0c9fdfb186ab75, shards8: 5, shards32: 21, shards128: 117, shards65536: 43893},
	}
	for _, test := range tests {
		if got := shardHash(test.key); got != test.hash {
			t.Errorf("shardHash(%+q) = %#016x, want %#016x", test.key, got, test.hash)
		}
		for _, shard := range []struct {
			count int
			want  int
		}{{1, 0}, {8, test.shards8}, {32, test.shards32}, {128, test.shards128}, {65536, test.shards65536}} {
			if got := int(shardHash(test.key) & uint64(shard.count-1)); got != shard.want {
				t.Errorf("shardHash(%+q) with %d shards = %d, want %d", test.key, shard.count, got, shard.want)
			}
		}
	}
}

func TestExpirationIndex(t *testing.T) {
	cache, _ := testCache(t, nil)
	if err := cache.SetWithExpiration("key", 1, time.Minute); err != nil {
		t.Fatal(err)
	}
	for range 100 {
		if found, err := cache.Touch("key", 2*time.Minute); err != nil || !found {
			t.Fatalf("Touch = %v, %v", found, err)
		}
	}
	shard := cache.shards[0]
	shard.mu.RLock()
	if len(shard.expiry) != 1 || shard.expiry[0].expiryIndex != 0 {
		t.Fatalf("expiry heap accumulated stale records: %d", len(shard.expiry))
	}
	shard.mu.RUnlock()
	for range 100 {
		if err := cache.SetWithExpiration("key", 2, time.Minute); err != nil {
			t.Fatal(err)
		}
	}
	shard.mu.RLock()
	defer shard.mu.RUnlock()
	if len(shard.expiry) != 1 || shard.liveCount != 1 || len(shard.ungrouped) != 1 || len(shard.groups) != 0 {
		t.Fatalf("replacement indexes: heap=%d count=%d ungrouped=%d groups=%d", len(shard.expiry), shard.liveCount, len(shard.ungrouped), len(shard.groups))
	}
}

func TestExpirationIndexTransitions(t *testing.T) {
	cache, clock := testCache(t, nil)
	if err := cache.Set("persistent", 1); err != nil {
		t.Fatal(err)
	}
	if err := cache.SetWithExpiration("late", 2, 2*time.Minute); err != nil {
		t.Fatal(err)
	}
	if err := cache.SetWithExpiration("middle", 3, time.Minute); err != nil {
		t.Fatal(err)
	}
	if err := cache.SetWithExpiration("persistent", 4, 30*time.Second); err != nil {
		t.Fatal(err)
	}
	shard := cache.shards[0]
	shard.mu.RLock()
	heapLength := len(shard.expiry)
	var root *cacheItem
	if heapLength != 0 {
		root = shard.expiry[0]
	}
	wantRoot := shard.memberLocked(EntryKey{Key: "persistent"})
	shard.mu.RUnlock()
	if heapLength != 3 || root != wantRoot {
		t.Fatalf("TTL insertion heap length/root = %d/%v", heapLength, root)
	}
	if err := cache.SetWithExpiration("late", 5, NoExpiration); err != nil {
		t.Fatal(err)
	}
	if err := cache.SetWithExpiration("persistent", 6, NoExpiration); err != nil {
		t.Fatal(err)
	}
	shard.mu.RLock()
	late := shard.memberLocked(EntryKey{Key: "late"})
	heapLength = len(shard.expiry)
	root = nil
	if heapLength != 0 {
		root = shard.expiry[0]
	}
	wantRoot = shard.memberLocked(EntryKey{Key: "middle"})
	lateIndex := late.expiryIndex
	shard.mu.RUnlock()
	if heapLength != 1 || root != wantRoot || lateIndex != -1 {
		t.Fatalf("TTL removal heap length/root/index = %d/%v/%d", heapLength, root, lateIndex)
	}
	if _, expiration, found := cache.GetWithExpiration("middle"); !found || !expiration.Equal(clock.Now().Add(time.Minute)) {
		t.Fatalf("middle expiration = %v, %v", expiration, found)
	}
	assertMembershipInvariants(t, shard)
}

func TestExistingKeyUpdatedInPlace(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			cache, _ := testCache(t, func(options *Options) {
				options.MaxEntriesPerShard = 2
				options.EvictionPolicy = policy
			})
			group, _ := cache.Group("group")
			var events []eviction
			if err := cache.OnEvicted(func(key EntryKey, value any, reason EvictionReason) {
				events = append(events, eviction{key: key, value: value, reason: reason})
			}); err != nil {
				t.Fatal(err)
			}
			if err := group.SetWithExpiration("key", "old", time.Hour); err != nil {
				t.Fatal(err)
			}
			if err := cache.Set("other", "other"); err != nil {
				t.Fatal(err)
			}
			shard := cache.shards[0]
			shard.mu.RLock()
			before := shard.memberLocked(EntryKey{Group: "group", Key: "key"})
			shard.mu.RUnlock()

			if err := group.SetWithExpiration("key", "new", 2*time.Hour); err != nil {
				t.Fatal(err)
			}
			shard.mu.RLock()
			after := shard.memberLocked(EntryKey{Group: "group", Key: "key"})
			var afterValue any
			if after != nil {
				afterValue = after.value
			}
			heapLength, count := len(shard.expiry), shard.liveCount
			shard.mu.RUnlock()
			if after != before || afterValue != "new" || heapLength != 1 || count != 2 {
				t.Fatalf("replacement item=%p/%p value=%v heap=%d count=%d", before, after, afterValue, heapLength, count)
			}
			wantEvent := eviction{key: EntryKey{Group: "group", Key: "key"}, value: "old", reason: EvictionReasonReplaced}
			if !reflect.DeepEqual(events, []eviction{wantEvent}) {
				t.Fatalf("replacement events = %+v", events)
			}
			if version := shard.mutationVersion.Load(); version != 0 {
				t.Fatalf("persistence-disabled mutation version = %d", version)
			}

			if err := cache.Set("newest", "newest"); err != nil {
				t.Fatal(err)
			}
			if _, found := cache.Get("other"); found {
				t.Fatal("replacement did not move the existing item to newest")
			}
			if value, found := group.Get("key"); !found || value != "new" {
				t.Fatalf("replaced value = %v, %v", value, found)
			}
		})
	}
}

func TestExpiredExistingKeyIsNotReplacement(t *testing.T) {
	cache, clock := testCache(t, nil)
	var events []eviction
	if err := cache.OnEvicted(func(key EntryKey, value any, reason EvictionReason) {
		events = append(events, eviction{key: key, value: value, reason: reason})
	}); err != nil {
		t.Fatal(err)
	}
	if err := cache.SetWithExpiration("key", "old", time.Minute); err != nil {
		t.Fatal(err)
	}
	shard := cache.shards[0]
	shard.mu.RLock()
	before := shard.memberLocked(EntryKey{Key: "key"})
	shard.mu.RUnlock()
	clock.Advance(time.Minute)
	if err := cache.SetWithExpiration("key", "new", time.Hour); err != nil {
		t.Fatal(err)
	}
	shard.mu.RLock()
	after := shard.memberLocked(EntryKey{Key: "key"})
	heapLength, count := len(shard.expiry), shard.liveCount
	shard.mu.RUnlock()
	if after == before || heapLength != 1 || count != 1 {
		t.Fatalf("expired replacement item=%p/%p heap=%d count=%d", before, after, heapLength, count)
	}
	want := []eviction{{key: EntryKey{Key: "key"}, value: "old", reason: EvictionReasonExpired}}
	if !reflect.DeepEqual(events, want) {
		t.Fatalf("expired replacement events = %+v", events)
	}
}

func TestExistingKeyUpdateAllocations(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			cache, _ := testCache(t, func(options *Options) { options.EvictionPolicy = policy })
			const key = "key"
			var value any = "value"
			if err := cache.Set(key, value); err != nil {
				t.Fatal(err)
			}
			if allocations := testing.AllocsPerRun(1000, func() {
				if err := cache.Set(key, value); err != nil {
					panic(err)
				}
			}); allocations != 0 {
				t.Fatalf("replacement allocations = %v", allocations)
			}
			if allocations := testing.AllocsPerRun(1000, func() {
				if err := cache.SetWithExpiration(key, value, time.Hour); err != nil {
					panic(err)
				}
			}); allocations != 0 {
				t.Fatalf("TTL update allocations = %v", allocations)
			}
		})
	}
}

func TestRemovalWithoutCallbackAllocations(t *testing.T) {
	for _, test := range []struct {
		name      string
		reason    EvictionReason
		expiresAt time.Time
	}{
		{name: "capacity", reason: EvictionReasonCapacity},
		{name: "expiration", reason: EvictionReasonExpired, expiresAt: time.Unix(1, 0)},
	} {
		t.Run(test.name, func(t *testing.T) {
			shard := newCacheShard(1, FIFO, false)
			item := &cacheItem{key: "key", value: "value", expiresAt: test.expiresAt, expiryIndex: -1}
			insert := func() {
				shard.insertMemberLocked(EntryKey{Key: "key"}, item)
				shard.appendPolicyLocked(item)
				shard.liveCount++
				if !item.expiresAt.IsZero() {
					heap.Push(&shard.expiry, item)
				}
			}
			shard.mu.Lock()
			insert()
			shard.mu.Unlock()
			if allocations := testing.AllocsPerRun(1000, func() {
				shard.mu.Lock()
				var result mutationResult
				shard.removeLocked(item, test.reason, true, false, &result)
				if len(result.events) != 0 || !result.changed {
					panic("removal result is inconsistent")
				}
				insert()
				shard.mu.Unlock()
			}); allocations != 0 {
				t.Fatalf("removal allocations = %v", allocations)
			}
		})
	}
}

func TestPointReadClockUsage(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			options := DefaultOptions()
			options.ShardCount = 1
			options.CleanupEnabled = false
			options.EvictionPolicy = policy
			clock := &countingClock{base: newManualClock()}
			cache, err := newWithClock(options, clock)
			if err != nil {
				t.Fatal(err)
			}
			defer cache.Close()
			if err := cache.Set("hit", "value"); err != nil {
				t.Fatal(err)
			}
			checks := []struct {
				name string
				run  func()
			}{
				{name: "Get hit", run: func() { cache.Get("hit") }},
				{name: "Get miss", run: func() { cache.Get("miss") }},
				{name: "GetWithExpiration hit", run: func() { cache.GetWithExpiration("hit") }},
				{name: "GetWithExpiration miss", run: func() { cache.GetWithExpiration("miss") }},
				{name: "Has hit", run: func() { cache.Has("hit") }},
				{name: "Has miss", run: func() { cache.Has("miss") }},
			}
			for _, check := range checks {
				clock.reset()
				check.run()
				if clock.calls != 0 {
					t.Errorf("%s clock calls = %d", check.name, clock.calls)
				}
			}
			if err := cache.SetWithExpiration("ttl", "value", time.Hour); err != nil {
				t.Fatal(err)
			}
			clock.reset()
			if _, found := cache.Get("ttl"); !found || clock.calls != 1 {
				t.Fatalf("TTL Get found/calls = %v/%d", found, clock.calls)
			}
		})
	}
}

func TestPointReadsDoNotAcquireLifecycleLock(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			cache, _ := testCache(t, func(options *Options) { options.EvictionPolicy = policy })
			if err := cache.Set("key", "value"); err != nil {
				t.Fatal(err)
			}
			locks := make(chan struct{}, 1)
			cache.lifecycleHooks = &lifecycleTestHooks{gateReadLock: func() { locks <- struct{}{} }}
			operations := []struct {
				name string
				run  func()
			}{
				{name: "Get", run: func() { cache.Get("key") }},
				{name: "GetWithExpiration", run: func() { cache.GetWithExpiration("key") }},
				{name: "Has", run: func() { cache.Has("key") }},
			}
			for _, operation := range operations {
				cache.gate.Lock()
				done := make(chan struct{})
				go func() {
					operation.run()
					close(done)
				}()
				select {
				case <-done:
					cache.gate.Unlock()
				case <-locks:
					cache.gate.Unlock()
					<-done
					t.Fatalf("%s acquired the lifecycle read lock", operation.name)
				case <-time.After(time.Second):
					cache.gate.Unlock()
					t.Fatalf("%s blocked on the lifecycle lock", operation.name)
				}
			}
		})
	}
}

func TestFIFOReadsShareShardReadLock(t *testing.T) {
	cache, _ := testCache(t, nil)
	if err := cache.Set("first", 1); err != nil {
		t.Fatal(err)
	}
	if err := cache.Set("second", 2); err != nil {
		t.Fatal(err)
	}
	firstEntered := make(chan struct{})
	secondEntered := make(chan struct{})
	release := make(chan struct{})
	var entered atomic.Int32
	cache.shards[0].pointReadHooks = &pointReadTestHooks{fifoLocked: func() {
		if entered.Add(1) == 1 {
			close(firstEntered)
			<-release
			return
		}
		close(secondEntered)
	}}
	results := make(chan bool, 2)
	go func() { _, found := cache.Get("first"); results <- found }()
	select {
	case <-firstEntered:
	case <-time.After(time.Second):
		close(release)
		t.Fatal("first FIFO read did not enter its read lock")
	}
	go func() { _, found := cache.Get("second"); results <- found }()
	select {
	case <-secondEntered:
	case <-time.After(time.Second):
		close(release)
		t.Fatal("second FIFO read did not enter while the first held its read lock")
	}
	close(release)
	for range 2 {
		if !<-results {
			t.Fatal("FIFO read missed a live key")
		}
	}
	cache.shards[0].pointReadHooks = nil
}

func TestConcurrentFIFOExpirationIsRemovedOnce(t *testing.T) {
	cache, clock := testCache(t, nil)
	if err := cache.SetWithExpiration("key", "value", time.Minute); err != nil {
		t.Fatal(err)
	}
	clock.Advance(time.Minute)
	var callbacks atomic.Int32
	if err := cache.OnEvicted(func(_ EntryKey, _ any, reason EvictionReason) {
		if reason != EvictionReasonExpired {
			t.Errorf("reason = %v", reason)
		}
		callbacks.Add(1)
	}); err != nil {
		t.Fatal(err)
	}
	entered := make(chan struct{}, 2)
	release := make(chan struct{})
	cache.shards[0].pointReadHooks = &pointReadTestHooks{fifoLocked: func() {
		entered <- struct{}{}
		<-release
	}}
	results := make(chan bool, 2)
	for range 2 {
		go func() { _, found := cache.Get("key"); results <- found }()
	}
	for range 2 {
		select {
		case <-entered:
		case <-time.After(time.Second):
			close(release)
			t.Fatal("FIFO expiration reader did not enter its read lock")
		}
	}
	close(release)
	for range 2 {
		if <-results {
			t.Fatal("expired key was reported found")
		}
	}
	cache.shards[0].pointReadHooks = nil
	if callbacks.Load() != 1 || cache.Count() != 0 {
		t.Fatalf("expiration callbacks/count = %d/%d", callbacks.Load(), cache.Count())
	}
}

func TestPointReadOrdinalsOnlyTrackPersistence(t *testing.T) {
	cache, _ := testCache(t, func(options *Options) { options.EvictionPolicy = LRU })
	if err := cache.Set("first", 1); err != nil {
		t.Fatal(err)
	}
	if err := cache.Set("second", 2); err != nil {
		t.Fatal(err)
	}
	if _, found := cache.Get("first"); !found {
		t.Fatal("LRU read missed")
	}
	if ordinal := cache.ordinal.Load(); ordinal != 0 {
		t.Fatalf("persistence-disabled ordinal = %d", ordinal)
	}
	shard := cache.shards[0]
	shard.mu.RLock()
	newest := shard.newest
	wantNewest := shard.memberLocked(EntryKey{Key: "first"})
	shard.mu.RUnlock()
	if newest != wantNewest {
		t.Fatal("LRU read did not promote the item")
	}

	t.Run("persistent", func(t *testing.T) {
		requirePersistenceSupport(t)
		options := persistentOptions(t.TempDir(), 1)
		options.EvictionPolicy = LRU
		persistent, err := New(options)
		if err != nil {
			t.Fatal(err)
		}
		defer persistent.Close()
		if err := persistent.Set("first", 1); err != nil {
			t.Fatal(err)
		}
		if err := persistent.Set("second", 2); err != nil {
			t.Fatal(err)
		}
		beforeOrdinal := persistent.ordinal.Load()
		beforeVersion := persistent.shards[0].mutationVersion.Load()
		if _, found := persistent.Get("first"); !found {
			t.Fatal("persistent LRU read missed")
		}
		if ordinal := persistent.ordinal.Load(); ordinal != beforeOrdinal+1 {
			t.Fatalf("persistence-enabled ordinal = %d, want %d", ordinal, beforeOrdinal+1)
		}
		if version := persistent.shards[0].mutationVersion.Load(); version != beforeVersion {
			t.Fatalf("LRU read changed persistence mutation version: %d -> %d", beforeVersion, version)
		}
	})
}

func TestExpirationBoundary(t *testing.T) {
	cache, clock := testCache(t, nil)
	if err := cache.SetWithExpiration("key", "value", time.Minute); err != nil {
		t.Fatal(err)
	}
	clock.Advance(time.Minute)
	if value, found := cache.Get("key"); found || value != nil {
		t.Fatalf("Get at exact expiration = %v, %v", value, found)
	}
	if cache.Count() != 0 {
		t.Fatal("due entry remained counted")
	}
}

func TestExpirationCheckedAfterShardLock(t *testing.T) {
	cache, baseClock := testCache(t, nil)
	if err := cache.SetWithExpiration("key", "value", time.Minute); err != nil {
		t.Fatal(err)
	}
	var reasons []EvictionReason
	if err := cache.OnEvicted(func(_ EntryKey, _ any, reason EvictionReason) { reasons = append(reasons, reason) }); err != nil {
		t.Fatal(err)
	}

	gated := &gatedSampleClock{base: baseClock, sampled: make(chan struct{}), release: make(chan struct{})}
	cache.clock = gated
	shard := cache.shards[0]
	shard.mu.Lock()
	started := make(chan struct{})
	result := make(chan bool, 1)
	go func() {
		close(started)
		_, found := cache.Get("key")
		result <- found
	}()
	<-started

	sampledBeforeUnlock := false
	select {
	case <-gated.sampled:
		sampledBeforeUnlock = true
	case <-time.After(100 * time.Millisecond):
	}
	baseClock.Advance(time.Minute)
	shard.mu.Unlock()
	if !sampledBeforeUnlock {
		select {
		case <-gated.sampled:
		case <-time.After(time.Second):
			t.Fatal("Get did not sample time after acquiring the shard lock")
		}
	}
	close(gated.release)

	select {
	case found := <-result:
		if found {
			t.Fatal("Get returned an entry that expired while waiting for the shard lock")
		}
	case <-time.After(time.Second):
		t.Fatal("Get remained blocked after releasing the shard lock")
	}
	if !reflect.DeepEqual(reasons, []EvictionReason{EvictionReasonExpired}) {
		t.Fatalf("expiration reasons = %v", reasons)
	}
}

func TestEvictionPolicyPromotionMatrix(t *testing.T) {
	operations := []struct {
		name         string
		promotesLRU  bool
		promotesFIFO bool
		run          func(*testing.T, *ShardedCache)
	}{
		{"replace", true, true, func(t *testing.T, c *ShardedCache) { t.Helper(); _ = c.Set("a", 10) }},
		{"get", true, false, func(t *testing.T, c *ShardedCache) { t.Helper(); c.Get("a") }},
		{"get expiration", true, false, func(t *testing.T, c *ShardedCache) { t.Helper(); c.GetWithExpiration("a") }},
		{"has", true, false, func(t *testing.T, c *ShardedCache) { t.Helper(); c.Has("a") }},
		{"get or set hit", true, false, func(t *testing.T, c *ShardedCache) { t.Helper(); _, _ = c.GetOrSet("a", 10) }},
		{"loader hit", true, false, func(t *testing.T, c *ShardedCache) {
			t.Helper()
			_, _ = c.GetOrSetFunc(context.Background(), "a", func(context.Context) (any, error) { return 10, nil })
		}},
		{"touch", false, false, func(t *testing.T, c *ShardedCache) { t.Helper(); _, _ = c.Touch("a", 2*time.Hour) }},
		{"persist", false, false, func(t *testing.T, c *ShardedCache) { t.Helper(); _, _ = c.Persist("a") }},
		{"miss", false, false, func(t *testing.T, c *ShardedCache) { t.Helper(); c.Get("missing") }},
		{"range", false, false, func(t *testing.T, c *ShardedCache) {
			t.Helper()
			c.Range(func(EntryKey, any, time.Time) bool { return true })
		}},
	}
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		for _, operation := range operations {
			t.Run(policy.String()+"/"+operation.name, func(t *testing.T) {
				cache, _ := testCache(t, func(o *Options) {
					o.MaxEntriesPerShard = 2
					o.EvictionPolicy = policy
				})
				_ = cache.SetWithExpiration("a", 1, time.Hour)
				_ = cache.Set("b", 2)
				operation.run(t, cache)
				_ = cache.Set("c", 3)
				shard := cache.shards[0]
				shard.mu.RLock()
				hasA := shard.memberLocked(EntryKey{Key: "a"}) != nil
				hasB := shard.memberLocked(EntryKey{Key: "b"}) != nil
				shard.mu.RUnlock()
				promotes := operation.promotesFIFO
				if policy == LRU {
					promotes = operation.promotesLRU
				}
				if promotes && (!hasA || hasB) {
					t.Fatalf("promoting operation evicted wrong key: a=%v b=%v", hasA, hasB)
				}
				if !promotes && (hasA || !hasB) {
					t.Fatalf("non-promoting operation changed order: a=%v b=%v", hasA, hasB)
				}
			})
		}
	}
}

func TestNamespaceIdentity(t *testing.T) {
	cache, _ := testCache(t, nil)
	first, err := cache.Group("group")
	if err != nil {
		t.Fatal(err)
	}
	second, err := cache.Group("group\x00:key")
	if err != nil {
		t.Fatal(err)
	}
	key := "x\x00:y"
	_ = cache.Set(key, "cache")
	_ = first.Set(key, "first")
	_ = second.Set("x", "second")
	if value, _ := cache.Get(key); value != "cache" {
		t.Fatalf("cache value = %v", value)
	}
	if value, _ := first.Get(key); value != "first" {
		t.Fatalf("first value = %v", value)
	}
	if value, _ := second.Get("x"); value != "second" {
		t.Fatalf("second value = %v", value)
	}
}

func assertMembershipInvariants(t *testing.T, shard *cacheShard) {
	t.Helper()
	shard.mu.RLock()
	defer shard.mu.RUnlock()

	members := make(map[*cacheItem]EntryKey, shard.liveCount)
	record := func(item *cacheItem, key EntryKey) {
		if item == nil {
			t.Fatalf("nil member for %+q", key)
		}
		if prior, duplicate := members[item]; duplicate {
			t.Fatalf("item is reachable as both %+q and %+q", prior, key)
		}
		members[item] = key
		if got := item.entryKey(); got != key {
			t.Fatalf("item identity = %+q, want %+q", got, key)
		}
	}
	for key, item := range shard.ungrouped {
		if item.namespace != nil {
			t.Fatalf("ungrouped item %q has namespace %q", key, item.namespace.group)
		}
		record(item, EntryKey{Key: key})
	}
	for group, namespace := range shard.groups {
		if group == "" || namespace == nil || namespace.group != group || len(namespace.members) == 0 {
			t.Fatalf("invalid namespace %q: %+v", group, namespace)
		}
		for key, item := range namespace.members {
			if item.namespace != namespace {
				t.Fatalf("grouped item %+q points at another namespace", EntryKey{Group: group, Key: key})
			}
			record(item, EntryKey{Group: group, Key: key})
		}
	}
	if len(members) != shard.liveCount {
		t.Fatalf("membership count = %d, live count = %d", len(members), shard.liveCount)
	}

	policyItems := make(map[*cacheItem]struct{}, shard.liveCount)
	var previous *cacheItem
	for item := shard.oldest; item != nil; item = item.next {
		if _, duplicate := policyItems[item]; duplicate {
			t.Fatal("policy chain contains a cycle or duplicate item")
		}
		if item.previous != previous {
			t.Fatal("policy chain has inconsistent previous link")
		}
		if _, found := members[item]; !found {
			t.Fatalf("policy item %+q has no membership", item.entryKey())
		}
		policyItems[item] = struct{}{}
		previous = item
	}
	if previous != shard.newest || len(policyItems) != shard.liveCount {
		t.Fatalf("policy count = %d, live count = %d", len(policyItems), shard.liveCount)
	}

	expiryItems := make(map[*cacheItem]struct{}, len(shard.expiry))
	for index, item := range shard.expiry {
		if item.expiryIndex != index {
			t.Fatalf("expiry index for %+q = %d, want %d", item.entryKey(), item.expiryIndex, index)
		}
		if item.expiresAt.IsZero() {
			t.Fatalf("non-expiring item %+q is in expiry heap", item.entryKey())
		}
		if _, found := members[item]; !found {
			t.Fatalf("expiry item %+q has no membership", item.entryKey())
		}
		expiryItems[item] = struct{}{}
	}
	for item, key := range members {
		_, inExpiry := expiryItems[item]
		if item.expiresAt.IsZero() == inExpiry {
			t.Fatalf("expiry membership for %+q is inconsistent", key)
		}
	}
}

func TestNamespaceMembershipInvariants(t *testing.T) {
	cache, clock := testCache(t, func(options *Options) {
		options.MaxEntriesPerShard = 4
		options.EvictionPolicy = LRU
	})
	first, _ := cache.Group("first")
	second, _ := cache.Group("second")
	must := func(err error) {
		t.Helper()
		if err != nil {
			t.Fatal(err)
		}
	}

	must(cache.Set("shared", "ungrouped"))
	must(first.SetWithExpiration("shared", "first", time.Minute))
	must(second.Set("shared", "second"))
	must(cache.SetWithExpiration("temporary", "temporary", time.Minute))
	assertMembershipInvariants(t, cache.shards[0])

	must(first.SetWithExpiration("shared", "replaced", 2*time.Minute))
	if found, err := cache.Persist("temporary"); err != nil || !found {
		t.Fatalf("Persist = %v, %v", found, err)
	}
	if found, err := second.Delete("shared"); err != nil || !found {
		t.Fatalf("Delete = %v, %v", found, err)
	}
	assertMembershipInvariants(t, cache.shards[0])

	must(first.SetWithExpiration("due", "due", time.Minute))
	clock.Advance(time.Minute)
	if count := cache.Count(); count != 3 {
		t.Fatalf("live count after expiration = %d", count)
	}
	if _, err := cache.GetOrSet("loaded", "loaded"); err != nil {
		t.Fatal(err)
	}
	assertMembershipInvariants(t, cache.shards[0])

	if err := first.Clear(); err != nil {
		t.Fatal(err)
	}
	if deleted, err := cache.DeletePrefix("temp"); err != nil || deleted != 1 {
		t.Fatalf("DeletePrefix = %d, %v", deleted, err)
	}
	assertMembershipInvariants(t, cache.shards[0])
}

func TestLiveCounts(t *testing.T) {
	cache, clock := testCache(t, nil)
	group, _ := cache.Group("g")
	_ = cache.Set("a", 1)
	_ = group.SetWithExpiration("b", 2, time.Minute)
	if cache.Count() != 2 || group.Count() != 1 {
		t.Fatalf("initial counts = %d, %d", cache.Count(), group.Count())
	}
	clock.Advance(time.Minute)
	if cache.Count() != 1 || group.Count() != 0 {
		t.Fatalf("live counts = %d, %d", cache.Count(), group.Count())
	}
}

func TestExpiredOperationMatrix(t *testing.T) {
	operations := []struct {
		name string
		run  func(*ShardedCache) bool
	}{
		{"Get", func(c *ShardedCache) bool { _, found := c.Get("key"); return found }},
		{"GetWithExpiration", func(c *ShardedCache) bool { _, _, found := c.GetWithExpiration("key"); return found }},
		{"Has", func(c *ShardedCache) bool { return c.Has("key") }},
		{"Touch", func(c *ShardedCache) bool { found, _ := c.Touch("key", time.Minute); return found }},
		{"Persist", func(c *ShardedCache) bool { found, _ := c.Persist("key"); return found }},
		{"Delete", func(c *ShardedCache) bool { found, _ := c.Delete("key"); return found }},
	}
	for _, operation := range operations {
		t.Run(operation.name, func(t *testing.T) {
			cache, clock := testCache(t, nil)
			var reasons []EvictionReason
			_ = cache.OnEvicted(func(_ EntryKey, _ any, reason EvictionReason) { reasons = append(reasons, reason) })
			_ = cache.SetWithExpiration("key", 1, time.Minute)
			clock.Advance(time.Minute)
			if operation.run(cache) {
				t.Fatal("expired key reported found")
			}
			if !reflect.DeepEqual(reasons, []EvictionReason{EvictionReasonExpired}) {
				t.Fatalf("reasons = %v", reasons)
			}
		})
	}
}

func TestCapacityReclaimsExpiredFirst(t *testing.T) {
	cache, clock := testCache(t, func(o *Options) { o.MaxEntriesPerShard = 2 })
	var events []eviction
	_ = cache.OnEvicted(func(key EntryKey, value any, reason EvictionReason) {
		events = append(events, eviction{key: key, value: value, reason: reason})
	})
	_ = cache.SetWithExpiration("expired", 1, time.Minute)
	_ = cache.Set("live", 2)
	clock.Advance(time.Minute)
	_ = cache.Set("new", 3)
	if _, found := cache.Get("live"); !found {
		t.Fatal("live entry was capacity-evicted while an expired entry remained")
	}
	if len(events) != 1 || events[0].key.Key != "expired" || events[0].reason != EvictionReasonExpired {
		t.Fatalf("events = %+v", events)
	}
}

func TestStatsAccounting(t *testing.T) {
	cache, _ := testCache(t, func(o *Options) { o.MaxEntriesPerShard = 3 })
	_ = cache.Set("hit", 1)
	cache.Get("hit")
	cache.GetWithExpiration("miss")
	cache.Has("hit")
	value, err := cache.GetOrSet("new", 2)
	if err != nil || value != 2 {
		t.Fatalf("GetOrSet = %v, %v", value, err)
	}
	before := cache.Stats()
	cache.Count()
	cache.Range(func(EntryKey, any, time.Time) bool { return true })
	after := cache.Stats()
	if before.Hits != 2 || before.Misses != 2 || before.TotalCount != 2 || before.HitRate != .5 {
		t.Fatalf("Stats = %+v", before)
	}
	if before.Hits != after.Hits || before.Misses != after.Misses {
		t.Fatalf("introspection changed query counters: before=%+v after=%+v", before, after)
	}
	if after.MaxEntriesPerShard != 3 || after.EffectiveMaxEntries != 3 || after.ShardCount != 1 || after.EvictionPolicy != FIFO {
		t.Fatalf("typed configuration stats = %+v", after)
	}
}

func TestRangeBehavior(t *testing.T) {
	cache, _ := testCache(t, func(o *Options) { o.ShardCount = 4 })
	group, _ := cache.Group("g")
	_ = cache.Set("a", 1)
	_ = group.Set("a", 2)
	_ = group.Set("b", 3)
	visited := make(map[EntryKey]any)
	cache.Range(func(key EntryKey, value any, _ time.Time) bool {
		visited[key] = value
		_ = cache.Set("reentrant", 4)
		return true
	})
	if len(visited) != 3 || visited[EntryKey{Key: "a"}] != 1 || visited[EntryKey{Group: "g", Key: "a"}] != 2 {
		t.Fatalf("visited = %#v", visited)
	}
	calls := 0
	cache.Range(func(EntryKey, any, time.Time) bool { calls++; return false })
	if calls != 1 {
		t.Fatalf("early stop calls = %d", calls)
	}
	var groupKeys []string
	group.Range(func(key string, _ any, _ time.Time) bool { groupKeys = append(groupKeys, key); return true })
	sort.Strings(groupKeys)
	if !reflect.DeepEqual(groupKeys, []string{"a", "b"}) {
		t.Fatalf("group keys = %v", groupKeys)
	}
}

func TestGroupIsolation(t *testing.T) {
	cache, _ := testCache(t, nil)
	first, _ := cache.Group("first")
	second, _ := cache.Group("second")
	for _, target := range []interface{ Set(string, any) error }{first, second} {
		_ = target.Set("prefix:1", 1)
		_ = target.Set("other", 2)
	}
	_ = cache.Set("prefix:1", 3)
	if deleted, err := first.DeletePrefix("prefix:"); err != nil || deleted != 1 {
		t.Fatalf("DeletePrefix = %d, %v", deleted, err)
	}
	if first.Count() != 1 || second.Count() != 2 || cache.Count() != 4 {
		t.Fatalf("counts cache=%d first=%d second=%d", cache.Count(), first.Count(), second.Count())
	}
	if err := second.Clear(); err != nil {
		t.Fatal(err)
	}
	if first.Count() != 1 || second.Count() != 0 || cache.Count() != 2 {
		t.Fatalf("clear isolation cache=%d first=%d second=%d", cache.Count(), first.Count(), second.Count())
	}
}

func TestBatchWorkerBounds(t *testing.T) {
	cache, _ := testCache(t, func(o *Options) { o.ShardCount = 8 })
	keys := make([]string, 200)
	for i := range keys {
		keys[i] = strings.Repeat("k", i%7) + string(rune(i))
		_ = cache.Set(keys[i], i)
	}
	withDuplicates := append(append([]string(nil), keys...), keys...)
	deleted, err := cache.DeleteKeys(withDuplicates)
	if err != nil || deleted != len(keys) || cache.Count() != 0 {
		t.Fatalf("DeleteKeys = %d, %v, count=%d", deleted, err, cache.Count())
	}

	inline := false
	oneResult := runShardJobs(map[int]struct{}{0: {}}, func(int, struct{}) int {
		inline = true
		return 1
	})
	if !inline {
		t.Fatal("one-shard batch work did not run inline")
	}
	<-oneResult

	previous := runtime.GOMAXPROCS(2)
	defer runtime.GOMAXPROCS(previous)
	jobs := map[int]struct{}{0: {}, 1: {}, 2: {}, 3: {}}
	entered := make(chan struct{}, len(jobs))
	release := make(chan struct{})
	results := runShardJobs(jobs, func(index int, _ struct{}) int {
		entered <- struct{}{}
		<-release
		return index
	})
	for range 2 {
		<-entered
	}
	exceeded := false
	select {
	case <-entered:
		exceeded = true
	case <-time.After(50 * time.Millisecond):
	}
	close(release)
	completed := 0
	for range results {
		completed++
	}
	if exceeded {
		t.Fatal("cross-shard batch exceeded GOMAXPROCS worker bound")
	}
	if completed != len(jobs) {
		t.Fatalf("completed shard jobs = %d, want %d", completed, len(jobs))
	}
}

func TestClearClassifiesExpiredFirst(t *testing.T) {
	cache, clock := testCache(t, nil)
	var reasons = make(map[string]EvictionReason)
	_ = cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) { reasons[key.Key] = reason })
	_ = cache.SetWithExpiration("expired", 1, time.Minute)
	_ = cache.Set("live", 2)
	clock.Advance(time.Minute)
	if err := cache.Clear(); err != nil {
		t.Fatal(err)
	}
	if reasons["expired"] != EvictionReasonExpired || reasons["live"] != EvictionReasonCleared {
		t.Fatalf("clear reasons = %v", reasons)
	}
}

func TestForegroundCallbacks(t *testing.T) {
	cache, clock := testCache(t, nil)
	var reasons []EvictionReason
	if err := cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) {
		reasons = append(reasons, reason)
		if key.Key != "nested" {
			_ = cache.Set("nested", 1)
		}
	}); err != nil {
		t.Fatal(err)
	}
	_ = cache.SetWithExpiration("expired", 1, time.Minute)
	clock.Advance(time.Minute)
	cache.Get("expired")
	if len(reasons) != 1 || reasons[0] != EvictionReasonExpired {
		t.Fatalf("callback was not synchronous or exact: %v", reasons)
	}
	if _, found := cache.Get("nested"); !found {
		t.Fatal("callback could not re-enter cache")
	}
}

func TestCallbackRegistrationConcurrentWithMutation(t *testing.T) {
	cache, _ := testCache(t, nil)
	start := make(chan struct{})
	var wait sync.WaitGroup
	wait.Go(func() {
		<-start
		for index := range 500 {
			var callback func(EntryKey, any, EvictionReason)
			if index%2 == 0 {
				callback = func(EntryKey, any, EvictionReason) {}
			}
			if err := cache.OnEvicted(callback); err != nil {
				t.Errorf("OnEvicted: %v", err)
				return
			}
		}
	})
	wait.Go(func() {
		<-start
		for index := range 500 {
			if err := cache.Set("key", index); err != nil {
				t.Errorf("Set: %v", err)
				return
			}
		}
	})
	close(start)
	wait.Wait()
}

func TestPointReadAllocations(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			options := DefaultOptions()
			options.CleanupEnabled = false
			options.EvictionPolicy = policy
			cache, err := New(options)
			if err != nil {
				t.Fatal(err)
			}
			defer cache.Close()
			if err := cache.Set("hit", 1); err != nil {
				t.Fatal(err)
			}
			if allocations := testing.AllocsPerRun(1000, func() { cache.Get("hit") }); allocations != 0 {
				t.Fatalf("hit allocations = %v", allocations)
			}
			if allocations := testing.AllocsPerRun(1000, func() { cache.Get("miss") }); allocations != 0 {
				t.Fatalf("miss allocations = %v", allocations)
			}
		})
	}
}

func TestLoaderPointAccounting(t *testing.T) {
	cache, _ := testCache(t, nil)
	value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) { return 1, nil })
	if err != nil || value != 1 {
		t.Fatalf("load = %v, %v", value, err)
	}
	value, err = cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) { return 2, nil })
	if err != nil || value != 1 {
		t.Fatalf("hit = %v, %v", value, err)
	}
	stats := cache.Stats()
	if stats.Hits != 1 || stats.Misses != 1 {
		t.Fatalf("loader stats = %+v", stats)
	}
}
