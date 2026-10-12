package plugin

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	redc "red-cloud/mod"
	"strings"
	"sync"

	version "github.com/hashicorp/go-version"
)

// PluginManifest is the plugin.json schema
type PluginManifest struct {
	Name           string                 `json:"name"`
	Version        string                 `json:"version"`
	Description    string                 `json:"description"`
	DescriptionEN  string                 `json:"description_en,omitempty"`
	Author         string                 `json:"author,omitempty"`
	Homepage       string                 `json:"homepage,omitempty"`
	Category       string                 `json:"category,omitempty"`
	Tags           []string               `json:"tags,omitempty"`
	MinRedCVersion string                 `json:"min_redc_version,omitempty"`
	Capabilities   PluginCapabilities     `json:"capabilities"`
	ConfigSchema   map[string]ConfigField `json:"config_schema,omitempty"`
}

// PluginCapabilities declares what the plugin provides
type PluginCapabilities struct {
	Templates []string               `json:"templates,omitempty"` // glob patterns relative to plugin dir
	Userdata  []string               `json:"userdata,omitempty"`  // glob patterns
	Hooks     map[string]interface{} `json:"hooks,omitempty"`     // hookPoint → script path (string) or config (object)
}

// ConfigField describes a single config parameter
type ConfigField struct {
	Type        string `json:"type"` // "string", "number", "boolean"
	Required    bool   `json:"required,omitempty"`
	Description string `json:"description,omitempty"`
	Default     string `json:"default,omitempty"`
}

// Plugin represents a loaded plugin
type Plugin struct {
	Manifest PluginManifest         `json:"manifest"`
	Dir      string                 `json:"dir"`
	Enabled  bool                   `json:"enabled"`
	Config   map[string]interface{} `json:"config,omitempty"`
}

// PluginManager manages all plugins
type PluginManager struct {
	mu         sync.RWMutex
	pluginsDir string
	plugins    map[string]*Plugin
}

// NewPluginManager creates a manager rooted at pluginsDir
func NewPluginManager(pluginsDir string) *PluginManager {
	if pluginsDir == "" {
		if d, err := DefaultPluginsDir(); err == nil {
			pluginsDir = d
		}
	}
	return &PluginManager{
		pluginsDir: pluginsDir,
		plugins:    make(map[string]*Plugin),
	}
}

// DefaultPluginsDir returns ~/.redc/plugins/
func DefaultPluginsDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot determine home directory: %w", err)
	}
	return filepath.Join(home, ".redc", "plugins"), nil
}

// List returns all loaded plugins
func (pm *PluginManager) List() []*Plugin {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	result := make([]*Plugin, 0, len(pm.plugins))
	for _, p := range pm.plugins {
		result = append(result, p)
	}
	return result
}

// Get returns a plugin by name
func (pm *PluginManager) Get(name string) (*Plugin, bool) {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	p, ok := pm.plugins[name]
	return p, ok
}

// PluginsDir returns the base plugins directory
func (pm *PluginManager) PluginsDir() string {
	return pm.pluginsDir
}

// loadManifest reads plugin.json from a directory
func loadManifest(dir string) (PluginManifest, error) {
	var m PluginManifest
	data, err := os.ReadFile(filepath.Join(dir, "plugin.json"))
	if err != nil {
		return m, fmt.Errorf("cannot read plugin.json: %w", err)
	}
	if err := json.Unmarshal(data, &m); err != nil {
		return m, fmt.Errorf("invalid plugin.json: %w", err)
	}
	if m.Name == "" {
		return m, fmt.Errorf("plugin.json missing 'name' field")
	}
	if m.MinRedCVersion != "" {
		required, requiredErr := version.NewVersion(strings.TrimPrefix(m.MinRedCVersion, "v"))
		current, currentErr := version.NewVersion(strings.TrimPrefix(redc.Version, "v"))
		if requiredErr != nil {
			return m, fmt.Errorf("plugin.json has invalid min_redc_version %q", m.MinRedCVersion)
		}
		if currentErr != nil {
			return m, fmt.Errorf("redc has invalid version %q", redc.Version)
		}
		if current.LessThan(required) {
			return m, fmt.Errorf("plugin %s requires redc %s or newer (current %s)", m.Name, m.MinRedCVersion, redc.Version)
		}
	}
	return m, nil
}

// loadPluginConfig reads config.yaml from plugin dir
func loadPluginConfig(dir string) map[string]interface{} {
	data, err := os.ReadFile(filepath.Join(dir, "config.yaml"))
	if err != nil {
		return nil
	}
	var cfg map[string]interface{}
	if err := json.Unmarshal(data, &cfg); err != nil {
		// try yaml
		return nil
	}
	return cfg
}

// isEnabled checks disabled marker file
func isEnabled(dir string) bool {
	_, err := os.Stat(filepath.Join(dir, ".disabled"))
	return err != nil // enabled if .disabled does NOT exist
}

// shouldAutoEnable returns false if the plugin has required config fields with no value configured.
func shouldAutoEnable(manifest PluginManifest, config map[string]interface{}) bool {
	for key, field := range manifest.ConfigSchema {
		if !field.Required {
			continue
		}
		val, ok := config[key]
		if !ok || val == nil || val == "" {
			return false
		}
	}
	return true
}
