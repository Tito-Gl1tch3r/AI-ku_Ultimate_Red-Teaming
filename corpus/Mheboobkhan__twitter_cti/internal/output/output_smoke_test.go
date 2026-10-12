package output

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"twitter-cti/internal/ioc"
)

func sampleRecords() []*ioc.Record {
	return []*ioc.Record{
		{
			Match:        ioc.Match{Type: "ip", Value: "1.2.3.4", Raw: "1.2.3[.]4", Defanged: true},
			FirstSeenAt:  time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC),
			SeenCount:    2,
			FirstURL:     "https://x.com/foo/status/1",
			FirstAuthor:  "foo",
			MatchedQuery: "#malware",
		},
		{
			Match:       ioc.Match{Type: "hash", Subtype: "md5", Value: "44d88612fea8a8f36de82e1278abb02f", Raw: "44d88612fea8a8f36de82e1278abb02f"},
			FirstSeenAt: time.Date(2026, 1, 2, 0, 0, 0, 0, time.UTC),
			SeenCount:   1,
		},
	}
}

func TestWriteTextToDir(t *testing.T) {
	dir := t.TempDir()
	if err := Write("text", dir, sampleRecords()); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 2 { // one "ip" file, one "hash" file
		t.Fatalf("expected 2 files, got %d: %v", len(entries), entries)
	}
	for _, e := range entries {
		data, err := os.ReadFile(filepath.Join(dir, e.Name()))
		if err != nil {
			t.Fatal(err)
		}
		if strings.HasPrefix(e.Name(), "ip_") && strings.TrimSpace(string(data)) != "1.2.3.4" {
			t.Errorf("unexpected ip file contents: %q", data)
		}
	}
}

func TestWriteJSONToDir(t *testing.T) {
	dir := t.TempDir()
	if err := Write("json", dir, sampleRecords()); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 json file, got %d", len(entries))
	}
	data, err := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), `"value": "1.2.3.4"`) {
		t.Errorf("json missing expected ip record: %s", data)
	}
	if !strings.Contains(string(data), `"subtype": "md5"`) {
		t.Errorf("json missing expected hash subtype: %s", data)
	}
}

func TestWriteCSVToDir(t *testing.T) {
	dir := t.TempDir()
	if err := Write("csv", dir, sampleRecords()); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 csv file, got %d", len(entries))
	}
	data, err := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 3 { // header + 2 records
		t.Fatalf("expected 3 csv lines, got %d: %v", len(lines), lines)
	}
}

func TestWriteUnknownFormat(t *testing.T) {
	if err := Write("xml", t.TempDir(), sampleRecords()); err == nil {
		t.Fatal("expected error for unknown format")
	}
}
