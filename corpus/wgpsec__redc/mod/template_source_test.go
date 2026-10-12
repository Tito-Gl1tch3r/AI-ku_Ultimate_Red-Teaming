package mod

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestTemplateSourceManagerScansLocalTemplates(t *testing.T) {
	root := t.TempDir()
	templateDir := filepath.Join(root, "private-templates")
	sceneDir := filepath.Join(templateDir, "aliyun", "vbdc")
	if err := os.MkdirAll(sceneDir, 0755); err != nil {
		t.Fatal(err)
	}
	caseJSON := `{
  "name": "vbdc",
  "user": "private",
  "version": "1.0.0",
  "description": "private vbdc",
  "description_en": "private vbdc",
  "template": "preset",
  "arch": "x86_64",
  "tags": ["private"]
}`
	if err := os.WriteFile(filepath.Join(sceneDir, TmplCaseFile), []byte(caseJSON), 0644); err != nil {
		t.Fatal(err)
	}

	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	source, err := manager.AddLocalSource("Private", templateDir)
	if err != nil {
		t.Fatalf("AddLocalSource() error = %v", err)
	}

	templates, err := manager.ScanSource(source.ID)
	if err != nil {
		t.Fatalf("ScanSource() error = %v", err)
	}
	if len(templates) != 1 {
		t.Fatalf("ScanSource() returned %d templates, want 1", len(templates))
	}
	if got, want := templates[0].Template.Name, "aliyun/vbdc"; got != want {
		t.Fatalf("template name = %q, want %q", got, want)
	}
	if got, want := templates[0].Source.ID, source.ID; got != want {
		t.Fatalf("source ID = %q, want %q", got, want)
	}
}

func TestTemplateSourceManagerPrefersHigherPrioritySource(t *testing.T) {
	root := t.TempDir()
	firstDir := filepath.Join(root, "first", "aliyun", "vbdc")
	secondDir := filepath.Join(root, "second", "aliyun", "vbdc")
	for _, dir := range []string{firstDir, secondDir} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			t.Fatal(err)
		}
	}
	writeCase := func(dir, description string) {
		t.Helper()
		data := []byte(`{"name":"vbdc","user":"private","version":"1.0.0","description":"` + description + `","description_en":"` + description + `","template":"preset","arch":"x86_64","tags":["private"]}`)
		if err := os.WriteFile(filepath.Join(dir, TmplCaseFile), data, 0644); err != nil {
			t.Fatal(err)
		}
	}
	writeCase(firstDir, "low priority")
	writeCase(secondDir, "high priority")

	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	first, err := manager.AddLocalSource("First", filepath.Join(root, "first"))
	if err != nil {
		t.Fatal(err)
	}
	second, err := manager.AddLocalSource("Second", filepath.Join(root, "second"))
	if err != nil {
		t.Fatal(err)
	}
	second.Priority = first.Priority + 1
	if err := manager.UpdateSource(second); err != nil {
		t.Fatalf("UpdateSource() error = %v", err)
	}

	merged, err := manager.ListMergedTemplates()
	if err != nil {
		t.Fatalf("ListMergedTemplates() error = %v", err)
	}
	if len(merged) != 1 {
		t.Fatalf("ListMergedTemplates() returned %d templates, want 1", len(merged))
	}
	if got, want := merged[0].Template.Description, "high priority"; got != want {
		t.Fatalf("selected description = %q, want %q", got, want)
	}
	conflicts, err := manager.ListTemplateConflicts()
	if err != nil {
		t.Fatalf("ListTemplateConflicts() error = %v", err)
	}
	if len(conflicts) != 1 || conflicts[0].TemplateName != "aliyun/vbdc" {
		t.Fatalf("conflicts = %#v, want aliyun/vbdc conflict", conflicts)
	}
	if conflicts[0].EffectiveSource.ID != second.ID || len(conflicts[0].ShadowedSources) != 1 {
		t.Fatalf("conflict resolution = %#v, want Second over one source", conflicts[0])
	}
}

func TestTemplateSourceManagerPersistsLocalSources(t *testing.T) {
	root := t.TempDir()
	templateDir := filepath.Join(root, "private-templates")
	if err := os.MkdirAll(templateDir, 0755); err != nil {
		t.Fatal(err)
	}
	sourcesPath := filepath.Join(root, "template-sources.json")

	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), sourcesPath)
	source, err := manager.AddLocalSource("Private", templateDir)
	if err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatalf("Save() error = %v", err)
	}
	if info, err := os.Stat(sourcesPath); err != nil {
		t.Fatal(err)
	} else if got, want := info.Mode().Perm(), os.FileMode(0600); got != want {
		t.Fatalf("source config mode = %04o, want %04o", got, want)
	}

	reloaded := NewTemplateSourceManager(filepath.Join(root, "managed"), sourcesPath)
	if err := reloaded.Load(); err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	sources := reloaded.ListSources()
	if len(sources) != 1 {
		t.Fatalf("ListSources() returned %d sources, want 1", len(sources))
	}
	if got, want := sources[0].ID, source.ID; got != want {
		t.Fatalf("source ID = %q, want %q", got, want)
	}
	wantPath, err := filepath.EvalSymlinks(templateDir)
	if err != nil {
		t.Fatal(err)
	}
	if got, want := sources[0].Path, wantPath; got != want {
		t.Fatalf("source path = %q, want %q", got, want)
	}
}

func TestTemplateSourceManagerSkipsUnavailableSource(t *testing.T) {
	root := t.TempDir()
	availableDir := filepath.Join(root, "available", "aliyun", "vbdc")
	if err := os.MkdirAll(availableDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(availableDir, TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	missingCreate := filepath.Join(root, "missing-create")
	if err := os.MkdirAll(missingCreate, 0755); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	if _, err := manager.AddLocalSource("Available", filepath.Join(root, "available")); err != nil {
		t.Fatal(err)
	}
	missing, err := manager.AddLocalSource("Missing", missingCreate)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.RemoveAll(missing.Path); err != nil {
		t.Fatal(err)
	}

	merged, err := manager.ListMergedTemplates()
	if err != nil {
		t.Fatalf("ListMergedTemplates() error = %v", err)
	}
	if len(merged) != 1 || merged[0].Template.Name != "aliyun/vbdc" {
		t.Fatalf("merged templates = %#v, want available template", merged)
	}
	sources := manager.ListSources()
	for _, source := range sources {
		if source.ID == missing.ID && source.LastError == "" {
			t.Fatal("unavailable source should expose its last error")
		}
	}
	missing.Enabled = false
	missing.Name = "Missing disabled"
	if err := manager.UpdateSource(missing); err != nil {
		t.Fatalf("UpdateSource() should allow disabling unavailable source: %v", err)
	}
}

func TestTemplateSourceManagerDisablesSource(t *testing.T) {
	root := t.TempDir()
	templatePath := filepath.Join(root, "templates", "aliyun", "vbdc")
	if err := os.MkdirAll(templatePath, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(templatePath, TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	source, err := manager.AddLocalSource("Private", filepath.Join(root, "templates"))
	if err != nil {
		t.Fatal(err)
	}
	source.Enabled = false
	if err := manager.UpdateSource(source); err != nil {
		t.Fatal(err)
	}
	merged, err := manager.ListMergedTemplates()
	if err != nil {
		t.Fatal(err)
	}
	if len(merged) != 0 {
		t.Fatalf("merged templates = %d, want 0 for disabled source", len(merged))
	}
}

func TestTemplateSourceManagerInstallsMergedTemplate(t *testing.T) {
	root := t.TempDir()
	sourceTemplate := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sourceTemplate, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sourceTemplate, TmplCaseFile), []byte(`{"name":"vbdc","version":"2.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sourceTemplate, "main.tf"), []byte("resource \"test\" \"vbdc\" {}"), 0644); err != nil {
		t.Fatal(err)
	}
	managed := filepath.Join(root, "managed")
	manager := NewTemplateSourceManager(managed, filepath.Join(root, "sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}

	installedPath, err := manager.InstallTemplate("aliyun/vbdc", false)
	if err != nil {
		t.Fatalf("InstallTemplate() error = %v", err)
	}
	if got, want := installedPath, filepath.Join(managed, "aliyun", "vbdc"); got != want {
		t.Fatalf("installed path = %q, want %q", got, want)
	}
	if _, err := os.Stat(filepath.Join(installedPath, "main.tf")); err != nil {
		t.Fatalf("installed template file missing: %v", err)
	}
	installations := manager.ListInstallations()
	installation, ok := installations["aliyun/vbdc"]
	if !ok {
		t.Fatal("template installation provenance was not recorded")
	}
	if got, want := installation.SourceID, manager.ListSources()[0].ID; got != want {
		t.Fatalf("installation source ID = %q, want %q", got, want)
	}
	installationsPath := filepath.Join(root, "template-installations.json")
	if info, err := os.Stat(installationsPath); err != nil {
		t.Fatal(err)
	} else if got, want := info.Mode().Perm(), os.FileMode(0600); got != want {
		t.Fatalf("installation config mode = %04o, want %04o", got, want)
	}
	reloaded := NewTemplateSourceManager(managed, filepath.Join(root, "sources.json"))
	if err := reloaded.Load(); err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if _, ok := reloaded.ListInstallations()["aliyun/vbdc"]; !ok {
		t.Fatal("installation provenance was not restored")
	}
}

func TestTemplateSourceManagerRemovesSource(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "templates")
	if err := os.MkdirAll(path, 0755); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	source, err := manager.AddLocalSource("Private", path)
	if err != nil {
		t.Fatal(err)
	}
	if err := manager.RemoveSource(source.ID); err != nil {
		t.Fatalf("RemoveSource() error = %v", err)
	}
	if got := len(manager.ListSources()); got != 0 {
		t.Fatalf("ListSources() returned %d sources after remove, want 0", got)
	}
}

func TestPullInstallsFromConfiguredLocalSource(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := RedcPath, TemplateDir
	RedcPath, TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		RedcPath, TemplateDir = oldRedcPath, oldTemplateDir
	})

	sourceTemplate := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sourceTemplate, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sourceTemplate, TmplCaseFile), []byte(`{"name":"vbdc","version":"2.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(TemplateDir, filepath.Join(RedcPath, "template-sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatal(err)
	}

	err := Pull(context.Background(), "aliyun/vbdc", PullOptions{
		RegistryURL: "http://127.0.0.1:1",
		Timeout:     100 * time.Millisecond,
	})
	if err != nil {
		t.Fatalf("Pull() error = %v", err)
	}
	if _, err := os.Stat(filepath.Join(TemplateDir, "aliyun", "vbdc", TmplCaseFile)); err != nil {
		t.Fatalf("configured local source was not installed: %v", err)
	}
}

func TestSearchReturnsConfiguredLocalSourceWhenRemoteUnavailable(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := RedcPath, TemplateDir
	RedcPath, TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		RedcPath, TemplateDir = oldRedcPath, oldTemplateDir
	})

	sceneDir := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sceneDir, 0755); err != nil {
		t.Fatal(err)
	}
	caseJSON := `{"name":"vbdc","version":"2.0.0","user":"private","description":"private VBDC"}`
	if err := os.WriteFile(filepath.Join(sceneDir, TmplCaseFile), []byte(caseJSON), 0644); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(TemplateDir, filepath.Join(RedcPath, "template-sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatal(err)
	}

	results, err := Search(context.Background(), "vbdc", PullOptions{
		RegistryURL: "http://127.0.0.1:1",
		Timeout:     100 * time.Millisecond,
	})
	if err != nil {
		t.Fatalf("Search() error = %v", err)
	}
	if len(results) != 1 || results[0].Key != "aliyun/vbdc" {
		t.Fatalf("Search() results = %#v, want local aliyun/vbdc", results)
	}
	if got, want := results[0].SourceType, string(TemplateSourceLocal); got != want {
		t.Fatalf("search source type = %q, want %q", got, want)
	}
	if got, want := results[0].SourceName, "Private"; got != want {
		t.Fatalf("search source name = %q, want %q", got, want)
	}
}

func TestTemplateSourceManagerUpdatesFromOriginalSource(t *testing.T) {
	root := t.TempDir()
	writeVersion := func(sourceRoot, version string) {
		t.Helper()
		dir := filepath.Join(sourceRoot, "aliyun", "vbdc")
		if err := os.MkdirAll(dir, 0755); err != nil {
			t.Fatal(err)
		}
		data := []byte(`{"name":"vbdc","version":"` + version + `"}`)
		if err := os.WriteFile(filepath.Join(dir, TmplCaseFile), data, 0644); err != nil {
			t.Fatal(err)
		}
	}
	firstRoot := filepath.Join(root, "first")
	secondRoot := filepath.Join(root, "second")
	writeVersion(firstRoot, "1.0.0")
	managed := filepath.Join(root, "managed")
	manager := NewTemplateSourceManager(managed, filepath.Join(root, "template-sources.json"))
	first, err := manager.AddLocalSource("First", firstRoot)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := manager.InstallTemplate("aliyun/vbdc", false); err != nil {
		t.Fatal(err)
	}

	writeVersion(firstRoot, "2.0.0")
	writeVersion(secondRoot, "9.0.0")
	second, err := manager.AddLocalSource("Second", secondRoot)
	if err != nil {
		t.Fatal(err)
	}
	second.Priority = first.Priority + 10
	if err := manager.UpdateSource(second); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.InstallTemplate("aliyun/vbdc", true); err != nil {
		t.Fatalf("InstallTemplate() update error = %v", err)
	}

	caseData, err := os.ReadFile(filepath.Join(managed, "aliyun", "vbdc", TmplCaseFile))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(caseData), `"2.0.0"`) {
		t.Fatalf("updated case.json = %s, want original source version 2.0.0", caseData)
	}
	if got := manager.ListInstallations()["aliyun/vbdc"].SourceID; got != first.ID {
		t.Fatalf("installation source ID = %q, want original %q", got, first.ID)
	}
}

func TestTemplateSourceManagerRejectsSymlinkEscape(t *testing.T) {
	root := t.TempDir()
	sourceRoot := filepath.Join(root, "private")
	escapedTemplate := filepath.Join(sourceRoot, "aliyun", "escaped")
	if err := os.MkdirAll(escapedTemplate, 0755); err != nil {
		t.Fatal(err)
	}
	outsideCase := filepath.Join(root, "outside-case.json")
	if err := os.WriteFile(outsideCase, []byte(`{"name":"escaped","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outsideCase, filepath.Join(escapedTemplate, TmplCaseFile)); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(filepath.Join(root, "managed"), filepath.Join(root, "sources.json"))
	if _, err := manager.AddLocalSource("Private", sourceRoot); err != nil {
		t.Fatal(err)
	}
	templates, err := manager.ListMergedTemplates()
	if err != nil {
		t.Fatal(err)
	}
	if len(templates) != 0 {
		t.Fatalf("escaped symlink produced %d templates, want 0", len(templates))
	}
}

func TestMergeLocalTemplatesIntoIndexHonorsOfficialPriority(t *testing.T) {
	idx := &RemoteIndex{Templates: map[string]TemplateItem{
		"aliyun/vbdc": {Latest: "1.0.0", Metadata: TemplateMetadata{Description: "official"}},
	}}
	local := []ResolvedTemplate{{
		Template: &RedcTmpl{Name: "aliyun/vbdc", Version: "2.0.0", Description: "private"},
		Source:   TemplateSource{ID: "local-1", Name: "Private", Type: TemplateSourceLocal, Priority: -1},
	}}
	mergeLocalTemplatesIntoIndex(idx, local)
	if got, want := idx.Templates["aliyun/vbdc"].Metadata.Description, "official"; got != want {
		t.Fatalf("merged description = %q, want %q", got, want)
	}
}

func TestPullDoesNotFallbackToOfficialAfterOriginalSourceRemoval(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := RedcPath, TemplateDir
	RedcPath, TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		RedcPath, TemplateDir = oldRedcPath, oldTemplateDir
	})
	sourceRoot := filepath.Join(root, "private")
	sceneDir := filepath.Join(sourceRoot, "aliyun", "vbdc")
	if err := os.MkdirAll(sceneDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sceneDir, TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	manager := NewTemplateSourceManager(TemplateDir, filepath.Join(RedcPath, "template-sources.json"))
	source, err := manager.AddLocalSource("Private", sourceRoot)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := manager.InstallTemplate("aliyun/vbdc", false); err != nil {
		t.Fatal(err)
	}
	if err := manager.RemoveSource(source.ID); err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatal(err)
	}

	err = Pull(context.Background(), "aliyun/vbdc", PullOptions{RegistryURL: "http://127.0.0.1:1", Timeout: 100 * time.Millisecond})
	if err == nil || !strings.Contains(err.Error(), "original template source") {
		t.Fatalf("Pull() error = %v, want original source error", err)
	}
}
