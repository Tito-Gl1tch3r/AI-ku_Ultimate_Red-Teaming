//go:build windows

package shardedcache

import (
	"errors"
	"fmt"
	"os"

	"golang.org/x/sys/windows"
)

type persistenceLock struct {
	file       *os.File
	overlapped windows.Overlapped
}

func acquirePersistenceLock(path string) (*persistenceLock, error) {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open persistence lock %q: %w", path, err)
	}
	lock := &persistenceLock{file: file}
	err = windows.LockFileEx(windows.Handle(file.Fd()), windows.LOCKFILE_EXCLUSIVE_LOCK|windows.LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0, &lock.overlapped)
	if err != nil {
		_ = file.Close()
		if errors.Is(err, windows.ERROR_LOCK_VIOLATION) {
			return nil, fmt.Errorf("%w: %s", ErrPersistenceLocked, path)
		}
		return nil, fmt.Errorf("lock persistence directory %q: %w", path, err)
	}
	return lock, nil
}

func (lock *persistenceLock) Close() error {
	if lock == nil || lock.file == nil {
		return nil
	}
	err := windows.UnlockFileEx(windows.Handle(lock.file.Fd()), 0, 1, 0, &lock.overlapped)
	closeErr := lock.file.Close()
	lock.file = nil
	return errors.Join(err, closeErr)
}
