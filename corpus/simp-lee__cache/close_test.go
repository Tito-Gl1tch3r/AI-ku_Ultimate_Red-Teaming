package shardedcache

import (
	"context"
	"errors"
	"runtime"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestCleanerDeadlines(t *testing.T) {
	cache, clock := testCache(t, nil)
	_ = cache.SetWithExpiration("late", 1, 2*time.Minute)
	_ = cache.SetWithExpiration("early", 2, time.Minute)
	deadline, found := cache.nextExpiration()
	if !found || !deadline.Equal(clock.Now().Add(time.Minute)) {
		t.Fatalf("earliest deadline = %v, %v", deadline, found)
	}
	clock.Advance(time.Minute)
	cache.expireDueInBackground()
	if _, found := cache.Get("early"); found {
		t.Fatal("due entry survived deadline cleanup")
	}
	if _, found := cache.Get("late"); !found {
		t.Fatal("later entry was removed")
	}
}

func TestMaintenanceWakeConditions(t *testing.T) {
	t.Run("disabled workers", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		var cleanerWakes, persisterWakes atomic.Int32
		cache.maintenanceHooks = &maintenanceTestHooks{
			cleanWake:   func() { cleanerWakes.Add(1) },
			persistWake: func() { persisterWakes.Add(1) },
		}
		if err := cache.SetWithExpiration("key", "value", time.Hour); err != nil {
			t.Fatal(err)
		}
		if cleanerWakes.Load() != 0 || persisterWakes.Load() != 0 || len(cache.cleanWake) != 0 || len(cache.persistWake) != 0 {
			t.Fatalf("disabled maintenance wakes = cleaner %d, persister %d", cleanerWakes.Load(), persisterWakes.Load())
		}
		if version := cache.shards[0].mutationVersion.Load(); version != 0 {
			t.Fatalf("persistence-disabled mutation version = %d", version)
		}
	})

	t.Run("periodic persistence", func(t *testing.T) {
		requirePersistenceSupport(t)
		options := persistentOptions(t.TempDir(), 1)
		options.Persistence.Interval = time.Hour
		cache, err := New(options)
		if err != nil {
			t.Fatal(err)
		}
		defer cache.Close()
		var persisterWakes atomic.Int32
		cache.maintenanceHooks = &maintenanceTestHooks{persistWake: func() { persisterWakes.Add(1) }}
		if err := cache.Set("key", "value"); err != nil {
			t.Fatal(err)
		}
		if persisterWakes.Load() != 0 || len(cache.persistWake) != 0 {
			t.Fatalf("threshold-zero persistence wakes = %d", persisterWakes.Load())
		}
		if version := cache.shards[0].mutationVersion.Load(); version != 1 {
			t.Fatalf("persistence mutation version = %d", version)
		}
	})
}

func TestCleanerAdoptsEarlierDeadline(t *testing.T) {
	cache, clock := testCache(t, nil)
	if err := cache.SetWithExpiration("late", 1, 2*time.Hour); err != nil {
		t.Fatal(err)
	}
	waits := make(chan time.Time, 2)
	var wakes atomic.Int32
	cache.maintenanceHooks = &maintenanceTestHooks{
		cleanWake: func() { wakes.Add(1) },
		cleanerWait: func(deadline time.Time) {
			waits <- deadline
		},
	}
	cache.opts.CleanupEnabled = true
	cache.maintenanceWG.Go(cache.runCleaner)
	select {
	case deadline := <-waits:
		if want := clock.Now().Add(2 * time.Hour); !deadline.Equal(want) {
			t.Fatalf("first cleaner deadline = %v, want %v", deadline, want)
		}
	case <-time.After(time.Second):
		t.Fatal("cleaner did not wait on the first deadline")
	}
	if err := cache.SetWithExpiration("early", 2, time.Hour); err != nil {
		t.Fatal(err)
	}
	select {
	case deadline := <-waits:
		if want := clock.Now().Add(time.Hour); !deadline.Equal(want) {
			t.Fatalf("updated cleaner deadline = %v, want %v", deadline, want)
		}
	case <-time.After(time.Second):
		t.Fatal("cleaner did not adopt the earlier deadline")
	}
	if wakes.Load() != 1 {
		t.Fatalf("cleaner wakes = %d, want 1", wakes.Load())
	}
}

func TestBackgroundCallbacks(t *testing.T) {
	cache, clock := testCache(t, nil)
	started := make(chan struct{})
	release := make(chan struct{})
	var calls atomic.Int32
	if err := cache.OnEvicted(func(_ EntryKey, _ any, reason EvictionReason) {
		if reason != EvictionReasonExpired {
			t.Errorf("reason = %v", reason)
		}
		calls.Add(1)
		close(started)
		<-release
	}); err != nil {
		t.Fatal(err)
	}
	_ = cache.SetWithExpiration("key", 1, time.Minute)
	clock.Advance(time.Minute)
	cache.expireDueInBackground()
	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("background callback did not start")
	}
	closed := make(chan error, 1)
	go func() { closed <- cache.Close() }()
	select {
	case err := <-closed:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(time.Second):
		t.Fatal("Close waited for a background callback")
	}
	close(release)
	deadline := time.After(time.Second)
	for calls.Load() != 1 {
		select {
		case <-deadline:
			t.Fatalf("callback calls = %d", calls.Load())
		default:
			runtime.Gosched()
		}
	}
}

func TestCloseWaitsForAdmittedMutation(t *testing.T) {
	cache, _ := testCache(t, nil)
	admitted := make(chan struct{})
	closeStarted := make(chan struct{})
	boundary := make(chan struct{})
	cache.lifecycleHooks = &lifecycleTestHooks{
		mutationAdmitted: func() { close(admitted) },
		closeStarted:     func() { close(closeStarted) },
		closeBoundary:    func() { close(boundary) },
	}
	shard := cache.shards[0]
	shard.mu.Lock()
	setDone := make(chan error, 1)
	go func() { setDone <- cache.Set("key", "value") }()
	<-admitted
	closeDone := make(chan error, 1)
	go func() { closeDone <- cache.Close() }()
	<-closeStarted
	select {
	case <-boundary:
		shard.mu.Unlock()
		t.Fatal("Close crossed its boundary before the admitted mutation completed")
	default:
	}
	shard.mu.Unlock()
	if err := <-setDone; err != nil {
		t.Fatal(err)
	}
	if err := <-closeDone; err != nil {
		t.Fatal(err)
	}
	if value, found := cache.Get("key"); !found || value != "value" {
		t.Fatalf("admitted mutation value = %v, %v", value, found)
	}
}

func TestCloseWaitsForAdmittedBatch(t *testing.T) {
	cache, _ := testCache(t, func(options *Options) { options.ShardCount = 2 })
	first := keyForShard(cache, 0, "first")
	second := keyForShard(cache, 1, "second")
	if err := cache.Set(first, 1); err != nil {
		t.Fatal(err)
	}
	if err := cache.Set(second, 2); err != nil {
		t.Fatal(err)
	}
	admitted := make(chan struct{})
	closeStarted := make(chan struct{})
	boundary := make(chan struct{})
	cache.lifecycleHooks = &lifecycleTestHooks{
		mutationAdmitted: func() { close(admitted) },
		closeStarted:     func() { close(closeStarted) },
		closeBoundary:    func() { close(boundary) },
	}
	cache.shards[0].mu.Lock()
	deleted := make(chan int, 1)
	batchErr := make(chan error, 1)
	go func() {
		count, err := cache.DeleteKeys([]string{first, second})
		deleted <- count
		batchErr <- err
	}()
	<-admitted
	closeDone := make(chan error, 1)
	go func() { closeDone <- cache.Close() }()
	<-closeStarted
	select {
	case <-boundary:
		cache.shards[0].mu.Unlock()
		t.Fatal("Close crossed its boundary during an admitted batch")
	default:
	}
	cache.shards[0].mu.Unlock()
	if count, err := <-deleted, <-batchErr; err != nil || count != 2 {
		t.Fatalf("DeleteKeys = %d, %v", count, err)
	}
	if err := <-closeDone; err != nil {
		t.Fatal(err)
	}
	if count := cache.Count(); count != 0 {
		t.Fatalf("post-close batch count = %d", count)
	}
}

func TestCloseBoundaryChangesOperationBehavior(t *testing.T) {
	cache, _ := testCache(t, func(options *Options) { options.EvictionPolicy = LRU })
	if err := cache.Set("key", "value"); err != nil {
		t.Fatal(err)
	}
	before := cache.Stats()
	boundary := make(chan struct{})
	release := make(chan struct{})
	cache.lifecycleHooks = &lifecycleTestHooks{closeBoundary: func() {
		close(boundary)
		<-release
	}}
	closeDone := make(chan error, 1)
	go func() { closeDone <- cache.Close() }()
	<-boundary
	if value, found := cache.Get("key"); !found || value != "value" {
		close(release)
		t.Fatalf("read at the closing boundary = %v, %v", value, found)
	}
	mutationDone := make(chan error, 1)
	go func() { mutationDone <- cache.Set("late", "value") }()
	close(release)
	if err := <-closeDone; err != nil {
		t.Fatal(err)
	}
	if err := <-mutationDone; !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("mutation after boundary = %v", err)
	}
	after := cache.Stats()
	if after.Hits != before.Hits || after.Misses != before.Misses {
		t.Fatalf("boundary read changed stats: before=%+v after=%+v", before, after)
	}
}

func TestCloseDoesNotWaitForForegroundCallback(t *testing.T) {
	cache, _ := testCache(t, nil)
	if err := cache.Set("key", "old"); err != nil {
		t.Fatal(err)
	}
	started := make(chan struct{})
	release := make(chan struct{})
	if err := cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) {
		if key != (EntryKey{Key: "key"}) || reason != EvictionReasonReplaced {
			t.Errorf("callback = %+q, %v", key, reason)
		}
		close(started)
		<-release
	}); err != nil {
		t.Fatal(err)
	}
	setDone := make(chan error, 1)
	go func() { setDone <- cache.Set("key", "new") }()
	<-started
	closeDone := make(chan error, 1)
	go func() { closeDone <- cache.Close() }()
	select {
	case err := <-closeDone:
		if err != nil {
			close(release)
			t.Fatal(err)
		}
	case <-time.After(time.Second):
		close(release)
		t.Fatal("Close waited for a foreground callback")
	}
	close(release)
	if err := <-setDone; err != nil {
		t.Fatal(err)
	}
	if value, found := cache.Get("key"); !found || value != "new" {
		t.Fatalf("callback mutation value = %v, %v", value, found)
	}
}

func TestFinalPersistenceCoversPreBoundaryMutation(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	if err := cache.Set("key", "value"); err != nil {
		t.Fatal(err)
	}
	commitStarted := make(chan struct{})
	releaseCommit := make(chan struct{})
	var once sync.Once
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "before-manifest-write" {
			once.Do(func() {
				close(commitStarted)
				<-releaseCommit
			})
		}
		return nil
	}
	cache.persistence.mu.Unlock()
	closeDone := make(chan error, 1)
	go func() { closeDone <- cache.Close() }()
	select {
	case <-commitStarted:
	case <-time.After(time.Second):
		close(releaseCommit)
		t.Fatal("final persistence did not start")
	}
	if err := cache.Flush(); !errors.Is(err, ErrCacheClosed) {
		close(releaseCommit)
		t.Fatalf("Flush after close boundary = %v", err)
	}
	close(releaseCommit)
	if err := <-closeDone; err != nil {
		t.Fatal(err)
	}
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	if value, found := restored.Get("key"); !found || value != "value" {
		t.Fatalf("final persisted value = %v, %v", value, found)
	}
}

func TestConcurrentCloseSharesFinalError(t *testing.T) {
	requirePersistenceSupport(t)
	options := persistentOptions(t.TempDir(), 1)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	if err := cache.Set("key", "value"); err != nil {
		t.Fatal(err)
	}
	commitStarted := make(chan struct{})
	releaseCommit := make(chan struct{})
	failure := errors.New("final persistence failed")
	var once sync.Once
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "before-manifest-write" {
			once.Do(func() {
				close(commitStarted)
				<-releaseCommit
			})
			return failure
		}
		return nil
	}
	cache.persistence.mu.Unlock()

	const callers = 8
	results := make(chan error, callers)
	go func() { results <- cache.Close() }()
	select {
	case <-commitStarted:
	case <-time.After(time.Second):
		close(releaseCommit)
		t.Fatal("failing final persistence did not start")
	}
	for range callers - 1 {
		go func() { results <- cache.Close() }()
	}
	close(releaseCommit)
	var first error
	for range callers {
		err := <-results
		if !errors.Is(err, failure) {
			t.Fatalf("Close error = %v", err)
		}
		if first == nil {
			first = err
		} else if err != first {
			t.Fatalf("concurrent Close returned distinct errors: %p != %p", err, first)
		}
	}
}

func TestConcurrentClose(t *testing.T) {
	cache, _ := testCache(t, nil)
	_ = cache.Set("key", 1)
	const callers = 32
	results := make(chan error, callers)
	var wait sync.WaitGroup
	for range callers {
		wait.Go(func() { results <- cache.Close() })
	}
	wait.Wait()
	close(results)
	for err := range results {
		if err != nil {
			t.Fatalf("Close result = %v", err)
		}
	}
	if err := cache.Set("x", 1); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Set after close = %v", err)
	}
	if err := cache.SetWithExpiration("x", 1, -2); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("invalid SetWithExpiration after close = %v", err)
	}
	if _, err := cache.Touch("x", -2); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Touch after close = %v", err)
	}
	if _, err := cache.Persist("x"); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Persist after close = %v", err)
	}
	if _, err := cache.Delete("x"); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Delete after close = %v", err)
	}
	if _, err := cache.DeleteKeys(nil); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("DeleteKeys after close = %v", err)
	}
	if _, err := cache.DeletePrefix(""); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("DeletePrefix after close = %v", err)
	}
	if _, err := cache.GetOrSet("x", 1); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("GetOrSet after close = %v", err)
	}
	if _, err := cache.GetOrSetFunc(context.Background(), "x", func(context.Context) (any, error) { return 1, nil }); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("loader after close = %v", err)
	}
	if err := cache.Clear(); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Clear after close = %v", err)
	}
	if err := cache.OnEvicted(nil); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("OnEvicted after close = %v", err)
	}
	if _, err := cache.Group(""); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Group after close = %v", err)
	}
	if err := cache.Flush(); !errors.Is(err, ErrCacheClosed) {
		t.Fatalf("Flush after close = %v", err)
	}
}

func TestPostCloseReads(t *testing.T) {
	cache, clock := testCache(t, func(o *Options) { o.EvictionPolicy = LRU })
	var callbacks atomic.Int32
	_ = cache.OnEvicted(func(EntryKey, any, EvictionReason) { callbacks.Add(1) })
	_ = cache.SetWithExpiration("key", 1, time.Minute)
	cache.Get("key")
	before := cache.Stats()
	shard := cache.shards[0]
	shard.mu.RLock()
	item := shard.memberLocked(EntryKey{Key: "key"})
	beforeOrdinal := item.ordinal
	shard.mu.RUnlock()
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	clock.Advance(time.Minute)
	if _, found := cache.Get("key"); found {
		t.Fatal("post-close Get returned expired value")
	}
	if _, _, found := cache.GetWithExpiration("key"); found || cache.Has("key") {
		t.Fatal("post-close point read returned expired value")
	}
	if count := cache.Count(); count != 0 {
		t.Fatalf("post-close Count = %d", count)
	}
	visits := 0
	cache.Range(func(EntryKey, any, time.Time) bool { visits++; return true })
	if visits != 0 {
		t.Fatalf("post-close Range visits = %d", visits)
	}
	after := cache.Stats()
	if after.Hits != before.Hits || after.Misses != before.Misses {
		t.Fatalf("post-close reads changed stats: before=%+v after=%+v", before, after)
	}
	if item.ordinal != beforeOrdinal {
		t.Fatal("post-close read promoted LRU order")
	}
	if callbacks.Load() != 0 || cache.shards[0].liveCount != 1 {
		t.Fatalf("post-close read mutated entry: callbacks=%d live=%d", callbacks.Load(), cache.shards[0].liveCount)
	}
	if !after.Closed {
		t.Fatal("Stats.Closed is false")
	}
}

func TestPostCloseExpirationCounts(t *testing.T) {
	cache, clock := testCache(t, nil)
	first, _ := cache.Group("first")
	second, _ := cache.Group("second")
	if err := cache.SetWithExpiration("early", 1, time.Minute); err != nil {
		t.Fatal(err)
	}
	if err := first.SetWithExpiration("later", 2, 2*time.Minute); err != nil {
		t.Fatal(err)
	}
	if err := first.Set("persistent", 3); err != nil {
		t.Fatal(err)
	}
	if err := second.SetWithExpiration("early", 4, time.Minute); err != nil {
		t.Fatal(err)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	clock.Advance(time.Minute)
	if total, firstCount, secondCount := cache.Count(), first.Count(), second.Count(); total != 2 || firstCount != 2 || secondCount != 0 {
		t.Fatalf("counts after first deadline = %d, %d, %d", total, firstCount, secondCount)
	}
	clock.Advance(time.Minute)
	if total, firstCount := cache.Count(), first.Count(); total != 1 || firstCount != 1 {
		t.Fatalf("counts after second deadline = %d, %d", total, firstCount)
	}
	if live := cache.shards[0].liveCount; live != 4 {
		t.Fatalf("post-close counts physically removed entries: live=%d", live)
	}
	visited := 0
	cache.Range(func(EntryKey, any, time.Time) bool { visited++; return true })
	if visited != 1 {
		t.Fatalf("post-close Range visits = %d", visited)
	}
}

func TestLoader(t *testing.T) {
	t.Run("successful TTL load wakes maintenance", func(t *testing.T) {
		cache, _ := testCache(t, func(options *Options) { options.CleanupEnabled = true })
		woke := make(chan struct{}, 1)
		cache.maintenanceHooks = &maintenanceTestHooks{cleanWake: func() { woke <- struct{}{} }}
		value, err := cache.GetOrSetFuncWithExpiration(context.Background(), "key", func(context.Context) (any, error) {
			return 1, nil
		}, time.Minute)
		if err != nil || value != 1 {
			t.Fatalf("load = %v, %v", value, err)
		}
		select {
		case <-woke:
		case <-time.After(time.Second):
			t.Fatal("loader insertion did not wake maintenance")
		}
	})

	t.Run("expired lookup and writeback coalesce maintenance", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		cache.opts.CleanupEnabled = true
		var wakes atomic.Int32
		cache.maintenanceHooks = &maintenanceTestHooks{cleanWake: func() { wakes.Add(1) }}
		started := make(chan struct{})
		release := make(chan struct{})
		loaded := make(chan error, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-release
				return "loaded", nil
			})
			if err == nil && value != "loaded" {
				err = errors.New("loader returned an unexpected value")
			}
			loaded <- err
		}()
		<-started
		if wakes.Load() != 0 {
			t.Fatalf("loader emitted an interim maintenance wake: %d", wakes.Load())
		}
		close(release)
		select {
		case err := <-loaded:
			if err != nil {
				t.Fatal(err)
			}
		case <-time.After(time.Second):
			t.Fatal("loader did not complete")
		}
		if wakes.Load() != 1 {
			t.Fatalf("loader maintenance wakes = %d, want 1", wakes.Load())
		}
	})

	t.Run("expired callback may load the same key", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		var outerLoads atomic.Int32
		if err := cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) {
			if key.Key != "key" || reason != EvictionReasonExpired {
				return
			}
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "callback", nil
			})
			if err != nil || value != "callback" {
				t.Errorf("callback load = %v, %v", value, err)
			}
		}); err != nil {
			t.Fatal(err)
		}
		result := make(chan any, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				outerLoads.Add(1)
				return "outer", nil
			})
			if err != nil {
				t.Errorf("outer load: %v", err)
			}
			result <- value
		}()
		select {
		case value := <-result:
			if value != "callback" || outerLoads.Load() != 0 {
				t.Fatalf("outer result = %v, outer loads = %d", value, outerLoads.Load())
			}
		case <-time.After(time.Second):
			t.Fatal("same-key expiration callback deadlocked the loader")
		}
	})

	t.Run("expired miss does not promote callback replacement", func(t *testing.T) {
		cache, clock := testCache(t, func(options *Options) {
			options.MaxEntriesPerShard = 2
			options.EvictionPolicy = LRU
		})
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		if err := cache.Set("other", "original"); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		if err := cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) {
			if key.Key != "key" || reason != EvictionReasonExpired {
				return
			}
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "callback", nil
			})
			if err != nil || value != "callback" {
				t.Errorf("callback load = %v, %v", value, err)
			}
			if err := cache.Set("other", "updated"); err != nil {
				t.Errorf("callback replacement: %v", err)
			}
		}); err != nil {
			t.Fatal(err)
		}
		value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
			return "outer", nil
		})
		if err != nil || value != "callback" {
			t.Fatalf("outer load = %v, %v", value, err)
		}
		if err := cache.Set("new", "value"); err != nil {
			t.Fatal(err)
		}
		if _, found := cache.Get("key"); found {
			t.Fatal("expired-miss recheck promoted the callback replacement")
		}
		if value, found := cache.Get("other"); !found || value != "updated" {
			t.Fatalf("older live value was evicted = %v, %v", value, found)
		}
	})

	t.Run("expired callback panic does not strand flight", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		if err := cache.OnEvicted(func(key EntryKey, _ any, _ EvictionReason) {
			if key.Key == "key" {
				panic("callback panic")
			}
		}); err != nil {
			t.Fatal(err)
		}
		recovered := func() (recovered any) {
			defer func() { recovered = recover() }()
			_, _ = cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "unreachable", nil
			})
			return nil
		}()
		if recovered != "callback panic" {
			t.Fatalf("recovered panic = %v", recovered)
		}
		if err := cache.OnEvicted(nil); err != nil {
			t.Fatal(err)
		}
		value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
			return "recovered", nil
		})
		if err != nil || value != "recovered" {
			t.Fatalf("load after callback panic = %v, %v", value, err)
		}
	})

	t.Run("pre-cancelled miss does not load or store", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		var loads atomic.Int32
		value, err := cache.GetOrSetFunc(ctx, "key", func(context.Context) (any, error) {
			loads.Add(1)
			return "loaded", nil
		})
		if value != nil || !errors.Is(err, context.Canceled) || loads.Load() != 0 {
			t.Fatalf("cancelled load = %v, %v, calls=%d", value, err, loads.Load())
		}
		if cache.Count() != 0 || cache.Stats().Misses != 1 {
			t.Fatalf("cancelled load state = count %d, stats %+v", cache.Count(), cache.Stats())
		}
	})

	t.Run("failed load removes concurrently expired value", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		started := make(chan struct{})
		release := make(chan struct{})
		loadError := errors.New("load failed")
		var reason EvictionReason
		_ = cache.OnEvicted(func(_ EntryKey, _ any, current EvictionReason) { reason = current })
		result := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-release
				return nil, loadError
			})
			result <- err
		}()
		<-started
		_ = cache.SetWithExpiration("key", 1, time.Minute)
		clock.Advance(time.Minute)
		close(release)
		if err := <-result; !errors.Is(err, loadError) {
			t.Fatalf("loader error = %v", err)
		}
		if reason != EvictionReasonExpired || cache.shards[0].liveCount != 0 {
			t.Fatalf("expired concurrent value: reason=%v live=%d", reason, cache.shards[0].liveCount)
		}
	})

	t.Run("failed load snapshots concurrent replacement", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		started := make(chan struct{})
		releaseLoader := make(chan struct{})
		released := false
		defer func() {
			if !released {
				close(releaseLoader)
			}
		}()

		type loadOutcome struct {
			value any
			err   error
		}
		ownerResult := make(chan loadOutcome, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-releaseLoader
				return nil, errors.New("load failed")
			})
			ownerResult <- loadOutcome{value: value, err: err}
		}()
		<-started

		waiterResult := make(chan loadOutcome, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "unexpected", nil
			})
			waiterResult <- loadOutcome{value: value, err: err}
		}()
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 2 {
			select {
			case <-deadline:
				t.Fatalf("waiter did not join owner flight: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		if err := cache.Set("key", "first"); err != nil {
			t.Fatal(err)
		}

		var replacementErr error
		shard := cache.shards[0]
		shard.mu.Lock()
		call := shard.flights[EntryKey{Key: "key"}]
		call.finishTestHook = func() {
			replaced := make(chan error, 1)
			go func() { replaced <- cache.Set("key", "second") }()
			replacementErr = <-replaced
		}
		shard.mu.Unlock()

		close(releaseLoader)
		released = true
		for name, result := range map[string]<-chan loadOutcome{"owner": ownerResult, "waiter": waiterResult} {
			outcome := <-result
			if outcome.err != nil || outcome.value != "first" {
				t.Errorf("%s result = %v, %v", name, outcome.value, outcome.err)
			}
		}
		if replacementErr != nil {
			t.Fatal(replacementErr)
		}
		if value, found := cache.Get("key"); !found || value != "second" {
			t.Fatalf("replacement value = %v, %v", value, found)
		}
	})

	t.Run("coalesces and waits independently", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		const callers = 16
		start := make(chan struct{})
		release := make(chan struct{})
		var loads atomic.Int32
		results := make(chan any, callers)
		var wait sync.WaitGroup
		for range callers {
			wait.Go(func() {
				<-start
				value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
					loads.Add(1)
					<-release
					return 42, nil
				})
				if err != nil {
					t.Errorf("load: %v", err)
				}
				results <- value
			})
		}
		close(start)
		deadline := time.After(time.Second)
		for cache.Stats().Misses != callers {
			select {
			case <-deadline:
				t.Fatalf("only %d callers reached flight", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		close(release)
		wait.Wait()
		close(results)
		for value := range results {
			if value != 42 {
				t.Fatalf("value = %v", value)
			}
		}
		if loads.Load() != 1 {
			t.Fatalf("loader calls = %d", loads.Load())
		}
	})

	t.Run("open retry preserves expiration callback reentry", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		ownerContext, cancelOwner := context.WithCancel(context.Background())
		ownerStarted := make(chan struct{})
		ownerResult := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(ownerContext, "key", func(ctx context.Context) (any, error) {
				close(ownerStarted)
				<-ctx.Done()
				return nil, ctx.Err()
			})
			ownerResult <- err
		}()
		<-ownerStarted
		var waiterLoads atomic.Int32
		waiterValue := make(chan any, 1)
		waiterError := make(chan error, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				waiterLoads.Add(1)
				return "waiter", nil
			})
			waiterValue <- value
			waiterError <- err
		}()
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 2 {
			select {
			case <-deadline:
				t.Fatalf("waiter did not join owner flight: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		retryBlocked := make(chan struct{})
		releaseRetry := make(chan struct{})
		shard := cache.shards[0]
		shard.mu.Lock()
		call := shard.flights[EntryKey{Key: "key"}]
		call.retryTestHook = func(*loadCall) {
			close(retryBlocked)
			<-releaseRetry
		}
		shard.mu.Unlock()
		cancelOwner()
		if err := <-ownerResult; !errors.Is(err, context.Canceled) {
			t.Fatalf("owner error = %v", err)
		}
		<-retryBlocked
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		if err := cache.OnEvicted(func(key EntryKey, _ any, reason EvictionReason) {
			if key == (EntryKey{Key: "key"}) && reason == EvictionReasonExpired {
				if err := cache.Set("key", "callback"); err != nil {
					t.Errorf("callback Set: %v", err)
				}
			}
		}); err != nil {
			t.Fatal(err)
		}
		close(releaseRetry)
		if value, err := <-waiterValue, <-waiterError; err != nil || value != "callback" {
			t.Fatalf("waiter result after expiration callback = %v, %v", value, err)
		}
		if waiterLoads.Load() != 0 {
			t.Fatalf("waiter loader calls = %d", waiterLoads.Load())
		}
	})

	t.Run("retry expiration callback panic does not strand waiters", func(t *testing.T) {
		cache, clock := testCache(t, nil)
		ownerContext, cancelOwner := context.WithCancel(context.Background())
		ownerStarted := make(chan struct{})
		ownerResult := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(ownerContext, "key", func(ctx context.Context) (any, error) {
				close(ownerStarted)
				<-ctx.Done()
				return nil, ctx.Err()
			})
			ownerResult <- err
		}()
		<-ownerStarted
		type retryOutcome struct {
			value      any
			err        error
			panicValue any
		}
		outcomes := make(chan retryOutcome, 2)
		var loaderCalls atomic.Int32
		for range 2 {
			go func() {
				outcome := retryOutcome{}
				defer func() {
					outcome.panicValue = recover()
					outcomes <- outcome
				}()
				outcome.value, outcome.err = cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
					loaderCalls.Add(1)
					return "recovered", nil
				})
			}()
		}
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 3 {
			select {
			case <-deadline:
				t.Fatalf("waiters did not join owner flight: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		retryEntered := make(chan struct{}, 2)
		releaseRetries := make(chan struct{})
		shard := cache.shards[0]
		shard.mu.Lock()
		call := shard.flights[EntryKey{Key: "key"}]
		call.retryTestHook = func(*loadCall) {
			retryEntered <- struct{}{}
			<-releaseRetries
		}
		shard.mu.Unlock()
		cancelOwner()
		if err := <-ownerResult; !errors.Is(err, context.Canceled) {
			t.Fatalf("owner error = %v", err)
		}
		<-retryEntered
		<-retryEntered
		if err := cache.SetWithExpiration("key", "expired", time.Minute); err != nil {
			t.Fatal(err)
		}
		clock.Advance(time.Minute)
		if err := cache.OnEvicted(func(EntryKey, any, EvictionReason) { panic("retry callback panic") }); err != nil {
			t.Fatal(err)
		}
		close(releaseRetries)
		var panics, successes int
		for range 2 {
			select {
			case outcome := <-outcomes:
				if outcome.panicValue == "retry callback panic" {
					panics++
				} else if outcome.panicValue == nil && outcome.err == nil && outcome.value == "recovered" {
					successes++
				} else {
					t.Fatalf("unexpected retry outcome = %+v", outcome)
				}
			case <-time.After(time.Second):
				t.Fatal("retry waiter remained stranded after callback panic")
			}
		}
		if panics != 1 || successes != 1 || loaderCalls.Load() != 1 {
			t.Fatalf("retry panic/success/load counts = %d/%d/%d", panics, successes, loaderCalls.Load())
		}
	})

	t.Run("owner may finish after close without writeback", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		started := make(chan struct{})
		release := make(chan struct{})
		result := make(chan any, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-release
				return "loaded", nil
			})
			if err != nil {
				t.Errorf("owner: %v", err)
			}
			result <- value
		}()
		<-started
		if err := cache.Close(); err != nil {
			t.Fatal(err)
		}
		close(release)
		if value := <-result; value != "loaded" {
			t.Fatalf("owner value = %v", value)
		}
		if _, found := cache.Get("key"); found {
			t.Fatal("loader wrote back after Close")
		}
	})

	t.Run("explicit value wins across close", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		started := make(chan struct{})
		release := make(chan struct{})
		result := make(chan any, 1)
		resultErr := make(chan error, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-release
				return "loaded", nil
			})
			result <- value
			resultErr <- err
		}()
		<-started
		if err := cache.Set("key", "explicit"); err != nil {
			t.Fatal(err)
		}
		if err := cache.Close(); err != nil {
			t.Fatal(err)
		}
		close(release)
		if value, err := <-result, <-resultErr; err != nil || value != "explicit" {
			t.Fatalf("loader result after explicit Set = %v, %v", value, err)
		}
		if value, found := cache.Get("key"); !found || value != "explicit" {
			t.Fatalf("explicit value after Close = %v, %v", value, found)
		}
	})

	t.Run("owner cancellation lets waiter retry", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		ownerContext, cancelOwner := context.WithCancel(context.Background())
		ownerStarted := make(chan struct{})
		ownerResult := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(ownerContext, "key", func(ctx context.Context) (any, error) {
				close(ownerStarted)
				<-ctx.Done()
				return nil, ctx.Err()
			})
			ownerResult <- err
		}()
		<-ownerStarted
		waiterResult := make(chan any, 1)
		waiterError := make(chan error, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "retried", nil
			})
			waiterResult <- value
			waiterError <- err
		}()
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 2 {
			select {
			case <-deadline:
				t.Fatalf("waiter did not join owner flight: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		cancelOwner()
		if err := <-ownerResult; !errors.Is(err, context.Canceled) {
			t.Fatalf("owner error = %v", err)
		}
		if value, err := <-waiterResult, <-waiterError; err != nil || value != "retried" {
			t.Fatalf("waiter retry = %v, %v", value, err)
		}
		if value, found := cache.Get("key"); !found || value != "retried" {
			t.Fatalf("retried value = %v, %v", value, found)
		}
	})

	t.Run("pre-close waiter inherits retry after close", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		ownerContext, cancelOwner := context.WithCancel(context.Background())
		ownerStarted := make(chan struct{})
		ownerResult := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(ownerContext, "key", func(ctx context.Context) (any, error) {
				close(ownerStarted)
				<-ctx.Done()
				return nil, ctx.Err()
			})
			ownerResult <- err
		}()
		<-ownerStarted
		waiterValue := make(chan any, 1)
		waiterError := make(chan error, 1)
		go func() {
			value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				return "inherited", nil
			})
			waiterValue <- value
			waiterError <- err
		}()
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 2 {
			select {
			case <-deadline:
				t.Fatalf("waiter did not join before Close: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}
		if err := cache.Close(); err != nil {
			t.Fatal(err)
		}
		cancelOwner()
		if err := <-ownerResult; !errors.Is(err, context.Canceled) {
			t.Fatalf("owner error = %v", err)
		}
		if value, err := <-waiterValue, <-waiterError; err != nil || value != "inherited" {
			t.Fatalf("inherited waiter result = %v, %v", value, err)
		}
		if _, found := cache.Get("key"); found {
			t.Fatal("inherited loader wrote back after Close")
		}
	})

	t.Run("inherited retry stays coalesced for active and delayed waiters", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		ownerContext, cancelOwner := context.WithCancel(context.Background())
		ownerStarted := make(chan struct{})
		ownerResult := make(chan error, 1)
		go func() {
			_, err := cache.GetOrSetFunc(ownerContext, "key", func(ctx context.Context) (any, error) {
				close(ownerStarted)
				<-ctx.Done()
				return nil, ctx.Err()
			})
			ownerResult <- err
		}()
		<-ownerStarted

		type loadResult struct {
			value any
			err   error
		}
		results := make(chan loadResult, 3)
		retryStarted := make(chan struct{})
		releaseRetry := make(chan struct{})
		var retryOnce sync.Once
		var loaderCalls atomic.Int32
		for range 3 {
			go func() {
				value, err := cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
					loaderCalls.Add(1)
					retryOnce.Do(func() { close(retryStarted) })
					<-releaseRetry
					return "shared", nil
				})
				results <- loadResult{value: value, err: err}
			}()
		}
		deadline := time.After(time.Second)
		for cache.Stats().Misses != 4 {
			select {
			case <-deadline:
				t.Fatalf("waiters did not join before Close: misses=%d", cache.Stats().Misses)
			default:
				runtime.Gosched()
			}
		}

		joined := make(chan struct{})
		delayed := make(chan struct{})
		releaseDelayed := make(chan struct{})
		var releaseMu sync.Mutex
		released := 0
		var joinedOnce sync.Once
		shard := cache.shards[0]
		shard.mu.Lock()
		call := shard.flights[EntryKey{Key: "key"}]
		call.retryTestHook = func(retry *loadCall) {
			releaseMu.Lock()
			defer releaseMu.Unlock()
			released++
			if released == 1 {
				retry.retryJoinTestHook = func() { joinedOnce.Do(func() { close(joined) }) }
			}
			if released == 3 {
				close(delayed)
				<-releaseDelayed
			}
		}
		shard.mu.Unlock()

		if err := cache.Close(); err != nil {
			t.Fatal(err)
		}
		cancelOwner()
		if err := <-ownerResult; !errors.Is(err, context.Canceled) {
			t.Fatalf("owner error = %v", err)
		}
		select {
		case <-retryStarted:
		case <-time.After(time.Second):
			t.Fatal("inherited retry did not start")
		}
		select {
		case <-joined:
		case <-time.After(time.Second):
			t.Fatal("second waiter did not join the active successor")
		}
		select {
		case <-delayed:
		case <-time.After(time.Second):
			t.Fatal("third waiter was not delayed")
		}
		close(releaseRetry)
		for range 2 {
			result := <-results
			if result.err != nil || result.value != "shared" {
				t.Fatalf("active inherited result = %v, %v", result.value, result.err)
			}
		}
		close(releaseDelayed)
		last := <-results
		if last.err != nil || last.value != "shared" {
			t.Fatalf("delayed inherited result = %v, %v", last.value, last.err)
		}
		if loaderCalls.Load() != 1 {
			t.Fatalf("inherited loader calls = %d", loaderCalls.Load())
		}
	})

	t.Run("waiter cancellation", func(t *testing.T) {
		cache, _ := testCache(t, nil)
		started := make(chan struct{})
		release := make(chan struct{})
		ownerDone := make(chan struct{})
		go func() {
			defer close(ownerDone)
			_, _ = cache.GetOrSetFunc(context.Background(), "key", func(context.Context) (any, error) {
				close(started)
				<-release
				return 1, nil
			})
		}()
		<-started
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		if _, err := cache.GetOrSetFunc(ctx, "key", func(context.Context) (any, error) { return 2, nil }); !errors.Is(err, context.Canceled) {
			t.Fatalf("waiter error = %v", err)
		}
		close(release)
		<-ownerDone
	})
}
