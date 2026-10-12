package main

import (
	"archive/zip"
	"bufio"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"mime"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"red-cloud/i18n"
	redc "red-cloud/mod"
	"regexp"
	"strings"
	"time"

	"github.com/projectdiscovery/gologger"
)

func (a *App) ListTemplates() ([]TemplateInfo, error) {
	templates, err := redc.ListLocalTemplates()
	if err != nil {
		return nil, err
	}
	result := make([]TemplateInfo, 0, len(templates))
	for _, t := range templates {
		result = append(result, TemplateInfo{
			Name:          t.Name,
			Description:   t.Description,
			DescriptionEN: t.DescriptionEN,
			Version:       t.Version,
			User:          t.User,
			Module:        t.RedcModule,
			Plugins:       t.RedcPlugins,
		})
	}
	return result, nil
}

func (a *App) ListAllTemplates() ([]TemplateInfo, error) {
	templates, err := redc.ListAllTemplates()
	if err != nil {
		return nil, err
	}
	result := make([]TemplateInfo, 0, len(templates))
	for _, t := range templates {
		result = append(result, TemplateInfo{
			Name:          t.Name,
			Description:   t.Description,
			DescriptionEN: t.DescriptionEN,
			Version:       t.Version,
			User:          t.User,
			Module:        t.RedcModule,
			Plugins:       t.RedcPlugins,
		})
	}
	return result, nil
}

// GetTemplatesDir returns the local templates directory path
func (a *App) GetTemplatesDir() string {
	return redc.TemplateDir
}

func (a *App) GetTemplateVariables(templateName string) ([]TemplateVariable, error) {
	templatePath := filepath.Join(redc.TemplateDir, templateName)
	if _, err := os.Stat(templatePath); os.IsNotExist(err) {
		if manager, managerErr := a.templateSourceManager(); managerErr == nil {
			if resolved, resolveErr := manager.ResolveTemplate(templateName); resolveErr == nil {
				templatePath = resolved.Template.Path
			}
		}
	}

	// Parse variables.tf to get variable definitions
	variablesFile := filepath.Join(templatePath, "variables.tf")
	tfvarsFile := filepath.Join(templatePath, "terraform.tfvars")

	variables := make(map[string]*TemplateVariable)

	// Parse variables.tf
	if _, err := os.Stat(variablesFile); err == nil {
		vars, err := parseVariablesTf(variablesFile)
		if err != nil {
			return nil, fmt.Errorf("%s", i18n.Tf("app_parse_variables_failed", err))
		}
		for _, v := range vars {
			variables[v.Name] = v
		}
	}

	// Parse terraform.tfvars for default values
	if _, err := os.Stat(tfvarsFile); err == nil {
		defaults, err := parseTfvars(tfvarsFile)
		if err != nil {
			return nil, fmt.Errorf("%s", i18n.Tf("app_parse_tfvars_failed", err))
		}
		for name, value := range defaults {
			if v, ok := variables[name]; ok {
				v.DefaultValue = value
			}
		}
	}

	// Convert map to slice
	result := make([]TemplateVariable, 0, len(variables))
	for _, v := range variables {
		v.Required = true
		result = append(result, *v)
	}
	return result, nil
}

func parseVariablesTf(filePath string) ([]*TemplateVariable, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var variables []*TemplateVariable
	scanner := bufio.NewScanner(file)

	varNameRegex := regexp.MustCompile(`^variable\s+"([^"]+)"`)
	typeRegex := regexp.MustCompile(`^\s*type\s*=\s*(.+)`)
	descRegex := regexp.MustCompile(`^\s*description\s*=\s*"([^"]*)"`)
	defaultRegex := regexp.MustCompile(`^\s*default\s*=\s*(.+)`)
	sensitiveRegex := regexp.MustCompile(`^\s*sensitive\s*=\s*true`)
	containsRegex := regexp.MustCompile(`contains\(\s*\[([^\]]*)\]`)

	var currentVar *TemplateVariable
	braceCount := 0
	inValidation := false
	validationBraceCount := 0

	for scanner.Scan() {
		line := scanner.Text()

		// Check for variable declaration
		if matches := varNameRegex.FindStringSubmatch(line); len(matches) > 1 {
			if currentVar != nil {
				variables = append(variables, currentVar)
			}
			currentVar = &TemplateVariable{
				Name:     matches[1],
				Required: true,
				Type:     "string",
			}
			braceCount = 1
			inValidation = false
			continue
		}

		if currentVar == nil {
			continue
		}

		// Detect validation block start
		trimmed := strings.TrimSpace(line)
		if !inValidation && strings.HasPrefix(trimmed, "validation") && strings.Contains(line, "{") {
			inValidation = true
			validationBraceCount = 1
			// Don't count these braces in the outer counter — they are already part of the variable block
			braceCount += strings.Count(line, "{") - strings.Count(line, "}")
			continue
		}

		if inValidation {
			validationBraceCount += strings.Count(line, "{") - strings.Count(line, "}")

			// Parse contains([...]) inside validation condition
			if matches := containsRegex.FindStringSubmatch(line); len(matches) > 1 {
				valuesStr := matches[1]
				var allowedValues []string
				for _, part := range strings.Split(valuesStr, ",") {
					v := strings.TrimSpace(part)
					v = strings.Trim(v, `"`)
					if v != "" {
						allowedValues = append(allowedValues, v)
					}
				}
				if len(allowedValues) > 0 {
					currentVar.Validation = &TemplateVariableValidation{
						AllowedValues: allowedValues,
					}
				}
			}

			braceCount += strings.Count(line, "{") - strings.Count(line, "}")

			if validationBraceCount <= 0 {
				inValidation = false
			}
			continue
		}

		// Count braces
		braceCount += strings.Count(line, "{") - strings.Count(line, "}")

		// Parse type
		if matches := typeRegex.FindStringSubmatch(line); len(matches) > 1 {
			currentVar.Type = strings.TrimSpace(matches[1])
		}

		// Parse description
		if matches := descRegex.FindStringSubmatch(line); len(matches) > 1 {
			currentVar.Description = matches[1]
		}

		// Parse default
		if matches := defaultRegex.FindStringSubmatch(line); len(matches) > 1 {
			defaultRaw := strings.TrimSpace(matches[1])
			currentVar.DefaultValue = strings.Trim(defaultRaw, `"`)
		}

		// Parse sensitive
		if sensitiveRegex.MatchString(line) {
			currentVar.Sensitive = true
		}

		// End of variable block
		if braceCount <= 0 && currentVar != nil {
			variables = append(variables, currentVar)
			currentVar = nil
		}
	}

	// Add last variable if exists
	if currentVar != nil {
		variables = append(variables, currentVar)
	}

	return variables, scanner.Err()
}

func (a *App) FetchRegistryTemplates(registryURL string) ([]RegistryTemplate, error) {
	if registryURL == "" {
		registryURL = "https://redc.wgpsec.org"
	}

	a.emitLog(i18n.Tf("app_connecting_registry", registryURL))

	// Fetch index.json
	indexURL := fmt.Sprintf("%s/index.json?t=%d", registryURL, time.Now().Unix())

	client := redc.NewProxyHTTPClient(30 * time.Second)
	resp, err := client.Get(indexURL)
	if err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("app_registry_connect_failed", err))
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("%s", i18n.Tf("app_registry_status_error", resp.Status))
	}

	var idx remoteIndexResponse
	if err := json.NewDecoder(resp.Body).Decode(&idx); err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("app_registry_parse_failed", err))
	}

	// Build result list
	result := make([]RegistryTemplate, 0, len(idx.Templates))
	for templateID, t := range idx.Templates {
		// Use templateID (e.g. "aliyun/ecs") as the name
		name := templateID
		if name == "" {
			name = t.ID
		}

		// Check if installed locally
		installed, localVer, _ := redc.CheckLocalImage(name)

		// Get version list
		versions := make([]string, 0, len(t.Versions))
		var updatedAt string
		for v, info := range t.Versions {
			versions = append(versions, v)
			if v == t.Latest && info.UpdatedAt != "" {
				updatedAt = info.UpdatedAt
			}
		}

		// Extract tags: prefer remote metadata tags, fallback to local case.json
		var tags []string
		if len(t.Metadata.Tags) > 0 {
			tags = t.Metadata.Tags
		} else if t.Provider != "" {
			tags = []string{t.Provider}
		}

		// For installed templates, read tags from local case.json
		if installed {
			localCasePath := filepath.Join(redc.TemplateDir, name, "case.json")
			if data, err := os.ReadFile(localCasePath); err == nil {
				var localCase struct {
					Tags []string `json:"tags"`
				}
				if json.Unmarshal(data, &localCase) == nil && len(localCase.Tags) > 0 {
					tags = localCase.Tags
				}
			}
		}

		result = append(result, RegistryTemplate{
			Name:          name,
			Description:   t.Metadata.Description,
			DescriptionEN: t.Metadata.DescriptionEN,
			Author:        t.Metadata.Author,
			Latest:        t.Latest,
			Versions:      versions,
			UpdatedAt:     updatedAt,
			Tags:          tags,
			Installed:     installed,
			LocalVer:      localVer,
		})
	}

	a.emitLog(i18n.Tf("app_fetched_templates", len(result)))
	return result, nil
}

func (a *App) FetchTemplateReadme(templateName string, lang string) (string, error) {
	templateDir := filepath.Join(redc.TemplateDir, templateName)
	if content, err := loadLocalReadme(templateDir, []string{templateDir}, lang); err == nil {
		return content, nil
	}
	if manager, err := a.templateSourceManager(); err == nil {
		if resolved, resolveErr := manager.ResolveTemplate(templateName); resolveErr == nil {
			if content, readErr := loadLocalReadme(resolved.Template.Path, []string{resolved.Template.Path}, lang); readErr == nil {
				return content, nil
			}
		}
	}

	return fetchRemoteTemplateReadme(templateName, lang)
}

type CaseReadmeInfo struct {
	Content string `json:"content"`
	Source  string `json:"source"`
}

func (a *App) FetchCaseReadme(caseID string, lang string) (string, error) {
	info, err := a.FetchCaseReadmeInfo(caseID, lang)
	if err != nil {
		return "", err
	}
	return info.Content, nil
}

func (a *App) FetchCaseReadmeInfo(caseID string, lang string) (CaseReadmeInfo, error) {
	a.mu.Lock()
	project := a.project
	initError := a.initError
	a.mu.Unlock()

	if project == nil {
		if initError != "" {
			return CaseReadmeInfo{}, fmt.Errorf("%s", initError)
		}
		return CaseReadmeInfo{}, fmt.Errorf("%s", i18n.T("app_project_not_loaded"))
	}

	c, err := project.GetCase(caseID)
	if err != nil {
		return CaseReadmeInfo{}, err
	}

	templateDir := filepath.Join(redc.TemplateDir, c.Type)
	if content, err := loadLocalReadme(c.Path, []string{c.Path, templateDir}, lang); err == nil {
		return CaseReadmeInfo{Content: content, Source: "case-local"}, nil
	}

	if content, err := loadLocalReadme(templateDir, []string{templateDir}, lang); err == nil {
		return CaseReadmeInfo{Content: content, Source: "template-local"}, nil
	}

	content, err := fetchRemoteTemplateReadme(c.Type, lang)
	if err != nil {
		return CaseReadmeInfo{}, err
	}

	return CaseReadmeInfo{Content: content, Source: "remote-registry"}, nil
}

func readmeFileCandidates(lang string) []string {
	if lang == "en" {
		return []string{"README_EN.md", "README.md"}
	}
	return []string{"README.md", "README_EN.md"}
}

func loadLocalReadme(baseDir string, assetDirs []string, lang string) (string, error) {
	if baseDir == "" {
		return "", fmt.Errorf("readme base dir is empty")
	}

	var lastErr error
	for _, readmeFile := range readmeFileCandidates(lang) {
		readmePath := filepath.Join(baseDir, readmeFile)
		content, err := os.ReadFile(readmePath)
		if err != nil {
			lastErr = err
			continue
		}
		return rewriteLocalReadmeReferences(string(content), assetDirs), nil
	}

	if lastErr == nil {
		lastErr = fmt.Errorf("README not found")
	}
	return "", fmt.Errorf("failed to load local README from %s: %w", baseDir, lastErr)
}

func rewriteLocalReadmeReferences(content string, assetDirs []string) string {
	linkRegex := regexp.MustCompile(`!?\[([^\]]*)\]\(([^)]+)\)`)
	return linkRegex.ReplaceAllStringFunc(content, func(match string) string {
		parts := linkRegex.FindStringSubmatch(match)
		if len(parts) != 3 {
			return match
		}

		label := parts[1]
		target := strings.TrimSpace(parts[2])
		if target == "" || strings.HasPrefix(target, "#") || isAbsoluteReadmeTarget(target) {
			return match
		}

		parsed, err := url.Parse(target)
		if err != nil || parsed.Path == "" {
			return match
		}

		resolvedPath, err := resolveLocalReadmePath(parsed.Path, assetDirs)
		if err != nil {
			return match
		}

		if strings.HasPrefix(match, "!") {
			dataURL, err := localFileToDataURL(resolvedPath)
			if err != nil {
				return match
			}
			return fmt.Sprintf("![%s](%s)", label, dataURL)
		}

		return fmt.Sprintf("[%s](%s)", label, localPathToFileURL(resolvedPath, parsed.RawQuery, parsed.Fragment))
	})
}

func isAbsoluteReadmeTarget(target string) bool {
	lowerTarget := strings.ToLower(target)
	return strings.HasPrefix(lowerTarget, "http://") ||
		strings.HasPrefix(lowerTarget, "https://") ||
		strings.HasPrefix(lowerTarget, "data:") ||
		strings.HasPrefix(lowerTarget, "file://") ||
		strings.HasPrefix(lowerTarget, "mailto:") ||
		strings.HasPrefix(target, "/")
}

func resolveLocalReadmePath(rawPath string, assetDirs []string) (string, error) {
	decodedPath, err := url.PathUnescape(rawPath)
	if err != nil {
		decodedPath = rawPath
	}

	for _, dir := range assetDirs {
		if dir == "" {
			continue
		}

		candidate := filepath.Clean(filepath.Join(dir, filepath.FromSlash(decodedPath)))
		if _, err := os.Stat(candidate); err == nil {
			return candidate, nil
		}
	}

	return "", fmt.Errorf("local README target not found: %s", rawPath)
}

func localFileToDataURL(filePath string) (string, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return "", err
	}

	mimeType := mime.TypeByExtension(strings.ToLower(filepath.Ext(filePath)))
	if mimeType == "" {
		mimeType = http.DetectContentType(data)
	}
	if !strings.HasPrefix(mimeType, "image/") {
		return "", fmt.Errorf("unsupported README asset type: %s", mimeType)
	}

	encoded := base64.StdEncoding.EncodeToString(data)
	return fmt.Sprintf("data:%s;base64,%s", mimeType, encoded), nil
}

func localPathToFileURL(filePath string, rawQuery string, fragment string) string {
	urlPath := filepath.ToSlash(filePath)
	if vol := filepath.VolumeName(filePath); vol != "" {
		urlPath = "/" + urlPath
	}

	parsed := &url.URL{
		Scheme:   "file",
		Path:     urlPath,
		RawQuery: rawQuery,
		Fragment: fragment,
	}
	return parsed.String()
}

func fetchRemoteTemplateReadme(templateName string, lang string) (string, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	var lastErr error

	for _, readmeFile := range readmeFileCandidates(lang) {
		readmeURL := fmt.Sprintf("https://raw.githubusercontent.com/wgpsec/redc-template/master/%s/%s", templateName, readmeFile)
		resp, err := client.Get(readmeURL)
		if err != nil {
			lastErr = err
			continue
		}

		if resp.StatusCode == http.StatusOK {
			content, err := io.ReadAll(resp.Body)
			resp.Body.Close()
			if err != nil {
				lastErr = err
				continue
			}
			return string(content), nil
		}

		lastErr = fmt.Errorf("HTTP %d", resp.StatusCode)
		resp.Body.Close()
	}

	return "", fmt.Errorf("failed to fetch README: %v", lastErr)
}

func (a *App) RemoveTemplate(templateName string) error {
	a.emitLog(i18n.Tf("app_deleting_template", templateName))

	if err := redc.RemoveTemplate(templateName); err != nil {
		a.emitLog(i18n.Tf("app_delete_failed", err))
		return err
	}

	a.emitLog(i18n.Tf("app_template_deleted", templateName))
	a.emitRefresh()
	return nil
}

func (a *App) PullTemplate(templateName string, force bool) error {
	a.emitLog(i18n.Tf("app_pulling_template", templateName))
	if manager, err := a.templateSourceManager(); err == nil {
		if templates, err := manager.ListMergedTemplates(); err == nil {
			for _, template := range templates {
				if template.Template.Name != templateName || template.Source.Priority < 0 {
					continue
				}
				if _, err := manager.InstallTemplate(templateName, force); err != nil {
					return err
				}
				a.emitLog(i18n.Tf("app_template_pulled", templateName))
				a.emitRefresh()
				return nil
			}
		}
	}

	go func() {
		defer func() {
			if r := recover(); r != nil {
				a.emitLog(i18n.Tf("app_pull_error", r))
			}
			a.emitRefresh()
		}()

		opts := redc.PullOptions{
			RegistryURL: "https://redc.wgpsec.org",
			Force:       force,
			Timeout:     120 * time.Second,
		}

		if err := redc.Pull(context.Background(), templateName, opts); err != nil {
			a.emitLog(i18n.Tf("app_pull_failed", err))
			return
		}

		a.emitLog(i18n.Tf("app_template_pulled", templateName))
	}()

	return nil
}

func (a *App) CopyTemplate(sourceName string, targetName string) error {
	if err := redc.CopyTemplate(sourceName, targetName); err != nil {
		a.emitLog(i18n.Tf("app_template_copy_failed", err))
		return err
	}
	a.emitLog(i18n.Tf("app_template_copy_success", sourceName, targetName))
	a.emitRefresh()
	return nil
}

func (a *App) GetTemplateFiles(templateName string) (map[string]string, error) {
	path, err := redc.GetTemplatePath(templateName)
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return nil, err
	}
	files := make(map[string]string)
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		// Read case.json, terraform.tfvars, *.tf, userdata files, and compose files
		if name == "case.json" || name == "terraform.tfvars" ||
			strings.HasSuffix(name, ".tf") ||
			strings.HasSuffix(name, ".yaml") || strings.HasSuffix(name, ".yml") ||
			strings.HasSuffix(name, ".sh") || strings.HasSuffix(name, ".userdata") ||
			strings.HasSuffix(name, ".md") ||
			name == "userdata" || name == "script.sh" || name == "README" {
			data, err := os.ReadFile(filepath.Join(path, name))
			if err != nil {
				continue
			}
			files[name] = string(data)
		}
	}
	return files, nil
}

func (a *App) ListUserdataTemplates() ([]redc.UserdataTemplate, error) {
	templates, err := redc.ListUserdataTemplates()
	if err != nil {
		return nil, err
	}
	result := make([]redc.UserdataTemplate, 0, len(templates))
	for _, t := range templates {
		result = append(result, *t)
	}
	return result, nil
}

func (a *App) ListComposeTemplates() ([]redc.ComposeTemplate, error) {
	templates, err := redc.ListComposeTemplates()
	if err != nil {
		return nil, err
	}
	result := make([]redc.ComposeTemplate, 0, len(templates))
	for _, t := range templates {
		result = append(result, *t)
	}
	return result, nil
}

func (a *App) SaveTemplateFiles(templateName string, files map[string]string) (string, error) {
	// 检查是否是 AI 模板（通过检查 templateName 是否包含 ai- 前缀）
	isAI := strings.HasPrefix(templateName, "ai-") || strings.HasPrefix(templateName, "AI-")
	path, err := redc.ResolveTemplatePath(templateName, isAI)
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(path, 0755); err != nil {
		return "", fmt.Errorf("failed to create template directory: %w", err)
	}
	for name, content := range files {
		// Save case.json, terraform.tfvars, *.tf, userdata files, and compose files
		if name == "case.json" || name == "terraform.tfvars" ||
			strings.HasSuffix(name, ".tf") ||
			strings.HasSuffix(name, ".yaml") || strings.HasSuffix(name, ".yml") ||
			strings.HasSuffix(name, ".sh") || strings.HasSuffix(name, ".userdata") ||
			strings.HasSuffix(name, ".md") ||
			name == "userdata" || name == "script.sh" || name == "README" {
			if err := os.WriteFile(filepath.Join(path, name), []byte(content), 0644); err != nil {
				return "", err
			}
		}
	}
	absPath, _ := filepath.Abs(path)
	a.emitLog(i18n.Tf("app_template_save_success", templateName))
	return absPath, nil
}

func (a *App) ExportTemplates(templateNames []string) (string, error) {
	if len(templateNames) == 0 {
		return "", fmt.Errorf("no templates selected")
	}

	// Create temp zip file
	tmpFile, err := os.CreateTemp("", "redc-templates-*.zip")
	if err != nil {
		return "", err
	}
	tmpFile.Close()
	zipPath := tmpFile.Name()

	zipFile, err := os.OpenFile(zipPath, os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		os.Remove(zipPath)
		return "", err
	}
	defer zipFile.Close()
	// Note: Don't remove zipPath here, let the frontend copy it first

	zipWriter := zip.NewWriter(zipFile)
	defer zipWriter.Close()

	for _, name := range templateNames {
		path, err := redc.GetTemplatePath(name)
		if err != nil {
			continue // Skip if template not found
		}

		// Walk through template directory
		err = filepath.Walk(path, func(filePath string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if info.IsDir() {
				return nil
			}

			relPath, err := filepath.Rel(redc.TemplateDir, filePath)
			if err != nil {
				return nil
			}

			// Read file content
			content, err := os.ReadFile(filePath)
			if err != nil {
				return nil
			}

			// Add to zip - use relPath directly (already includes template name)
			w, err := zipWriter.Create(relPath)
			if err != nil {
				return nil
			}
			w.Write(content)
			return nil
		})
		if err != nil {
			continue
		}
	}

	zipWriter.Close()
	zipFile.Close()

	return zipPath, nil
}

func (a *App) ImportTemplates(zipPath string) ([]string, error) {
	reader, err := zip.OpenReader(zipPath)
	if err != nil {
		return nil, err
	}
	defer reader.Close()

	imported := []string{}
	importedSet := make(map[string]bool)

	for _, file := range reader.File {
		// Skip directories
		if file.FileInfo().IsDir() {
			continue
		}

		name := file.Name
		// ZIP path is already correct, e.g., "aliyun/ecs/case.json"
		// Extract template name for tracking
		parts := strings.Split(name, "/")
		if len(parts) < 2 {
			continue
		}
		templateName := strings.Join(parts[:len(parts)-1], "/")

		// Extract file to TemplateDir
		destPath := filepath.Join(redc.TemplateDir, name)
		srcFile, err := file.Open()
		if err != nil {
			continue
		}
		defer srcFile.Close()

		// Create parent directories
		if err := os.MkdirAll(filepath.Dir(destPath), 0755); err != nil {
			continue
		}

		destFile, err := os.Create(destPath)
		if err != nil {
			continue
		}
		defer destFile.Close()

		if _, err := io.Copy(destFile, srcFile); err != nil {
			continue
		}

		// Track imported templates (use full template path)
		if !importedSet[templateName] {
			importedSet[templateName] = true
			imported = append(imported, templateName)
		}
	}

	// Validate each imported template: must have case.json with valid RedcTmpl structure
	var valid []string
	var invalid []string
	for _, tplName := range imported {
		tplDir := filepath.Join(redc.TemplateDir, tplName)
		casePath := filepath.Join(tplDir, redc.TmplCaseFile)
		data, err := os.ReadFile(casePath)
		if err != nil {
			invalid = append(invalid, tplName)
			os.RemoveAll(tplDir)
			continue
		}
		var tmpl redc.RedcTmpl
		if err := json.Unmarshal(data, &tmpl); err != nil {
			invalid = append(invalid, tplName)
			os.RemoveAll(tplDir)
			continue
		}
		valid = append(valid, tplName)
	}

	if len(valid) == 0 && len(invalid) > 0 {
		docURL := "https://github.com/wgpsec/redc-template/blob/master/WRITING_TEMPLATES_CN.md"
		if i18n.GetLang() == "en" {
			docURL = "https://github.com/wgpsec/redc-template/blob/master/WRITING_TEMPLATES_EN.md"
		}
		return nil, fmt.Errorf("%s", i18n.Tf("app_template_import_invalid", strings.Join(invalid, ", "), docURL))
	}
	if len(invalid) > 0 {
		gologger.Warning().Msgf("import: skipped invalid templates: %s", strings.Join(invalid, ", "))
	}

	return valid, nil
}

func (a *App) CopyFileTo(sourcePath string, destPath string) error {
	absSource, err := filepath.Abs(sourcePath)
	if err != nil {
		return fmt.Errorf("invalid source path: %w", err)
	}
	absDest, err := filepath.Abs(destPath)
	if err != nil {
		return fmt.Errorf("invalid dest path: %w", err)
	}
	allowedBase, _ := filepath.Abs(redc.RedcPath)
	if allowedBase == "" {
		return fmt.Errorf("redc path not configured")
	}
	if !strings.HasPrefix(absSource, allowedBase+string(filepath.Separator)) && absSource != allowedBase {
		return fmt.Errorf("source path outside allowed directory")
	}
	if !strings.HasPrefix(absDest, allowedBase+string(filepath.Separator)) && absDest != allowedBase {
		return fmt.Errorf("dest path outside allowed directory")
	}

	sourceFile, err := os.Open(absSource)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destDir := filepath.Dir(absDest)
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return err
	}

	destFile, err := os.Create(absDest)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, sourceFile)
	return err
}

// validTemplateName checks if a template name is safe (allows letters, digits, -, _, /)
var validTemplateNameRe = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_\-/]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$`)

// CreateLocalTemplate creates a new empty template directory with scaffold files
func (a *App) CreateLocalTemplate(name string, scaffold string) error {
	name = strings.TrimSpace(name)
	if name == "" {
		return fmt.Errorf("%s", i18n.T("app_template_name_empty"))
	}
	if !validTemplateNameRe.MatchString(name) {
		return fmt.Errorf("%s", i18n.T("app_template_name_invalid"))
	}
	// Block path traversal
	if strings.Contains(name, "..") {
		return fmt.Errorf("%s", i18n.T("app_template_name_invalid"))
	}

	tmplPath := filepath.Join(redc.TemplateDir, name)
	if _, err := os.Stat(tmplPath); err == nil {
		return fmt.Errorf("%s", i18n.T("app_template_already_exists"))
	}

	if err := os.MkdirAll(tmplPath, 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	// Write scaffold files
	files := scaffoldFiles(scaffold, name)
	for fname, content := range files {
		if err := os.WriteFile(filepath.Join(tmplPath, fname), []byte(content), 0644); err != nil {
			return fmt.Errorf("failed to write %s: %w", fname, err)
		}
	}

	a.emitLog(i18n.Tf("app_template_create_success", name))
	a.emitRefresh()
	return nil
}

func scaffoldFiles(scaffold string, name string) map[string]string {
	baseName := filepath.Base(name)

	makeCaseJSON := func(tmplType string) string {
		return fmt.Sprintf(`{
  "name": "%s",
  "description": "",
  "version": "1.0.0",
  "user": "",
  "template": "%s"
}`, baseName, tmplType)
	}

	mainTF := `# =============================================================================
# Terraform Main Configuration
# =============================================================================
#
# Configure your provider and resources below.
#
# Example provider block:
#   terraform {
#     required_providers {
#       alicloud = {
#         source  = "aliyun/alicloud"
#         version = "~> 1.200"
#       }
#     }
#   }
#
#   provider "alicloud" {
#     region = var.region
#   }
#
# Example resource block:
#   resource "alicloud_instance" "main" {
#     instance_type        = var.instance_type
#     image_id             = "ubuntu_22_04_x64_20G_alibase_20230815.vhd"
#     security_groups      = [alicloud_security_group.default.id]
#     vswitch_id           = alicloud_vswitch.default.id
#     instance_name        = var.instance_name
#     system_disk_category = "cloud_efficiency"
#     user_data            = file("userdata")
#   }
#
`

	variablesTF := `# =============================================================================
# Input Variables
# =============================================================================
#
# Define your input variables here.
#
# variable "region" {
#   description = "Cloud region"
#   type        = string
#   default     = "cn-hangzhou"
# }
#
# variable "instance_type" {
#   description = "Instance type"
#   type        = string
#   default     = "ecs.t6-c1m1.large"
# }
#
# variable "instance_name" {
#   description = "Instance name"
#   type        = string
#   default     = "redc-instance"
# }
#
# variable "instance_password" {
#   description = "Instance password"
#   type        = string
#   sensitive   = true
# }
`

	outputsTF := `# =============================================================================
# Outputs
# =============================================================================
#
# Define your outputs here. Outputs with "ip" in the name will be used
# by redc for SSH connections.
#
# output "ip" {
#   value = alicloud_instance.main.public_ip
# }
#
# output "password" {
#   value     = var.instance_password
#   sensitive = true
# }
`

	switch scaffold {
	case "preset":
		return map[string]string{
			"case.json":    makeCaseJSON("preset"),
			"main.tf":      mainTF,
			"variables.tf": variablesTF,
			"outputs.tf":   outputsTF,
		}
	case "preset-userdata":
		return map[string]string{
			"case.json":    makeCaseJSON("preset"),
			"main.tf":      mainTF,
			"variables.tf": variablesTF,
			"outputs.tf":   outputsTF,
			"userdata":     "#!/bin/bash\n# Add your initialization script here\necho \"Hello from redc\"\n",
		}
	case "base":
		return map[string]string{
			"case.json":    makeCaseJSON("base"),
			"main.tf":      mainTF,
			"variables.tf": variablesTF,
			"outputs.tf":   outputsTF,
		}
	case "userdata":
		userdataCaseJSON := fmt.Sprintf(`{
  "name": "%s",
  "description": "",
  "version": "1.0.0",
  "user": "",
  "type": "bash",
  "category": "custom",
  "template": "userdata"
}`, baseName)
		return map[string]string{
			"case.json": userdataCaseJSON,
			"userdata":  "#!/bin/bash\n# Add your initialization script here\necho \"Hello from redc\"\n",
		}
	case "compose":
		composeCaseJSON := fmt.Sprintf(`{
  "name": "%s",
  "description": "",
  "version": "1.0.0",
  "user": "",
  "template": "compose"
}`, baseName)
		composeYAML := `version: "3.9"

# =============================================================================
# Redc Compose - 多云编排配置
# =============================================================================
#
# 使用 redc compose up redc-compose.yaml 启动编排
# 使用 redc compose down -f redc-compose.yaml 销毁环境
# 使用 redc compose config redc-compose.yaml 预览配置
#

services:

  # 示例服务 - 修改 image 为你的模板路径 (如 aliyun/ecs)
  # my_server:
  #   image: aliyun/ecs
  #   container_name: my_ecs_instance
  #   environment:
  #     - instance_type=ecs.e-c1m2.large
  #     - password=YourPassword123
  #   command: |
  #     echo "实例初始化完成"
  #     uptime
`
		return map[string]string{
			"case.json":         composeCaseJSON,
			"redc-compose.yaml": composeYAML,
		}
	default: // backward compat — treat as preset
		return map[string]string{
			"case.json":    makeCaseJSON("preset"),
			"main.tf":      mainTF,
			"variables.tf": variablesTF,
			"outputs.tf":   outputsTF,
		}
	}
}

// DeleteTemplateFile deletes a single file from a template directory
func (a *App) DeleteTemplateFile(templateName string, fileName string) error {
	tmplPath, err := redc.GetTemplatePath(templateName)
	if err != nil {
		return err
	}

	// Safety: ensure fileName doesn't contain path traversal
	if strings.Contains(fileName, "..") || strings.Contains(fileName, "/") || strings.Contains(fileName, "\\") {
		return fmt.Errorf("invalid file name")
	}

	filePath := filepath.Join(tmplPath, fileName)
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return fmt.Errorf("file not found: %s", fileName)
	}

	if err := os.Remove(filePath); err != nil {
		return fmt.Errorf("failed to delete file: %w", err)
	}

	a.emitLog(fmt.Sprintf("Deleted file %s from template %s", fileName, templateName))
	return nil
}

// TemplateValidateResult holds the result of a terraform validate run
type TemplateValidateResult struct {
	Valid        bool                         `json:"valid"`
	ErrorCount   int                          `json:"error_count"`
	WarningCount int                          `json:"warning_count"`
	Diagnostics  []TemplateValidateDiagnostic `json:"diagnostics"`
}

// TemplateValidateDiagnostic represents a single validation diagnostic
type TemplateValidateDiagnostic struct {
	Severity string `json:"severity"`
	Summary  string `json:"summary"`
	Detail   string `json:"detail"`
	Filename string `json:"filename"`
	Line     int    `json:"line"`
}

// ValidateTemplate runs terraform init + validate on a template to check syntax
func (a *App) ValidateTemplate(templateName string) (*TemplateValidateResult, error) {
	tmplPath, err := redc.GetTemplatePath(templateName)
	if err != nil {
		return nil, fmt.Errorf("%s", i18n.Tf("app_template_not_found", templateName))
	}

	a.emitLog(i18n.Tf("app_template_validate_start", templateName))

	// Step 1: terraform init (needed before validate)
	if err := redc.TfInit(tmplPath); err != nil {
		return &TemplateValidateResult{
			Valid:      false,
			ErrorCount: 1,
			Diagnostics: []TemplateValidateDiagnostic{
				{Severity: "error", Summary: "terraform init failed", Detail: err.Error()},
			},
		}, nil
	}

	// Step 2: terraform validate
	output, err := redc.TfValidate(tmplPath)
	if err != nil {
		return &TemplateValidateResult{
			Valid:      false,
			ErrorCount: 1,
			Diagnostics: []TemplateValidateDiagnostic{
				{Severity: "error", Summary: "terraform validate failed", Detail: err.Error()},
			},
		}, nil
	}

	result := &TemplateValidateResult{
		Valid:        output.Valid,
		ErrorCount:   output.ErrorCount,
		WarningCount: output.WarningCount,
	}

	for _, d := range output.Diagnostics {
		diag := TemplateValidateDiagnostic{
			Severity: string(d.Severity),
			Summary:  d.Summary,
			Detail:   d.Detail,
		}
		if d.Range != nil {
			diag.Filename = d.Range.Filename
			diag.Line = d.Range.Start.Line
		}
		result.Diagnostics = append(result.Diagnostics, diag)
	}

	if result.Valid {
		a.emitLog(i18n.Tf("app_template_validate_success", templateName))
	} else {
		a.emitLog(i18n.Tf("app_template_validate_failed", templateName))
	}

	return result, nil
}
