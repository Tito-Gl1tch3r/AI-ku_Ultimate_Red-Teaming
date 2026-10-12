package main

import (
	"os"
	"path/filepath"
	redc "red-cloud/mod"
	"strings"
	"testing"
)

func TestRewriteLocalReadmeReferences_InlinesImagesAndRewritesLinks(t *testing.T) {
	tmpDir := t.TempDir()
	imageDir := filepath.Join(tmpDir, "img")
	if err := os.MkdirAll(imageDir, 0o755); err != nil {
		t.Fatalf("mkdir img dir: %v", err)
	}

	imagePath := filepath.Join(imageDir, "demo.png")
	if err := os.WriteFile(imagePath, []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
		0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
		0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4,
		0x89, 0x00, 0x00, 0x00, 0x0a, 0x49, 0x44, 0x41,
		0x54, 0x78, 0x9c, 0x63, 0x00, 0x01, 0x00, 0x00,
		0x05, 0x00, 0x01, 0x0d, 0x0a, 0x2d, 0xb4, 0x00,
		0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae,
		0x42, 0x60, 0x82,
	}, 0o644); err != nil {
		t.Fatalf("write image: %v", err)
	}

	docPath := filepath.Join(tmpDir, "docs.md")
	if err := os.WriteFile(docPath, []byte("# docs"), 0o644); err != nil {
		t.Fatalf("write doc: %v", err)
	}

	content := "![demo](./img/demo.png)\n[details](./docs.md#usage)\n[remote](https://example.com)"
	rewritten := rewriteLocalReadmeReferences(content, []string{tmpDir})

	if !strings.Contains(rewritten, "data:image/png;base64,") {
		t.Fatalf("expected image to be inlined, got %q", rewritten)
	}

	if !strings.Contains(rewritten, "file://") || !strings.Contains(rewritten, "#usage") {
		t.Fatalf("expected relative link to become file URL with fragment, got %q", rewritten)
	}

	if !strings.Contains(rewritten, "https://example.com") {
		t.Fatalf("expected absolute link to remain untouched, got %q", rewritten)
	}
}

func TestResolveLocalReadmePath_UsesFallbackAssetDirs(t *testing.T) {
	firstDir := filepath.Join(t.TempDir(), "case")
	secondDir := filepath.Join(t.TempDir(), "template")
	if err := os.MkdirAll(filepath.Join(firstDir, "assets"), 0o755); err != nil {
		t.Fatalf("mkdir first assets: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(secondDir, "assets"), 0o755); err != nil {
		t.Fatalf("mkdir second assets: %v", err)
	}

	expected := filepath.Join(secondDir, "assets", "guide.md")
	if err := os.WriteFile(expected, []byte("guide"), 0o644); err != nil {
		t.Fatalf("write fallback file: %v", err)
	}

	resolved, err := resolveLocalReadmePath("./assets/guide.md", []string{firstDir, secondDir})
	if err != nil {
		t.Fatalf("resolve fallback path: %v", err)
	}

	if resolved != expected {
		t.Fatalf("resolved path = %s, want %s", resolved, expected)
	}
}

func TestMergeLocalRegistryTemplatesPrefersLocalSource(t *testing.T) {
	oldTemplateDir := redc.TemplateDir
	redc.TemplateDir = filepath.Join(t.TempDir(), "managed")
	t.Cleanup(func() { redc.TemplateDir = oldTemplateDir })

	remote := []RegistryTemplate{{Name: "aliyun/vbdc", Description: "public", Latest: "1.0.0"}}
	local := []redc.ResolvedTemplate{{
		Template: &redc.RedcTmpl{Name: "aliyun/vbdc", Description: "private", Version: "2.0.0"},
		Source:   redc.TemplateSource{ID: "local-1", Name: "Private", Type: redc.TemplateSourceLocal, Priority: 100},
	}}

	merged := mergeLocalRegistryTemplates(remote, local, nil)
	if len(merged) != 1 {
		t.Fatalf("merged registry returned %d templates, want 1", len(merged))
	}
	if got, want := merged[0].Description, "private"; got != want {
		t.Fatalf("description = %q, want %q", got, want)
	}
	if got, want := merged[0].SourceName, "Private"; got != want {
		t.Fatalf("source name = %q, want %q", got, want)
	}
	if got, want := merged[0].ConflictCount, 1; got != want {
		t.Fatalf("conflict count = %d, want %d", got, want)
	}
}

func TestMergeLocalRegistryTemplatesHonorsOfficialPriority(t *testing.T) {
	remote := []RegistryTemplate{{Name: "aliyun/vbdc", Description: "public", Latest: "1.0.0"}}
	local := []redc.ResolvedTemplate{{
		Template: &redc.RedcTmpl{Name: "aliyun/vbdc", Description: "private", Version: "2.0.0"},
		Source:   redc.TemplateSource{ID: "local-1", Name: "Private", Type: redc.TemplateSourceLocal, Priority: -1},
	}}

	merged := mergeLocalRegistryTemplates(remote, local, nil)
	if len(merged) != 1 {
		t.Fatalf("merged registry returned %d templates, want 1", len(merged))
	}
	if got, want := merged[0].Description, "public"; got != want {
		t.Fatalf("description = %q, want official %q", got, want)
	}
	if got, want := merged[0].ConflictCount, 1; got != want {
		t.Fatalf("conflict count = %d, want %d", got, want)
	}
}

func TestPullTemplateInstallsFromLocalSource(t *testing.T) {
	root := t.TempDir()
	sourceTemplate := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sourceTemplate, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sourceTemplate, redc.TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	managed := filepath.Join(root, "managed")
	manager := redc.NewTemplateSourceManager(managed, filepath.Join(root, "template-sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}
	app := NewApp()
	app.templateSources = manager

	if err := app.PullTemplate("aliyun/vbdc", false); err != nil {
		t.Fatalf("PullTemplate() error = %v", err)
	}
	if _, err := os.Stat(filepath.Join(managed, "aliyun", "vbdc", redc.TmplCaseFile)); err != nil {
		t.Fatalf("local source template was not installed: %v", err)
	}
}
