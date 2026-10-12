package memory

import (
	"encoding/json"
	"fmt"

	"github.com/ace-teknologi/memzy"
)

// Store provides a key-value store in memory.
type Store struct {
	key string
	m   map[string][]byte
}

// NewStore returns a pointer to a Store that uses key as the PrimaryKey
func NewStore(key string) *Store {
	return &Store{
		key: key,
		m:   make(map[string][]byte),
	}
}

// GetItem retrieves an item from the Store
func (s *Store) GetItem(v interface{}, key map[string]interface{}) error {
	// Check that the correct primary key has been used
	var bytes []byte
	var keyStr string
	if len(key) != 1 {
		return fmt.Errorf("Store only supports a single primary key")
	}
	for k, val := range key {
		if k != s.key {
			return fmt.Errorf("MemoryBackend's primary key is %v, you used %v", s.key, k)
		}

		var ok bool
		keyStr, ok = val.(string)
		if !ok {
			return fmt.Errorf("Could not convert %v into a string", val)
		}

		bytes = s.m[keyStr]
	}

	if len(bytes) == 0 {
		return memzy.ErrNotFound
	}

	return json.Unmarshal(bytes, v)
}

// PutItem stores an item
func (s *Store) PutItem(v interface{}) error {
	// Turn it into a map[string]interface{} so we can check if the primary key is there
	var m map[string]interface{}
	bytes, err := json.Marshal(v)
	if err != nil {
		return fmt.Errorf("Could not convert item to JSON: %w", err)
	}
	json.Unmarshal(bytes, &m)

	key, ok := m[s.key]
	if !ok {
		return fmt.Errorf("Your object does not contain the primary key for this store (%v)", s.key)
	}

	s.m[key.(string)] = bytes
	return nil
}
