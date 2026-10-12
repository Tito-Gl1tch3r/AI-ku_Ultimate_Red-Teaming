package main

import (
	redc "red-cloud/mod"
	"sort"
)

func (a *App) templateSourceManager() (*redc.TemplateSourceManager, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.templateSources != nil {
		return a.templateSources, nil
	}
	manager, err := redc.LoadConfiguredTemplateSourceManager()
	if err != nil {
		return nil, err
	}
	a.templateSources = manager
	return manager, nil
}

// ListTemplateSources returns the configured local template sources.
func (a *App) ListTemplateSources() ([]redc.TemplateSource, error) {
	manager, err := a.templateSourceManager()
	if err != nil {
		return nil, err
	}
	return manager.ListSources(), nil
}

// AddLocalTemplateSource adds and persists a read-only local directory source.
func (a *App) AddLocalTemplateSource(name, path string) (redc.TemplateSource, error) {
	manager, err := a.templateSourceManager()
	if err != nil {
		return redc.TemplateSource{}, err
	}
	source, err := manager.AddLocalSource(name, path)
	if err != nil {
		return redc.TemplateSource{}, err
	}
	if _, err := manager.ScanSource(source.ID); err != nil {
		// The source remains configured so the GUI can display and repair it.
	}
	if err := manager.Save(); err != nil {
		return redc.TemplateSource{}, err
	}
	for _, current := range manager.ListSources() {
		if current.ID == source.ID {
			return current, nil
		}
	}
	return source, nil
}

// UpdateTemplateSource updates mutable source settings and persists them.
func (a *App) UpdateTemplateSource(source redc.TemplateSource) error {
	manager, err := a.templateSourceManager()
	if err != nil {
		return err
	}
	if err := manager.UpdateSource(source); err != nil {
		return err
	}
	return manager.Save()
}

// RemoveTemplateSource removes only the source configuration. Installed
// templates and files in the source directory are left untouched.
func (a *App) RemoveTemplateSource(sourceID string) error {
	manager, err := a.templateSourceManager()
	if err != nil {
		return err
	}
	if err := manager.RemoveSource(sourceID); err != nil {
		return err
	}
	return manager.Save()
}

// ScanTemplateSource refreshes source health and template count.
func (a *App) ScanTemplateSource(sourceID string) ([]redc.ResolvedTemplate, error) {
	manager, err := a.templateSourceManager()
	if err != nil {
		return nil, err
	}
	templates, scanErr := manager.ScanSource(sourceID)
	if err := manager.Save(); err != nil && scanErr == nil {
		return nil, err
	}
	return templates, scanErr
}

// InstallTemplateFromSource copies a merged local template into redc/templates.
func (a *App) InstallTemplateFromSource(name string, force bool) (string, error) {
	manager, err := a.templateSourceManager()
	if err != nil {
		return "", err
	}
	path, err := manager.InstallTemplate(name, force)
	if err != nil {
		return "", err
	}
	a.emitRefresh()
	return path, nil
}

// FetchMergedTemplateRegistry combines the official registry with enabled
// local sources. Local entries win name conflicts.
func (a *App) FetchMergedTemplateRegistry(registryURL string) ([]RegistryTemplate, error) {
	remote, remoteErr := a.FetchRegistryTemplates(registryURL)
	manager, err := a.templateSourceManager()
	if err != nil {
		if remoteErr != nil {
			return nil, remoteErr
		}
		return remote, nil
	}
	local, localErr := manager.ListMergedTemplates()
	if localErr != nil {
		return nil, localErr
	}
	conflicts, conflictErr := manager.ListTemplateConflicts()
	if conflictErr != nil {
		return nil, conflictErr
	}
	result := mergeLocalRegistryTemplates(remote, local, conflicts)
	if len(result) == 0 && remoteErr != nil {
		return nil, remoteErr
	}
	return result, nil
}

func mergeLocalRegistryTemplates(remote []RegistryTemplate, local []redc.ResolvedTemplate, conflicts []redc.TemplateConflict) []RegistryTemplate {
	byName := make(map[string]RegistryTemplate, len(remote)+len(local))
	remoteNames := make(map[string]bool, len(remote))
	for _, template := range remote {
		if template.SourceType == "" {
			template.SourceType = string(redc.TemplateSourceRemote)
			template.SourceID = "official"
			template.SourceName = "Official"
		}
		byName[template.Name] = template
		remoteNames[template.Name] = true
	}
	localConflicts := make(map[string][]string, len(conflicts))
	for _, conflict := range conflicts {
		for _, source := range conflict.ShadowedSources {
			localConflicts[conflict.TemplateName] = append(localConflicts[conflict.TemplateName], source.Name)
		}
	}
	for _, resolved := range local {
		template := resolved.Template
		installed, localVersion, _ := redc.CheckLocalImage(template.Name)
		conflictSources := append([]string(nil), localConflicts[template.Name]...)
		if remoteNames[template.Name] && resolved.Source.Priority < 0 {
			official := byName[template.Name]
			official.ConflictSources = append(official.ConflictSources, resolved.Source.Name)
			official.ConflictSources = append(official.ConflictSources, conflictSources...)
			official.ConflictCount = len(official.ConflictSources)
			byName[template.Name] = official
			continue
		}
		if remoteNames[template.Name] {
			conflictSources = append(conflictSources, "Official")
		}
		byName[template.Name] = RegistryTemplate{
			Name:            template.Name,
			Description:     template.Description,
			DescriptionEN:   template.DescriptionEN,
			Author:          template.User,
			Latest:          template.Version,
			Versions:        []string{template.Version},
			Tags:            template.Tags,
			Installed:       installed,
			LocalVer:        localVersion,
			SourceType:      string(resolved.Source.Type),
			SourceID:        resolved.Source.ID,
			SourceName:      resolved.Source.Name,
			ConflictCount:   len(conflictSources),
			ConflictSources: conflictSources,
		}
	}
	result := make([]RegistryTemplate, 0, len(byName))
	for _, template := range byName {
		result = append(result, template)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Name < result[j].Name })
	return result
}
