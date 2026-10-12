// Package output renders deduplicated IOC records as text, JSON, or CSV,
// either to a directory of files or to stdout.
package output

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"twitter-cti/internal/ioc"
)

// jsonRecord is the stable on-disk/stdout shape for JSON and CSV output.
type jsonRecord struct {
	Type         string `json:"type"`
	Subtype      string `json:"subtype,omitempty"`
	Value        string `json:"value"`
	Raw          string `json:"raw"`
	Defanged     bool   `json:"defanged"`
	SeenCount    int    `json:"seen_count"`
	FirstSeenAt  string `json:"first_seen_at"`
	FirstAuthor  string `json:"first_author,omitempty"`
	FirstURL     string `json:"first_tweet_url,omitempty"`
	MatchedQuery string `json:"matched_query,omitempty"`
}

func toJSONRecords(records []*ioc.Record) []jsonRecord {
	out := make([]jsonRecord, len(records))
	for i, r := range records {
		out[i] = jsonRecord{
			Type:         r.Type,
			Subtype:      r.Subtype,
			Value:        r.Value,
			Raw:          r.Raw,
			Defanged:     r.Defanged,
			SeenCount:    r.SeenCount,
			FirstSeenAt:  r.FirstSeenAt.Format(time.RFC3339),
			FirstAuthor:  r.FirstAuthor,
			FirstURL:     r.FirstURL,
			MatchedQuery: r.MatchedQuery,
		}
	}
	return out
}

// Write renders records in the given format ("text", "json", "csv"). If dir
// is empty, output goes to stdout; otherwise it's written to timestamped
// file(s) in dir.
func Write(format, dir string, records []*ioc.Record) error {
	switch format {
	case "", "text":
		return writeText(dir, records)
	case "json":
		return writeJSON(dir, records)
	case "csv":
		return writeCSV(dir, records)
	default:
		return fmt.Errorf("unknown output format %q (want text, json, or csv)", format)
	}
}

func byType(records []*ioc.Record) map[string][]*ioc.Record {
	grouped := make(map[string][]*ioc.Record)
	for _, r := range records {
		grouped[r.Type] = append(grouped[r.Type], r)
	}
	return grouped
}

func writeText(dir string, records []*ioc.Record) error {
	grouped := byType(records)

	if dir == "" {
		for _, t := range []string{"ip", "domain", "hash", "url"} {
			fmt.Printf("\n-- %s (%d) --\n", t, len(grouped[t]))
			for _, r := range grouped[t] {
				fmt.Println(r.Value)
			}
		}
		return nil
	}

	stamp := time.Now().Format("20060102_150405")
	for _, t := range []string{"ip", "domain", "hash", "url"} {
		rs := grouped[t]
		if len(rs) == 0 {
			continue
		}
		name := filepath.Join(dir, fmt.Sprintf("%s_%s.txt", t, stamp))
		lines := make([]string, len(rs))
		for i, r := range rs {
			lines[i] = r.Value
		}
		if err := writeLines(name, lines); err != nil {
			return err
		}
	}
	return nil
}

func writeLines(path string, lines []string) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_TRUNC|os.O_CREATE, 0666)
	if err != nil {
		return err
	}
	defer f.Close()
	for _, l := range lines {
		if _, err := f.WriteString(l + "\n"); err != nil {
			return err
		}
	}
	return nil
}

func writeJSON(dir string, records []*ioc.Record) error {
	data, err := json.MarshalIndent(toJSONRecords(records), "", "  ")
	if err != nil {
		return err
	}
	if dir == "" {
		fmt.Println(string(data))
		return nil
	}
	name := filepath.Join(dir, fmt.Sprintf("iocs_%s.json", time.Now().Format("20060102_150405")))
	return os.WriteFile(name, data, 0666)
}

func writeCSV(dir string, records []*ioc.Record) error {
	var w *csv.Writer
	var f *os.File
	if dir == "" {
		w = csv.NewWriter(os.Stdout)
	} else {
		var err error
		name := filepath.Join(dir, fmt.Sprintf("iocs_%s.csv", time.Now().Format("20060102_150405")))
		f, err = os.OpenFile(name, os.O_WRONLY|os.O_TRUNC|os.O_CREATE, 0666)
		if err != nil {
			return err
		}
		defer f.Close()
		w = csv.NewWriter(f)
	}

	header := []string{"type", "subtype", "value", "raw", "defanged", "seen_count", "first_seen_at", "first_author", "first_tweet_url", "matched_query"}
	if err := w.Write(header); err != nil {
		return err
	}
	for _, r := range toJSONRecords(records) {
		row := []string{
			r.Type, r.Subtype, r.Value, r.Raw, strconv.FormatBool(r.Defanged),
			strconv.Itoa(r.SeenCount), r.FirstSeenAt, r.FirstAuthor, r.FirstURL, r.MatchedQuery,
		}
		if err := w.Write(row); err != nil {
			return err
		}
	}
	w.Flush()
	return w.Error()
}
