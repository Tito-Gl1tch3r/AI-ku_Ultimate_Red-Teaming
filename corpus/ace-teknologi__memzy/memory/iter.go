package memory

import (
	"encoding/json"

	"github.com/ace-teknologi/memzy"
)

// Iter provides a way to iterate through all of the items in the store
type Iter struct {
	m   map[string][]byte
	cur []byte
	err error
}

// NewIter returns a pointer to an Iter
func (s *Store) NewIter(args ...interface{}) memzy.Iter {
	return &Iter{m: s.m}
}

// Current unmarshals the current byte slice into your object
func (i *Iter) Current(v interface{}) error {
	return json.Unmarshal(i.cur, v)
}

// Err is here to implement memzy.Iter, but it won't be used
func (i *Iter) Err() error {
	return i.err
}

// Next moves along to the next item in the Iter
func (i *Iter) Next() bool {
	for k, v := range i.m {
		i.cur = v
		delete(i.m, k)
		return true
	}

	return false
}
