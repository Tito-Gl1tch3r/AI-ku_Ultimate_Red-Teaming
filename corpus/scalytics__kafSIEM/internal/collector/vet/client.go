// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package vet

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/config"
)

// ErrCircuitOpen is returned without contacting the endpoint after repeated
// consecutive failures. Callers should treat it as "LLM unavailable" and skip
// per-item logging; the failures that tripped the breaker were already logged.
var ErrCircuitOpen = errors.New("llm endpoint circuit open")

const (
	breakerFailureThreshold = 3
	breakerCooldown         = 10 * time.Minute
)

// Breaker state is shared per completions URL, not per Client: clients are
// constructed at many call sites, so instance state would reset constantly.
type breaker struct {
	mu        sync.Mutex
	failures  int
	openUntil time.Time
}

var (
	breakersMu sync.Mutex
	breakers   = map[string]*breaker{}
)

func breakerFor(url string) *breaker {
	breakersMu.Lock()
	defer breakersMu.Unlock()
	b, ok := breakers[url]
	if !ok {
		b = &breaker{}
		breakers[url] = b
	}
	return b
}

func (b *breaker) open() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return time.Now().Before(b.openUntil)
}

func (b *breaker) recordFailure() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.failures++
	if b.failures >= breakerFailureThreshold {
		b.openUntil = time.Now().Add(breakerCooldown)
		b.failures = 0
	}
}

func (b *breaker) recordSuccess() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.failures = 0
	b.openUntil = time.Time{}
}

type Client struct {
	httpClient      *http.Client
	baseURL         string
	apiKey          string
	model           string
	configuredModel string
	modelFallbacks  []string
	temperature     float64
	breaker         *breaker
	workload        Workload
	discoverModels  bool
	modelRefresh    time.Duration
	maxOutputTokens int
}

func NewClient(cfg config.Config) *Client {
	return NewClientForWorkload(cfg, WorkloadSourceVetting)
}

func NewClientForWorkload(cfg config.Config, workload Workload) *Client {
	timeout := time.Duration(cfg.VettingTimeoutMS) * time.Millisecond
	if timeout <= 0 {
		timeout = 45 * time.Second
	}
	baseURL := strings.TrimSpace(cfg.VettingBaseURL)
	refresh := time.Duration(cfg.LLMModelRefreshHours) * time.Hour
	if refresh <= 0 {
		refresh = 7 * 24 * time.Hour
	}
	model := strings.TrimSpace(cfg.VettingModel)
	modelFallbacks := mergeModelFallbacks(cfg.VettingModelFallbacks, model)
	maxOutputTokens := cfg.LLMMaxOutputTokens
	if maxOutputTokens <= 0 {
		maxOutputTokens = 1200
	}
	return &Client{
		httpClient:      &http.Client{Timeout: timeout},
		baseURL:         baseURL,
		apiKey:          strings.TrimSpace(cfg.VettingAPIKey),
		model:           model,
		configuredModel: model,
		modelFallbacks:  modelFallbacks,
		temperature:     cfg.VettingTemperature,
		breaker:         breakerFor(completionsURL(baseURL)),
		workload:        workload,
		discoverModels:  cfg.LLMModelDiscoveryEnabled,
		modelRefresh:    refresh,
		maxOutputTokens: maxOutputTokens,
	}
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float64   `json:"temperature,omitempty"`
	MaxTokens   int       `json:"max_tokens,omitempty"`
}

type chatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int   `json:"prompt_tokens"`
		CompletionTokens int   `json:"completion_tokens"`
		TotalTokens      int   `json:"total_tokens"`
		CostUSDTicks     int64 `json:"cost_in_usd_ticks"`
	} `json:"usage"`
}

func (c *Client) Complete(ctx context.Context, messages []Message) (string, error) {
	if c.breaker.open() {
		return "", ErrCircuitOpen
	}
	c.model = c.resolveModel(ctx, false)
	content, status, err := c.completeWithModel(ctx, messages, c.model)
	if err != nil && status == http.StatusNotFound {
		previous := c.model
		if c.discoverModels {
			c.model = c.resolveModel(ctx, true)
		}
		if c.model == "" || c.model == previous {
			c.model = c.nextFallback(previous)
		}
		if c.model != "" && c.model != previous {
			content, _, retryErr := c.completeWithModel(ctx, messages, c.model)
			return content, retryErr
		}
	}
	return content, err
}

func (c *Client) nextFallback(current string) string {
	current = strings.ToLower(strings.TrimSpace(current))
	for _, candidate := range c.modelFallbacks {
		if strings.ToLower(strings.TrimSpace(candidate)) != current {
			return strings.TrimSpace(candidate)
		}
	}
	return ""
}

func (c *Client) ResolvedModel() string {
	return strings.TrimSpace(c.model)
}

func (c *Client) resolveModel(ctx context.Context, force bool) string {
	if !c.discoverModels {
		return c.configuredModel
	}
	endpoint := modelsURL(c.baseURL)
	inv := inventoryFor(endpoint)
	inv.mu.Lock()
	defer inv.mu.Unlock()
	now := time.Now().UTC()
	if force || inv.lastAttemptAt.IsZero() || now.Sub(inv.lastAttemptAt) >= c.modelRefresh {
		inv.lastAttemptAt = now
		models, err := fetchModels(ctx, c.httpClient, c.baseURL, c.apiKey)
		if err != nil {
			inv.lastError = err.Error()
			resolved := c.configuredModel
			if len(inv.models) > 0 {
				resolved = resolveAvailableModel(inv.models, c.configuredModel, c.modelFallbacks, c.workload)
			}
			updateModelStatus(endpoint, c.workload, func(status *ModelResolutionStatus) {
				status.ConfiguredModel = c.configuredModel
				status.ResolvedModel = resolved
				if !inv.fetchedAt.IsZero() {
					status.InventoryFetchedAt = inv.fetchedAt.Format(time.RFC3339)
				}
				status.InventoryError = err.Error()
			})
			return resolved
		}
		inv.models = models
		inv.fetchedAt = now
		inv.lastError = ""
	}
	resolved := resolveAvailableModel(inv.models, c.configuredModel, c.modelFallbacks, c.workload)
	if resolved == "" {
		resolved = c.configuredModel
	}
	updateModelStatus(endpoint, c.workload, func(status *ModelResolutionStatus) {
		status.ConfiguredModel = c.configuredModel
		status.ResolvedModel = resolved
		status.InventoryFetchedAt = inv.fetchedAt.Format(time.RFC3339)
		status.InventoryError = inv.lastError
	})
	return resolved
}

func (c *Client) completeWithModel(ctx context.Context, messages []Message, model string) (string, int, error) {
	reqBody, err := json.Marshal(chatRequest{
		Model:       model,
		Messages:    messages,
		Temperature: c.temperature,
		MaxTokens:   c.maxOutputTokens,
	})
	if err != nil {
		return "", 0, fmt.Errorf("marshal source vetting request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, completionsURL(c.baseURL), bytes.NewReader(reqBody))
	if err != nil {
		return "", 0, fmt.Errorf("build source vetting request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}
	res, err := c.httpClient.Do(req)
	if err != nil {
		// A caller-cancelled context is not an endpoint failure.
		if ctx.Err() != context.Canceled {
			c.breaker.recordFailure()
		}
		return "", 0, fmt.Errorf("request source vetting completion: %w", err)
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		c.breaker.recordFailure()
		return "", res.StatusCode, fmt.Errorf("read source vetting response: %w", err)
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		if res.StatusCode != http.StatusNotFound {
			c.breaker.recordFailure()
		}
		err := fmt.Errorf("source vetting endpoint status %d: %s", res.StatusCode, strings.TrimSpace(string(body)))
		updateModelStatus(modelsURL(c.baseURL), c.workload, func(status *ModelResolutionStatus) {
			status.ConfiguredModel = c.configuredModel
			status.ResolvedModel = model
			status.LastError = err.Error()
		})
		return "", res.StatusCode, err
	}
	c.breaker.recordSuccess()

	var parsed chatResponse
	if err := json.Unmarshal(body, &parsed); err != nil {
		return "", res.StatusCode, fmt.Errorf("decode source vetting response: %w", err)
	}
	if len(parsed.Choices) == 0 {
		return "", res.StatusCode, fmt.Errorf("source vetting response returned no choices")
	}
	updateModelStatus(modelsURL(c.baseURL), c.workload, func(status *ModelResolutionStatus) {
		status.ConfiguredModel = c.configuredModel
		status.ResolvedModel = model
		status.LastSuccessAt = time.Now().UTC().Format(time.RFC3339)
		status.LastError = ""
		status.PromptTokens = parsed.Usage.PromptTokens
		status.CompletionTokens = parsed.Usage.CompletionTokens
		status.TotalTokens = parsed.Usage.TotalTokens
		status.CostUSD = float64(parsed.Usage.CostUSDTicks) / 10_000_000_000
		status.Requests++
		status.CumulativeTokens += parsed.Usage.TotalTokens
		status.CumulativeCostUSD += status.CostUSD
	})
	return strings.TrimSpace(parsed.Choices[0].Message.Content), res.StatusCode, nil
}

func completionsURL(baseURL string) string {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		return "https://api.openai.com/v1/chat/completions"
	}
	if strings.HasSuffix(baseURL, "/chat/completions") {
		return baseURL
	}
	return baseURL + "/chat/completions"
}
