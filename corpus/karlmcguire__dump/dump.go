// Package dump manages a list of items in memory with concurrency-safe
// functions for accessing and manipulating them.
package dump

import (
	"bytes"
	"encoding/gob"
	"errors"
	"io/ioutil"
	"sync"
	"time"
)

const (
	// PERSIST_MANUAL is the default disk-persistence setting. The user has to
	// manually save the dump to disk using the Save() function.
	PERSIST_MANUAL = iota

	// PERSIST_WRITES is a disk-persistence setting that will save the dump
	// to disk when either Add() or Update() is called.
	PERSIST_WRITES

	// PERSIST_INTERVAL is a disk-persistence setting that will save the dump
	// on a set interval (currently once every 60 seconds).
	PERSIST_INTERVAL
)

var (
	// ErrInvalidPersist is thrown when an invalid disk-persistence setting is
	// provided when calling NewDump().
	ErrInvalidPersist = errors.New("invalid persist type")

	// ErrInvalidTypes is thrown when no types are listed when calling
	// NewDump(). Without type definitions it is impossible to persist on disk
	// without possible data loss.
	ErrInvalidTypes = errors.New("no types were provided")

	// ErrInvalidFilename is thrown when NewDump() is called with an empty
	// filename - making persistence impossible.
	ErrInvalidFilename = errors.New("invalid filename")
)

// Dump represents a collection of items that persist on disk.
type Dump struct {
	filename string
	items    []Item
	persist  int
	mutex    sync.RWMutex
}

// Type is used to register types from outside packages so that they are
// recognized when loading or saving the dump.
type Type struct {
	// Name is the name of this type. Usually it takes the form of
	// "package.Name" -- so for a struct User{} in package main this field
	// would be "main.User".
	Name string

	// Value is an empty struct of this type. For a struct User{}, this would
	// be User{}.
	Value interface{}
}

// NewDump is the primary constructor function for creating dumps. The
// provided filename is where the dump will persist to disk (and read from
// disk). The persist int is one of the dump.PERSIST_ constants. The provided
// types register the types that will be held in the dump.
//
// NewDump will return an error if the persist parameter is not a valid
// dump.PERSIST_ constant.
func NewDump(filename string, persist int, types ...Type) (*Dump, error) {
	if len(filename) == 0 {
		return nil, ErrInvalidFilename
	}

	if len(types) == 0 {
		return nil, ErrInvalidTypes
	}

	for _, t := range types {
		gob.RegisterName(t.Name, t.Value)
	}

	if persist != PERSIST_MANUAL &&
		persist != PERSIST_WRITES &&
		persist != PERSIST_INTERVAL {
		return nil, ErrInvalidPersist
	}

	dump := &Dump{
		filename: filename,
		items:    make([]Item, 0),
		persist:  persist,
		mutex:    sync.RWMutex{},
	}

	if persist == PERSIST_INTERVAL {
		go dump.persistInterval()
	}

	return dump, nil
}

// Item implements the json.Marshaler interface and is used so that the dump
// itself can implement the json.Marshaler function by aggregating all items.
type Item interface {
	MarshalJSON() ([]byte, error)
}

func (d *Dump) persistInterval() {
	for {
		time.Sleep(time.Second * 60)

		if err := d.Save(); err != nil {
			println(err.Error())
		}
	}
}

// Add appends an Item on the end of the dump. It returns the id of the item
// and an error if there was a problem persisting the dump on the disk (if
// PERSIST_WRITE is enabled).
func (d *Dump) Add(item Item) (int, error) {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	d.items = append(d.items, item)

	if d.persist == PERSIST_WRITES {
		return len(d.items) - 1, d.save()
	}

	return len(d.items) - 1, nil
}

// MarshalJSON returns the dump as a JSON list. It returns an error if there
// was an error marshaling one of the items.
func (d *Dump) MarshalJSON() ([]byte, error) {
	d.mutex.RLock()
	defer d.mutex.RUnlock()

	var buffer bytes.Buffer

	buffer.WriteString(`[`)
	for i, item := range d.items {
		da, err := item.MarshalJSON()
		if err != nil {
			return nil, err
		}
		buffer.Write(da)
		if i != len(d.items)-1 {
			buffer.WriteString(`,`)
		}
	}
	buffer.WriteString(`]`)

	return buffer.Bytes(), nil
}

func (d *Dump) encodeGob() []byte {
	var buffer bytes.Buffer
	gob.NewEncoder(&buffer).Encode(d.items)
	return buffer.Bytes()
}

func (d *Dump) decodeGob(data []byte) error {
	return gob.NewDecoder(bytes.NewBuffer(data)).Decode(&d.items)
}

// Save persists the dump on disk using the filename provided when NewDump()
// was called.
func (d *Dump) Save() error {
	d.mutex.RLock()
	defer d.mutex.RUnlock()

	return d.save()
}

// no mutex
func (d *Dump) save() error {
	return ioutil.WriteFile(d.filename, d.encodeGob(), 0644)
}

// Load reads the dump from disk using the filename provided when NewDump()
// was called.
func (d *Dump) Load() error {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	var (
		data []byte
		err  error
	)

	if data, err = ioutil.ReadFile(d.filename); err != nil {
		return err
	}

	return d.decodeGob(data)
}

// Update is used to manipulate an item (or items) in the dump. It returns
// an error if there is an error saving the dump (if PERSIST_WRITES is
// enabled) or if there is an error inside the f function.
func (d *Dump) Update(f func(items []Item) error) error {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	if err := f(d.items); err != nil {
		return err
	}

	if d.persist == PERSIST_WRITES {
		return d.save()
	}

	return nil
}

// Map applies the function f to each item in the dump. It returns an error if
// f returns an error for one of the items. If PERSIST_WRITES is enabled Map
// might also return an error if there is an error saving the dump to disk.
func (d *Dump) Map(f func(item Item) error) error {
	d.mutex.Lock()
	defer d.mutex.Unlock()

	var err error
	for _, i := range d.items {
		if err = f(i); err != nil {
			return err
		}
	}

	if d.persist == PERSIST_WRITES {
		return d.save()
	}

	return nil
}

// View is used to read an item (or items) in the dump. It returns an error
// if there is an error inside the f function.
func (d *Dump) View(f func(items []Item) error) error {
	d.mutex.RLock()
	defer d.mutex.RUnlock()

	return f(d.items)
}
