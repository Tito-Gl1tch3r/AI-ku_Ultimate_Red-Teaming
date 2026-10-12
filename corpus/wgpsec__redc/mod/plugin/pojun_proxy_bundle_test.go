package plugin

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestWritePojunProxyBundleKeepsRevisionStableForUnchangedNodes(t *testing.T) {
	ctx := &TemplateContext{
		CaseID:       "stable-fixture",
		CaseName:     "before",
		CasePath:     t.TempDir(),
		CaseTemplate: "aliyun/proxy",
		IPs:          []string{"203.0.113.10", "203.0.113.11"},
	}
	first, err := writePojunProxyBundle(ctx, "redc-stable-fixture-aliyun-proxy", "8388", "fixture-value")
	if err != nil {
		t.Fatal(err)
	}
	ctx.CaseName = "after"
	second, err := writePojunProxyBundle(ctx, "redc-stable-fixture-aliyun-proxy", "8388", "fixture-value")
	if err != nil {
		t.Fatal(err)
	}
	if first["revision"] != second["revision"] {
		t.Fatalf("unchanged nodes changed revision: %q != %q", first["revision"], second["revision"])
	}

	raw, err := os.ReadFile(filepath.Join(ctx.CasePath, "pojun-proxy", "bundle.json"))
	if err != nil {
		t.Fatal(err)
	}
	var bundle pojunProxyBundle
	if err := json.Unmarshal(raw, &bundle); err != nil {
		t.Fatal(err)
	}
	if bundle.Revision != second["revision"] || bundle.Source.CaseName != "after" {
		t.Fatalf("bundle metadata or revision was not refreshed: %#v", bundle)
	}
}

func TestWritePojunProxyBundleRejectsBadRefreshWithoutReplacingBundle(t *testing.T) {
	caseDir := t.TempDir()
	ctx := &TemplateContext{
		CaseID:       "refresh-fixture",
		CaseName:     "refresh-fixture",
		CasePath:     caseDir,
		CaseTemplate: "aliyun/proxy",
		IPs:          []string{"203.0.113.20"},
	}
	if _, err := writePojunProxyBundle(ctx, "redc-refresh-fixture-aliyun-proxy", "8388", "fixture-value"); err != nil {
		t.Fatal(err)
	}
	bundlePath := filepath.Join(caseDir, "pojun-proxy", "bundle.json")
	originalBundle, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}

	ctx.IPs = []string{"203.0.113.20", "203.0.113.20"}
	if _, err := writePojunProxyBundle(ctx, "redc-refresh-fixture-aliyun-proxy", "8388", "fixture-value"); err == nil {
		t.Fatal("duplicate proxy nodes were accepted")
	}
	gotBundle, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(gotBundle, originalBundle) {
		t.Fatal("invalid refresh replaced the last-known-good bundle")
	}
}

func TestWritePojunProxyBundleRejectsSymlinkDirectory(t *testing.T) {
	caseDir := t.TempDir()
	outsideDir := t.TempDir()
	if err := os.Symlink(outsideDir, filepath.Join(caseDir, "pojun-proxy")); err != nil {
		t.Skipf("symlinks are unavailable: %v", err)
	}
	ctx := &TemplateContext{
		CaseID:       "symlink-fixture",
		CaseName:     "symlink-fixture",
		CasePath:     caseDir,
		CaseTemplate: "aliyun/proxy",
		IPs:          []string{"203.0.113.30"},
	}
	if _, err := writePojunProxyBundle(ctx, "redc-symlink-fixture-aliyun-proxy", "8388", "fixture-value"); err == nil {
		t.Fatal("bundle directory symlink was accepted")
	}
	if _, err := os.Stat(filepath.Join(outsideDir, "bundle.json")); !os.IsNotExist(err) {
		t.Fatalf("proxy credentials escaped through symlink: %v", err)
	}
}

func TestRemovePojunProxyBundleRevokesOnlyTheManagedArtifact(t *testing.T) {
	caseDir := t.TempDir()
	bundleDir := filepath.Join(caseDir, "pojun-proxy")
	if err := os.Mkdir(bundleDir, 0700); err != nil {
		t.Fatal(err)
	}
	bundlePath := filepath.Join(bundleDir, "bundle.json")
	if err := os.WriteFile(bundlePath, []byte(`{"password":"fixture"}`), 0600); err != nil {
		t.Fatal(err)
	}
	sentinelPath := filepath.Join(bundleDir, "operator-note.txt")
	if err := os.WriteFile(sentinelPath, []byte("preserve"), 0600); err != nil {
		t.Fatal(err)
	}

	if err := removePojunProxyBundle(&TemplateContext{CasePath: caseDir}); err != nil {
		t.Fatal(err)
	}

	if _, err := os.Lstat(bundlePath); !os.IsNotExist(err) {
		t.Fatalf("destroyed Case retained proxy credentials: %v", err)
	}
	if got, err := os.ReadFile(sentinelPath); err != nil || string(got) != "preserve" {
		t.Fatalf("cleanup changed an operator-owned artifact: %q, %v", got, err)
	}
}

func TestRemovePojunProxyBundleRejectsSymlinkDirectory(t *testing.T) {
	caseDir := t.TempDir()
	outsideDir := t.TempDir()
	outsideBundle := filepath.Join(outsideDir, "bundle.json")
	if err := os.WriteFile(outsideBundle, []byte(`{"password":"fixture"}`), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outsideDir, filepath.Join(caseDir, "pojun-proxy")); err != nil {
		t.Skipf("symlinks are unavailable: %v", err)
	}

	if err := removePojunProxyBundle(&TemplateContext{CasePath: caseDir}); err == nil {
		t.Fatal("bundle directory symlink was accepted during cleanup")
	}
	if got, err := os.ReadFile(outsideBundle); err != nil || string(got) != `{"password":"fixture"}` {
		t.Fatalf("cleanup followed a symlink outside the Case: %q, %v", got, err)
	}
}
