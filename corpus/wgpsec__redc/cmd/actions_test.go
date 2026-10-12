package cmd

import (
	"encoding/json"
	"os"
	"path/filepath"
	redc "red-cloud/mod"
	"reflect"
	"testing"

	tfjson "github.com/hashicorp/terraform-json"
)

func TestStatusJSONDataIncludesPluginOutputsSeparately(t *testing.T) {
	caseDir := t.TempDir()
	pluginOutputs := map[string]string{
		"pojun_proxy_bundle_file": filepath.Join(caseDir, "pojun-proxy", "bundle.json"),
		"pojun_proxy_node_count":  "2",
	}
	rawPluginOutputs, err := json.Marshal(pluginOutputs)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(caseDir, "plugin_outputs.json"), rawPluginOutputs, 0600); err != nil {
		t.Fatal(err)
	}

	c := &redc.Case{Id: "case-01", Name: "proxy-01", State: redc.StateRunning, Path: caseDir}
	state := &tfjson.State{Values: &tfjson.StateValues{Outputs: map[string]*tfjson.StateOutput{
		"public_ip": {Value: []interface{}{"203.0.113.10", "203.0.113.11"}},
	}}}

	got := statusJSONData(c, state)

	if !reflect.DeepEqual(got["plugin_outputs"], pluginOutputs) {
		t.Fatalf("plugin_outputs = %#v, want %#v", got["plugin_outputs"], pluginOutputs)
	}
	terraformOutputs, ok := got["outputs"].(map[string]interface{})
	if !ok {
		t.Fatalf("outputs has unexpected type %T", got["outputs"])
	}
	if _, exists := terraformOutputs["pojun_proxy_bundle_file"]; exists {
		t.Fatal("plugin output leaked into Terraform outputs")
	}
	if !reflect.DeepEqual(terraformOutputs["public_ip"], []interface{}{"203.0.113.10", "203.0.113.11"}) {
		t.Fatalf("public_ip = %#v", terraformOutputs["public_ip"])
	}
}
