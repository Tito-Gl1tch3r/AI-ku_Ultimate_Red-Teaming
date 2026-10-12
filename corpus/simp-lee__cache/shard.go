package shardedcache

import (
	"container/heap"
	"context"
	"runtime"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type clock interface {
	Now() time.Time
}

type realClock struct{}

func (realClock) Now() time.Time { return time.Now() }

type cacheItem struct {
	key         string
	namespace   *namespaceIndex
	value       any
	expiresAt   time.Time
	expiryIndex int
	previous    *cacheItem
	next        *cacheItem
	ordinal     uint64
}

func (item *cacheItem) group() string {
	if item.namespace == nil {
		return ""
	}
	return item.namespace.group
}

func (item *cacheItem) entryKey() EntryKey {
	return EntryKey{Group: item.group(), Key: item.key}
}

type expiryHeap []*cacheItem

func (h expiryHeap) Len() int { return len(h) }
func (h expiryHeap) Less(i, j int) bool {
	if h[i].expiresAt.Equal(h[j].expiresAt) {
		leftGroup, rightGroup := h[i].group(), h[j].group()
		if leftGroup == rightGroup {
			return h[i].key < h[j].key
		}
		return leftGroup < rightGroup
	}
	return h[i].expiresAt.Before(h[j].expiresAt)
}
func (h expiryHeap) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
	h[i].expiryIndex = i
	h[j].expiryIndex = j
}
func (h *expiryHeap) Push(value any) {
	item := value.(*cacheItem)
	item.expiryIndex = len(*h)
	*h = append(*h, item)
}
func (h *expiryHeap) Pop() any {
	old := *h
	last := len(old) - 1
	item := old[last]
	old[last] = nil
	item.expiryIndex = -1
	*h = old[:last]
	return item
}

type namespaceIndex struct {
	group   string
	members map[string]*cacheItem
}

type cacheShard struct {
	mu               sync.RWMutex
	ungrouped        map[string]*cacheItem
	groups           map[string]*namespaceIndex
	expiry           expiryHeap
	oldest           *cacheItem
	newest           *cacheItem
	liveCount        int
	maxEntries       int
	policy           EvictionPolicy
	trackPersistence bool
	pointReadHooks   *pointReadTestHooks

	hits             atomic.Uint64
	misses           atomic.Uint64
	mutationVersion  atomic.Uint64
	persistedVersion atomic.Uint64
	flights          map[EntryKey]*loadCall
}

type pointReadTestHooks struct {
	fifoLocked func()
}

type loadCall struct {
	done              chan struct{}
	value             any
	err               error
	panicValue        any
	retry             *loadCall
	retryTestHook     func(*loadCall)
	retryJoinTestHook func()
	finishTestHook    func()
	retryClaimWait    *loadCall
	completed         bool
	goexit            bool
}

type eviction struct {
	key    EntryKey
	value  any
	reason EvictionReason
}

type mutationResult struct {
	events          []eviction
	changed         bool
	deadlineChanged bool
}

func (result *mutationResult) merge(other mutationResult) {
	result.events = append(result.events, other.events...)
	result.changed = result.changed || other.changed
	result.deadlineChanged = result.deadlineChanged || other.deadlineChanged
}

type rangeEntry struct {
	key       EntryKey
	value     any
	expiresAt time.Time
}

func newCacheShard(maxEntries int, policy EvictionPolicy, trackPersistence bool) *cacheShard {
	return &cacheShard{
		ungrouped:        make(map[string]*cacheItem),
		groups:           make(map[string]*namespaceIndex),
		maxEntries:       maxEntries,
		policy:           policy,
		trackPersistence: trackPersistence,
		flights:          make(map[EntryKey]*loadCall),
	}
}

func itemExpired(item *cacheItem, now time.Time) bool {
	return !item.expiresAt.IsZero() && !now.Before(item.expiresAt)
}

func expirationTime(now time.Time, expiration, defaultExpiration time.Duration) time.Time {
	if expiration == DefaultExpiration {
		expiration = defaultExpiration
	}
	if expiration <= 0 {
		return time.Time{}
	}
	return now.Add(expiration)
}

func (s *cacheShard) markDirtyLocked(changes uint64) {
	if s.trackPersistence && changes != 0 {
		s.mutationVersion.Add(changes)
	}
}

func (s *cacheShard) earliestExpiryLocked() time.Time {
	if len(s.expiry) == 0 {
		return time.Time{}
	}
	return s.expiry[0].expiresAt
}

func (s *cacheShard) finishDeadlineChange(result *mutationResult, before time.Time) {
	result.deadlineChanged = result.deadlineChanged || !before.Equal(s.earliestExpiryLocked())
}

func (s *cacheShard) memberLocked(key EntryKey) *cacheItem {
	if key.Group == "" {
		return s.ungrouped[key.Key]
	}
	namespace := s.groups[key.Group]
	if namespace == nil {
		return nil
	}
	return namespace.members[key.Key]
}

func (s *cacheShard) membersForGroupLocked(group string) map[string]*cacheItem {
	if group == "" {
		return s.ungrouped
	}
	namespace := s.groups[group]
	if namespace == nil {
		return nil
	}
	return namespace.members
}

func (s *cacheShard) insertMemberLocked(key EntryKey, item *cacheItem) {
	item.key = key.Key
	if key.Group == "" {
		item.namespace = nil
		s.ungrouped[key.Key] = item
		return
	}
	namespace := s.groups[key.Group]
	if namespace == nil {
		namespace = &namespaceIndex{group: key.Group, members: make(map[string]*cacheItem)}
		s.groups[key.Group] = namespace
	}
	item.namespace = namespace
	namespace.members[key.Key] = item
}

func (s *cacheShard) deleteMemberLocked(item *cacheItem) {
	if item.namespace == nil {
		delete(s.ungrouped, item.key)
		return
	}
	namespace := item.namespace
	delete(namespace.members, item.key)
	if len(namespace.members) == 0 {
		delete(s.groups, namespace.group)
	}
}

func (s *cacheShard) appendPolicyLocked(item *cacheItem) {
	item.previous = s.newest
	item.next = nil
	if s.newest == nil {
		s.oldest = item
	} else {
		s.newest.next = item
	}
	s.newest = item
}

func (s *cacheShard) unlinkPolicyLocked(item *cacheItem) {
	if item.previous == nil {
		s.oldest = item.next
	} else {
		item.previous.next = item.next
	}
	if item.next == nil {
		s.newest = item.previous
	} else {
		item.next.previous = item.previous
	}
	item.previous = nil
	item.next = nil
}

func (s *cacheShard) promoteLocked(item *cacheItem, ordinal uint64) {
	item.ordinal = ordinal
	if item == s.newest {
		return
	}
	s.unlinkPolicyLocked(item)
	s.appendPolicyLocked(item)
}

func (s *cacheShard) policyOrdinal(ordinal func() uint64) uint64 {
	if !s.trackPersistence {
		return 0
	}
	return ordinal()
}

func (s *cacheShard) promoteForAccessLocked(item *cacheItem, ordinal func() uint64) {
	if s.trackPersistence {
		s.promoteLocked(item, ordinal())
		return
	}
	if item != s.newest {
		s.unlinkPolicyLocked(item)
		s.appendPolicyLocked(item)
	}
}

func (s *cacheShard) removeLocked(item *cacheItem, reason EvictionReason, markDirty, collectEvents bool, result *mutationResult) {
	if collectEvents {
		result.events = append(result.events, eviction{key: item.entryKey(), value: item.value, reason: reason})
	}
	s.deleteMemberLocked(item)
	if item.expiryIndex >= 0 {
		heap.Remove(&s.expiry, item.expiryIndex)
	}
	s.unlinkPolicyLocked(item)
	s.liveCount--
	if markDirty {
		s.markDirtyLocked(1)
	}
	result.changed = true
}

func (s *cacheShard) purgeDueLocked(now time.Time, collectEvents bool, result *mutationResult) {
	for len(s.expiry) != 0 {
		item := s.expiry[0]
		if now.Before(item.expiresAt) {
			break
		}
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, result)
	}
}

func (s *cacheShard) updateExpiryLocked(item *cacheItem, expiresAt time.Time) {
	item.expiresAt = expiresAt
	if expiresAt.IsZero() {
		if item.expiryIndex >= 0 {
			heap.Remove(&s.expiry, item.expiryIndex)
		}
	} else if item.expiryIndex < 0 {
		heap.Push(&s.expiry, item)
	} else {
		heap.Fix(&s.expiry, item.expiryIndex)
	}
}

func (s *cacheShard) setLocked(key EntryKey, value any, expiration time.Duration, defaultExpiration time.Duration, now time.Time, ordinal func() uint64, collectEvents bool) mutationResult {
	beforeDeadline := s.earliestExpiryLocked()
	var result mutationResult
	old := s.memberLocked(key)
	if old != nil && itemExpired(old, now) {
		s.removeLocked(old, EvictionReasonExpired, true, collectEvents, &result)
		old = nil
	}

	newExpiry := expirationTime(now, expiration, defaultExpiration)
	if old != nil {
		if collectEvents {
			result.events = append(result.events, eviction{key: old.entryKey(), value: old.value, reason: EvictionReasonReplaced})
		}
		old.value = value
		s.updateExpiryLocked(old, newExpiry)
		s.promoteForAccessLocked(old, ordinal)
		s.markDirtyLocked(1)
		result.changed = true
		s.finishDeadlineChange(&result, beforeDeadline)
		return result
	}

	s.purgeDueLocked(now, collectEvents, &result)
	if s.maxEntries > 0 && s.liveCount >= s.maxEntries && s.oldest != nil {
		s.removeLocked(s.oldest, EvictionReasonCapacity, true, collectEvents, &result)
	}
	item := &cacheItem{
		value:       value,
		expiresAt:   newExpiry,
		expiryIndex: -1,
		ordinal:     s.policyOrdinal(ordinal),
	}
	s.insertMemberLocked(key, item)
	s.appendPolicyLocked(item)
	s.liveCount++
	if !item.expiresAt.IsZero() {
		heap.Push(&s.expiry, item)
	}
	s.markDirtyLocked(1)
	result.changed = true
	s.finishDeadlineChange(&result, beforeDeadline)
	return result
}

func (s *cacheShard) closedValueLocked(item *cacheItem, cacheClock clock) (any, time.Time, bool) {
	if item == nil {
		return nil, time.Time{}, false
	}
	if !item.expiresAt.IsZero() && itemExpired(item, cacheClock.Now()) {
		return nil, time.Time{}, false
	}
	return item.value, item.expiresAt, true
}

func (s *cacheShard) get(key EntryKey, cacheClock clock, state *atomic.Uint32, policy EvictionPolicy, ordinal func() uint64, collectEvents bool) (any, time.Time, bool, mutationResult) {
	if policy == FIFO {
		s.mu.RLock()
		if hooks := s.pointReadHooks; hooks != nil && hooks.fifoLocked != nil {
			hooks.fifoLocked()
		}
		item := s.memberLocked(key)
		if state.Load() != cacheOpen {
			value, expiresAt, found := s.closedValueLocked(item, cacheClock)
			s.mu.RUnlock()
			return value, expiresAt, found, mutationResult{}
		}
		if item == nil {
			s.misses.Add(1)
			s.mu.RUnlock()
			return nil, time.Time{}, false, mutationResult{}
		}
		if item.expiresAt.IsZero() {
			value := item.value
			s.hits.Add(1)
			s.mu.RUnlock()
			return value, time.Time{}, true, mutationResult{}
		}
		now := cacheClock.Now()
		if !itemExpired(item, now) {
			value, expiresAt := item.value, item.expiresAt
			s.hits.Add(1)
			s.mu.RUnlock()
			return value, expiresAt, true, mutationResult{}
		}
		s.mu.RUnlock()

		s.mu.Lock()
		item = s.memberLocked(key)
		if state.Load() != cacheOpen {
			value, expiresAt, found := s.closedValueLocked(item, cacheClock)
			s.mu.Unlock()
			return value, expiresAt, found, mutationResult{}
		}
		if item == nil {
			s.misses.Add(1)
			s.mu.Unlock()
			return nil, time.Time{}, false, mutationResult{}
		}
		if item.expiresAt.IsZero() || !itemExpired(item, cacheClock.Now()) {
			value, expiresAt := item.value, item.expiresAt
			s.hits.Add(1)
			s.mu.Unlock()
			return value, expiresAt, true, mutationResult{}
		}
		beforeDeadline := s.earliestExpiryLocked()
		var result mutationResult
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		s.misses.Add(1)
		s.mu.Unlock()
		return nil, time.Time{}, false, result
	}

	s.mu.Lock()
	item := s.memberLocked(key)
	if state.Load() != cacheOpen {
		value, expiresAt, found := s.closedValueLocked(item, cacheClock)
		s.mu.Unlock()
		return value, expiresAt, found, mutationResult{}
	}
	if item == nil {
		s.misses.Add(1)
		s.mu.Unlock()
		return nil, time.Time{}, false, mutationResult{}
	}
	if !item.expiresAt.IsZero() && itemExpired(item, cacheClock.Now()) {
		beforeDeadline := s.earliestExpiryLocked()
		var result mutationResult
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		s.misses.Add(1)
		s.mu.Unlock()
		return nil, time.Time{}, false, result
	}
	s.promoteForAccessLocked(item, ordinal)
	value, expiresAt := item.value, item.expiresAt
	s.hits.Add(1)
	s.mu.Unlock()
	return value, expiresAt, true, mutationResult{}
}

func (s *cacheShard) touch(key EntryKey, expiration, defaultExpiration time.Duration, cacheClock clock, collectEvents bool) (bool, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	item := s.memberLocked(key)
	if item == nil {
		s.mu.Unlock()
		return false, mutationResult{}
	}
	beforeDeadline := s.earliestExpiryLocked()
	var result mutationResult
	if itemExpired(item, now) {
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		s.mu.Unlock()
		return false, result
	}
	newExpiry := expirationTime(now, expiration, defaultExpiration)
	if item.expiresAt.Equal(newExpiry) {
		s.mu.Unlock()
		return true, mutationResult{}
	}
	s.updateExpiryLocked(item, newExpiry)
	s.markDirtyLocked(1)
	result.changed = true
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return true, result
}

func (s *cacheShard) delete(key EntryKey, cacheClock clock, collectEvents bool) (bool, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	item := s.memberLocked(key)
	if item == nil {
		s.mu.Unlock()
		return false, mutationResult{}
	}
	beforeDeadline := s.earliestExpiryLocked()
	var result mutationResult
	if itemExpired(item, now) {
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		s.mu.Unlock()
		return false, result
	}
	s.removeLocked(item, EvictionReasonDeleted, true, collectEvents, &result)
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return true, result
}

func (s *cacheShard) deleteKeys(keys []EntryKey, cacheClock clock, collectEvents bool) (int, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	beforeDeadline := s.earliestExpiryLocked()
	deleted := 0
	var result mutationResult
	seen := make(map[EntryKey]struct{}, len(keys))
	for _, key := range keys {
		if _, duplicate := seen[key]; duplicate {
			continue
		}
		seen[key] = struct{}{}
		item := s.memberLocked(key)
		if item == nil {
			continue
		}
		if itemExpired(item, now) {
			s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
			continue
		}
		s.removeLocked(item, EvictionReasonDeleted, true, collectEvents, &result)
		deleted++
	}
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return deleted, result
}

func (s *cacheShard) deletePrefix(group, prefix string, cacheClock clock, collectEvents bool) (int, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	members := s.membersForGroupLocked(group)
	if len(members) == 0 {
		s.mu.Unlock()
		return 0, mutationResult{}
	}
	beforeDeadline := s.earliestExpiryLocked()
	deleted := 0
	var result mutationResult
	for key, item := range members {
		if !strings.HasPrefix(key, prefix) {
			continue
		}
		if itemExpired(item, now) {
			s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
			continue
		}
		s.removeLocked(item, EvictionReasonDeleted, true, collectEvents, &result)
		deleted++
	}
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return deleted, result
}

func (s *cacheShard) clear(group *string, cacheClock clock, collectEvents bool) mutationResult {
	s.mu.Lock()
	now := cacheClock.Now()
	beforeDeadline := s.earliestExpiryLocked()
	var items []*cacheItem
	if group == nil {
		items = make([]*cacheItem, 0, s.liveCount)
		for item := s.oldest; item != nil; item = item.next {
			items = append(items, item)
		}
	} else {
		members := s.membersForGroupLocked(*group)
		items = make([]*cacheItem, 0, len(members))
		for _, item := range members {
			items = append(items, item)
		}
	}
	var result mutationResult
	if collectEvents {
		result.events = make([]eviction, 0, len(items))
	}
	for _, item := range items {
		reason := EvictionReasonCleared
		if itemExpired(item, now) {
			reason = EvictionReasonExpired
		}
		s.removeLocked(item, reason, true, collectEvents, &result)
	}
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return result
}

func (s *cacheShard) count(cacheClock clock, group *string, open, collectEvents bool) (int, mutationResult) {
	if open {
		s.mu.Lock()
		now := cacheClock.Now()
		beforeDeadline := s.earliestExpiryLocked()
		var result mutationResult
		s.purgeDueLocked(now, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		count := s.liveCount
		if group != nil {
			count = len(s.membersForGroupLocked(*group))
		}
		s.mu.Unlock()
		return count, result
	}

	s.mu.RLock()
	now := cacheClock.Now()
	if group != nil {
		count := 0
		for _, item := range s.membersForGroupLocked(*group) {
			if !itemExpired(item, now) {
				count++
			}
		}
		s.mu.RUnlock()
		return count, mutationResult{}
	}
	count := s.liveCount
	due := sort.Search(len(s.expiry), func(i int) bool { return s.expiry[i].expiresAt.After(now) })
	s.mu.RUnlock()
	return count - due, mutationResult{}
}

func (s *cacheShard) snapshotRange(cacheClock clock, group *string, open, collectEvents bool) ([]rangeEntry, mutationResult) {
	if open {
		s.mu.Lock()
		now := cacheClock.Now()
		beforeDeadline := s.earliestExpiryLocked()
		var result mutationResult
		s.purgeDueLocked(now, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		entries := s.copyRangeLocked(group, now, false)
		s.mu.Unlock()
		return entries, result
	}
	s.mu.RLock()
	now := cacheClock.Now()
	entries := s.copyRangeLocked(group, now, true)
	s.mu.RUnlock()
	return entries, mutationResult{}
}

func (s *cacheShard) copyRangeLocked(group *string, now time.Time, filterDue bool) []rangeEntry {
	capacity := s.liveCount
	if group != nil {
		capacity = len(s.membersForGroupLocked(*group))
		if capacity == 0 {
			return nil
		}
	}
	entries := make([]rangeEntry, 0, capacity)
	appendItem := func(item *cacheItem) {
		if filterDue && itemExpired(item, now) {
			return
		}
		entries = append(entries, rangeEntry{key: item.entryKey(), value: item.value, expiresAt: item.expiresAt})
	}
	if group == nil {
		for item := s.oldest; item != nil; item = item.next {
			appendItem(item)
		}
	} else {
		for _, item := range s.membersForGroupLocked(*group) {
			appendItem(item)
		}
	}
	return entries
}

func (s *cacheShard) hasEntries(group *string) bool {
	s.mu.RLock()
	found := s.liveCount != 0
	if group != nil {
		found = len(s.membersForGroupLocked(*group)) != 0
	}
	s.mu.RUnlock()
	return found
}

func (s *cacheShard) earliestExpiry() (time.Time, bool) {
	s.mu.RLock()
	if len(s.expiry) == 0 {
		s.mu.RUnlock()
		return time.Time{}, false
	}
	deadline := s.expiry[0].expiresAt
	s.mu.RUnlock()
	return deadline, true
}

func (s *cacheShard) purgeDue(cacheClock clock, collectEvents bool) mutationResult {
	s.mu.Lock()
	beforeDeadline := s.earliestExpiryLocked()
	var result mutationResult
	s.purgeDueLocked(cacheClock.Now(), collectEvents, &result)
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return result
}

func (s *cacheShard) persistenceSnapshot(cacheClock clock) (persistedShard, uint64) {
	s.mu.RLock()
	now := cacheClock.Now()
	version := s.mutationVersion.Load()
	items := make([]persistedItem, 0, s.liveCount)
	for item := s.oldest; item != nil; item = item.next {
		if itemExpired(item, now) {
			continue
		}
		items = append(items, persistedItem{
			Key:       item.entryKey(),
			Value:     item.value,
			ExpiresAt: item.expiresAt,
			Ordinal:   item.ordinal,
		})
	}
	s.mu.RUnlock()
	return persistedShard{Items: items}, version
}

func (s *cacheShard) addRestored(item persistedItem) {
	s.mu.Lock()
	stored := &cacheItem{
		value:       item.Value,
		expiresAt:   item.ExpiresAt,
		expiryIndex: -1,
		ordinal:     item.Ordinal,
	}
	s.insertMemberLocked(item.Key, stored)
	s.appendPolicyLocked(stored)
	s.liveCount++
	if !stored.expiresAt.IsZero() {
		heap.Push(&s.expiry, stored)
	}
	s.mu.Unlock()
}

func (s *cacheShard) freezeExpirationOrder() {
	s.mu.Lock()
	sort.Sort(s.expiry)
	for index, item := range s.expiry {
		item.expiryIndex = index
	}
	s.mu.Unlock()
}

func (s *cacheShard) getOrSet(key EntryKey, value any, defaultExpiration time.Duration, cacheClock clock, policy EvictionPolicy, ordinal func() uint64, collectEvents bool) (any, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	beforeDeadline := s.earliestExpiryLocked()
	item := s.memberLocked(key)
	var result mutationResult
	if item != nil && itemExpired(item, now) {
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		item = nil
	}
	if item != nil {
		if policy == LRU {
			s.promoteForAccessLocked(item, ordinal)
		}
		s.hits.Add(1)
		value := item.value
		s.finishDeadlineChange(&result, beforeDeadline)
		s.mu.Unlock()
		return value, result
	}
	s.misses.Add(1)
	result.merge(s.setLocked(key, value, DefaultExpiration, defaultExpiration, now, ordinal, collectEvents))
	s.finishDeadlineChange(&result, beforeDeadline)
	s.mu.Unlock()
	return value, result
}

func (s *cacheShard) lookupLoader(ctx context.Context, key EntryKey, cacheClock clock, policy EvictionPolicy, ordinal func() uint64, countQuery, collectEvents bool) (any, bool, *loadCall, bool, mutationResult, error) {
	s.mu.Lock()
	now := cacheClock.Now()
	item := s.memberLocked(key)
	if item != nil && itemExpired(item, now) {
		beforeDeadline := s.earliestExpiryLocked()
		var result mutationResult
		s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
		s.finishDeadlineChange(&result, beforeDeadline)
		if countQuery {
			s.misses.Add(1)
		}
		s.mu.Unlock()
		return nil, false, nil, false, result, nil
	}
	if item != nil {
		if countQuery {
			s.hits.Add(1)
		}
		if policy == LRU && countQuery {
			s.promoteForAccessLocked(item, ordinal)
		}
		value := item.value
		s.mu.Unlock()
		return value, true, nil, false, mutationResult{}, nil
	}
	if countQuery {
		s.misses.Add(1)
	}
	if call := s.flights[key]; call != nil {
		s.mu.Unlock()
		return nil, false, call, false, mutationResult{}, nil
	}
	if err := ctx.Err(); err != nil {
		s.mu.Unlock()
		return nil, false, nil, false, mutationResult{}, err
	}
	call := &loadCall{done: make(chan struct{})}
	s.flights[key] = call
	s.mu.Unlock()
	return nil, false, call, true, mutationResult{}, nil
}

func (s *cacheShard) claimRetryLoader(ctx context.Context, key EntryKey, retry *loadCall, cacheClock clock, canMutate, collectEvents bool) (any, bool, *loadCall, bool, mutationResult, bool, error) {
	s.mu.Lock()
	if retry.completed {
		s.mu.Unlock()
		return nil, false, retry, false, mutationResult{}, false, nil
	}
	if retry.retryClaimWait != nil {
		wait := retry.retryClaimWait
		s.mu.Unlock()
		return nil, false, wait, false, mutationResult{}, false, nil
	}
	if call := s.flights[key]; call != nil {
		if call == retry {
			if retry.retryJoinTestHook != nil {
				retry.retryJoinTestHook()
			}
			s.mu.Unlock()
			return nil, false, retry, false, mutationResult{}, false, nil
		}
		retry.retry = call
		retry.completed = true
		close(retry.done)
		s.mu.Unlock()
		return nil, false, retry, false, mutationResult{}, false, nil
	}
	item := s.memberLocked(key)
	if item != nil {
		expired := !item.expiresAt.IsZero() && itemExpired(item, cacheClock.Now())
		if !expired {
			retry.value = item.value
			retry.completed = true
			close(retry.done)
			value := item.value
			s.mu.Unlock()
			return value, true, nil, false, mutationResult{}, false, nil
		}
		if canMutate {
			beforeDeadline := s.earliestExpiryLocked()
			var result mutationResult
			s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &result)
			s.finishDeadlineChange(&result, beforeDeadline)
			retry.retryClaimWait = &loadCall{done: make(chan struct{}), retry: retry}
			s.mu.Unlock()
			return nil, false, nil, false, result, true, nil
		}
	}
	if err := ctx.Err(); err != nil {
		s.mu.Unlock()
		return nil, false, nil, false, mutationResult{}, false, err
	}
	s.flights[key] = retry
	s.mu.Unlock()
	return nil, false, retry, true, mutationResult{}, false, nil
}

func (s *cacheShard) releaseRetryClaim(retry *loadCall) {
	s.mu.Lock()
	wait := retry.retryClaimWait
	retry.retryClaimWait = nil
	if wait != nil {
		wait.completed = true
		close(wait.done)
	}
	s.mu.Unlock()
}

func (s *cacheShard) finishLoad(key EntryKey, call *loadCall, loaded any, loadErr error, ownerCanceled bool, cacheClock clock, canStore bool, expiration, defaultExpiration time.Duration, ordinal func() uint64, collectEvents bool) (any, error, mutationResult) {
	s.mu.Lock()
	now := cacheClock.Now()
	beforeDeadline := s.earliestExpiryLocked()
	var mutation mutationResult
	if loadErr != nil {
		if item := s.memberLocked(key); item != nil {
			if !itemExpired(item, now) {
				call.value = item.value
				call.completed = true
				delete(s.flights, key)
				close(call.done)
				finishTestHook := call.finishTestHook
				s.mu.Unlock()
				if finishTestHook != nil {
					finishTestHook()
				}
				return call.value, nil, mutationResult{}
			}
			if canStore {
				s.removeLocked(item, EvictionReasonExpired, true, collectEvents, &mutation)
			}
		}
		call.err = loadErr
		if ownerCanceled {
			call.retry = &loadCall{done: make(chan struct{})}
		}
		call.completed = true
		delete(s.flights, key)
		close(call.done)
		s.finishDeadlineChange(&mutation, beforeDeadline)
		s.mu.Unlock()
		return nil, loadErr, mutation
	}

	result := loaded
	if item := s.memberLocked(key); item != nil && !itemExpired(item, now) {
		result = item.value
	} else if canStore {
		mutation = s.setLocked(key, loaded, expiration, defaultExpiration, now, ordinal, collectEvents)
	}
	call.value = result
	call.completed = true
	delete(s.flights, key)
	close(call.done)
	s.finishDeadlineChange(&mutation, beforeDeadline)
	s.mu.Unlock()
	return result, nil, mutation
}

func invokeLoader(ctx context.Context, loader LoaderFunc) (value any, panicValue any, err error) {
	func() {
		defer func() { panicValue = recover() }()
		value, err = loader(ctx)
	}()
	return value, panicValue, err
}

func (s *cacheShard) failLoadPanic(key EntryKey, call *loadCall, panicValue any) {
	s.mu.Lock()
	call.panicValue = panicValue
	call.completed = true
	delete(s.flights, key)
	close(call.done)
	s.mu.Unlock()
}

func (s *cacheShard) failLoadGoexit(key EntryKey, call *loadCall) {
	s.mu.Lock()
	call.goexit = true
	call.completed = true
	delete(s.flights, key)
	close(call.done)
	s.mu.Unlock()
}

func awaitLoad(ctx context.Context, call *loadCall) (any, error, *loadCall) {
	select {
	case <-call.done:
		if err := ctx.Err(); err != nil {
			return nil, err, nil
		}
		if call.goexit {
			runtime.Goexit()
		}
		if call.panicValue != nil {
			panic(call.panicValue)
		}
		if call.retry != nil {
			if call.retryTestHook != nil {
				call.retryTestHook(call.retry)
			}
			return nil, nil, call.retry
		}
		return call.value, call.err, nil
	case <-ctx.Done():
		return nil, ctx.Err(), nil
	}
}
