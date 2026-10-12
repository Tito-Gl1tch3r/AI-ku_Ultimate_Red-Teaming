package internal

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const CurrentVersion = "v1.0.0"

const modulePath = "github.com/umair9747/bucky"

// CheckForUpdate queries the Go module proxy for the latest version and prints
// a reminder to stderr if a newer version is available. Errors are silently
// ignored so this never blocks or breaks normal operation.
func CheckForUpdate() {
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(fmt.Sprintf("https://proxy.golang.org/%s/@latest", modulePath))
	if err != nil {
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return
	}

	// Response is JSON with a "Version" field, e.g. {"Version":"v1.2.0",...}
	// Parse it minimally to avoid importing encoding/json just for this.
	latest := extractVersion(string(body))
	if latest == "" || latest == CurrentVersion {
		return
	}

	fmt.Fprintf(os.Stderr, "[*] A new version of bucky is available: %s (current: %s)\n", latest, CurrentVersion)
	fmt.Fprintln(os.Stderr, "[*] Run `bucky --update` or `go install github.com/umair9747/bucky@latest` to update.")
}

// extractVersion pulls the Version value from a JSON string like {"Version":"v1.0.0",...}
func extractVersion(body string) string {
	key := `"Version":"`
	idx := strings.Index(body, key)
	if idx == -1 {
		return ""
	}
	start := idx + len(key)
	end := strings.Index(body[start:], `"`)
	if end == -1 {
		return ""
	}
	return body[start : start+end]
}
