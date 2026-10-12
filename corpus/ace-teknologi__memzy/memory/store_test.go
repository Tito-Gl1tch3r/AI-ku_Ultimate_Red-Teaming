package memory

import (
	"testing"

	"github.com/ace-teknologi/memzy"
)

type testObject struct {
	MegaID     string `json:"megaID"`
	MegaAge    int    `json:"megaAge"`
	MegaColour string `json:"megaColour"`
}

func TestStorePutThenGetItem(t *testing.T) {
	s := NewStore("megaID")
	obj := &testObject{
		MegaID:     "123",
		MegaAge:    27,
		MegaColour: "brown",
	}

	err := s.PutItem(obj)
	if err != nil {
		t.Errorf("Unable to put item: %v", err)
	}

	newObj := &testObject{}

	err = s.GetItem(newObj, map[string]interface{}{"megaID": "123"})
	if err != nil {
		t.Errorf("Unable to get item: %v", err)
	}

	err = s.GetItem(newObj, map[string]interface{}{"megaID": "456"})
	if err == nil {
		t.Errorf("Expected an error")
	}
}

func TestStoreGetItemBadKeys(t *testing.T) {
	s := NewStore("derp")
	o := &testObject{}

	badKeys := []map[string]interface{}{
		{"wrongKeyDerp": "nar"},
		{
			"derp":  "soFarSogood",
			"derp2": "tooManyKeys",
		},
		{"derp": 22},
	}

	for _, k := range badKeys {
		err := s.GetItem(o, k)
		if err == nil {
			t.Errorf("Expected an error, got none")
		}
	}

}

func TestStorePutItemBad(t *testing.T) {
	s := NewStore("MegaID")

	badObjects := []interface{}{
		&testObject{},
		1,
		nil,
		&testObject{
			MegaAge: 11,
		},
		struct {
			WrongKey string
		}{
			"derp",
		},
	}

	for _, o := range badObjects {
		err := s.PutItem(o)
		if err == nil {
			t.Errorf("Expected an error, got none")
			return
		}
	}
}

func TestStoreImplementsMemzy(t *testing.T) {
	m := NewStore("ImplementsMemzy")
	if _, ok := interface{}(m).(memzy.Memzy); !ok {
		t.Errorf("Store does not implement memzy.Memzy")
	}
}
