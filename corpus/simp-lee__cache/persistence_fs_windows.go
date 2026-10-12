//go:build windows

package shardedcache

import (
	"fmt"

	"golang.org/x/sys/windows"
)

func checkPersistenceDurability() error { return nil }

func renamePersistenceFile(source, destination string, replace bool) error {
	from, err := windows.UTF16PtrFromString(source)
	if err != nil {
		return fmt.Errorf("encode persistence source path: %w", err)
	}
	to, err := windows.UTF16PtrFromString(destination)
	if err != nil {
		return fmt.Errorf("encode persistence destination path: %w", err)
	}
	flags := uint32(windows.MOVEFILE_WRITE_THROUGH)
	if replace {
		flags |= windows.MOVEFILE_REPLACE_EXISTING
	}
	if err := windows.MoveFileEx(from, to, flags); err != nil {
		return fmt.Errorf("move persistence file %q to %q: %w", source, destination, err)
	}
	return nil
}

// Windows does not support flushing an opened directory handle. Persistence
// renames use MOVEFILE_WRITE_THROUGH instead, so there is no separate directory
// flush operation to perform.
func syncDirectory(string) error { return nil }
