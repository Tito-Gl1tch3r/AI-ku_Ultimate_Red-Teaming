// mod/plugin/template_engine_test.go
package plugin

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestExecuteTemplateHook_Basic(t *testing.T) {
	pluginDir := t.TempDir()
	os.MkdirAll(filepath.Join(pluginDir, "hooks"), 0755)
	tmplContent := `proxies:
{{- range .IPs}}
  - server: {{.}}
    port: {{$.Vars.port}}
{{- end}}
`
	os.WriteFile(filepath.Join(pluginDir, "hooks", "post-apply.tmpl"), []byte(tmplContent), 0644)

	caseDir := t.TempDir()
	os.WriteFile(filepath.Join(caseDir, "terraform.tfvars"), []byte(`port = "8388"`), 0644)

	outputs := map[string]interface{}{
		"ecs_ip": map[string]interface{}{
			"value": []interface{}{"1.2.3.4", "5.6.7.8"},
		},
	}
	outputJSON, _ := json.Marshal(outputs)

	hook := HookEntry{
		PluginName:   "test-plugin",
		PluginDir:    pluginDir,
		Type:         "template",
		TemplatePath: filepath.Join(pluginDir, "hooks", "post-apply.tmpl"),
		OutputPath:   "{{.CasePath}}/config.yaml",
		Config:       map[string]interface{}{},
	}

	hctx := &HookContext{
		CaseName:   "test-case",
		CasePath:   caseDir,
		OutputJSON: string(outputJSON),
	}

	_, err := executeTemplateHook(hook, hctx)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	content, err := os.ReadFile(filepath.Join(caseDir, "config.yaml"))
	if err != nil {
		t.Fatalf("output file not created: %v", err)
	}

	output := string(content)
	if !strings.Contains(output, "1.2.3.4") || !strings.Contains(output, "5.6.7.8") {
		t.Errorf("output missing IPs: %s", output)
	}
	if !strings.Contains(output, "port: 8388") {
		t.Errorf("output missing port: %s", output)
	}
}

func TestExtractIPs_Array(t *testing.T) {
	outputs := map[string]interface{}{
		"ecs_ip": map[string]interface{}{
			"value": []interface{}{"10.0.0.1", "10.0.0.2"},
		},
	}
	ips := extractIPs(outputs)
	if len(ips) != 2 || ips[0] != "10.0.0.1" {
		t.Errorf("got %v", ips)
	}
}

func TestExtractIPs_String(t *testing.T) {
	outputs := map[string]interface{}{
		"public_ip": map[string]interface{}{
			"value": "192.168.1.1",
		},
	}
	ips := extractIPs(outputs)
	if len(ips) != 1 || ips[0] != "192.168.1.1" {
		t.Errorf("got %v", ips)
	}
}

func TestExtractIPs_Empty(t *testing.T) {
	outputs := map[string]interface{}{}
	ips := extractIPs(outputs)
	if len(ips) != 0 {
		t.Errorf("expected empty, got %v", ips)
	}
}

func TestExecuteTemplateHook_SetOutput(t *testing.T) {
	pluginDir := t.TempDir()
	os.MkdirAll(filepath.Join(pluginDir, "hooks"), 0755)
	tmplContent := `{{setOutput "key1" "value1"}}{{setOutput "key2" "value2"}}done`
	os.WriteFile(filepath.Join(pluginDir, "hooks", "test.tmpl"), []byte(tmplContent), 0644)

	hook := HookEntry{
		PluginName:   "test",
		PluginDir:    pluginDir,
		Type:         "template",
		TemplatePath: filepath.Join(pluginDir, "hooks", "test.tmpl"),
		OutputPath:   "",
		Config:       map[string]interface{}{},
	}

	results, err := executeTemplateHook(hook, &HookContext{CasePath: t.TempDir()})
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if results["key1"] != "value1" || results["key2"] != "value2" {
		t.Errorf("unexpected results: %v", results)
	}
}

func TestExecuteTemplateHookWritesPrivatePojunProxyBundle(t *testing.T) {
	pluginDir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(pluginDir, "hooks"), 0755); err != nil {
		t.Fatal(err)
	}
	tmplContent := `{{- $poolID := .Config.pool_id | default (printf "redc-%s-aliyun-proxy" .CaseID) -}}
{{- $bundle := writePojunProxyBundle $poolID .Vars.port .Vars.password -}}
{{- setOutput "pojun_proxy_bundle_file" (index $bundle "bundle_file") -}}
{{- setOutput "pojun_proxy_pool_id" (index $bundle "pool_id") -}}
{{- setOutput "pojun_proxy_node_count" (index $bundle "node_count") -}}
{{- setOutput "pojun_proxy_revision" (index $bundle "revision") -}}`
	tmplPath := filepath.Join(pluginDir, "hooks", "post-apply.tmpl")
	if err := os.WriteFile(tmplPath, []byte(tmplContent), 0644); err != nil {
		t.Fatal(err)
	}

	caseDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(caseDir, "terraform.tfvars"), []byte("port = \"8388\"\npassword = \"template-value\"\n"), 0600); err != nil {
		t.Fatal(err)
	}
	outputs := map[string]interface{}{
		"ecs_ip": map[string]interface{}{
			"value": []interface{}{"203.0.113.10", "203.0.113.11"},
		},
	}
	outputJSON, err := json.Marshal(outputs)
	if err != nil {
		t.Fatal(err)
	}

	hook := HookEntry{
		PluginName:   "redc-plugin-pojun-proxy",
		PluginDir:    pluginDir,
		Type:         "template",
		TemplatePath: tmplPath,
		Config:       map[string]interface{}{},
	}
	got, err := executeTemplateHook(hook, &HookContext{
		CaseID:       "4dfaf64b-426c-40ec-84d7-456d2a43dc67",
		CaseName:     "proxy-fixture",
		CasePath:     caseDir,
		CaseTemplate: "aliyun/proxy",
		OutputJSON:   string(outputJSON),
		CaseVars:     `{"port":"9443","password":"runtime-value"}`,
	})
	if err != nil {
		t.Fatal(err)
	}

	bundleDir := filepath.Join(caseDir, "pojun-proxy")
	bundlePath := filepath.Join(bundleDir, "bundle.json")
	bundle, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	var decoded struct {
		SchemaVersion int                      `json:"schema_version"`
		PoolID        string                   `json:"pool_id"`
		Revision      string                   `json:"revision"`
		NodeCount     int                      `json:"node_count"`
		Nodes         []map[string]interface{} `json:"nodes"`
	}
	if err := json.Unmarshal(bundle, &decoded); err != nil {
		t.Fatal(err)
	}
	nodesJSON, err := json.Marshal(decoded.Nodes)
	if err != nil {
		t.Fatal(err)
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(nodesJSON))
	if decoded.SchemaVersion != 1 || decoded.PoolID != "redc-4dfaf64b-426c-40ec-84d7-456d2a43dc67-aliyun-proxy" || decoded.Revision != digest {
		t.Fatalf("bundle = %#v", decoded)
	}
	if decoded.NodeCount != 2 || len(decoded.Nodes) != 2 {
		t.Fatalf("bundle = %#v", decoded)
	}
	if decoded.Nodes[0]["server"] != "203.0.113.10" || decoded.Nodes[0]["port"] != float64(9443) || decoded.Nodes[0]["password"] != "runtime-value" {
		t.Fatalf("nodes = %#v", decoded.Nodes)
	}
	if got["pojun_proxy_bundle_file"] != bundlePath || got["pojun_proxy_revision"] != digest || got["pojun_proxy_node_count"] != "2" {
		t.Fatalf("plugin outputs = %#v", got)
	}
	for _, legacyName := range []string{"manifest.json", "proxies.yaml"} {
		if _, err := os.Stat(filepath.Join(bundleDir, legacyName)); !os.IsNotExist(err) {
			t.Fatalf("legacy split bundle file still exists: %s", legacyName)
		}
	}
	for _, item := range []struct {
		path string
		mode os.FileMode
	}{
		{bundleDir, 0700},
		{bundlePath, 0600},
	} {
		info, err := os.Stat(item.path)
		if err != nil {
			t.Fatal(err)
		}
		if info.Mode().Perm() != item.mode {
			t.Fatalf("%s mode = %04o, want %04o", item.path, info.Mode().Perm(), item.mode)
		}
	}
}

func TestExecuteTemplateHookRevokesPojunProxyBundleAfterDestroy(t *testing.T) {
	pluginDir := t.TempDir()
	hooksDir := filepath.Join(pluginDir, "hooks")
	if err := os.MkdirAll(hooksDir, 0755); err != nil {
		t.Fatal(err)
	}
	tmplPath := filepath.Join(hooksDir, "post-destroy.tmpl")
	tmplContent := `{{- removePojunProxyBundle -}}
{{- setOutput "pojun_proxy_bundle_file" "" -}}
{{- setOutput "pojun_proxy_node_count" "0" -}}
{{- setOutput "pojun_proxy_revision" "" -}}`
	if err := os.WriteFile(tmplPath, []byte(tmplContent), 0644); err != nil {
		t.Fatal(err)
	}

	caseDir := t.TempDir()
	ctx := &TemplateContext{
		CaseID:       "destroy-fixture",
		CasePath:     caseDir,
		CaseTemplate: "aliyun/proxy",
		IPs:          []string{"203.0.113.40"},
	}
	if _, err := writePojunProxyBundle(ctx, "redc-destroy-fixture-aliyun-proxy", "8388", "fixture-value"); err != nil {
		t.Fatal(err)
	}
	bundlePath := filepath.Join(caseDir, "pojun-proxy", "bundle.json")

	got, err := executeTemplateHook(HookEntry{
		PluginName:   "redc-plugin-pojun-proxy",
		PluginDir:    pluginDir,
		Type:         "template",
		TemplatePath: tmplPath,
	}, &HookContext{CaseID: "destroy-fixture", CasePath: caseDir})
	if err != nil {
		t.Fatal(err)
	}

	if _, err := os.Lstat(bundlePath); !os.IsNotExist(err) {
		t.Fatalf("post-destroy retained proxy credentials: %v", err)
	}
	if got["pojun_proxy_bundle_file"] != "" || got["pojun_proxy_node_count"] != "0" || got["pojun_proxy_revision"] != "" {
		t.Fatalf("post-destroy outputs = %#v", got)
	}
}
