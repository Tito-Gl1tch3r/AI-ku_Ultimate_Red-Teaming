// mod/plugin/template_engine.go
package plugin

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"

	"red-cloud/mod/gologger"
)

// TemplateContext is the data available inside .tmpl hook files.
type TemplateContext struct {
	CaseID       string
	CaseName     string
	CasePath     string
	CaseTemplate string
	CaseState    string

	Outputs map[string]interface{}
	IPs     []string

	Vars   map[string]string
	Config map[string]string

	PluginName string
	PluginDir  string
	HookPoint  string

	outputs map[string]string // collects setOutput calls
}

// executeTemplateHook renders a .tmpl file with the plugin context.
// It expects hook to have the following fields set:
//   - PluginName, PluginDir, Config (standard)
//   - Type == "template"
//   - TemplatePath: absolute path to the .tmpl file
//   - OutputPath: template string for output file path (may be empty)
func executeTemplateHook(hook HookEntry, hctx *HookContext) (map[string]string, error) {
	ctx := buildTemplateContext(hook, hctx)

	// Build function map with setOutput closure
	fm := BuiltinFuncs()
	fm["setOutput"] = func(key, value string) string {
		ctx.outputs[key] = value
		return ""
	}
	fm["readFile"] = func(path string) (string, error) {
		return safeReadFile(path, ctx.CasePath, ctx.PluginDir)
	}
	fm["writePojunProxyBundle"] = func(poolID, port, password string) (map[string]string, error) {
		return writePojunProxyBundle(ctx, poolID, port, password)
	}
	fm["removePojunProxyBundle"] = func() (string, error) {
		return "", removePojunProxyBundle(ctx)
	}

	// Parse template
	tmplBytes, err := os.ReadFile(hook.TemplatePath)
	if err != nil {
		return nil, fmt.Errorf("read template %s: %w", hook.TemplatePath, err)
	}

	tmpl, err := template.New(filepath.Base(hook.TemplatePath)).Funcs(fm).Parse(string(tmplBytes))
	if err != nil {
		return nil, fmt.Errorf("parse template %s: %w", hook.TemplatePath, err)
	}

	// Execute template
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, ctx); err != nil {
		return nil, fmt.Errorf("execute template %s: %w", hook.TemplatePath, err)
	}

	// Write output file if OutputPath is configured
	if hook.OutputPath != "" {
		outPath, err := renderString(hook.OutputPath, ctx, fm)
		if err != nil {
			return nil, fmt.Errorf("render output path: %w", err)
		}
		outPath = strings.TrimSpace(outPath)

		if err := os.MkdirAll(filepath.Dir(outPath), 0755); err != nil {
			return nil, fmt.Errorf("create output dir: %w", err)
		}
		if err := os.WriteFile(outPath, buf.Bytes(), 0644); err != nil {
			return nil, fmt.Errorf("write output file: %w", err)
		}
		gologger.Info().Msgf("plugin[%s]: wrote %s (%d bytes)", hook.PluginName, outPath, buf.Len())
	} else {
		if rendered := strings.TrimSpace(buf.String()); rendered != "" {
			for _, line := range strings.Split(rendered, "\n") {
				gologger.Info().Msgf("plugin[%s]: %s", hook.PluginName, line)
			}
		}
	}

	return ctx.outputs, nil
}

func buildTemplateContext(hook HookEntry, hctx *HookContext) *TemplateContext {
	ctx := &TemplateContext{
		PluginName: hook.PluginName,
		PluginDir:  hook.PluginDir,
		Outputs:    make(map[string]interface{}),
		Vars:       make(map[string]string),
		Config:     make(map[string]string),
		IPs:        []string{},
		outputs:    make(map[string]string),
	}

	if hctx != nil {
		ctx.CaseID = hctx.CaseID
		ctx.CaseName = hctx.CaseName
		ctx.CasePath = hctx.CasePath
		ctx.CaseTemplate = hctx.CaseTemplate
		ctx.CaseState = hctx.CaseState

		if hctx.OutputJSON != "" {
			json.Unmarshal([]byte(hctx.OutputJSON), &ctx.Outputs)
		}

		if hctx.CasePath != "" {
			ctx.Vars = ParseTfvars(filepath.Join(hctx.CasePath, "terraform.tfvars"))
		}
		if hctx.CaseVars != "" {
			var runtimeVars map[string]interface{}
			if json.Unmarshal([]byte(hctx.CaseVars), &runtimeVars) == nil {
				for key, value := range runtimeVars {
					switch typed := value.(type) {
					case string:
						ctx.Vars[key] = typed
					case float64:
						ctx.Vars[key] = fmt.Sprintf("%v", typed)
					}
				}
			}
		}
	}

	ctx.IPs = extractIPs(ctx.Outputs)

	if hook.Config != nil {
		for k, v := range hook.Config {
			ctx.Config[k] = fmt.Sprintf("%v", v)
		}
	}

	return ctx
}

// extractIPs tries ecs_ip then public_ip from terraform outputs.
func extractIPs(outputs map[string]interface{}) []string {
	for _, key := range []string{"ecs_ip", "public_ip"} {
		entry, ok := outputs[key]
		if !ok {
			continue
		}
		entryMap, ok := entry.(map[string]interface{})
		if !ok {
			continue
		}
		val, ok := entryMap["value"]
		if !ok {
			continue
		}
		switch v := val.(type) {
		case []interface{}:
			ips := make([]string, 0, len(v))
			for _, item := range v {
				if s, ok := item.(string); ok && s != "" {
					ips = append(ips, s)
				}
			}
			if len(ips) > 0 {
				return ips
			}
		case string:
			if v != "" {
				return []string{v}
			}
		}
	}
	return []string{}
}

func renderString(tmplStr string, data interface{}, fm template.FuncMap) (string, error) {
	tmpl, err := template.New("").Funcs(fm).Parse(tmplStr)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, data); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func safeReadFile(path, casePath, pluginDir string) (string, error) {
	absPath, err := filepath.Abs(path)
	if err != nil {
		return "", fmt.Errorf("readFile: invalid path")
	}
	absCasePath, _ := filepath.Abs(casePath)
	absPluginDir, _ := filepath.Abs(pluginDir)

	if !strings.HasPrefix(absPath, absCasePath) && !strings.HasPrefix(absPath, absPluginDir) {
		return "", fmt.Errorf("readFile: access denied (path must be within case or plugin directory)")
	}

	data, err := os.ReadFile(absPath)
	if err != nil {
		return "", err
	}
	return string(data), nil
}
