package shardedcache

import (
	"bytes"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

const (
	manifestFilename = "manifest.bin"
	lockFilename     = "cache.lock"
)

var (
	shardFilenamePattern     = regexp.MustCompile(`^shard-([0-9]+)-generation-([0-9]+)\.bin$`)
	legacyFilenamePattern    = regexp.MustCompile(`^[0-9]+\.dat$`)
	temporaryFilenamePattern = regexp.MustCompile(`^\.(?:manifest\.tmp|shard-.*\.tmp)-[0-9]+-[0-9]+$`)
	persistenceTempCounter   atomic.Uint64
)

type persistenceState struct {
	mu             sync.Mutex
	dir            string
	lock           *persistenceLock
	current        *manifestFile
	nextGeneration uint64
	lastSuccess    time.Time
	lastError      error
	pendingReport  error
	failedVersions []uint64
	fault          func(string) error
}

func (c *ShardedCache) openPersistence() (resultErr error) {
	if err := checkPersistenceDurability(); err != nil {
		return err
	}
	path, err := filepath.Abs(c.opts.Persistence.Path)
	if err != nil {
		return fmt.Errorf("resolve Persistence.Path: %w", err)
	}
	if info, statErr := os.Stat(path); statErr == nil {
		if !info.IsDir() {
			return fmt.Errorf("Persistence.Path %q is not a directory", path)
		}
	} else if errors.Is(statErr, os.ErrNotExist) {
		if err := mkdirAllAndSyncParents(path, 0o700, syncDirectory); err != nil {
			return fmt.Errorf("create Persistence.Path %q: %w", path, err)
		}
	} else {
		return fmt.Errorf("inspect Persistence.Path %q: %w", path, statErr)
	}

	lock, err := acquirePersistenceLock(filepath.Join(path, lockFilename))
	if err != nil {
		return err
	}
	state := &persistenceState{dir: path, lock: lock, fault: c.constructorPersistenceFault}
	c.persistence = state
	defer func() {
		if resultErr != nil {
			_ = state.lock.Close()
			c.persistence = nil
		}
	}()

	needsCommit, err := c.restorePersistence()
	if err != nil {
		return err
	}
	state.mu.Lock()
	err = state.cleanupOrphans()
	state.mu.Unlock()
	if err != nil {
		return fmt.Errorf("clean persistence residue: %w", err)
	}
	if needsCommit {
		for _, shard := range c.shards {
			shard.mutationVersion.Add(1)
		}
		if err := c.commitPersistence(false); err != nil {
			return fmt.Errorf("commit restored persistence migration: %w", err)
		}
	}
	return nil
}

func mkdirAllAndSyncParents(path string, perm os.FileMode, syncParent func(string) error) error {
	missing := []string{path}
	for current := filepath.Dir(path); ; current = filepath.Dir(current) {
		info, err := os.Stat(current)
		if err == nil {
			if !info.IsDir() {
				return fmt.Errorf("persistence path component %q is not a directory", current)
			}
			break
		}
		if !errors.Is(err, os.ErrNotExist) {
			return fmt.Errorf("inspect persistence path component %q: %w", current, err)
		}
		missing = append(missing, current)
		if parent := filepath.Dir(current); parent == current {
			return fmt.Errorf("find existing persistence path ancestor: %w", err)
		}
	}
	if err := os.MkdirAll(path, perm); err != nil {
		return err
	}
	for index := len(missing) - 1; index >= 0; index-- {
		parent := filepath.Dir(missing[index])
		if err := syncParent(parent); err != nil {
			return fmt.Errorf("sync parent %q of new persistence directory %q: %w", parent, missing[index], err)
		}
	}
	return nil
}

func (c *ShardedCache) restorePersistence() (bool, error) {
	state := c.persistence
	manifestPath := filepath.Join(state.dir, manifestFilename)
	metadata, payload, _, err := readEnvelopeFile(manifestPath, fileTypeManifest)
	if errors.Is(err, os.ErrNotExist) {
		if err := inspectAndCleanNoManifest(state.dir); err != nil {
			return false, err
		}
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("read persistence manifest: %w", err)
	}
	if metadata.shardID != -1 || metadata.generation == 0 || metadata.shardCount == 0 || metadata.shardCount&(metadata.shardCount-1) != 0 {
		return false, errors.New("persistence manifest envelope metadata is inconsistent")
	}
	var manifest manifestFile
	if err := decodeGob(payload, &manifest); err != nil {
		return false, fmt.Errorf("decode persistence manifest: %w", err)
	}
	if manifest.Generation != metadata.generation || manifest.ShardCount != metadata.shardCount {
		return false, errors.New("persistence manifest payload metadata is inconsistent")
	}
	if manifest.ShardCount > uint64(^uint(0)>>1) || len(manifest.Shards) != int(manifest.ShardCount) {
		return false, errors.New("persistence manifest topology is invalid")
	}

	entries := make([]persistedItem, 0)
	seenShards := make(map[int]struct{}, len(manifest.Shards))
	seenKeys := make(map[EntryKey]struct{})
	oldMask := manifest.ShardCount - 1
	for _, reference := range manifest.Shards {
		if reference.ShardID < 0 || uint64(reference.ShardID) >= manifest.ShardCount {
			return false, fmt.Errorf("persistence manifest shard id %d is invalid", reference.ShardID)
		}
		if reference.Generation == 0 || reference.Generation > manifest.Generation {
			return false, fmt.Errorf("persistence manifest shard %d generation %d is invalid", reference.ShardID, reference.Generation)
		}
		if _, duplicate := seenShards[reference.ShardID]; duplicate {
			return false, fmt.Errorf("persistence manifest repeats shard %d", reference.ShardID)
		}
		seenShards[reference.ShardID] = struct{}{}
		fileShard, fileGeneration, validName := parseShardFilename(reference.File)
		if filepath.Base(reference.File) != reference.File || !validName || fileShard != reference.ShardID || fileGeneration != reference.Generation {
			return false, fmt.Errorf("persistence manifest shard file %q is invalid", reference.File)
		}
		path := filepath.Join(state.dir, reference.File)
		info, statErr := os.Stat(path)
		if statErr != nil {
			return false, fmt.Errorf("inspect persistence shard %q: %w", reference.File, statErr)
		}
		if info.Size() != reference.Size {
			return false, fmt.Errorf("persistence shard %q size mismatch", reference.File)
		}
		shardMetadata, shardPayload, hash, readErr := readEnvelopeFile(path, fileTypeShard)
		if readErr != nil {
			return false, fmt.Errorf("read persistence shard %q: %w", reference.File, readErr)
		}
		if !bytes.Equal(hash, reference.Hash[:]) {
			return false, fmt.Errorf("persistence shard %q manifest checksum mismatch", reference.File)
		}
		if shardMetadata.generation != reference.Generation || shardMetadata.shardCount != manifest.ShardCount || shardMetadata.shardID != int64(reference.ShardID) {
			return false, fmt.Errorf("persistence shard %q envelope metadata is inconsistent", reference.File)
		}
		var persisted persistedShard
		if err := decodeGob(shardPayload, &persisted); err != nil {
			return false, fmt.Errorf("decode persistence shard %q: %w", reference.File, err)
		}
		for _, item := range persisted.Items {
			if uint64(shardHash(item.Key))&oldMask != uint64(reference.ShardID) {
				return false, fmt.Errorf("persistence shard %q contains an entry for another shard", reference.File)
			}
			if _, duplicate := seenKeys[item.Key]; duplicate {
				return false, fmt.Errorf("persistence contains duplicate entry %+v", item.Key)
			}
			seenKeys[item.Key] = struct{}{}
			entries = append(entries, item)
		}
	}

	state.current = &manifest
	state.nextGeneration = manifest.Generation
	now := c.clock.Now()
	needsCommit := manifest.ShardCount != uint64(c.opts.ShardCount)
	live := entries[:0]
	var maxOrdinal uint64
	for _, item := range entries {
		if item.Ordinal > maxOrdinal {
			maxOrdinal = item.Ordinal
		}
		if !item.ExpiresAt.IsZero() && !now.Before(item.ExpiresAt) {
			needsCommit = true
			continue
		}
		live = append(live, item)
	}
	entries = live
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Ordinal != entries[j].Ordinal {
			return entries[i].Ordinal < entries[j].Ordinal
		}
		if entries[i].Key.Group != entries[j].Key.Group {
			return entries[i].Key.Group < entries[j].Key.Group
		}
		return entries[i].Key.Key < entries[j].Key.Key
	})

	byShard := make([][]persistedItem, len(c.shards))
	for _, item := range entries {
		index := c.shardIndex(item.Key)
		byShard[index] = append(byShard[index], item)
	}
	for index, items := range byShard {
		if limit := c.opts.MaxEntriesPerShard; limit > 0 && len(items) > limit {
			items = items[len(items)-limit:]
			needsCommit = true
		}
		for _, item := range items {
			c.shards[index].addRestored(item)
		}
	}
	c.ordinal.Store(maxOrdinal)
	return needsCommit, nil
}

func inspectAndCleanNoManifest(dir string) error {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Errorf("read persistence directory: %w", err)
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if legacyFilenamePattern.MatchString(entry.Name()) {
			return fmt.Errorf("%w: legacy bare gob shard %q", ErrUnsupportedFormat, entry.Name())
		}
	}
	removed := false
	for _, entry := range entries {
		if entry.IsDir() || entry.Name() == lockFilename {
			continue
		}
		if shardFilenamePattern.MatchString(entry.Name()) || temporaryFilenamePattern.MatchString(entry.Name()) {
			if err := os.Remove(filepath.Join(dir, entry.Name())); err != nil && !errors.Is(err, os.ErrNotExist) {
				return fmt.Errorf("remove orphan persistence file %q: %w", entry.Name(), err)
			}
			removed = true
		}
	}
	if removed {
		return syncDirectory(dir)
	}
	return nil
}

func (c *ShardedCache) runPersister() {
	options := c.opts.Persistence
	var ticker *time.Ticker
	var interval <-chan time.Time
	if options.Interval > 0 {
		ticker = time.NewTicker(options.Interval)
		interval = ticker.C
		defer ticker.Stop()
	}
	for {
		select {
		case <-c.maintenanceStop:
			return
		case <-interval:
			if c.dirtyShardCount() != 0 {
				_ = c.commitPersistence(false)
			}
		case <-c.persistWake:
			if options.Threshold > 0 && c.thresholdReached(options.Threshold) {
				_ = c.commitPersistence(false)
			}
			if hooks := c.maintenanceHooks; hooks != nil && hooks.persisterHandled != nil {
				hooks.persisterHandled()
			}
		}
	}
}

func (c *ShardedCache) thresholdReached(threshold int) bool {
	for _, shard := range c.shards {
		if shard.mutationVersion.Load()-shard.persistedVersion.Load() >= uint64(threshold) {
			return true
		}
	}
	return false
}

func (c *ShardedCache) dirtyShardCount() int {
	dirty := 0
	for _, shard := range c.shards {
		if shard.mutationVersion.Load() != shard.persistedVersion.Load() {
			dirty++
		}
	}
	return dirty
}

// PersistenceStatus returns a concurrency-safe status snapshot.
func (c *ShardedCache) PersistenceStatus() PersistenceStatus {
	state := c.persistence
	if state == nil {
		return PersistenceStatus{Enabled: false}
	}
	state.mu.Lock()
	status := PersistenceStatus{
		Enabled:     true,
		DirtyShards: c.dirtyShardCount(),
		LastSuccess: state.lastSuccess,
		LastError:   state.lastError,
	}
	state.mu.Unlock()
	return status
}

func (c *ShardedCache) commitPersistence(reportBackground bool) error {
	state := c.persistence
	if state == nil {
		return ErrPersistenceDisabled
	}
	state.mu.Lock()
	defer state.mu.Unlock()

	var prior error
	if reportBackground {
		prior = state.pendingReport
		state.pendingReport = nil
	}
	state.nextGeneration++
	generation := state.nextGeneration
	capturedVersions := make([]uint64, len(c.shards))
	currentReferences := make(map[int]manifestEntry)
	if state.current != nil && state.current.ShardCount == uint64(len(c.shards)) {
		for _, reference := range state.current.Shards {
			currentReferences[reference.ShardID] = reference
		}
	}

	references := make([]manifestEntry, len(c.shards))
	var writeErrors []error
	for index, shard := range c.shards {
		version := shard.mutationVersion.Load()
		capturedVersions[index] = version
		reference, reusable := currentReferences[index]
		if reusable && version == shard.persistedVersion.Load() {
			references[index] = reference
			continue
		}
		snapshot, captured := shard.persistenceSnapshot(c.clock)
		capturedVersions[index] = captured
		payload, err := encodeGob(snapshot)
		if err != nil {
			writeErrors = append(writeErrors, fmt.Errorf("encode shard %d: %w", index, err))
			continue
		}
		data, err := encodeEnvelope(envelopeMetadata{
			fileType:   fileTypeShard,
			generation: generation,
			shardCount: uint64(len(c.shards)),
			shardID:    int64(index),
		}, payload)
		if err != nil {
			writeErrors = append(writeErrors, fmt.Errorf("encode shard %d envelope: %w", index, err))
			continue
		}
		filename := fmt.Sprintf("shard-%d-generation-%d.bin", index, generation)
		if err := state.writeImmutable(filename, data, "shard"); err != nil {
			writeErrors = append(writeErrors, fmt.Errorf("write shard %d: %w", index, err))
			continue
		}
		hash := sha256.Sum256(data)
		references[index] = manifestEntry{ShardID: index, Generation: generation, File: filename, Size: int64(len(data)), Hash: hash}
	}
	if err := errors.Join(writeErrors...); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	if err := state.callFault("before-data-directory-sync"); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	if err := syncDirectory(state.dir); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	if err := state.callFault("after-data-directory-sync"); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}

	manifest := manifestFile{Generation: generation, ShardCount: uint64(len(c.shards)), Shards: references}
	payload, err := encodeGob(manifest)
	if err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	data, err := encodeEnvelope(envelopeMetadata{
		fileType:   fileTypeManifest,
		generation: generation,
		shardCount: uint64(len(c.shards)),
		shardID:    -1,
	}, payload)
	if err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	if err := state.replaceManifest(data); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}

	state.current = &manifest
	state.lastSuccess = c.clock.Now()
	for index, version := range capturedVersions {
		c.shards[index].persistedVersion.Store(version)
	}
	if versionsCover(capturedVersions, state.failedVersions) {
		state.lastError = nil
		state.failedVersions = nil
	}
	if err := state.callFault("before-orphan-cleanup"); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	if err := state.cleanupOrphans(); err != nil {
		state.recordFailure(err, capturedVersions, !reportBackground)
		return errors.Join(prior, err)
	}
	return prior
}

func (state *persistenceState) recordFailure(err error, versions []uint64, background bool) {
	state.lastError = err
	if len(state.failedVersions) != len(versions) {
		state.failedVersions = append([]uint64(nil), versions...)
	} else {
		for index, version := range versions {
			if version > state.failedVersions[index] {
				state.failedVersions[index] = version
			}
		}
	}
	if background {
		state.pendingReport = errors.Join(state.pendingReport, err)
	}
}

func versionsCover(current, required []uint64) bool {
	if len(required) == 0 {
		return true
	}
	if len(current) != len(required) {
		return false
	}
	for index := range current {
		if current[index] < required[index] {
			return false
		}
	}
	return true
}

func (state *persistenceState) callFault(stage string) error {
	if state.fault == nil {
		return nil
	}
	if err := state.fault(stage); err != nil {
		return fmt.Errorf("persistence fault at %s: %w", stage, err)
	}
	return nil
}

func (state *persistenceState) writeImmutable(filename string, data []byte, kind string) error {
	if err := state.callFault("before-" + kind + "-write"); err != nil {
		return err
	}
	destination := filepath.Join(state.dir, filename)
	if _, err := os.Lstat(destination); err == nil {
		return fmt.Errorf("immutable persistence file %q already exists", filename)
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	temporary := filepath.Join(state.dir, fmt.Sprintf(".%s-%s.tmp-%d-%d", kind, filename, os.Getpid(), persistenceTempCounter.Add(1)))
	file, err := os.OpenFile(temporary, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	removeTemporary := true
	defer func() {
		_ = file.Close()
		if removeTemporary {
			_ = os.Remove(temporary)
		}
	}()
	if _, err := file.Write(data); err != nil {
		return err
	}
	if err := file.Sync(); err != nil {
		return err
	}
	if err := state.callFault("after-" + kind + "-sync"); err != nil {
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	if err := renamePersistenceFile(temporary, destination, false); err != nil {
		return err
	}
	removeTemporary = false
	return state.callFault("after-" + kind + "-rename")
}

func (state *persistenceState) replaceManifest(data []byte) error {
	if err := state.callFault("before-manifest-write"); err != nil {
		return err
	}
	temporary := filepath.Join(state.dir, fmt.Sprintf(".manifest.tmp-%d-%d", os.Getpid(), persistenceTempCounter.Add(1)))
	file, err := os.OpenFile(temporary, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	removeTemporary := true
	defer func() {
		_ = file.Close()
		if removeTemporary {
			_ = os.Remove(temporary)
		}
	}()
	if _, err := file.Write(data); err != nil {
		return err
	}
	if err := file.Sync(); err != nil {
		return err
	}
	if err := state.callFault("after-manifest-sync"); err != nil {
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	if err := renamePersistenceFile(temporary, filepath.Join(state.dir, manifestFilename), true); err != nil {
		return err
	}
	removeTemporary = false
	if err := state.callFault("after-manifest-rename"); err != nil {
		return err
	}
	if err := syncDirectory(state.dir); err != nil {
		return err
	}
	return state.callFault("after-manifest-directory-sync")
}

func (state *persistenceState) cleanupOrphans() error {
	if state.current == nil {
		return nil
	}
	referenced := make(map[string]struct{}, len(state.current.Shards))
	for _, reference := range state.current.Shards {
		referenced[reference.File] = struct{}{}
	}
	entries, err := os.ReadDir(state.dir)
	if err != nil {
		return err
	}
	removed := false
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if _, keep := referenced[name]; keep {
			continue
		}
		if shardFilenamePattern.MatchString(name) || temporaryFilenamePattern.MatchString(name) {
			if err := os.Remove(filepath.Join(state.dir, name)); err != nil && !errors.Is(err, os.ErrNotExist) {
				return fmt.Errorf("remove orphan persistence file %q: %w", name, err)
			}
			removed = true
		}
	}
	if removed {
		return syncDirectory(state.dir)
	}
	return nil
}

func (c *ShardedCache) closePersistence() error {
	state := c.persistence
	if state == nil {
		return nil
	}
	state.mu.Lock()
	err := state.lock.Close()
	state.mu.Unlock()
	return err
}

func parseShardFilename(name string) (int, uint64, bool) {
	matches := shardFilenamePattern.FindStringSubmatch(name)
	if matches == nil {
		return 0, 0, false
	}
	shard, shardErr := strconv.Atoi(matches[1])
	generation, generationErr := strconv.ParseUint(matches[2], 10, 64)
	return shard, generation, shardErr == nil && generationErr == nil
}
