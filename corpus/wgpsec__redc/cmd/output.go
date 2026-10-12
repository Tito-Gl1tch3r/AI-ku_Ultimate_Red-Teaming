package cmd

import (
	"encoding/json"
	"fmt"
	"os"
)

// OutputFormat holds the global output format setting
var outputFormat string

// JSONOutput is the standard JSON response structure
type JSONOutput struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// IsJSON returns true if --output json was specified
func IsJSON() bool {
	return outputFormat == "json"
}

// PrintJSON outputs a successful JSON response
func PrintJSON(data interface{}) {
	out := JSONOutput{Success: true, Data: data}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	enc.Encode(out)
}

// PrintJSONError outputs an error JSON response
func PrintJSONError(err error) {
	out := JSONOutput{Success: false, Error: err.Error()}
	enc := json.NewEncoder(os.Stderr)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	enc.Encode(out)
}

// PrintJSONMessage outputs a simple message as JSON
func PrintJSONMessage(msg string) {
	PrintJSON(map[string]string{"message": msg})
}

// MustJSON is a helper that prints JSON on error and exits
func MustJSON(err error) {
	if err != nil && IsJSON() {
		PrintJSONError(err)
		os.Exit(1)
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
