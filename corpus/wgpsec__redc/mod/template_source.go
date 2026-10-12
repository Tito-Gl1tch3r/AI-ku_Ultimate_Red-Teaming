package mod

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"red-cloud/utils"
)

// TemplateSourceType identifies where a template is loaded from.
type TemplateSourceType string

const (
	TemplateSourceRemote TemplateSourceType = "remote"
	TemplateSourceLocal  TemplateSourceType = "local"
)

// TemplateSource describes a configured template source.
type TemplateSource struct {
	ID            string             `json:"id"`
	Name          string             `json:"name"`
	Type          TemplateSourceType `json:"type"`
	Path          string             `json:"path,omitempty"`
	URL           string             `json:"url,omitempty"`
	Priority      int                `json:"priority"`
	Enabled       bool               `json:"enabled"`
	ReadOnly      bool               `json:"read_only"`
	LastScanAt    string             `json:"last_scan_at,omitempty"`
	LastError     string             `json:"last_error,omitempty"`
	TemplateCount int                `json:"template_count"`
}

// ResolvedTemplate ties template metadata to the source that provides it.
type ResolvedTemplate struct {
	Template *RedcTmpl
	Source   TemplateSource
}

// TemplateInstallation records which source produced a managed template.
type TemplateInstallation struct {
	SourceID    string `json:"source_id"`
	Version     string `json:"version"`
	InstalledAt string `json:"installed_at"`
}

// TemplateConflict describes sources shadowed by priority resolution.
type TemplateConflict struct {
	TemplateName    string           `json:"template_name"`
	EffectiveSource TemplateSource   `json:"effective_source"`
	ShadowedSources []TemplateSource `json:"shadowed_sources"`
}

// TemplateSourceManager manages local template sources.
type TemplateSourceManager struct {
	mu                sync.RWMutex
	templateDir       string
	sourcesPath       string
	installationsPath string
	sources           []TemplateSource
	installations     map[string]TemplateInstallation
}

// NewTemplateSourceManager creates a source manager. sourcesPath is reserved
// for persistence and is not read until the manager is asked to load sources.
func NewTemplateSourceManager(templateDir, sourcesPath string) *TemplateSourceManager {
	return &TemplateSourceManager{
		templateDir:       templateDir,
		sourcesPath:       sourcesPath,
		installationsPath: filepath.Join(filepath.Dir(sourcesPath), "template-installations.json"),
		installations:     make(map[string]TemplateInstallation),
	}
}

// LoadConfiguredTemplateSourceManager loads sources from the active redc
// configuration so GUI, CLI, and MCP share identical resolution behavior.
func LoadConfiguredTemplateSourceManager() (*TemplateSourceManager, error) {
	if strings.TrimSpace(RedcPath) == "" {
		return nil, fmt.Errorf("redc path is not initialized")
	}
	manager := NewTemplateSourceManager(
		TemplateDir,
		filepath.Join(RedcPath, "template-sources.json"),
	)
	if err := manager.Load(); err != nil {
		return nil, err
	}
	return manager, nil
}

// AddLocalSource registers a local directory as a template source.
func (m *TemplateSourceManager) AddLocalSource(name, path string) (TemplateSource, error) {
	if strings.TrimSpace(name) == "" {
		return TemplateSource{}, fmt.Errorf("template source name cannot be empty")
	}

	canonicalPath, err := canonicalDirectory(path)
	if err != nil {
		return TemplateSource{}, err
	}

	source := TemplateSource{
		ID:       localSourceID(canonicalPath),
		Name:     strings.TrimSpace(name),
		Type:     TemplateSourceLocal,
		Path:     canonicalPath,
		Priority: 100,
		Enabled:  true,
		ReadOnly: true,
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, existing := range m.sources {
		if existing.ID == source.ID {
			return existing, nil
		}
	}
	m.sources = append(m.sources, source)
	return source, nil
}

// UpdateSource updates a configured source while preserving its identity.
func (m *TemplateSourceManager) UpdateSource(updated TemplateSource) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	for i, source := range m.sources {
		if source.ID != updated.ID {
			continue
		}
		if updated.Type != TemplateSourceLocal {
			return fmt.Errorf("template source type %q is not supported", updated.Type)
		}
		if updated.Path != source.Path {
			canonicalPath, err := canonicalDirectory(updated.Path)
			if err != nil {
				return err
			}
			updated.Path = canonicalPath
		}
		updated.Name = strings.TrimSpace(updated.Name)
		if updated.Name == "" {
			return fmt.Errorf("template source name cannot be empty")
		}
		updated.ReadOnly = true
		m.sources[i] = updated
		return nil
	}
	return fmt.Errorf("template source not found: %s", updated.ID)
}

// RemoveSource removes a configured source. It never deletes the source's
// directory or already-installed managed templates.
func (m *TemplateSourceManager) RemoveSource(sourceID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	for i, source := range m.sources {
		if source.ID != sourceID {
			continue
		}
		m.sources = append(m.sources[:i], m.sources[i+1:]...)
		return nil
	}
	return fmt.Errorf("template source not found: %s", sourceID)
}

// ListMergedTemplates scans enabled sources and returns one effective template
// per template ID. Higher priority sources win conflicts.
func (m *TemplateSourceManager) ListMergedTemplates() ([]ResolvedTemplate, error) {
	m.mu.RLock()
	sources := append([]TemplateSource(nil), m.sources...)
	m.mu.RUnlock()
	byName := make(map[string]ResolvedTemplate)
	for _, source := range sources {
		if !source.Enabled {
			continue
		}
		templates, err := scanLocalTemplateSource(source)
		if err != nil {
			m.updateSourceStatus(source.ID, 0, err)
			continue
		}
		m.updateSourceStatus(source.ID, len(templates), nil)
		for _, candidate := range templates {
			current, exists := byName[candidate.Template.Name]
			if !exists || sourcePrecedes(candidate.Source, current.Source) {
				byName[candidate.Template.Name] = candidate
			}
		}
	}

	merged := make([]ResolvedTemplate, 0, len(byName))
	for _, template := range byName {
		merged = append(merged, template)
	}
	sort.Slice(merged, func(i, j int) bool {
		return merged[i].Template.Name < merged[j].Template.Name
	})
	return merged, nil
}

// ResolveTemplate returns the effective template for a name after source
// priority has been applied.
func (m *TemplateSourceManager) ResolveTemplate(name string) (*ResolvedTemplate, error) {
	merged, err := m.ListMergedTemplates()
	if err != nil {
		return nil, err
	}
	for i := range merged {
		if merged[i].Template.Name == name {
			return &merged[i], nil
		}
	}
	return nil, fmt.Errorf("template not found: %s", name)
}

// ListTemplateConflicts returns enabled local templates provided by more than
// one source, ordered by template name.
func (m *TemplateSourceManager) ListTemplateConflicts() ([]TemplateConflict, error) {
	m.mu.RLock()
	sources := append([]TemplateSource(nil), m.sources...)
	m.mu.RUnlock()
	providers := make(map[string][]TemplateSource)
	for _, source := range sources {
		if !source.Enabled {
			continue
		}
		templates, err := scanLocalTemplateSource(source)
		if err != nil {
			m.updateSourceStatus(source.ID, 0, err)
			continue
		}
		m.updateSourceStatus(source.ID, len(templates), nil)
		for _, template := range templates {
			providers[template.Template.Name] = append(providers[template.Template.Name], source)
		}
	}

	conflicts := make([]TemplateConflict, 0)
	for name, candidates := range providers {
		if len(candidates) < 2 {
			continue
		}
		sort.Slice(candidates, func(i, j int) bool {
			return sourcePrecedes(candidates[i], candidates[j])
		})
		conflicts = append(conflicts, TemplateConflict{
			TemplateName:    name,
			EffectiveSource: candidates[0],
			ShadowedSources: append([]TemplateSource(nil), candidates[1:]...),
		})
	}
	sort.Slice(conflicts, func(i, j int) bool {
		return conflicts[i].TemplateName < conflicts[j].TemplateName
	})
	return conflicts, nil
}

// ScanSource scans a configured source and returns templates with source data.
func (m *TemplateSourceManager) ScanSource(sourceID string) ([]ResolvedTemplate, error) {
	m.mu.RLock()
	sources := append([]TemplateSource(nil), m.sources...)
	m.mu.RUnlock()
	for _, source := range sources {
		if source.ID != sourceID {
			continue
		}
		if !source.Enabled {
			return []ResolvedTemplate{}, nil
		}
		if source.Type != TemplateSourceLocal {
			return nil, fmt.Errorf("template source type %q is not supported", source.Type)
		}
		templates, err := scanLocalTemplateSource(source)
		if err != nil {
			m.updateSourceStatus(source.ID, 0, err)
			return nil, err
		}
		m.updateSourceStatus(source.ID, len(templates), nil)
		return templates, nil
	}
	return nil, fmt.Errorf("template source not found: %s", sourceID)
}

func (m *TemplateSourceManager) updateSourceStatus(sourceID string, templateCount int, scanErr error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for i := range m.sources {
		if m.sources[i].ID != sourceID {
			continue
		}
		m.sources[i].TemplateCount = templateCount
		m.sources[i].LastScanAt = time.Now().UTC().Format(time.RFC3339)
		m.sources[i].LastError = ""
		if scanErr != nil {
			m.sources[i].LastError = scanErr.Error()
		}
		return
	}
}

// ListSources returns a snapshot of configured template sources.
func (m *TemplateSourceManager) ListSources() []TemplateSource {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return append([]TemplateSource(nil), m.sources...)
}

// InstallTemplate copies an effective source template into the managed
// template directory used by deployments. The source itself remains read-only.
func (m *TemplateSourceManager) InstallTemplate(name string, force bool) (string, error) {
	name = filepath.ToSlash(strings.TrimSpace(name))
	if name == "" {
		return "", fmt.Errorf("template name cannot be empty")
	}
	selected, err := m.resolveTemplateForInstall(name)
	if err != nil {
		return "", err
	}
	if filepath.IsAbs(filepath.FromSlash(name)) || name == "." || strings.HasPrefix(name, "../") || strings.Contains(name, "/../") {
		return "", fmt.Errorf("invalid template name: %s", name)
	}
	target := filepath.Join(m.templateDir, filepath.FromSlash(name))
	base, err := filepath.Abs(m.templateDir)
	if err != nil {
		return "", fmt.Errorf("resolve managed template directory: %w", err)
	}
	absTarget, err := filepath.Abs(target)
	if err != nil || (absTarget != base && !strings.HasPrefix(absTarget, base+string(os.PathSeparator))) {
		return "", fmt.Errorf("invalid template name: %s", name)
	}
	if _, err := os.Stat(target); err == nil && !force {
		return "", fmt.Errorf("template already installed: %s", name)
	}
	parent := filepath.Dir(target)
	if err := os.MkdirAll(parent, 0755); err != nil {
		return "", fmt.Errorf("create managed template directory: %w", err)
	}
	tmp, err := os.MkdirTemp(parent, ".template-install-*")
	if err != nil {
		return "", fmt.Errorf("create managed template temp directory: %w", err)
	}
	defer os.RemoveAll(tmp)
	if err := validateTemplateTree(selected.Source.Path, selected.Template.Path); err != nil {
		return "", err
	}
	if err := utils.Dir(selected.Template.Path, tmp); err != nil {
		return "", fmt.Errorf("copy template from source: %w", err)
	}
	if force {
		if err := os.RemoveAll(target); err != nil {
			return "", fmt.Errorf("remove existing managed template: %w", err)
		}
	}
	if err := os.Rename(tmp, target); err != nil {
		return "", fmt.Errorf("install template: %w", err)
	}
	m.mu.Lock()
	m.installations[name] = TemplateInstallation{
		SourceID:    selected.Source.ID,
		Version:     selected.Template.Version,
		InstalledAt: time.Now().UTC().Format(time.RFC3339),
	}
	m.mu.Unlock()
	if err := m.saveInstallations(); err != nil {
		return "", err
	}
	return target, nil
}

func (m *TemplateSourceManager) resolveTemplateForInstall(name string) (*ResolvedTemplate, error) {
	m.mu.RLock()
	installation, installed := m.installations[name]
	sources := append([]TemplateSource(nil), m.sources...)
	m.mu.RUnlock()
	if !installed || installation.SourceID == "" {
		return m.ResolveTemplate(name)
	}

	for _, source := range sources {
		if source.ID != installation.SourceID {
			continue
		}
		if !source.Enabled {
			return nil, fmt.Errorf("original template source is disabled: %s", source.Name)
		}
		templates, err := scanLocalTemplateSource(source)
		if err != nil {
			m.updateSourceStatus(source.ID, 0, err)
			return nil, fmt.Errorf("original template source is unavailable: %w", err)
		}
		m.updateSourceStatus(source.ID, len(templates), nil)
		for i := range templates {
			if templates[i].Template.Name == name {
				return &templates[i], nil
			}
		}
		return nil, fmt.Errorf("template %q no longer exists in original source %q", name, source.Name)
	}
	return nil, fmt.Errorf("original template source not found: %s", installation.SourceID)
}

// Save persists configured template sources as a private JSON file.
func (m *TemplateSourceManager) Save() error {
	m.mu.RLock()
	sources := append([]TemplateSource(nil), m.sources...)
	m.mu.RUnlock()

	if strings.TrimSpace(m.sourcesPath) == "" {
		return fmt.Errorf("template source persistence path cannot be empty")
	}
	data, err := json.MarshalIndent(sources, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal template sources: %w", err)
	}
	data = append(data, '\n')
	if err := os.MkdirAll(filepath.Dir(m.sourcesPath), 0700); err != nil {
		return fmt.Errorf("create template source config directory: %w", err)
	}
	tmp, err := os.CreateTemp(filepath.Dir(m.sourcesPath), ".template-sources-*.tmp")
	if err != nil {
		return fmt.Errorf("create template source temp file: %w", err)
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	if err := tmp.Chmod(0600); err != nil {
		tmp.Close()
		return fmt.Errorf("set template source config permissions: %w", err)
	}
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return fmt.Errorf("write template source config: %w", err)
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		return fmt.Errorf("sync template source config: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close template source config: %w", err)
	}
	if err := os.Rename(tmpPath, m.sourcesPath); err != nil {
		return fmt.Errorf("replace template source config: %w", err)
	}
	return nil
}

// Load restores configured template sources. A missing file means no sources.
// Paths are intentionally not resolved here so an unavailable source can be
// repaired later from the GUI without losing its configuration.
func (m *TemplateSourceManager) Load() error {
	if strings.TrimSpace(m.sourcesPath) == "" {
		return fmt.Errorf("template source persistence path cannot be empty")
	}
	data, err := os.ReadFile(m.sourcesPath)
	if os.IsNotExist(err) {
		m.mu.Lock()
		m.sources = nil
		m.mu.Unlock()
		return m.loadInstallations()
	}
	if err != nil {
		return fmt.Errorf("read template source config: %w", err)
	}
	var sources []TemplateSource
	if err := json.Unmarshal(data, &sources); err != nil {
		return fmt.Errorf("parse template source config: %w", err)
	}
	for i := range sources {
		if sources[i].Type == "" {
			sources[i].Type = TemplateSourceLocal
		}
		if sources[i].Type != TemplateSourceLocal {
			return fmt.Errorf("template source type %q is not supported", sources[i].Type)
		}
		if sources[i].ID == "" || sources[i].Name == "" || sources[i].Path == "" {
			return fmt.Errorf("template source config contains an incomplete source")
		}
	}
	m.mu.Lock()
	m.sources = sources
	m.mu.Unlock()
	return m.loadInstallations()
}

// ListInstallations returns a snapshot of managed template provenance.
func (m *TemplateSourceManager) ListInstallations() map[string]TemplateInstallation {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make(map[string]TemplateInstallation, len(m.installations))
	for name, installation := range m.installations {
		result[name] = installation
	}
	return result
}

func (m *TemplateSourceManager) saveInstallations() error {
	m.mu.RLock()
	data, err := json.MarshalIndent(m.installations, "", "  ")
	m.mu.RUnlock()
	if err != nil {
		return fmt.Errorf("marshal template installations: %w", err)
	}
	data = append(data, '\n')
	if err := os.MkdirAll(filepath.Dir(m.installationsPath), 0700); err != nil {
		return fmt.Errorf("create template installation config directory: %w", err)
	}
	tmp, err := os.CreateTemp(filepath.Dir(m.installationsPath), ".template-installations-*.tmp")
	if err != nil {
		return fmt.Errorf("create template installations temp file: %w", err)
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	if err := tmp.Chmod(0600); err != nil {
		tmp.Close()
		return fmt.Errorf("set template installations permissions: %w", err)
	}
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		return fmt.Errorf("write template installations: %w", err)
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		return fmt.Errorf("sync template installations: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close template installations: %w", err)
	}
	if err := os.Rename(tmpPath, m.installationsPath); err != nil {
		return fmt.Errorf("replace template installations: %w", err)
	}
	return nil
}

func (m *TemplateSourceManager) loadInstallations() error {
	data, err := os.ReadFile(m.installationsPath)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("read template installations: %w", err)
	}
	var installations map[string]TemplateInstallation
	if err := json.Unmarshal(data, &installations); err != nil {
		return fmt.Errorf("parse template installations: %w", err)
	}
	m.mu.Lock()
	if installations == nil {
		installations = make(map[string]TemplateInstallation)
	}
	m.installations = installations
	m.mu.Unlock()
	return nil
}

func scanLocalTemplateSource(source TemplateSource) ([]ResolvedTemplate, error) {
	if _, err := os.Stat(source.Path); err != nil {
		return nil, fmt.Errorf("template source %q is unavailable: %w", source.Name, err)
	}
	dirs, err := ScanTemplateDirs(source.Path, MaxTfDepth)
	if err != nil {
		return nil, fmt.Errorf("scan template source %q: %w", source.Name, err)
	}

	result := make([]ResolvedTemplate, 0, len(dirs))
	for _, dir := range dirs {
		template, err := readTemplateMetaAt(source.Path, dir)
		if err != nil {
			continue
		}
		result = append(result, ResolvedTemplate{Template: template, Source: source})
	}
	return result, nil
}

func sourcePrecedes(candidate, current TemplateSource) bool {
	if candidate.Priority != current.Priority {
		return candidate.Priority > current.Priority
	}
	return candidate.ID < current.ID
}

func readTemplateMetaAt(rootDir, dirPath string) (*RedcTmpl, error) {
	casePath := filepath.Join(dirPath, TmplCaseFile)
	within, err := resolvedPathWithin(rootDir, casePath)
	if err != nil || !within {
		return nil, fmt.Errorf("template metadata escapes source root: %s", casePath)
	}
	data, err := os.ReadFile(casePath)
	if err != nil {
		return nil, err
	}

	template := &RedcTmpl{}
	if err := json.Unmarshal(data, template); err != nil {
		return nil, err
	}
	relPath, err := filepath.Rel(rootDir, dirPath)
	if err != nil {
		return nil, err
	}
	template.Name = filepath.ToSlash(relPath)
	template.Path = dirPath
	return template, nil
}

func validateTemplateTree(sourceRoot, templatePath string) error {
	return filepath.WalkDir(templatePath, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.Type()&os.ModeSymlink == 0 {
			return nil
		}
		within, err := resolvedPathWithin(sourceRoot, path)
		if err != nil {
			return fmt.Errorf("resolve template symlink %q: %w", path, err)
		}
		if !within {
			return fmt.Errorf("template symlink escapes source root: %s", path)
		}
		return nil
	})
}

func resolvedPathWithin(root, path string) (bool, error) {
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return false, err
	}
	resolvedPath, err := filepath.EvalSymlinks(path)
	if err != nil {
		return false, err
	}
	rel, err := filepath.Rel(resolvedRoot, resolvedPath)
	if err != nil {
		return false, err
	}
	return rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator)), nil
}

func canonicalDirectory(path string) (string, error) {
	if strings.TrimSpace(path) == "" {
		return "", fmt.Errorf("template source path cannot be empty")
	}
	absPath, err := filepath.Abs(path)
	if err != nil {
		return "", fmt.Errorf("resolve template source path: %w", err)
	}
	resolvedPath, err := filepath.EvalSymlinks(absPath)
	if err != nil {
		return "", fmt.Errorf("resolve template source path: %w", err)
	}
	info, err := os.Stat(resolvedPath)
	if err != nil {
		return "", fmt.Errorf("stat template source path: %w", err)
	}
	if !info.IsDir() {
		return "", fmt.Errorf("template source path is not a directory: %s", resolvedPath)
	}
	return filepath.Clean(resolvedPath), nil
}

func localSourceID(path string) string {
	digest := sha256.Sum256([]byte(path))
	return "local-" + hex.EncodeToString(digest[:])[:16]
}
