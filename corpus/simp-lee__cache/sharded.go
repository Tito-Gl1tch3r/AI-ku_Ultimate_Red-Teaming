package shardedcache

import (
	"context"
	"errors"
	"math/bits"
	"runtime"
	"sync"
	"sync/atomic"
	"time"

	"github.com/cespare/xxhash/v2"
)

const (
	cacheOpen uint32 = iota
	cacheClosing
	cacheClosed
)

// ShardedCache is a concurrent cache split into independently locked shards.
type ShardedCache struct {
	shards    []*cacheShard
	shardMask uint64
	opts      Options
	clock     clock
	ordinal   atomic.Uint64

	gate      sync.RWMutex
	state     atomic.Uint32
	closeOnce sync.Once
	closeErr  error

	maintenanceStop  chan struct{}
	maintenanceWG    sync.WaitGroup
	cleanWake        chan struct{}
	persistWake      chan struct{}
	maintenanceHooks *maintenanceTestHooks
	lifecycleHooks   *lifecycleTestHooks

	callback   atomic.Pointer[callbackRegistration]
	background struct {
		mu      sync.Mutex
		cond    *sync.Cond
		queue   []callbackEviction
		head    int
		closing bool
	}

	persistence                 *persistenceState
	constructorPersistenceFault func(string) error
}

type callbackRegistration struct {
	callback func(EntryKey, any, EvictionReason)
}

type callbackEviction struct {
	callback *callbackRegistration
	event    eviction
}

type lifecycleTestHooks struct {
	gateReadLock     func()
	mutationAdmitted func()
	closeStarted     func()
	closeBoundary    func()
}

type maintenanceTestHooks struct {
	cleanWake        func()
	persistWake      func()
	cleanerWait      func(time.Time)
	persisterHandled func()
}

// New constructs a cache from strictly validated options.
func New(options Options) (*ShardedCache, error) {
	return newWithClock(options, realClock{})
}

func newWithClock(options Options, cacheClock clock) (*ShardedCache, error) {
	return newWithClockAndPersistenceFault(options, cacheClock, nil)
}

func newWithClockAndPersistenceFault(options Options, cacheClock clock, fault func(string) error) (*ShardedCache, error) {
	if err := options.Validate(); err != nil {
		return nil, err
	}
	if cacheClock == nil {
		return nil, errors.New("cache clock is nil")
	}
	if options.Persistence != nil {
		persistence := *options.Persistence
		options.Persistence = &persistence
	}

	cache := &ShardedCache{
		shards:                      make([]*cacheShard, options.ShardCount),
		shardMask:                   uint64(options.ShardCount - 1),
		opts:                        options,
		clock:                       cacheClock,
		maintenanceStop:             make(chan struct{}),
		cleanWake:                   make(chan struct{}, 1),
		persistWake:                 make(chan struct{}, 1),
		constructorPersistenceFault: fault,
	}
	cache.background.cond = sync.NewCond(&cache.background.mu)
	for i := range cache.shards {
		cache.shards[i] = newCacheShard(options.MaxEntriesPerShard, options.EvictionPolicy, options.Persistence != nil)
	}
	go cache.dispatchBackgroundCallbacks()

	if options.Persistence != nil {
		if err := cache.openPersistence(); err != nil {
			cache.closeBackgroundDispatcher()
			return nil, err
		}
	}
	if options.CleanupEnabled {
		cache.maintenanceWG.Go(cache.runCleaner)
	}
	if cache.persistence != nil {
		cache.maintenanceWG.Go(cache.runPersister)
	}
	return cache, nil
}

func (c *ShardedCache) nextOrdinal() uint64 { return c.ordinal.Add(1) }

func shardHash(key EntryKey) uint64 {
	groupHash := xxhash.Sum64String(key.Group)
	keyHash := xxhash.Sum64String(key.Key)
	return groupHash ^ bits.RotateLeft64(keyHash, 23) ^ 0x9e3779b97f4a7c15
}

func (c *ShardedCache) shardFor(key EntryKey) *cacheShard {
	return c.shards[shardHash(key)&c.shardMask]
}

func (c *ShardedCache) shardIndex(key EntryKey) int {
	return int(shardHash(key) & c.shardMask)
}

func (c *ShardedCache) lockGateRead() {
	if hooks := c.lifecycleHooks; hooks != nil && hooks.gateReadLock != nil {
		hooks.gateReadLock()
	}
	c.gate.RLock()
}

func (c *ShardedCache) beginMutation() error {
	c.lockGateRead()
	if c.state.Load() != cacheOpen {
		c.gate.RUnlock()
		return ErrCacheClosed
	}
	if hooks := c.lifecycleHooks; hooks != nil && hooks.mutationAdmitted != nil {
		hooks.mutationAdmitted()
	}
	return nil
}

func (c *ShardedCache) finishMutation(result mutationResult, callback *callbackRegistration) {
	c.gate.RUnlock()
	c.notifyMaintenance(result)
	c.invokeForeground(callback, result.events)
}

func (c *ShardedCache) notifyMaintenance(result mutationResult) {
	if result.deadlineChanged && c.opts.CleanupEnabled {
		select {
		case c.cleanWake <- struct{}{}:
			if hooks := c.maintenanceHooks; hooks != nil && hooks.cleanWake != nil {
				hooks.cleanWake()
			}
		default:
		}
	}
	if result.changed && c.persistence != nil && c.opts.Persistence.Threshold > 0 {
		select {
		case c.persistWake <- struct{}{}:
			if hooks := c.maintenanceHooks; hooks != nil && hooks.persistWake != nil {
				hooks.persistWake()
			}
		default:
		}
	}
}

func (c *ShardedCache) currentCallback() *callbackRegistration {
	return c.callback.Load()
}

func (c *ShardedCache) invokeForeground(callback *callbackRegistration, events []eviction) {
	if callback == nil {
		return
	}
	for _, event := range events {
		callback.callback(event.key, event.value, event.reason)
	}
}

func (c *ShardedCache) enqueueBackground(callback *callbackRegistration, events []eviction) {
	if callback == nil || len(events) == 0 {
		return
	}
	c.background.mu.Lock()
	for _, event := range events {
		c.background.queue = append(c.background.queue, callbackEviction{callback: callback, event: event})
	}
	c.background.cond.Signal()
	c.background.mu.Unlock()
}

func (c *ShardedCache) dispatchBackgroundCallbacks() {
	for {
		c.background.mu.Lock()
		for c.background.head == len(c.background.queue) && !c.background.closing {
			c.background.cond.Wait()
		}
		if c.background.head == len(c.background.queue) && c.background.closing {
			c.background.mu.Unlock()
			return
		}
		task := c.background.queue[c.background.head]
		c.background.queue[c.background.head] = callbackEviction{}
		c.background.head++
		if c.background.head == len(c.background.queue) {
			c.background.queue = nil
			c.background.head = 0
		}
		c.background.mu.Unlock()
		task.callback.callback(task.event.key, task.event.value, task.event.reason)
	}
}

func (c *ShardedCache) closeBackgroundDispatcher() {
	c.background.mu.Lock()
	c.background.closing = true
	c.background.cond.Broadcast()
	c.background.mu.Unlock()
}

// Set stores an ungrouped value using the default expiration.
func (c *ShardedCache) Set(key string, value any) error {
	return c.setEntry(EntryKey{Key: key}, value, DefaultExpiration)
}

// SetWithExpiration stores an ungrouped value with an explicit expiration rule.
func (c *ShardedCache) SetWithExpiration(key string, value any, expiration time.Duration) error {
	return c.setEntry(EntryKey{Key: key}, value, expiration)
}

func (c *ShardedCache) setEntry(key EntryKey, value any, expiration time.Duration) error {
	if err := c.beginMutation(); err != nil {
		return err
	}
	if err := validateExpiration(expiration); err != nil {
		c.gate.RUnlock()
		return err
	}
	callback := c.currentCallback()
	shard := c.shardFor(key)
	shard.mu.Lock()
	now := c.clock.Now()
	result := shard.setLocked(key, value, expiration, c.opts.DefaultExpiration, now, c.nextOrdinal, callback != nil)
	shard.mu.Unlock()
	c.finishMutation(result, callback)
	return nil
}

// Get retrieves an ungrouped live value.
func (c *ShardedCache) Get(key string) (any, bool) {
	return c.getEntry(EntryKey{Key: key})
}

func (c *ShardedCache) getEntry(key EntryKey) (any, bool) {
	value, _, found := c.getEntryWithExpiration(key)
	return value, found
}

// GetWithExpiration retrieves an ungrouped live value and expiration time.
func (c *ShardedCache) GetWithExpiration(key string) (any, time.Time, bool) {
	return c.getEntryWithExpiration(EntryKey{Key: key})
}

func (c *ShardedCache) getEntryWithExpiration(key EntryKey) (any, time.Time, bool) {
	callback := c.currentCallback()
	value, expiresAt, found, result := c.shardFor(key).get(key, c.clock, &c.state, c.opts.EvictionPolicy, c.nextOrdinal, callback != nil)
	c.notifyMaintenance(result)
	c.invokeForeground(callback, result.events)
	return value, expiresAt, found
}

// Has reports whether an ungrouped live value exists and records one hit or miss.
func (c *ShardedCache) Has(key string) bool { return c.hasEntry(EntryKey{Key: key}) }

func (c *ShardedCache) hasEntry(key EntryKey) bool {
	_, found := c.getEntry(key)
	return found
}

// Touch changes an ungrouped value's TTL without changing policy order.
func (c *ShardedCache) Touch(key string, expiration time.Duration) (bool, error) {
	return c.touchEntry(EntryKey{Key: key}, expiration)
}

func (c *ShardedCache) touchEntry(key EntryKey, expiration time.Duration) (bool, error) {
	if err := c.beginMutation(); err != nil {
		return false, err
	}
	if err := validateExpiration(expiration); err != nil {
		c.gate.RUnlock()
		return false, err
	}
	callback := c.currentCallback()
	found, result := c.shardFor(key).touch(key, expiration, c.opts.DefaultExpiration, c.clock, callback != nil)
	c.finishMutation(result, callback)
	return found, nil
}

// Persist removes expiration from an ungrouped value.
func (c *ShardedCache) Persist(key string) (bool, error) {
	return c.touchEntry(EntryKey{Key: key}, NoExpiration)
}

// Delete removes an ungrouped live value.
func (c *ShardedCache) Delete(key string) (bool, error) {
	return c.deleteEntry(EntryKey{Key: key})
}

func (c *ShardedCache) deleteEntry(key EntryKey) (bool, error) {
	if err := c.beginMutation(); err != nil {
		return false, err
	}
	callback := c.currentCallback()
	deleted, result := c.shardFor(key).delete(key, c.clock, callback != nil)
	c.finishMutation(result, callback)
	return deleted, nil
}

// DeleteKeys removes the named ungrouped live values.
func (c *ShardedCache) DeleteKeys(keys []string) (int, error) {
	entries := make([]EntryKey, len(keys))
	for i, key := range keys {
		entries[i] = EntryKey{Key: key}
	}
	return c.deleteEntries(entries)
}

func (c *ShardedCache) deleteEntries(keys []EntryKey) (int, error) {
	if err := c.beginMutation(); err != nil {
		return 0, err
	}
	callback := c.currentCallback()
	if len(keys) == 0 {
		c.finishMutation(mutationResult{}, callback)
		return 0, nil
	}
	buckets := make(map[int][]EntryKey)
	for _, key := range keys {
		index := c.shardIndex(key)
		buckets[index] = append(buckets[index], key)
	}
	type shardResult struct {
		deleted int
		mutationResult
	}
	results := runShardJobs(buckets, func(index int, keys []EntryKey) shardResult {
		deleted, result := c.shards[index].deleteKeys(keys, c.clock, callback != nil)
		return shardResult{deleted: deleted, mutationResult: result}
	})
	deleted := 0
	var result mutationResult
	for shardResult := range results {
		deleted += shardResult.deleted
		result.merge(shardResult.mutationResult)
	}
	c.finishMutation(result, callback)
	return deleted, nil
}

// DeletePrefix removes ungrouped live values with the prefix.
func (c *ShardedCache) DeletePrefix(prefix string) (int, error) {
	return c.deletePrefix("", prefix)
}

func (c *ShardedCache) deletePrefix(group, prefix string) (int, error) {
	if err := c.beginMutation(); err != nil {
		return 0, err
	}
	callback := c.currentCallback()
	type job struct{}
	buckets := make(map[int]job, len(c.shards))
	for index, shard := range c.shards {
		if shard.hasEntries(&group) {
			buckets[index] = job{}
		}
	}
	type shardResult struct {
		deleted int
		mutationResult
	}
	results := runShardJobs(buckets, func(index int, _ job) shardResult {
		deleted, result := c.shards[index].deletePrefix(group, prefix, c.clock, callback != nil)
		return shardResult{deleted: deleted, mutationResult: result}
	})
	deleted := 0
	var result mutationResult
	for shardResult := range results {
		deleted += shardResult.deleted
		result.merge(shardResult.mutationResult)
	}
	c.finishMutation(result, callback)
	return deleted, nil
}

// GetOrSet returns an existing ungrouped live value or stores value.
func (c *ShardedCache) GetOrSet(key string, value any) (any, error) {
	return c.getOrSetEntry(EntryKey{Key: key}, value)
}

func (c *ShardedCache) getOrSetEntry(key EntryKey, value any) (any, error) {
	if err := c.beginMutation(); err != nil {
		return nil, err
	}
	callback := c.currentCallback()
	value, result := c.shardFor(key).getOrSet(key, value, c.opts.DefaultExpiration, c.clock, c.opts.EvictionPolicy, c.nextOrdinal, callback != nil)
	c.finishMutation(result, callback)
	return value, nil
}

// GetOrSetFunc loads a missing ungrouped value using the default expiration.
func (c *ShardedCache) GetOrSetFunc(ctx context.Context, key string, loader LoaderFunc) (any, error) {
	return c.getOrSetFuncEntry(ctx, EntryKey{Key: key}, loader, DefaultExpiration)
}

// GetOrSetFuncWithExpiration loads a missing ungrouped value with an explicit expiration.
func (c *ShardedCache) GetOrSetFuncWithExpiration(ctx context.Context, key string, loader LoaderFunc, expiration time.Duration) (any, error) {
	return c.getOrSetFuncEntry(ctx, EntryKey{Key: key}, loader, expiration)
}

func (c *ShardedCache) getOrSetFuncEntry(ctx context.Context, key EntryKey, loader LoaderFunc, expiration time.Duration) (result any, resultErr error) {
	if err := c.beginMutation(); err != nil {
		return nil, err
	}
	if ctx == nil {
		c.gate.RUnlock()
		return nil, errors.New("loader context is nil")
	}
	if loader == nil {
		c.gate.RUnlock()
		return nil, errors.New("loader is nil")
	}
	if err := validateExpiration(expiration); err != nil {
		c.gate.RUnlock()
		return nil, err
	}
	c.gate.RUnlock()
	var maintenance mutationResult
	defer func() { c.notifyMaintenance(maintenance) }()
	countQuery := true
	var retryCall *loadCall
	for {
		shard := c.shardFor(key)
		var (
			value             any
			found             bool
			call              *loadCall
			owner             bool
			lookupErr         error
			callback          *callbackRegistration
			mutation          mutationResult
			inherited         bool
			releaseRetryClaim bool
		)
		if retryCall != nil {
			if err := c.beginMutation(); err != nil {
				inherited = true
			} else {
				callback = c.currentCallback()
			}
			value, found, call, owner, mutation, releaseRetryClaim, lookupErr = shard.claimRetryLoader(ctx, key, retryCall, c.clock, !inherited, callback != nil)
			if !inherited {
				c.gate.RUnlock()
			}
			maintenance.merge(mutation)
			if releaseRetryClaim {
				func() {
					defer shard.releaseRetryClaim(retryCall)
					c.invokeForeground(callback, mutation.events)
				}()
			} else {
				c.invokeForeground(callback, mutation.events)
			}
		} else {
			if err := c.beginMutation(); err != nil {
				return nil, err
			}
			callback = c.currentCallback()
			value, found, call, owner, mutation, lookupErr = shard.lookupLoader(ctx, key, c.clock, c.opts.EvictionPolicy, c.nextOrdinal, countQuery, callback != nil)
			c.gate.RUnlock()
			maintenance.merge(mutation)
			c.invokeForeground(callback, mutation.events)
		}
		if lookupErr != nil {
			return nil, lookupErr
		}
		if found {
			return value, nil
		}
		countQuery = false
		if call == nil {
			continue
		}
		if !owner {
			value, err, nextRetry := awaitLoad(ctx, call)
			if nextRetry != nil {
				retryCall = nextRetry
				continue
			}
			return value, err
		}

		loaderFinished := false
		defer func() {
			if !loaderFinished {
				shard.failLoadGoexit(key, call)
			}
		}()
		loaded, panicValue, loadErr := invokeLoader(ctx, loader)
		loaderFinished = true
		if panicValue != nil {
			shard.failLoadPanic(key, call, panicValue)
			panic(panicValue)
		}

		canStore := false
		if !inherited {
			c.lockGateRead()
			canStore = c.state.Load() == cacheOpen
			callback = c.currentCallback()
		}
		result, resultErr, mutation = shard.finishLoad(key, call, loaded, loadErr, ctx.Err() != nil, c.clock, canStore, expiration, c.opts.DefaultExpiration, c.nextOrdinal, callback != nil)
		if !inherited {
			c.gate.RUnlock()
		}
		maintenance.merge(mutation)
		c.invokeForeground(callback, mutation.events)
		return result, resultErr
	}
}

// Count returns the exact number of live entries across every namespace.
func (c *ShardedCache) Count() int { return c.countGroupPointer(nil) }

func (c *ShardedCache) countGroup(group string) int { return c.countGroupPointer(&group) }

func (c *ShardedCache) countGroupPointer(group *string) int {
	c.lockGateRead()
	open := c.state.Load() == cacheOpen
	callback := c.currentCallback()
	total := 0
	var result mutationResult
	for _, shard := range c.shards {
		count, removed := shard.count(c.clock, group, open, callback != nil)
		total += count
		result.merge(removed)
	}
	c.gate.RUnlock()
	c.notifyMaintenance(result)
	c.invokeForeground(callback, result.events)
	return total
}

// Stats returns a strongly typed statistics snapshot. It does not change hit/miss counters.
func (c *ShardedCache) Stats() Stats {
	total := c.Count()
	var hits, misses uint64
	for _, shard := range c.shards {
		hits += shard.hits.Load()
		misses += shard.misses.Load()
	}
	rate := 0.0
	if queries := hits + misses; queries != 0 {
		rate = float64(hits) / float64(queries)
	}
	effective := 0
	if c.opts.MaxEntriesPerShard > 0 {
		effective = c.opts.MaxEntriesPerShard * c.opts.ShardCount
	}
	return Stats{
		TotalCount:          total,
		Hits:                hits,
		Misses:              misses,
		HitRate:             rate,
		MaxEntriesPerShard:  c.opts.MaxEntriesPerShard,
		EffectiveMaxEntries: effective,
		DefaultExpiration:   c.opts.DefaultExpiration,
		ShardCount:          c.opts.ShardCount,
		EvictionPolicy:      c.opts.EvictionPolicy,
		PersistenceStatus:   c.PersistenceStatus(),
		Closed:              c.state.Load() != cacheOpen,
	}
}

// OnEvicted installs or removes the cache-wide eviction callback.
func (c *ShardedCache) OnEvicted(callback func(EntryKey, any, EvictionReason)) error {
	if err := c.beginMutation(); err != nil {
		return err
	}
	if callback == nil {
		c.callback.Store(nil)
	} else {
		c.callback.Store(&callbackRegistration{callback: callback})
	}
	c.gate.RUnlock()
	return nil
}

// Range visits all namespaces one shard snapshot at a time. The visitor runs
// outside internal locks and may re-enter the cache.
func (c *ShardedCache) Range(visitor func(EntryKey, any, time.Time) bool) {
	if visitor == nil {
		return
	}
	for _, shard := range c.shards {
		c.lockGateRead()
		open := c.state.Load() == cacheOpen
		callback := c.currentCallback()
		entries, result := shard.snapshotRange(c.clock, nil, open, callback != nil)
		c.gate.RUnlock()
		c.notifyMaintenance(result)
		c.invokeForeground(callback, result.events)
		for _, entry := range entries {
			if !visitor(entry.key, entry.value, entry.expiresAt) {
				return
			}
		}
	}
}

func (c *ShardedCache) rangeGroup(group string, visitor func(string, any, time.Time) bool) {
	if visitor == nil {
		return
	}
	for _, shard := range c.shards {
		c.lockGateRead()
		open := c.state.Load() == cacheOpen
		callback := c.currentCallback()
		entries, result := shard.snapshotRange(c.clock, &group, open, callback != nil)
		c.gate.RUnlock()
		c.notifyMaintenance(result)
		c.invokeForeground(callback, result.events)
		for _, entry := range entries {
			if !visitor(entry.key.Key, entry.value, entry.expiresAt) {
				return
			}
		}
	}
}

// Clear removes every entry in every namespace.
func (c *ShardedCache) Clear() error { return c.clearGroupPointer(nil) }

func (c *ShardedCache) clearGroup(group string) error { return c.clearGroupPointer(&group) }

func (c *ShardedCache) clearGroupPointer(group *string) error {
	if err := c.beginMutation(); err != nil {
		return err
	}
	callback := c.currentCallback()
	type job struct{}
	buckets := make(map[int]job, len(c.shards))
	for index, shard := range c.shards {
		if shard.hasEntries(group) {
			buckets[index] = job{}
		}
	}
	results := runShardJobs(buckets, func(index int, _ job) mutationResult {
		return c.shards[index].clear(group, c.clock, callback != nil)
	})
	var result mutationResult
	for shardResult := range results {
		result.merge(shardResult)
	}
	c.finishMutation(result, callback)
	return nil
}

// Group returns a concrete structured namespace handle.
func (c *ShardedCache) Group(name string) (Group, error) {
	c.lockGateRead()
	open := c.state.Load() == cacheOpen
	c.gate.RUnlock()
	if !open {
		return Group{}, ErrCacheClosed
	}
	if name == "" {
		return Group{}, ErrEmptyGroup
	}
	return Group{cache: c, name: name}, nil
}

// Flush commits a new snapshot generation when persistence is enabled.
func (c *ShardedCache) Flush() error {
	c.lockGateRead()
	if c.state.Load() != cacheOpen {
		c.gate.RUnlock()
		return ErrCacheClosed
	}
	if c.persistence == nil {
		c.gate.RUnlock()
		return ErrPersistenceDisabled
	}
	err := c.commitPersistence(true)
	c.gate.RUnlock()
	return err
}

// Close stops maintenance, performs the final persistence commit, and releases
// the writer lock. Concurrent callers wait for and receive the same result.
func (c *ShardedCache) Close() error {
	c.closeOnce.Do(func() {
		if hooks := c.lifecycleHooks; hooks != nil && hooks.closeStarted != nil {
			hooks.closeStarted()
		}
		c.gate.Lock()
		c.state.Store(cacheClosing)
		if hooks := c.lifecycleHooks; hooks != nil && hooks.closeBoundary != nil {
			hooks.closeBoundary()
		}
		for _, shard := range c.shards {
			shard.freezeExpirationOrder()
		}
		c.gate.Unlock()

		close(c.maintenanceStop)
		c.maintenanceWG.Wait()
		if c.persistence != nil {
			c.closeErr = c.commitPersistence(true)
			if err := c.closePersistence(); err != nil {
				c.closeErr = errors.Join(c.closeErr, err)
			}
		}
		c.state.Store(cacheClosed)
		c.closeBackgroundDispatcher()
	})
	return c.closeErr
}

func (c *ShardedCache) runCleaner() {
	for {
		deadline, found := c.nextExpiration()
		if !found {
			select {
			case <-c.maintenanceStop:
				return
			case <-c.cleanWake:
				continue
			}
		}
		if hooks := c.maintenanceHooks; hooks != nil && hooks.cleanerWait != nil {
			hooks.cleanerWait(deadline)
		}
		delay := deadline.Sub(c.clock.Now())
		if delay < 0 {
			delay = 0
		}
		timer := time.NewTimer(delay)
		select {
		case <-c.maintenanceStop:
			stopTimer(timer)
			return
		case <-c.cleanWake:
			stopTimer(timer)
			continue
		case <-timer.C:
			c.expireDueInBackground()
		}
	}
}

func stopTimer(timer *time.Timer) {
	if !timer.Stop() {
		select {
		case <-timer.C:
		default:
		}
	}
}

func (c *ShardedCache) nextExpiration() (time.Time, bool) {
	var earliest time.Time
	found := false
	for _, shard := range c.shards {
		deadline, ok := shard.earliestExpiry()
		if ok && (!found || deadline.Before(earliest)) {
			earliest, found = deadline, true
		}
	}
	return earliest, found
}

func (c *ShardedCache) expireDueInBackground() {
	c.lockGateRead()
	if c.state.Load() != cacheOpen {
		c.gate.RUnlock()
		return
	}
	callback := c.currentCallback()
	var result mutationResult
	for _, shard := range c.shards {
		result.merge(shard.purgeDue(c.clock, callback != nil))
	}
	c.gate.RUnlock()
	c.notifyMaintenance(result)
	c.enqueueBackground(callback, result.events)
}

func runShardJobs[J any, R any](jobs map[int]J, work func(int, J) R) <-chan R {
	results := make(chan R, len(jobs))
	if len(jobs) == 0 {
		close(results)
		return results
	}
	if len(jobs) == 1 {
		for index, job := range jobs {
			results <- work(index, job)
		}
		close(results)
		return results
	}
	workers := min(runtime.GOMAXPROCS(0), len(jobs))
	type shardJob struct {
		index int
		value J
	}
	queue := make(chan shardJob)
	var wait sync.WaitGroup
	for range workers {
		wait.Go(func() {
			for job := range queue {
				results <- work(job.index, job.value)
			}
		})
	}
	go func() {
		for index, job := range jobs {
			queue <- shardJob{index: index, value: job}
		}
		close(queue)
		wait.Wait()
		close(results)
	}()
	return results
}
