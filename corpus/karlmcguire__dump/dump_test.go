package dump

import (
	"bytes"
	"errors"
	"os"
	"testing"
	"time"
)

func TestNewDump(t *testing.T) {
	type params struct {
		filename string
		persist  int
		types    []Type
		err      error
	}

	tests := []params{
		{
			filename: "test.db",
			persist:  PERSIST_WRITES,
			types:    nil,
			err:      ErrInvalidTypes,
		},
		{
			filename: "test.db",
			persist:  999,
			types:    []Type{{"meh", params{}}},
			err:      ErrInvalidPersist,
		},
		{
			filename: "test.db",
			persist:  PERSIST_WRITES,
			types:    []Type{{"meh", params{}}},
			err:      nil,
		},
		{
			filename: "",
			persist:  PERSIST_WRITES,
			types:    []Type{{"meh", params{}}},
			err:      ErrInvalidFilename,
		},
		{
			filename: "test.db",
			persist:  PERSIST_INTERVAL,
			types:    []Type{{"meh", params{}}},
			err:      nil,
		},
	}

	var err error

	for _, v := range tests {
		if v.types != nil {
			if _, err = NewDump(v.filename, v.persist, v.types[0]); err != v.err {
				t.Fatal("unexpected error")
			}
		} else {
			if _, err = NewDump(v.filename, v.persist); err != v.err {
				t.Fatal("unexpected error")
			}
		}
	}
}

type Blob struct {
	Data string
}

func (b *Blob) MarshalJSON() ([]byte, error) {
	var buffer bytes.Buffer

	buffer.WriteString(`{"data":"`)
	buffer.WriteString(b.Data)
	buffer.WriteString(`"}`)

	if b.Data == "bad" {
		return nil, errors.New("bad test")
	}

	return buffer.Bytes(), nil
}

func TestPersistInterval(t *testing.T) {
	test, _ := NewDump("persist.db", PERSIST_INTERVAL, Type{"dump.Blob", &Blob{}})

	_, _ = test.Add(&Blob{"meh"})

	os.Chmod("persist.db", 0444)

	time.Sleep(time.Second * 70)
}

func TestAdd(t *testing.T) {
	test, _ := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})

	_, _ = test.Add(&Blob{"meh"})
}

func TestMarshalJSON(t *testing.T) {
	test, _ := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})

	_, _ = test.Add(&Blob{"meh"})

	data, _ := test.MarshalJSON()

	if !bytes.Equal(data, []byte(`[{"data":"meh"}]`)) {
		t.Fatal("bad json encoding")
	}

	_, _ = test.Add(&Blob{"bad"})

	if _, err := test.MarshalJSON(); err == nil {
		t.Fatal("not handling marshal errors")
	}
}

func TestView(t *testing.T) {
	test, _ := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})

	id, _ := test.Add(&Blob{"hi"})

	err := test.View(func(items []Item) error {
		if items[id].(*Blob).Data != "hi" {
			t.Fatal("something is very wrong")
		}

		return errors.New("test")
	})
	if err.Error() != "test" {
		t.Fatal("problem with view errors")
	}
}

func TestUpdate(t *testing.T) {
	test, _ := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})

	id, _ := test.Add(&Blob{"hi"})

	err := test.Update(func(items []Item) error {
		items[id].(*Blob).Data = "new"
		return nil
	})
	if err != nil {
		t.Fatal("problem updating")
	}

	var testErr = errors.New("example error")

	err = test.Update(func(items []Item) error {
		return testErr
	})
	if err != testErr {
		t.Fatal("update error catch")
	}

	err = test.View(func(items []Item) error {
		if items[id].(*Blob).Data != "new" {
			t.Fatal("update didn't save")
		}
		return nil
	})
	if err != nil {
		t.Fatal("update didn't save")
	}

	another, _ := NewDump("test.db", PERSIST_MANUAL, Type{"dump.Blob", &Blob{}})
	id, _ = another.Add(&Blob{"hi"})
	err = another.Update(func(items []Item) error {
		items[id].(*Blob).Data = "new"
		return nil
	})
	if err != nil {
		t.Fatal("problem updating")
	}
}

func TestLoad(t *testing.T) {
	test, err := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})
	if err != nil {
		t.Fatal(err)
	}

	id, err := test.Add(&Blob{"hi"})
	if err != nil {
		t.Fatal(err)
	}

	other, err := NewDump("test.db", PERSIST_MANUAL, Type{"dump.Blob", &Blob{}})
	if err != nil {
		t.Fatal(err)
	}

	if err = other.Load(); err != nil {
		t.Fatal(err)
	}

	if err := other.View(func(items []Item) error {
		if items[id].(*Blob).Data != "hi" {
			t.Fatal("load error")
		}
		return nil
	}); err != nil {
		t.Fatal("load error")
	}

	another, err := NewDump("missing.db", PERSIST_MANUAL, Type{"dump.Blob", &Blob{}})
	if err != nil {
		t.Fatal(err)
	}

	if err = another.Load(); err == nil {
		t.Fatal("didn't throw io error")
	}
}

func TestMap(t *testing.T) {
	test, err := NewDump("test.db", PERSIST_MANUAL, Type{"dump.Blob", &Blob{}})
	if err != nil {
		t.Fatal(err)
	}

	if _, err = test.Add(&Blob{"meh"}); err != nil {
		t.Fatal("adding")
	}

	var errTest = errors.New("map")

	if err = test.Map(func(item Item) error {
		if item.(*Blob).Data == "meh" {
			return errTest
		}
		return nil
	}); err != nil {
		if err != errTest {
			t.Fatal("bad error")
		}
	}

	if err = test.Map(func(item Item) error {
		return nil
	}); err != nil {
		t.Fatal(err)
	}

	testTwo, err := NewDump("test.db", PERSIST_WRITES, Type{"dump.Blob", &Blob{}})
	if err != nil {
		t.Fatal(err)
	}

	if err = testTwo.Map(func(item Item) error {
		item.(*Blob).Data = "nice"
		return nil
	}); err != nil {
		t.Fatal(err)
	}
}
