//go:build aix

package shardedcache

import (
	"errors"
	"fmt"
	"os"
	"sync"

	"golang.org/x/sys/unix"
)

type aixLockIdentity struct {
	device uint64
	inode  uint64
}

var aixProcessLocks = struct {
	sync.Mutex
	held map[aixLockIdentity]struct{}
}{held: make(map[aixLockIdentity]struct{})}

type persistenceLock struct {
	file     *os.File
	identity aixLockIdentity
}

func acquirePersistenceLock(path string) (*persistenceLock, error) {
	aixProcessLocks.Lock()
	defer aixProcessLocks.Unlock()

	var existing unix.Stat_t
	if err := unix.Stat(path, &existing); err == nil {
		identity := aixLockIdentity{device: existing.Dev, inode: existing.Ino}
		if _, held := aixProcessLocks.held[identity]; held {
			return nil, fmt.Errorf("%w: %s", ErrPersistenceLocked, path)
		}
	} else if !errors.Is(err, unix.ENOENT) {
		return nil, fmt.Errorf("inspect persistence lock %q: %w", path, err)
	}

	file, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open persistence lock %q: %w", path, err)
	}
	var stat unix.Stat_t
	if err := unix.Fstat(int(file.Fd()), &stat); err != nil {
		_ = file.Close()
		return nil, fmt.Errorf("identify persistence lock %q: %w", path, err)
	}
	identity := aixLockIdentity{device: stat.Dev, inode: stat.Ino}
	request := unix.Flock_t{Type: unix.F_WRLCK, Whence: 0, Start: 0, Len: 0}
	if err := unix.FcntlFlock(file.Fd(), unix.F_SETLK, &request); err != nil {
		_ = file.Close()
		if errors.Is(err, unix.EACCES) || errors.Is(err, unix.EAGAIN) {
			return nil, fmt.Errorf("%w: %s", ErrPersistenceLocked, path)
		}
		return nil, fmt.Errorf("lock persistence directory %q: %w", path, err)
	}
	aixProcessLocks.held[identity] = struct{}{}
	return &persistenceLock{file: file, identity: identity}, nil
}

func (lock *persistenceLock) Close() error {
	if lock == nil {
		return nil
	}
	aixProcessLocks.Lock()
	defer aixProcessLocks.Unlock()
	if lock.file == nil {
		return nil
	}
	request := unix.Flock_t{Type: unix.F_UNLCK, Whence: 0, Start: 0, Len: 0}
	err := unix.FcntlFlock(lock.file.Fd(), unix.F_SETLK, &request)
	closeErr := lock.file.Close()
	lock.file = nil
	delete(aixProcessLocks.held, lock.identity)
	return errors.Join(err, closeErr)
}
