package plugin

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const DefaultRegistryURL = "https://redc.wgpsec.org/plugins/plugin-registry.json"

// RegistryIndex is the remote plugin registry
type RegistryIndex struct {
	Version int              `json:"version"`
	Updated string           `json:"updated"`
	Plugins []RegistryPlugin `json:"plugins"`
}

// RegistryPlugin describes an available plugin in the registry
type RegistryPlugin struct {
	Name          string   `json:"name"`
	Version       string   `json:"version"`
	Description   string   `json:"description"`
	DescriptionEN string   `json:"description_en,omitempty"`
	Author        string   `json:"author,omitempty"`
	Category      string   `json:"category,omitempty"`
	Tags          []string `json:"tags,omitempty"`
	MinVersion    string   `json:"min_redc_version,omitempty"`
	URL           string   `json:"url"`
}

// FetchRegistry fetches the plugin registry from the remote URL
func FetchRegistry(registryURL string) (*RegistryIndex, error) {
	if registryURL == "" {
		registryURL = DefaultRegistryURL
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Get(registryURL)
	if err != nil {
		return nil, fmt.Errorf("fetch registry: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("registry returned %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read registry: %w", err)
	}

	var index RegistryIndex
	if err := json.Unmarshal(body, &index); err != nil {
		return nil, fmt.Errorf("parse registry: %w", err)
	}

	return &index, nil
}
