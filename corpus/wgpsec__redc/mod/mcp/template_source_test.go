package mcp

import (
	"os"
	"path/filepath"
	redc "red-cloud/mod"
	"strings"
	"testing"
)

func TestSearchTemplatesUsesConfiguredLocalSource(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := redc.RedcPath, redc.TemplateDir
	redc.RedcPath, redc.TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		redc.RedcPath, redc.TemplateDir = oldRedcPath, oldTemplateDir
	})
	sceneDir := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sceneDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sceneDir, redc.TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	manager := redc.NewTemplateSourceManager(redc.TemplateDir, filepath.Join(redc.RedcPath, "template-sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatal(err)
	}

	result, err := (&MCPServer{}).toolSearchTemplates("vbdc", "http://127.0.0.1:1")
	if err != nil {
		t.Fatalf("toolSearchTemplates() error = %v", err)
	}
	if len(result.Content) != 1 {
		t.Fatalf("tool result content count = %d, want 1", len(result.Content))
	}
	text := result.Content[0].Text
	if !strings.Contains(text, "aliyun/vbdc") || !strings.Contains(text, "Private (local)") {
		t.Fatalf("tool result = %q, want local source details", text)
	}
}

func TestPullTemplateUsesConfiguredLocalSource(t *testing.T) {
	root := t.TempDir()
	oldRedcPath, oldTemplateDir := redc.RedcPath, redc.TemplateDir
	redc.RedcPath, redc.TemplateDir = root, filepath.Join(root, "managed")
	t.Cleanup(func() {
		redc.RedcPath, redc.TemplateDir = oldRedcPath, oldTemplateDir
	})
	sceneDir := filepath.Join(root, "private", "aliyun", "vbdc")
	if err := os.MkdirAll(sceneDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sceneDir, redc.TmplCaseFile), []byte(`{"name":"vbdc","version":"1.0.0"}`), 0644); err != nil {
		t.Fatal(err)
	}
	manager := redc.NewTemplateSourceManager(redc.TemplateDir, filepath.Join(redc.RedcPath, "template-sources.json"))
	if _, err := manager.AddLocalSource("Private", filepath.Join(root, "private")); err != nil {
		t.Fatal(err)
	}
	if err := manager.Save(); err != nil {
		t.Fatal(err)
	}

	if _, err := (&MCPServer{}).toolPullTemplate("aliyun/vbdc", "http://127.0.0.1:1", false); err != nil {
		t.Fatalf("toolPullTemplate() error = %v", err)
	}
	if _, err := os.Stat(filepath.Join(redc.TemplateDir, "aliyun", "vbdc", redc.TmplCaseFile)); err != nil {
		t.Fatalf("MCP pull did not install local template: %v", err)
	}
}
