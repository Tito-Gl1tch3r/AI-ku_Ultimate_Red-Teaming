package plugin

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"red-cloud/mod/gologger"
)

// Install installs a plugin from a git URL, ZIP URL, or local path
func (pm *PluginManager) Install(source string) (string, error) {
	if err := os.MkdirAll(pm.pluginsDir, 0755); err != nil {
		return "", fmt.Errorf("cannot create plugins dir: %w", err)
	}

	if isGitURL(source) {
		if isZipURL(source) {
			return pm.installFromZipURL(source)
		}
		return pm.installFromGit(source)
	}
	return pm.installFromLocal(source)
}

func isGitURL(s string) bool {
	return strings.HasPrefix(s, "http://") ||
		strings.HasPrefix(s, "https://") ||
		strings.HasPrefix(s, "git@") ||
		strings.HasSuffix(s, ".git")
}

func isZipURL(s string) bool {
	return strings.HasSuffix(strings.ToLower(s), ".zip")
}

func (pm *PluginManager) installFromGit(url string) (string, error) {
	// Clone to temp dir first, read manifest, then move
	tmpDir, err := os.MkdirTemp("", "redc-plugin-*")
	if err != nil {
		return "", fmt.Errorf("cannot create temp dir: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	gologger.Info().Msgf("plugin: cloning %s", url)
	cmd := exec.Command("git", "clone", "--depth", "1", url, tmpDir)
	if out, err := cmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("git clone failed: %s\n%s", err, string(out))
	}

	manifest, err := loadManifest(tmpDir)
	if err != nil {
		return "", fmt.Errorf("invalid plugin: %w", err)
	}

	destDir := filepath.Join(pm.pluginsDir, manifest.Name)
	if _, err := os.Stat(destDir); err == nil {
		return "", fmt.Errorf("plugin %s already installed at %s", manifest.Name, destDir)
	}

	if err := os.Rename(tmpDir, destDir); err != nil {
		// cross-device rename fallback: copy
		if err := copyDir(tmpDir, destDir); err != nil {
			return "", fmt.Errorf("cannot move plugin: %w", err)
		}
	}

	// Reload
	cfg := loadPluginConfig(destDir)
	enabled := shouldAutoEnable(manifest, cfg)
	if !enabled {
		os.WriteFile(filepath.Join(destDir, ".disabled"), []byte("disabled"), 0644)
	}
	pm.mu.Lock()
	pm.plugins[manifest.Name] = &Plugin{
		Manifest: manifest,
		Dir:      destDir,
		Enabled:  enabled,
		Config:   cfg,
	}
	pm.mu.Unlock()

	gologger.Info().Msgf("plugin: installed %s v%s", manifest.Name, manifest.Version)
	return manifest.Name, nil
}

// installFromZipURL downloads a ZIP archive and extracts it
func (pm *PluginManager) installFromZipURL(url string) (string, error) {
	tmpFile, err := os.CreateTemp("", "redc-plugin-*.zip")
	if err != nil {
		return "", fmt.Errorf("cannot create temp file: %w", err)
	}
	tmpPath := tmpFile.Name()
	defer os.Remove(tmpPath)

	gologger.Info().Msgf("plugin: downloading %s", url)
	client := &http.Client{Timeout: 2 * time.Minute}
	resp, err := client.Get(url)
	if err != nil {
		tmpFile.Close()
		return "", fmt.Errorf("download failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		tmpFile.Close()
		return "", fmt.Errorf("download returned %d", resp.StatusCode)
	}

	if _, err := io.Copy(tmpFile, resp.Body); err != nil {
		tmpFile.Close()
		return "", fmt.Errorf("download write failed: %w", err)
	}
	tmpFile.Close()

	// Extract to temp dir
	tmpDir, err := os.MkdirTemp("", "redc-plugin-extract-*")
	if err != nil {
		return "", fmt.Errorf("cannot create temp dir: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	if err := extractZip(tmpPath, tmpDir); err != nil {
		return "", fmt.Errorf("extract failed: %w", err)
	}

	manifest, err := loadManifest(tmpDir)
	if err != nil {
		return "", fmt.Errorf("invalid plugin: %w", err)
	}

	destDir := filepath.Join(pm.pluginsDir, manifest.Name)
	if _, err := os.Stat(destDir); err == nil {
		return "", fmt.Errorf("plugin %s already installed at %s", manifest.Name, destDir)
	}

	if err := os.Rename(tmpDir, destDir); err != nil {
		if err := copyDir(tmpDir, destDir); err != nil {
			return "", fmt.Errorf("cannot move plugin: %w", err)
		}
	}

	cfg2 := loadPluginConfig(destDir)
	enabled2 := shouldAutoEnable(manifest, cfg2)
	if !enabled2 {
		os.WriteFile(filepath.Join(destDir, ".disabled"), []byte("disabled"), 0644)
	}
	pm.mu.Lock()
	pm.plugins[manifest.Name] = &Plugin{
		Manifest: manifest,
		Dir:      destDir,
		Enabled:  enabled2,
		Config:   cfg2,
	}
	pm.mu.Unlock()

	gologger.Info().Msgf("plugin: installed %s v%s from ZIP", manifest.Name, manifest.Version)
	return manifest.Name, nil
}

func extractZip(zipPath, destDir string) error {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		target := filepath.Join(destDir, f.Name)

		// Prevent zip slip
		if !strings.HasPrefix(filepath.Clean(target), filepath.Clean(destDir)+string(os.PathSeparator)) {
			continue
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(target, f.Mode())
			continue
		}

		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			return err
		}

		out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, f.Mode())
		if err != nil {
			rc.Close()
			return err
		}

		_, err = io.Copy(out, rc)
		rc.Close()
		out.Close()
		if err != nil {
			return err
		}
	}
	return nil
}

func (pm *PluginManager) installFromLocal(srcPath string) (string, error) {
	absPath, err := filepath.Abs(srcPath)
	if err != nil {
		return "", fmt.Errorf("invalid path: %w", err)
	}

	manifest, err := loadManifest(absPath)
	if err != nil {
		return "", fmt.Errorf("invalid plugin: %w", err)
	}

	destDir := filepath.Join(pm.pluginsDir, manifest.Name)
	if _, err := os.Stat(destDir); err == nil {
		return "", fmt.Errorf("plugin %s already installed at %s", manifest.Name, destDir)
	}

	if err := copyDir(absPath, destDir); err != nil {
		return "", fmt.Errorf("cannot copy plugin: %w", err)
	}

	cfg3 := loadPluginConfig(destDir)
	enabled3 := shouldAutoEnable(manifest, cfg3)
	if !enabled3 {
		os.WriteFile(filepath.Join(destDir, ".disabled"), []byte("disabled"), 0644)
	}
	pm.mu.Lock()
	pm.plugins[manifest.Name] = &Plugin{
		Manifest: manifest,
		Dir:      destDir,
		Enabled:  enabled3,
		Config:   cfg3,
	}
	pm.mu.Unlock()

	gologger.Info().Msgf("plugin: installed %s v%s from local path", manifest.Name, manifest.Version)
	return manifest.Name, nil
}

// Uninstall removes a plugin
func (pm *PluginManager) Uninstall(name string) error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	p, ok := pm.plugins[name]
	if !ok {
		return fmt.Errorf("plugin %s not found", name)
	}

	if err := os.RemoveAll(p.Dir); err != nil {
		return fmt.Errorf("cannot remove plugin: %w", err)
	}

	delete(pm.plugins, name)
	gologger.Info().Msgf("plugin: uninstalled %s", name)
	return nil
}

// Enable enables a plugin by removing .disabled marker
func (pm *PluginManager) Enable(name string) error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	p, ok := pm.plugins[name]
	if !ok {
		return fmt.Errorf("plugin %s not found", name)
	}

	if !shouldAutoEnable(p.Manifest, p.Config) {
		var missing []string
		for key, field := range p.Manifest.ConfigSchema {
			if !field.Required {
				continue
			}
			val, has := p.Config[key]
			if !has || val == nil || val == "" {
				missing = append(missing, key)
			}
		}
		return fmt.Errorf("plugin %s has unconfigured required fields: %s", name, strings.Join(missing, ", "))
	}

	os.Remove(filepath.Join(p.Dir, ".disabled"))
	p.Enabled = true
	gologger.Info().Msgf("plugin: enabled %s", name)
	return nil
}

// Disable disables a plugin by creating .disabled marker
func (pm *PluginManager) Disable(name string) error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	p, ok := pm.plugins[name]
	if !ok {
		return fmt.Errorf("plugin %s not found", name)
	}

	if err := os.WriteFile(filepath.Join(p.Dir, ".disabled"), []byte("disabled"), 0644); err != nil {
		return fmt.Errorf("cannot disable plugin: %w", err)
	}

	p.Enabled = false
	gologger.Info().Msgf("plugin: disabled %s", name)
	return nil
}

// Update pulls latest changes for a git-based plugin
func (pm *PluginManager) Update(name string) (string, error) {
	pm.mu.Lock()
	p, ok := pm.plugins[name]
	pm.mu.Unlock()

	if !ok {
		return "", fmt.Errorf("plugin %s not found", name)
	}

	// Check if it's a git repo
	gitDir := filepath.Join(p.Dir, ".git")
	if _, err := os.Stat(gitDir); err != nil {
		// Not a git repo — try re-download from registry
		return pm.updateFromRegistry(name)
	}

	cmd := exec.Command("git", "-C", p.Dir, "pull", "--ff-only")
	out, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("git pull failed: %s\n%s", err, string(out))
	}

	// Reload manifest
	manifest, err := loadManifest(p.Dir)
	if err != nil {
		return "", fmt.Errorf("manifest reload failed: %w", err)
	}

	pm.mu.Lock()
	p.Manifest = manifest
	p.Config = loadPluginConfig(p.Dir)
	pm.mu.Unlock()

	gologger.Info().Msgf("plugin: updated %s to v%s", name, manifest.Version)
	return manifest.Version, nil
}

// updateFromRegistry fetches registry, finds the plugin URL, and reinstalls
func (pm *PluginManager) updateFromRegistry(name string) (string, error) {
	index, err := FetchRegistry("")
	if err != nil {
		return "", fmt.Errorf("cannot fetch registry for update: %w", err)
	}

	var downloadURL string
	for _, rp := range index.Plugins {
		if rp.Name == name {
			downloadURL = rp.URL
			break
		}
	}
	if downloadURL == "" {
		return "", fmt.Errorf("plugin %s not found in registry, cannot update (not a git repo)", name)
	}

	return pm.ReinstallFromURL(name, downloadURL)
}

// ReinstallFromURL removes old plugin and reinstalls from URL (preserves config)
func (pm *PluginManager) ReinstallFromURL(name, url string) (string, error) {
	pm.mu.Lock()
	oldPlugin, ok := pm.plugins[name]
	pm.mu.Unlock()

	// Preserve config and enabled state
	var oldConfig map[string]interface{}
	wasEnabled := true
	if ok {
		oldConfig = oldPlugin.Config
		wasEnabled = oldPlugin.Enabled
		// Remove old
		if err := os.RemoveAll(oldPlugin.Dir); err != nil {
			return "", fmt.Errorf("cannot remove old plugin: %w", err)
		}
		pm.mu.Lock()
		delete(pm.plugins, name)
		pm.mu.Unlock()
	}

	// Install fresh
	installedName, err := pm.Install(url)
	if err != nil {
		return "", fmt.Errorf("reinstall failed: %w", err)
	}

	// Restore config and enabled state
	pm.mu.Lock()
	if p, ok := pm.plugins[installedName]; ok {
		if oldConfig != nil {
			p.Config = oldConfig
			// Persist config
			data, _ := json.MarshalIndent(oldConfig, "", "  ")
			_ = os.WriteFile(filepath.Join(p.Dir, "config.json"), data, 0644)
		}
		if !wasEnabled {
			p.Enabled = false
			_ = os.WriteFile(filepath.Join(p.Dir, ".disabled"), []byte("disabled"), 0644)
		}
	}
	pm.mu.Unlock()

	gologger.Info().Msgf("plugin: reinstalled %s from registry", installedName)
	return installedName, nil
}

// SaveConfig saves plugin config to config.json in plugin dir
func (pm *PluginManager) SaveConfig(name string, config map[string]interface{}) error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	p, ok := pm.plugins[name]
	if !ok {
		return fmt.Errorf("plugin %s not found", name)
	}

	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("cannot marshal config: %w", err)
	}

	if err := os.WriteFile(filepath.Join(p.Dir, "config.json"), data, 0644); err != nil {
		return fmt.Errorf("cannot write config: %w", err)
	}

	p.Config = config
	return nil
}

// --- helpers ---

func copyDir(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)

		if info.IsDir() {
			return os.MkdirAll(target, info.Mode())
		}

		return copyFile(path, target)
	})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
