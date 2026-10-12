//go:build aix

package shardedcache

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestPersistenceIsRejectedOnAIX(t *testing.T) {
	for _, name := range []string{"existing directory", "missing directory"} {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			path := root
			if name == "missing directory" {
				path = filepath.Join(root, "missing", "cache")
			}
			cache, err := New(persistentOptions(path, 2))
			if cache != nil {
				cache.Close()
				t.Fatal("New returned a cache with unsupported persistence")
			}
			if !errors.Is(err, errAIXDirectorySyncUnsupported) {
				t.Fatalf("New error = %v, want %v", err, errAIXDirectorySyncUnsupported)
			}
			entries, readErr := os.ReadDir(root)
			if readErr != nil {
				t.Fatal(readErr)
			}
			if len(entries) != 0 {
				t.Fatalf("unsupported persistence created files or directories: %v", entries)
			}
		})
	}
}

func TestInMemoryCacheOnAIX(t *testing.T) {
	for _, policy := range []EvictionPolicy{FIFO, LRU} {
		t.Run(policy.String(), func(t *testing.T) {
			options := DefaultOptions()
			options.EvictionPolicy = policy
			cache, err := New(options)
			if err != nil {
				t.Fatal(err)
			}
			defer cache.Close()
			if err := cache.Set("key", "value"); err != nil {
				t.Fatal(err)
			}
			if value, found := cache.Get("key"); !found || value != "value" {
				t.Fatalf("Get = %v, %v", value, found)
			}
			if status := cache.PersistenceStatus(); status.Enabled {
				t.Fatalf("in-memory cache enabled persistence: %+v", status)
			}
			if err := cache.Flush(); !errors.Is(err, ErrPersistenceDisabled) {
				t.Fatalf("Flush = %v, want %v", err, ErrPersistenceDisabled)
			}
			if err := cache.Close(); err != nil {
				t.Fatal(err)
			}
			if value, found := cache.Get("key"); !found || value != "value" {
				t.Fatalf("Get after Close = %v, %v", value, found)
			}
		})
	}
}
