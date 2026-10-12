package internal

import (
	"crypto/rand"
	"encoding/json"
	"fmt"
	"os"
)

// ScanOutput is the top-level JSON output structure.
type ScanOutput struct {
	Timestamp string         `json:"timestamp"`
	Results   []BucketResult `json:"results"`
}

// BucketResult holds the enumeration and fuzzing results for a single source bucket.
type BucketResult struct {
	Bucket     string   `json:"bucket"`
	AccountID  string   `json:"account_id"`
	Region     string   `json:"region,omitempty"`
	Discovered []string `json:"discovered_buckets"`
}

// WriteJSON marshals the output and writes it to the given file path.
func WriteJSON(path string, output ScanOutput) error {
	data, err := json.MarshalIndent(output, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal json: %w", err)
	}
	return os.WriteFile(path, data, 0644)
}

// GenerateOutputPath returns a default output filename: bucky-{uuid}.json
func GenerateOutputPath() string {
	return fmt.Sprintf("bucky-%s.json", uuidV4())
}

func uuidV4() string {
	b := make([]byte, 16)
	rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}
