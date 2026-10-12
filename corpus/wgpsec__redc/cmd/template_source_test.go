package cmd

import (
	"os"
	"path/filepath"
	redc "red-cloud/mod"
	"testing"
)

func TestAddLocalTemplateSourcePersistsForCLI(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := redc.RedcPath, redc.TemplateDir
	redc.RedcPath, redc.TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		redc.RedcPath, redc.TemplateDir = oldRedcPath, oldTemplateDir
	})
	sourceDir := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sourceDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sourceDir, redc.TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}

	source, err := addLocalTemplateSource("Private", filepath.Join(root, "private"))
	if err != nil {
		t.Fatalf("addLocalTemplateSource() error = %v", err)
	}
	manager, err := redc.LoadConfiguredTemplateSourceManager()
	if err != nil {
		t.Fatal(err)
	}
	sources := manager.ListSources()
	if len(sources) != 1 || sources[0].ID != source.ID {
		t.Fatalf("persisted sources = %#v, want source %q", sources, source.ID)
	}
	if sources[0].TemplateCount != 1 {
		t.Fatalf("template count = %d, want 1", sources[0].TemplateCount)
	}
}
