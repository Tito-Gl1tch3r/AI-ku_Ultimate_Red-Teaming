package shardedcache

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func requirePersistenceSupport(t *testing.T) {
	t.Helper()
	if runtime.GOOS == "aix" {
		t.Skip("persistence is unsupported on AIX")
	}
}

func persistentOptions(path string, shards int) Options {
	options := DefaultOptions()
	options.ShardCount = shards
	options.CleanupEnabled = false
	options.Persistence = &PersistenceOptions{Path: path}
	return options
}

func readManifestForTest(t *testing.T, path string) manifestFile {
	t.Helper()
	metadata, payload, _, err := readEnvelopeFile(filepath.Join(path, manifestFilename), fileTypeManifest)
	if err != nil {
		t.Fatal(err)
	}
	var manifest manifestFile
	if err := decodeGob(payload, &manifest); err != nil {
		t.Fatal(err)
	}
	if metadata.generation != manifest.Generation {
		t.Fatalf("metadata generation %d != payload %d", metadata.generation, manifest.Generation)
	}
	return manifest
}

func keyForShard(cache *ShardedCache, shard int, prefix string) string {
	for index := 0; ; index++ {
		key := prefix + string(rune(index))
		if cache.shardIndex(EntryKey{Key: key}) == shard {
			return key
		}
	}
}

func copyBaselineSnapshotFixture(t *testing.T) string {
	t.Helper()
	destination := t.TempDir()
	for _, name := range []string{manifestFilename, "shard-0-generation-1.bin"} {
		data, err := os.ReadFile(filepath.Join("testdata", "baseline-v1", name))
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(destination, name), data, 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return destination
}

func TestMkdirAllAndSyncParents(t *testing.T) {
	t.Run("syncs every new parent", func(t *testing.T) {
		root := t.TempDir()
		existing := filepath.Join(root, "existing")
		if err := os.Mkdir(existing, 0o700); err != nil {
			t.Fatal(err)
		}
		path := filepath.Join(existing, "first", "second")
		var synced []string
		err := mkdirAllAndSyncParents(path, 0o700, func(parent string) error {
			synced = append(synced, parent)
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
		want := []string{existing, filepath.Join(existing, "first")}
		if !reflect.DeepEqual(synced, want) {
			t.Fatalf("synced parents = %v, want %v", synced, want)
		}
		if info, err := os.Stat(path); err != nil || !info.IsDir() {
			t.Fatalf("created path: info=%v err=%v", info, err)
		}
	})

	t.Run("propagates sync failure", func(t *testing.T) {
		failure := errors.New("injected parent sync failure")
		path := filepath.Join(t.TempDir(), "first", "second")
		err := mkdirAllAndSyncParents(path, 0o700, func(string) error { return failure })
		if !errors.Is(err, failure) {
			t.Fatalf("mkdirAllAndSyncParents error = %v, want %v", err, failure)
		}
	})
}

func TestBaselineSnapshotV1(t *testing.T) {
	requirePersistenceSupport(t)
	t.Run("contents", func(t *testing.T) {
		options := persistentOptions(copyBaselineSnapshotFixture(t), 1)
		options.EvictionPolicy = LRU
		cache, err := New(options)
		if err != nil {
			t.Fatal(err)
		}
		defer cache.Close()
		group, err := cache.Group("baseline\x00group")
		if err != nil {
			t.Fatal(err)
		}
		if cache.Count() != 4 || group.Count() != 2 {
			t.Fatalf("restored counts = %d, %d", cache.Count(), group.Count())
		}
		checks := []struct {
			name  string
			get   func() (any, bool)
			value string
		}{
			{name: "ungrouped alpha", get: func() (any, bool) { return cache.Get("alpha") }, value: "ungrouped-alpha"},
			{name: "ungrouped beta", get: func() (any, bool) { return cache.Get("beta") }, value: "ungrouped-beta"},
			{name: "grouped alpha", get: func() (any, bool) { return group.Get("alpha") }, value: "grouped-alpha"},
			{name: "grouped omega", get: func() (any, bool) { return group.Get("omega") }, value: "grouped-omega"},
		}
		for _, check := range checks {
			if value, found := check.get(); !found || value != check.value {
				t.Errorf("%s = %v, %v", check.name, value, found)
			}
		}
	})

	t.Run("policy order", func(t *testing.T) {
		options := persistentOptions(copyBaselineSnapshotFixture(t), 1)
		options.EvictionPolicy = LRU
		options.MaxEntriesPerShard = 3
		cache, err := New(options)
		if err != nil {
			t.Fatal(err)
		}
		defer cache.Close()
		group, err := cache.Group("baseline\x00group")
		if err != nil {
			t.Fatal(err)
		}
		if _, found := cache.Get("beta"); found {
			t.Fatal("oldest ungrouped beta survived restore capacity enforcement")
		}
		if err := cache.Set("probe", "probe"); err != nil {
			t.Fatal(err)
		}
		if _, found := group.Get("omega"); found {
			t.Fatal("next-oldest grouped omega survived insertion")
		}
		if value, found := cache.Get("alpha"); !found || value != "ungrouped-alpha" {
			t.Fatalf("ungrouped alpha = %v, %v", value, found)
		}
		if value, found := group.Get("alpha"); !found || value != "grouped-alpha" {
			t.Fatalf("grouped alpha = %v, %v", value, found)
		}
	})
}

func TestPersistenceEnvelope(t *testing.T) {
	payload := []byte("payload")
	metadata := envelopeMetadata{fileType: fileTypeShard, generation: 7, shardCount: 8, shardID: 3}
	data, err := encodeEnvelope(metadata, payload)
	if err != nil {
		t.Fatal(err)
	}
	decoded, got, err := decodeEnvelope(data, fileTypeShard)
	if err != nil {
		t.Fatal(err)
	}
	if decoded != metadata || string(got) != string(payload) {
		t.Fatalf("decoded = %+v, %q", decoded, got)
	}
	for _, mutate := range []func([]byte){
		func(value []byte) { value[0] ^= 0xff },
		func(value []byte) { value[8]++ },
		func(value []byte) { value[20]++ },
		func(value []byte) { value[43]++ },
		func(value []byte) { value[len(value)-1] ^= 1 },
	} {
		corrupt := append([]byte(nil), data...)
		mutate(corrupt)
		if _, _, err := decodeEnvelope(corrupt, fileTypeShard); err == nil {
			t.Fatal("corrupt envelope was accepted")
		}
	}
	if _, _, err := decodeEnvelope(data[:len(data)-1], fileTypeShard); err == nil {
		t.Fatal("truncated envelope was accepted")
	}
}

func TestPersistenceCommit(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 2)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	first := keyForShard(cache, 0, "first")
	second := keyForShard(cache, 1, "second")
	_ = cache.Set(first, "a")
	_ = cache.Set(second, "b")
	if err := cache.Flush(); err != nil {
		t.Fatal(err)
	}
	before := readManifestForTest(t, path)
	_ = cache.Set(first, "updated")
	if err := cache.Flush(); err != nil {
		t.Fatal(err)
	}
	after := readManifestForTest(t, path)
	if after.Generation <= before.Generation {
		t.Fatalf("generations: before=%d after=%d", before.Generation, after.Generation)
	}
	byShardBefore := make(map[int]manifestEntry)
	for _, entry := range before.Shards {
		byShardBefore[entry.ShardID] = entry
	}
	for _, entry := range after.Shards {
		if entry.ShardID == 1 && entry != byShardBefore[1] {
			t.Fatalf("unchanged shard was not explicitly reused: before=%+v after=%+v", byShardBefore[1], entry)
		}
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	if value, found := restored.Get(first); !found || value != "updated" {
		t.Fatalf("first = %v, %v", value, found)
	}
	if value, found := restored.Get(second); !found || value != "b" {
		t.Fatalf("second = %v, %v", value, found)
	}
}

func TestConcurrentPersistenceTriggers(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 4)
	options.Persistence.Threshold = 1
	options.Persistence.Interval = time.Millisecond
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	for index := range 100 {
		if err := cache.Set(string(rune(index)), index); err != nil {
			t.Fatal(err)
		}
	}
	if err := cache.Flush(); err != nil {
		t.Fatal(err)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	if restored.Count() != 100 {
		t.Fatalf("restored count = %d", restored.Count())
	}
}

func TestBackgroundPersistenceError(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	cache, err := New(persistentOptions(path, 1))
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	_ = cache.Set("key", 1)
	failed := false
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "before-manifest-write" && !failed {
			failed = true
			return errors.New("injected background failure")
		}
		return nil
	}
	cache.persistence.mu.Unlock()
	if err := cache.commitPersistence(false); err == nil {
		t.Fatal("background commit succeeded")
	}
	if status := cache.PersistenceStatus(); status.LastError == nil || status.DirtyShards == 0 {
		t.Fatalf("failed status = %+v", status)
	}
	if err := cache.Flush(); err == nil || !strings.Contains(err.Error(), "injected background failure") {
		t.Fatalf("first Flush did not report background error: %v", err)
	}
	if status := cache.PersistenceStatus(); status.LastError != nil || status.DirtyShards != 0 || status.LastSuccess.IsZero() {
		t.Fatalf("resolved status = %+v", status)
	}
	if err := cache.Flush(); err != nil {
		t.Fatalf("second Flush = %v", err)
	}
}

func TestAutomaticPersistenceTriggers(t *testing.T) {
	requirePersistenceSupport(t)
	triggers := []struct {
		name      string
		configure func(*PersistenceOptions)
	}{
		{name: "threshold", configure: func(options *PersistenceOptions) { options.Threshold = 1 }},
		{name: "interval", configure: func(options *PersistenceOptions) { options.Interval = time.Millisecond }},
	}
	for _, trigger := range triggers {
		t.Run(trigger.name, func(t *testing.T) {
			path := t.TempDir()
			options := persistentOptions(path, 1)
			trigger.configure(options.Persistence)
			cache, err := New(options)
			if err != nil {
				t.Fatal(err)
			}
			defer cache.Close()

			committed := make(chan struct{})
			var once sync.Once
			cache.persistence.mu.Lock()
			cache.persistence.fault = func(stage string) error {
				if stage == "before-orphan-cleanup" {
					once.Do(func() { close(committed) })
				}
				return nil
			}
			cache.persistence.mu.Unlock()
			if err := cache.Set("key", trigger.name); err != nil {
				t.Fatal(err)
			}
			select {
			case <-committed:
			case <-time.After(time.Second):
				t.Fatalf("%s trigger did not publish a manifest", trigger.name)
			}
			manifest := readManifestForTest(t, path)
			if manifest.Generation == 0 || len(manifest.Shards) != 1 {
				t.Fatalf("automatic manifest = %+v", manifest)
			}
			if persisted, mutated := cache.shards[0].persistedVersion.Load(), cache.shards[0].mutationVersion.Load(); persisted < mutated {
				t.Fatalf("automatic commit version = %d, want at least %d", persisted, mutated)
			}
		})
	}
}

func TestPersistenceThresholdCrossing(t *testing.T) {
	requirePersistenceSupport(t)
	options := persistentOptions(t.TempDir(), 1)
	options.Persistence.Threshold = 2
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	var wakes, commits atomic.Int32
	handled := make(chan struct{}, 2)
	cache.maintenanceHooks = &maintenanceTestHooks{
		persistWake:      func() { wakes.Add(1) },
		persisterHandled: func() { handled <- struct{}{} },
	}
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "before-orphan-cleanup" {
			commits.Add(1)
		}
		return nil
	}
	cache.persistence.mu.Unlock()

	if err := cache.Set("first", 1); err != nil {
		t.Fatal(err)
	}
	select {
	case <-handled:
	case <-time.After(time.Second):
		t.Fatal("persister did not inspect the first mutation")
	}
	if commits.Load() != 0 || cache.shards[0].persistedVersion.Load() != 0 {
		t.Fatalf("below-threshold commit count/version = %d/%d", commits.Load(), cache.shards[0].persistedVersion.Load())
	}

	if err := cache.Set("second", 2); err != nil {
		t.Fatal(err)
	}
	select {
	case <-handled:
	case <-time.After(time.Second):
		t.Fatal("persister did not handle the threshold crossing")
	}
	if wakes.Load() != 2 || commits.Load() != 1 {
		t.Fatalf("threshold wake/commit count = %d/%d", wakes.Load(), commits.Load())
	}
	if persisted := cache.shards[0].persistedVersion.Load(); persisted < 2 {
		t.Fatalf("threshold commit version = %d, want at least 2", persisted)
	}
}

func TestPersistenceVersionEffects(t *testing.T) {
	requirePersistenceSupport(t)
	clock := newManualClock()
	options := persistentOptions(t.TempDir(), 1)
	cache, err := newWithClock(options, clock)
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	shard := cache.shards[0]

	if err := cache.SetWithExpiration("key", "first", time.Minute); err != nil {
		t.Fatal(err)
	}
	shard.mu.RLock()
	first := shard.memberLocked(EntryKey{Key: "key"})
	shard.mu.RUnlock()
	if version := shard.mutationVersion.Load(); version != 1 {
		t.Fatalf("initial mutation version = %d", version)
	}
	if err := cache.SetWithExpiration("key", "second", 2*time.Minute); err != nil {
		t.Fatal(err)
	}
	shard.mu.RLock()
	second := shard.memberLocked(EntryKey{Key: "key"})
	heapLength, count := len(shard.expiry), shard.liveCount
	shard.mu.RUnlock()
	if second != first || heapLength != 1 || count != 1 {
		t.Fatalf("live replacement item=%p/%p heap=%d count=%d", first, second, heapLength, count)
	}
	if version := shard.mutationVersion.Load(); version != 2 {
		t.Fatalf("live replacement mutation version = %d", version)
	}

	clock.Advance(2 * time.Minute)
	if err := cache.Set("key", "third"); err != nil {
		t.Fatal(err)
	}
	shard.mu.RLock()
	third := shard.memberLocked(EntryKey{Key: "key"})
	heapLength, count = len(shard.expiry), shard.liveCount
	shard.mu.RUnlock()
	if third == second || heapLength != 0 || count != 1 {
		t.Fatalf("expired replacement item=%p/%p heap=%d count=%d", second, third, heapLength, count)
	}
	if version := shard.mutationVersion.Load(); version != 4 {
		t.Fatalf("expired replacement mutation version = %d, want deletion plus insertion", version)
	}
}

func TestPersistenceOptionsAreCopied(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	options.Persistence.Path = t.TempDir()
	options.Persistence.Interval = time.Hour
	options.Persistence.Threshold = 99
	if cache.opts.Persistence.Path != path || cache.opts.Persistence.Interval != 0 || cache.opts.Persistence.Threshold != 0 {
		t.Fatalf("cache options changed through caller alias: %+v", cache.opts.Persistence)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
}

func TestBackgroundPersistenceCleanupError(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	cache, err := New(persistentOptions(path, 1))
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	_ = cache.Set("key", 1)
	failed := false
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "before-orphan-cleanup" && !failed {
			failed = true
			return errors.New("injected cleanup failure")
		}
		return nil
	}
	cache.persistence.mu.Unlock()
	if err := cache.commitPersistence(false); err == nil {
		t.Fatal("background cleanup failure was ignored")
	}
	if status := cache.PersistenceStatus(); status.LastError == nil {
		t.Fatalf("cleanup failure status = %+v", status)
	}
	if err := cache.Flush(); err == nil || !strings.Contains(err.Error(), "injected cleanup failure") {
		t.Fatalf("Flush did not report background cleanup error: %v", err)
	}
	if status := cache.PersistenceStatus(); status.LastError != nil {
		t.Fatalf("cleanup status did not recover: %+v", status)
	}
}

func TestPersistenceStatus(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	cache, err := New(persistentOptions(path, 2))
	if err != nil {
		t.Fatal(err)
	}
	_ = cache.Set("key", 1)
	status := cache.PersistenceStatus()
	if !status.Enabled || status.DirtyShards != 1 || status.LastError != nil || !status.LastSuccess.IsZero() {
		t.Fatalf("dirty status = %+v", status)
	}
	if err := cache.Flush(); err != nil {
		t.Fatal(err)
	}
	status = cache.PersistenceStatus()
	if status.DirtyShards != 0 || status.LastSuccess.IsZero() || status.LastError != nil {
		t.Fatalf("clean status = %+v", status)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	if status := cache.PersistenceStatus(); !status.Enabled {
		t.Fatalf("closed status = %+v", status)
	}
}

func TestPersistenceVersionRace(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	cache, err := New(persistentOptions(path, 1))
	if err != nil {
		t.Fatal(err)
	}
	defer cache.Close()
	_ = cache.Set("first", 1)
	blocked := make(chan struct{})
	release := make(chan struct{})
	cache.persistence.mu.Lock()
	cache.persistence.fault = func(stage string) error {
		if stage == "after-shard-sync" {
			select {
			case <-blocked:
			default:
				close(blocked)
				<-release
			}
		}
		return nil
	}
	cache.persistence.mu.Unlock()
	flushDone := make(chan error, 1)
	go func() { flushDone <- cache.Flush() }()
	<-blocked
	_ = cache.Set("second", 2)
	close(release)
	if err := <-flushDone; err != nil {
		t.Fatal(err)
	}
	if status := cache.PersistenceStatus(); status.DirtyShards != 1 {
		t.Fatalf("concurrent mutation was marked persisted: %+v", status)
	}
	cache.persistence.mu.Lock()
	cache.persistence.fault = nil
	cache.persistence.mu.Unlock()
	if err := cache.Flush(); err != nil {
		t.Fatal(err)
	}
}

func TestPersistenceCorruption(t *testing.T) {
	requirePersistenceSupport(t)
	for _, target := range []string{"manifest", "shard"} {
		t.Run(target, func(t *testing.T) {
			path := t.TempDir()
			options := persistentOptions(path, 1)
			cache, err := New(options)
			if err != nil {
				t.Fatal(err)
			}
			_ = cache.Set("key", "value")
			if err := cache.Close(); err != nil {
				t.Fatal(err)
			}
			filename := manifestFilename
			if target == "shard" {
				filename = readManifestForTest(t, path).Shards[0].File
			}
			file := filepath.Join(path, filename)
			data, err := os.ReadFile(file)
			if err != nil {
				t.Fatal(err)
			}
			data[len(data)-1] ^= 1
			if err := os.WriteFile(file, data, 0o600); err != nil {
				t.Fatal(err)
			}
			if cache, err := New(options); err == nil {
				cache.Close()
				t.Fatal("corrupt persistence was accepted")
			}
		})
	}
}

func TestPersistenceManifestRecovery(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	_ = cache.Set("key", 1)
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(path, "unrelated.txt"), []byte("keep"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(path, "shard-9-generation-999.bin"), []byte("orphan"), 0o600); err != nil {
		t.Fatal(err)
	}
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(path, "unrelated.txt")); err != nil {
		t.Fatalf("unrelated file was removed: %v", err)
	}
	if err := restored.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(path, "shard-9-generation-999.bin")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("orphan file remains: %v", err)
	}
}

func TestPersistenceWriterLock(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	first, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	if second, err := New(options); !errors.Is(err, ErrPersistenceLocked) {
		if second != nil {
			second.Close()
		}
		t.Fatalf("second writer error = %v", err)
	}
	if err := first.Close(); err != nil {
		t.Fatal(err)
	}
	second, err := New(options)
	if err != nil {
		t.Fatalf("lock was not released: %v", err)
	}
	if err := second.Close(); err != nil {
		t.Fatal(err)
	}
}

func TestRejectedWriterPreservesProcessLock(t *testing.T) {
	requirePersistenceSupport(t)
	if path := os.Getenv("CACHE_LOCK_PROBE_DIR"); path != "" {
		cache, err := New(persistentOptions(path, 1))
		if errors.Is(err, ErrPersistenceLocked) {
			os.Exit(0)
		}
		if cache != nil {
			_ = cache.Close()
		}
		os.Exit(1)
	}

	path := t.TempDir()
	options := persistentOptions(path, 1)
	first, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer first.Close()
	if second, err := New(options); !errors.Is(err, ErrPersistenceLocked) {
		if second != nil {
			_ = second.Close()
		}
		t.Fatalf("second local writer error = %v", err)
	}
	command := exec.Command(os.Args[0], "-test.run=^TestRejectedWriterPreservesProcessLock$")
	command.Env = append(os.Environ(), "CACHE_LOCK_PROBE_DIR="+path)
	if err := command.Run(); err != nil {
		t.Fatalf("external writer acquired after local rejection: %v", err)
	}
}

func TestPersistenceFormatDetection(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	if err := os.WriteFile(filepath.Join(path, "0.dat"), []byte("legacy gob"), 0o600); err != nil {
		t.Fatal(err)
	}
	if cache, err := New(persistentOptions(path, 1)); !errors.Is(err, ErrUnsupportedFormat) {
		if cache != nil {
			cache.Close()
		}
		t.Fatalf("legacy format error = %v", err)
	}
}

func TestPersistenceTopologyMigration(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	oldOptions := persistentOptions(path, 1)
	cache, err := New(oldOptions)
	if err != nil {
		t.Fatal(err)
	}
	newOptions := persistentOptions(path, 2)
	probe, err := New(persistentOptions(t.TempDir(), 2))
	if err != nil {
		t.Fatal(err)
	}
	keys := []string{
		keyForShard(probe, 0, "a"),
		keyForShard(probe, 0, "b"),
		keyForShard(probe, 0, "c"),
	}
	probe.Close()
	for index, key := range keys {
		_ = cache.Set(key, index)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	newOptions.MaxEntriesPerShard = 2
	migrated, err := New(newOptions)
	if err != nil {
		t.Fatal(err)
	}
	if _, found := migrated.Get(keys[0]); found {
		t.Fatal("oldest key survived migrated capacity enforcement")
	}
	for _, key := range keys[1:] {
		if _, found := migrated.Get(key); !found {
			t.Fatalf("newer key %q missing", key)
		}
	}
	manifest := readManifestForTest(t, path)
	if manifest.ShardCount != 2 {
		t.Fatalf("migrated manifest topology = %d", manifest.ShardCount)
	}
	if err := migrated.Close(); err != nil {
		t.Fatal(err)
	}
}

func TestPersistenceTopologyDecreasePreservesGroups(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 4)
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	groupName := "group\x00:name"
	key := "key\x00:value"
	group, _ := cache.Group(groupName)
	_ = cache.Set(key, "ungrouped")
	_ = group.Set(key, "grouped")
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	options.ShardCount = 1
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	restoredGroup, err := restored.Group(groupName)
	if err != nil {
		t.Fatal(err)
	}
	if value, found := restored.Get(key); !found || value != "ungrouped" {
		t.Fatalf("ungrouped = %v, %v", value, found)
	}
	if value, found := restoredGroup.Get(key); !found || value != "grouped" {
		t.Fatalf("grouped = %v, %v", value, found)
	}
	if manifest := readManifestForTest(t, path); manifest.ShardCount != 1 {
		t.Fatalf("decreased manifest topology = %d", manifest.ShardCount)
	}
}

func TestPersistenceMigrationFailurePreservesRecovery(t *testing.T) {
	requirePersistenceSupport(t)
	stages := []string{
		"before-shard-write",
		"after-shard-sync",
		"after-shard-rename",
		"before-data-directory-sync",
		"after-data-directory-sync",
		"before-manifest-write",
		"after-manifest-sync",
		"after-manifest-rename",
		"after-manifest-directory-sync",
		"before-orphan-cleanup",
	}
	for _, stage := range stages {
		t.Run(stage, func(t *testing.T) {
			path := t.TempDir()
			oldOptions := persistentOptions(path, 1)
			cache, err := New(oldOptions)
			if err != nil {
				t.Fatal(err)
			}
			group, _ := cache.Group("group")
			_ = cache.Set("key", "ungrouped")
			_ = group.Set("key", "grouped")
			if err := cache.Close(); err != nil {
				t.Fatal(err)
			}

			newOptions := persistentOptions(path, 2)
			fault := func(current string) error {
				if current == stage {
					return errors.New("injected migration failure")
				}
				return nil
			}
			if migrated, err := newWithClockAndPersistenceFault(newOptions, realClock{}, fault); err == nil {
				migrated.Close()
				t.Fatal("migration unexpectedly succeeded")
			}

			restored, err := New(newOptions)
			if err != nil {
				t.Fatalf("target topology retry did not recover: %v", err)
			}
			restoredGroup, err := restored.Group("group")
			if err != nil {
				t.Fatal(err)
			}
			if value, found := restored.Get("key"); !found || value != "ungrouped" {
				t.Fatalf("ungrouped = %v, %v", value, found)
			}
			if value, found := restoredGroup.Get("key"); !found || value != "grouped" {
				t.Fatalf("grouped = %v, %v", value, found)
			}
			if manifest := readManifestForTest(t, path); manifest.ShardCount != 2 {
				t.Fatalf("retried manifest topology = %d", manifest.ShardCount)
			}
			if err := restored.Close(); err != nil {
				t.Fatal(err)
			}
		})
	}
}

func TestTopologyPolicyOrder(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	options.EvictionPolicy = FIFO
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"a", "b", "c"} {
		_ = cache.Set(key, key)
	}
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	options.MaxEntriesPerShard = 2
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	if _, found := restored.Get("a"); found {
		t.Fatal("FIFO oldest survived capacity restore")
	}
	if restored.Count() != 2 {
		t.Fatalf("restored count = %d", restored.Count())
	}
}

func TestPolicyOrderRecovery(t *testing.T) {
	requirePersistenceSupport(t)
	path := t.TempDir()
	options := persistentOptions(path, 1)
	options.EvictionPolicy = LRU
	cache, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"a", "b", "c"} {
		_ = cache.Set(key, key)
	}
	cache.Get("a")
	_ = cache.Set("marker", 1)
	if err := cache.Close(); err != nil {
		t.Fatal(err)
	}
	options.MaxEntriesPerShard = 2
	restored, err := New(options)
	if err != nil {
		t.Fatal(err)
	}
	defer restored.Close()
	var keys []string
	restored.Range(func(key EntryKey, _ any, _ time.Time) bool { keys = append(keys, key.Key); return true })
	sort.Strings(keys)
	if !reflect.DeepEqual(keys, []string{"a", "marker"}) {
		t.Fatalf("restored LRU keys = %v", keys)
	}
}

func TestPersistenceInterruption(t *testing.T) {
	requirePersistenceSupport(t)
	if stage := os.Getenv("CACHE_INTERRUPTION_STAGE"); stage != "" {
		path := os.Getenv("CACHE_INTERRUPTION_DIR")
		cache, err := New(persistentOptions(path, 1))
		if err != nil {
			os.Exit(91)
		}
		_ = cache.Set("unstable", stage)
		cache.persistence.mu.Lock()
		cache.persistence.fault = func(current string) error {
			if current == stage {
				os.Exit(23)
			}
			return nil
		}
		cache.persistence.mu.Unlock()
		_ = cache.Flush()
		os.Exit(92)
	}

	stages := []struct {
		name       string
		newVisible bool
	}{
		{"before-shard-write", false},
		{"after-shard-sync", false},
		{"after-shard-rename", false},
		{"before-data-directory-sync", false},
		{"after-data-directory-sync", false},
		{"before-manifest-write", false},
		{"after-manifest-sync", false},
		{"after-manifest-rename", true},
		{"after-manifest-directory-sync", true},
	}
	for _, stage := range stages {
		t.Run(stage.name, func(t *testing.T) {
			path := t.TempDir()
			options := persistentOptions(path, 1)
			cache, err := New(options)
			if err != nil {
				t.Fatal(err)
			}
			_ = cache.Set("stable", 1)
			if err := cache.Close(); err != nil {
				t.Fatal(err)
			}
			command := exec.Command(os.Args[0], "-test.run=^TestPersistenceInterruption$")
			command.Env = append(os.Environ(), "CACHE_INTERRUPTION_STAGE="+stage.name, "CACHE_INTERRUPTION_DIR="+path)
			if err := command.Run(); err == nil {
				t.Fatal("child did not interrupt")
			}
			restored, err := New(options)
			if err != nil {
				t.Fatalf("restore after %s: %v", stage.name, err)
			}
			defer restored.Close()
			entries, err := os.ReadDir(path)
			if err != nil {
				t.Fatal(err)
			}
			for _, entry := range entries {
				if temporaryFilenamePattern.MatchString(entry.Name()) {
					t.Fatalf("temporary file was not cleaned: %s", entry.Name())
				}
			}
			if value, found := restored.Get("stable"); !found || value != 1 {
				t.Fatalf("stable = %v, %v", value, found)
			}
			_, found := restored.Get("unstable")
			if found != stage.newVisible {
				t.Fatalf("unstable visible=%v, want %v", found, stage.newVisible)
			}
		})
	}
}
