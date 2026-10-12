package plugin

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseTfvars(t *testing.T) {
	content := `# This is a comment
// Another comment

port = "8388"
password = "mypass"
count = 10
domain = "ns1.example.com"
`
	dir := t.TempDir()
	path := filepath.Join(dir, "terraform.tfvars")
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	result := ParseTfvars(path)

	expected := map[string]string{
		"port":     "8388",
		"password": "mypass",
		"count":    "10",
		"domain":   "ns1.example.com",
	}

	for k, want := range expected {
		got, ok := result[k]
		if !ok {
			t.Errorf("missing key %q", k)
			continue
		}
		if got != want {
			t.Errorf("key %q: got %q, want %q", k, got, want)
		}
	}

	if len(result) != len(expected) {
		t.Errorf("result has %d keys, want %d", len(result), len(expected))
	}
}

func TestParseTfvarsNotExist(t *testing.T) {
	result := ParseTfvars("/nonexistent/path/terraform.tfvars")
	if result == nil {
		t.Fatal("expected non-nil map for missing file")
	}
	if len(result) != 0 {
		t.Errorf("expected empty map, got %v", result)
	}
}
