// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package vet

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/config"
)

type Workload string

const (
	WorkloadSourceVetting       Workload = "source_vetting"
	WorkloadAlertClassification Workload = "alert_classification"
	WorkloadConflictAnalysis    Workload = "conflict_analysis"
	WorkloadTerrorAnalysis      Workload = "terror_analysis"
)

type ModelResolutionStatus struct {
	Endpoint           string   `json:"endpoint"`
	Workload           Workload `json:"workload"`
	ConfiguredModel    string   `json:"configured_model"`
	ResolvedModel      string   `json:"resolved_model"`
	InventoryFetchedAt string   `json:"inventory_fetched_at,omitempty"`
	LastSuccessAt      string   `json:"last_success_at,omitempty"`
	LastError          string   `json:"last_error,omitempty"`
	InventoryError     string   `json:"inventory_error,omitempty"`
	PromptTokens       int      `json:"prompt_tokens,omitempty"`
	CompletionTokens   int      `json:"completion_tokens,omitempty"`
	TotalTokens        int      `json:"total_tokens,omitempty"`
	CostUSD            float64  `json:"cost_usd,omitempty"`
	Requests           int      `json:"requests,omitempty"`
	CumulativeTokens   int      `json:"cumulative_tokens,omitempty"`
	CumulativeCostUSD  float64  `json:"cumulative_cost_usd,omitempty"`
}

type modelInventory struct {
	mu            sync.Mutex
	models        []string
	fetchedAt     time.Time
	lastAttemptAt time.Time
	lastError     string
}

var modelRegistry = struct {
	sync.RWMutex
	inventories map[string]*modelInventory
	statuses    map[string]ModelResolutionStatus
}{
	inventories: map[string]*modelInventory{},
	statuses:    map[string]ModelResolutionStatus{},
}

type modelsResponse struct {
	Data []struct {
		ID      string   `json:"id"`
		Aliases []string `json:"aliases"`
	} `json:"data"`
	Models []struct {
		ID      string   `json:"id"`
		Name    string   `json:"name"`
		Aliases []string `json:"aliases"`
	} `json:"models"`
}

func modelsURL(baseURL string) string {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	baseURL = strings.TrimSuffix(baseURL, "/chat/completions")
	if baseURL == "" {
		return "https://api.openai.com/v1/models"
	}
	return strings.TrimRight(baseURL, "/") + "/models"
}

func inventoryFor(endpoint string) *modelInventory {
	modelRegistry.Lock()
	defer modelRegistry.Unlock()
	inv := modelRegistry.inventories[endpoint]
	if inv == nil {
		inv = &modelInventory{}
		modelRegistry.inventories[endpoint] = inv
	}
	return inv
}

func fetchModels(ctx context.Context, httpClient *http.Client, baseURL, apiKey string) ([]string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, modelsURL(baseURL), nil)
	if err != nil {
		return nil, fmt.Errorf("build model inventory request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if strings.TrimSpace(apiKey) != "" {
		req.Header.Set("Authorization", "Bearer "+strings.TrimSpace(apiKey))
	}
	res, err := httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request model inventory: %w", err)
	}
	defer res.Body.Close()
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		return nil, fmt.Errorf("model inventory endpoint status %d", res.StatusCode)
	}
	var payload modelsResponse
	if err := json.NewDecoder(io.LimitReader(res.Body, 4<<20)).Decode(&payload); err != nil {
		return nil, fmt.Errorf("decode model inventory: %w", err)
	}
	seen := map[string]struct{}{}
	add := func(value string) {
		value = strings.TrimSpace(value)
		if value != "" {
			seen[value] = struct{}{}
		}
	}
	for _, item := range payload.Data {
		add(item.ID)
		for _, alias := range item.Aliases {
			add(alias)
		}
	}
	for _, item := range payload.Models {
		add(item.ID)
		add(item.Name)
		for _, alias := range item.Aliases {
			add(alias)
		}
	}
	if len(seen) == 0 {
		return nil, fmt.Errorf("model inventory returned no model identifiers")
	}
	models := make([]string, 0, len(seen))
	for model := range seen {
		models = append(models, model)
	}
	sort.Strings(models)
	return models, nil
}

func resolveAvailableModel(models []string, preferred string, fallbacks []string, workload Workload) string {
	available := make(map[string]string, len(models))
	for _, model := range models {
		available[strings.ToLower(strings.TrimSpace(model))] = strings.TrimSpace(model)
	}
	for _, candidate := range append([]string{preferred}, fallbacks...) {
		if model := available[strings.ToLower(strings.TrimSpace(candidate))]; model != "" {
			return model
		}
	}
	type scoredModel struct {
		name  string
		score int
	}
	scored := make([]scoredModel, 0, len(models))
	for _, model := range models {
		name := strings.ToLower(model)
		if containsModelKind(name, "embed", "image", "audio", "whisper", "tts", "moderation", "rerank", "transcri", "realtime", "code", "build") {
			continue
		}
		score := 0
		if containsModelKind(name, "chat", "instruct") {
			score += 10
		}
		if containsModelKind(name, "latest") {
			score += 8
		}
		switch workload {
		case WorkloadSourceVetting, WorkloadAlertClassification:
			if containsModelKind(name, "mini", "small", "fast", "flash") {
				score += 30
			}
			if containsModelKind(name, "non-reasoning", "nonreasoning") {
				score += 15
			}
		case WorkloadConflictAnalysis, WorkloadTerrorAnalysis:
			if containsModelKind(name, "mini", "small") {
				score -= 5
			}
			if containsModelKind(name, "reasoning") && !containsModelKind(name, "non-reasoning", "nonreasoning") {
				score -= 5
			}
		}
		scored = append(scored, scoredModel{name: model, score: score})
	}
	if len(scored) == 0 {
		return strings.TrimSpace(preferred)
	}
	sort.SliceStable(scored, func(i, j int) bool {
		if scored[i].score == scored[j].score {
			return scored[i].name > scored[j].name
		}
		return scored[i].score > scored[j].score
	})
	return scored[0].name
}

func containsModelKind(model string, needles ...string) bool {
	for _, needle := range needles {
		if strings.Contains(model, needle) {
			return true
		}
	}
	return false
}

func mergeModelFallbacks(configured []string, preferred string) []string {
	seen := map[string]struct{}{strings.ToLower(strings.TrimSpace(preferred)): {}}
	out := make([]string, 0, len(configured))
	for _, candidate := range configured {
		candidate = strings.TrimSpace(candidate)
		key := strings.ToLower(candidate)
		if candidate == "" {
			continue
		}
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, candidate)
	}
	return out
}

func statusKey(endpoint string, workload Workload) string {
	return endpoint + "|" + string(workload)
}

func updateModelStatus(endpoint string, workload Workload, update func(*ModelResolutionStatus)) {
	modelRegistry.Lock()
	defer modelRegistry.Unlock()
	key := statusKey(endpoint, workload)
	status := modelRegistry.statuses[key]
	status.Endpoint = endpoint
	status.Workload = workload
	update(&status)
	modelRegistry.statuses[key] = status
}

func ModelResolutionStatuses() []ModelResolutionStatus {
	modelRegistry.RLock()
	defer modelRegistry.RUnlock()
	out := make([]ModelResolutionStatus, 0, len(modelRegistry.statuses))
	for _, status := range modelRegistry.statuses {
		out = append(out, status)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Endpoint == out[j].Endpoint {
			return out[i].Workload < out[j].Workload
		}
		return out[i].Endpoint < out[j].Endpoint
	})
	return out
}

func ProbeModels(ctx context.Context, cfg config.Config) ([]string, error) {
	timeout := time.Duration(cfg.VettingTimeoutMS) * time.Millisecond
	if timeout <= 0 {
		timeout = 45 * time.Second
	}
	client := &http.Client{Timeout: timeout}
	models, err := fetchModels(ctx, client, cfg.VettingBaseURL, cfg.VettingAPIKey)
	endpoint := modelsURL(cfg.VettingBaseURL)
	inv := inventoryFor(endpoint)
	inv.mu.Lock()
	defer inv.mu.Unlock()
	inv.lastAttemptAt = time.Now().UTC()
	if err != nil {
		inv.lastError = err.Error()
		updateModelStatus(endpoint, WorkloadSourceVetting, func(status *ModelResolutionStatus) {
			status.ConfiguredModel = cfg.VettingModel
			status.ResolvedModel = cfg.VettingModel
			status.InventoryError = err.Error()
		})
		return nil, err
	}
	inv.models = append([]string(nil), models...)
	inv.fetchedAt = time.Now().UTC()
	inv.lastError = ""
	resolved := resolveAvailableModel(models, cfg.VettingModel, cfg.VettingModelFallbacks, WorkloadSourceVetting)
	updateModelStatus(endpoint, WorkloadSourceVetting, func(status *ModelResolutionStatus) {
		status.ConfiguredModel = cfg.VettingModel
		status.ResolvedModel = resolved
		status.InventoryFetchedAt = inv.fetchedAt.Format(time.RFC3339)
		status.InventoryError = ""
	})
	return models, nil
}
