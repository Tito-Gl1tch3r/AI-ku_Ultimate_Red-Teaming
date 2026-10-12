package main

import (
	"fmt"
	"strings"

	"red-cloud/i18n"
	"red-cloud/mod/compose"

	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// ComposePreview parses a compose file and returns services summary
func (a *App) ComposePreview(filePath string, profiles []string) (ComposeSummary, error) {
	a.mu.Lock()
	project := a.project
	a.mu.Unlock()

	if project == nil {
		if a.initError != "" {
			return ComposeSummary{}, fmt.Errorf("%s", a.initError)
		}
		return ComposeSummary{}, fmt.Errorf("项目未加载")
	}

	if strings.TrimSpace(filePath) == "" {
		filePath = "redc-compose.yaml"
	}

	ctx, err := compose.NewComposeContext(compose.ComposeOptions{
		File:     filePath,
		Profiles: profiles,
		Project:  project,
	})
	if err != nil {
		return ComposeSummary{}, err
	}

	services := make([]ComposeServiceSummary, 0, len(ctx.SortedSvcKeys))
	for _, name := range ctx.SortedSvcKeys {
		svc := ctx.RuntimeSvcs[name]
		status := "not_deployed"
		if c, err := project.GetCase(svc.Name); err == nil {
			status = c.State
		}
		services = append(services, ComposeServiceSummary{
			Name:      svc.Name,
			RawName:   svc.RawName,
			Template:  svc.Spec.Image,
			Provider:  formatComposeProvider(svc.Spec.Provider),
			Profiles:  svc.Spec.Profiles,
			DependsOn: svc.Spec.DependsOn,
			Replicas:  svc.Spec.Deploy.Replicas,
			Status:    status,
		})
	}

	return ComposeSummary{
		File:     filePath,
		Services: services,
		Total:    len(services),
	}, nil
}

// ComposeUp starts compose deployment asynchronously (GUI button)
func (a *App) ComposeUp(filePath string, profiles []string) error {
	a.mu.Lock()
	project := a.project
	a.mu.Unlock()

	if project == nil {
		if a.initError != "" {
			return fmt.Errorf("%s", a.initError)
		}
		return fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	if strings.TrimSpace(filePath) == "" {
		filePath = "redc-compose.yaml"
	}

	opts := compose.ComposeOptions{
		File:     filePath,
		Profiles: profiles,
		Project:  project,
		LogCallback: func(msg string) {
			a.emitEvent("compose-log", map[string]string{"message": msg})
		},
	}

	a.emitLog(i18n.Tf("app_compose_up_start", filePath))
	a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "running"})
	go func() {
		a.activeOps.Add(1)
		defer a.activeOps.Add(-1)
		defer a.emitRefresh()
		if err := compose.RunComposeUp(opts); err != nil {
			errMsg := i18n.Tf("app_compose_up_failed", err)
			a.emitLog(errMsg)
			a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "error", "error": errMsg})
			return
		}
		a.emitLog(i18n.T("app_compose_up_done"))
		a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "done"})
	}()
	return nil
}

// ComposeUpSync runs compose deployment synchronously, returning deployed case details.
// Used by MCP/Agent tools to block until completion and get case IDs.
func (a *App) ComposeUpSync(filePath string, profiles []string) (interface{}, error) {
	a.mu.Lock()
	project := a.project
	a.mu.Unlock()

	if project == nil {
		if a.initError != "" {
			return nil, fmt.Errorf("%s", a.initError)
		}
		return nil, fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	if strings.TrimSpace(filePath) == "" {
		filePath = "redc-compose.yaml"
	}

	opts := compose.ComposeOptions{
		File:     filePath,
		Profiles: profiles,
		Project:  project,
		LogCallback: func(msg string) {
			a.emitEvent("compose-log", map[string]string{"message": msg})
		},
	}

	a.emitLog(i18n.Tf("app_compose_up_start", filePath))
	a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "running"})
	a.activeOps.Add(1)
	defer a.activeOps.Add(-1)
	defer a.emitRefresh()

	result, err := compose.RunComposeUpWithResult(opts)
	if err != nil {
		errMsg := i18n.Tf("app_compose_up_failed", err)
		a.emitLog(errMsg)
		a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "error", "error": errMsg})
		return nil, err
	}
	a.emitLog(i18n.T("app_compose_up_done"))
	a.emitEvent("compose-status", map[string]string{"action": "up", "phase": "done"})
	return result, nil
}

// ComposeDown destroys compose deployment asynchronously (GUI button)
func (a *App) ComposeDown(filePath string, profiles []string) error {
	a.mu.Lock()
	project := a.project
	a.mu.Unlock()

	if project == nil {
		if a.initError != "" {
			return fmt.Errorf("%s", a.initError)
		}
		return fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	if strings.TrimSpace(filePath) == "" {
		filePath = "redc-compose.yaml"
	}

	opts := compose.ComposeOptions{
		File:     filePath,
		Profiles: profiles,
		Project:  project,
		LogCallback: func(msg string) {
			a.emitEvent("compose-log", map[string]string{"message": msg})
		},
	}

	a.emitLog(i18n.Tf("app_compose_down_start", filePath))
	a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "running"})
	go func() {
		a.activeOps.Add(1)
		defer a.activeOps.Add(-1)
		defer a.emitRefresh()
		if err := compose.RunComposeDown(opts); err != nil {
			errMsg := i18n.Tf("app_compose_down_failed", err)
			a.emitLog(errMsg)
			a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "error", "error": errMsg})
			return
		}
		a.emitLog(i18n.T("app_compose_down_done"))
		a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "done"})
	}()
	return nil
}

// ComposeDownSync runs compose destroy synchronously. Used by MCP/Agent tools.
func (a *App) ComposeDownSync(filePath string, profiles []string) error {
	a.mu.Lock()
	project := a.project
	a.mu.Unlock()

	if project == nil {
		if a.initError != "" {
			return fmt.Errorf("%s", a.initError)
		}
		return fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	if strings.TrimSpace(filePath) == "" {
		filePath = "redc-compose.yaml"
	}

	opts := compose.ComposeOptions{
		File:     filePath,
		Profiles: profiles,
		Project:  project,
		LogCallback: func(msg string) {
			a.emitEvent("compose-log", map[string]string{"message": msg})
		},
	}

	a.emitLog(i18n.Tf("app_compose_down_start", filePath))
	a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "running"})
	a.activeOps.Add(1)
	defer a.activeOps.Add(-1)
	defer a.emitRefresh()

	if err := compose.RunComposeDown(opts); err != nil {
		errMsg := i18n.Tf("app_compose_down_failed", err)
		a.emitLog(errMsg)
		a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "error", "error": errMsg})
		return err
	}
	a.emitLog(i18n.T("app_compose_down_done"))
	a.emitEvent("compose-status", map[string]string{"action": "down", "phase": "done"})
	return nil
}

func formatComposeProvider(provider interface{}) string {
	if provider == nil {
		return ""
	}
	switch v := provider.(type) {
	case string:
		return v
	case []string:
		return strings.Join(v, ",")
	case []interface{}:
		items := make([]string, 0, len(v))
		for _, item := range v {
			items = append(items, fmt.Sprintf("%v", item))
		}
		return strings.Join(items, ",")
	default:
		return fmt.Sprintf("%v", provider)
	}
}

// SelectComposeFile opens a file dialog to select a compose file
func (a *App) SelectComposeFile() (string, error) {
	filePath, err := runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{
		Title: "选择 Compose 文件",
		Filters: []runtime.FileFilter{
			{
				DisplayName: "YAML 文件 (*.yaml, *.yml)",
				Pattern:     "*.yaml;*.yml",
			},
			{
				DisplayName: "所有文件 (*.*)",
				Pattern:     "*.*",
			},
		},
	})
	if err != nil {
		return "", err
	}
	return filePath, nil
}
