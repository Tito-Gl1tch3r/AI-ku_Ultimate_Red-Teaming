package mod

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// F8xSubTool represents an individual tool included in a batch flag
type F8xSubTool struct {
	Name string `json:"name"`
	URL  string `json:"url,omitempty"`
}

// F8xModule represents a single tool installable via f8x
type F8xModule struct {
	ID            string       `json:"id"`
	Name          string       `json:"name"`
	NameZh        string       `json:"nameZh"`
	Flag          string       `json:"flag"`
	Category      string       `json:"category"`
	Description   string       `json:"description"`
	DescriptionZh string       `json:"descriptionZh"`
	Tags          []string     `json:"tags"`
	Includes      []F8xSubTool `json:"includes,omitempty"`
}

// F8xCategoryInfo describes a tool category
type F8xCategoryInfo struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	NameZh string `json:"nameZh"`
	Count  int    `json:"count"`
}

// F8xPreset is a curated combination of tools
type F8xPreset struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	NameZh      string   `json:"nameZh"`
	Description string   `json:"description"`
	Flags       []string `json:"flags"`
}

// F8xTool represents an individual tool installable via `f8x -install <id>`
type F8xTool struct {
	ID            string   `json:"id"`
	Name          string   `json:"name"`
	NameZh        string   `json:"nameZh"`
	Description   string   `json:"description"`
	DescriptionZh string   `json:"descriptionZh"`
	Category      string   `json:"category"`
	Tags          []string `json:"tags"`
	Deps          int      `json:"deps"`
	URL           string   `json:"url"`
}

// F8xInstalledInfo represents a single tool's install record
type F8xInstalledInfo struct {
	InstalledAt string `json:"installed_at"`
	Method      string `json:"method"`
}

// F8xInstalledFile represents the /opt/.f8x/installed.json structure
type F8xInstalledFile struct {
	Tools       map[string]F8xInstalledInfo `json:"tools"`
	F8xVersion  string                      `json:"f8x_version"`
	LastUpdated string                      `json:"last_updated"`
}

// F8xRemoteCatalog is the structure returned by the remote catalog.json
type F8xRemoteCatalog struct {
	Version        string            `json:"version"`
	CatalogVersion int               `json:"catalog_version"`
	UpdatedAt      string            `json:"updated_at"`
	Modules        []F8xModule       `json:"modules"`
	Tools          []F8xTool         `json:"tools"`
	Categories     []F8xCategoryInfo `json:"categories"`
	Presets        []F8xPreset       `json:"presets"`
}

// F8xDefaultURL is the default download URL for f8x
const F8xDefaultURL = "https://f8x.io/f8x"

// F8xFallbackURL is the fallback GitHub raw URL
const F8xFallbackURL = "https://raw.githubusercontent.com/ffffffff0x/f8x/main/f8x"

// F8xCatalogURL is the remote catalog URL (served via GitHub Pages)
const F8xCatalogURL = "https://f8x.wgpsec.org/catalog.json"

// ── Remote catalog cache ──

var (
	f8xRemoteCache   *F8xRemoteCatalog
	f8xRemoteCacheMu sync.RWMutex
	f8xRemoteCacheAt time.Time
	f8xCacheTTL      = 30 * time.Minute
)

// FetchF8xRemoteCatalog fetches catalog from the remote URL with caching
func FetchF8xRemoteCatalog() (*F8xRemoteCatalog, error) {
	f8xRemoteCacheMu.RLock()
	if f8xRemoteCache != nil && time.Since(f8xRemoteCacheAt) < f8xCacheTTL {
		cached := f8xRemoteCache
		f8xRemoteCacheMu.RUnlock()
		return cached, nil
	}
	f8xRemoteCacheMu.RUnlock()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s?t=%d", F8xCatalogURL, time.Now().Unix())
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}

	// Use TLS-skip client for f8x.wgpsec.org (our own domain, cert may expire)
	client := newTLSSkipClient(10 * time.Second)
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("fetch catalog: HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 2*1024*1024))
	if err != nil {
		return nil, err
	}

	var catalog F8xRemoteCatalog
	if err := json.Unmarshal(body, &catalog); err != nil {
		return nil, err
	}

	if len(catalog.Modules) == 0 {
		return nil, fmt.Errorf("remote catalog has no modules")
	}

	f8xRemoteCacheMu.Lock()
	f8xRemoteCache = &catalog
	f8xRemoteCacheAt = time.Now()
	f8xRemoteCacheMu.Unlock()

	return &catalog, nil
}

// InvalidateF8xCache clears the remote catalog cache
func InvalidateF8xCache() {
	f8xRemoteCacheMu.Lock()
	f8xRemoteCache = nil
	f8xRemoteCacheMu.Unlock()
}

// GetF8xCatalog returns the full tool catalog from remote
func GetF8xCatalog() []F8xModule {
	if remote, err := FetchF8xRemoteCatalog(); err == nil {
		return remote.Modules
	}
	return nil
}

// GetF8xCategories returns category metadata with counts from remote
func GetF8xCategories() []F8xCategoryInfo {
	if remote, err := FetchF8xRemoteCatalog(); err == nil {
		return remote.Categories
	}
	return nil
}

// GetF8xPresets returns preset combinations from remote
func GetF8xPresets() []F8xPreset {
	if remote, err := FetchF8xRemoteCatalog(); err == nil {
		return remote.Presets
	}
	return nil
}

// GetF8xTools returns the individual tools list from the cached catalog.
func GetF8xTools() []F8xTool {
	catalog, err := FetchF8xRemoteCatalog()
	if err != nil || catalog == nil {
		return nil
	}
	return catalog.Tools
}
