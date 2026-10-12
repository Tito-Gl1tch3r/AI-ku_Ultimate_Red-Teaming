// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package vet

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/config"
)

func TestClientCompleteUsesOpenAICompatibleEndpoint(t *testing.T) {
	var gotAuth string
	var gotModel string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/models" {
			_ = json.NewEncoder(w).Encode(map[string]any{"data": []map[string]any{{"id": "gpt-test"}}})
			return
		}
		if r.URL.Path != "/v1/chat/completions" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		gotAuth = r.Header.Get("Authorization")
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		gotModel, _ = payload["model"].(string)
		_ = json.NewEncoder(w).Encode(map[string]any{
			"choices": []map[string]any{
				{"message": map[string]any{"content": `{"approve":true}`}},
			},
		})
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.VettingAPIKey = "secret"
	cfg.VettingModel = "gpt-test"
	client := NewClient(cfg)
	content, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "test"}})
	if err != nil {
		t.Fatal(err)
	}
	if gotAuth != "Bearer secret" {
		t.Fatalf("expected bearer auth header, got %q", gotAuth)
	}
	if gotModel != "gpt-test" {
		t.Fatalf("expected model gpt-test, got %q", gotModel)
	}
	if content != `{"approve":true}` {
		t.Fatalf("unexpected content %q", content)
	}
}

func TestCompletionsURLNormalizesBase(t *testing.T) {
	if got := completionsURL("http://localhost:11434/v1"); got != "http://localhost:11434/v1/chat/completions" {
		t.Fatalf("unexpected ollama/vllm url %q", got)
	}
	if got := completionsURL("https://gateway.example/openai/v1/chat/completions"); got != "https://gateway.example/openai/v1/chat/completions" {
		t.Fatalf("unexpected passthrough url %q", got)
	}
	if got := modelsURL("https://gateway.example/openai/v1/chat/completions"); got != "https://gateway.example/openai/v1/models" {
		t.Fatalf("unexpected models url %q", got)
	}
}

func TestClientCircuitBreakerTripsAfterConsecutiveFailures(t *testing.T) {
	var requests int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		http.Error(w, `{"error":"credits exhausted"}`, http.StatusForbidden)
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.LLMModelDiscoveryEnabled = false
	client := NewClient(cfg)

	for i := 0; i < breakerFailureThreshold; i++ {
		if _, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}}); err == nil {
			t.Fatal("expected failure")
		}
	}
	if requests != breakerFailureThreshold {
		t.Fatalf("expected %d requests before trip, got %d", breakerFailureThreshold, requests)
	}

	_, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}})
	if !errors.Is(err, ErrCircuitOpen) {
		t.Fatalf("expected ErrCircuitOpen, got %v", err)
	}
	if requests != breakerFailureThreshold {
		t.Fatalf("open circuit must not contact endpoint, got %d requests", requests)
	}

	// A second client for the same endpoint shares the breaker.
	other := NewClient(cfg)
	if _, err := other.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}}); !errors.Is(err, ErrCircuitOpen) {
		t.Fatalf("expected shared breaker to be open, got %v", err)
	}
}

func TestClientCircuitBreakerResetsOnSuccessAndCooldown(t *testing.T) {
	var fail bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if fail {
			http.Error(w, "boom", http.StatusInternalServerError)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"choices": []map[string]any{{"message": map[string]any{"content": "ok"}}},
		})
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.LLMModelDiscoveryEnabled = false
	client := NewClient(cfg)

	fail = true
	for i := 0; i < breakerFailureThreshold-1; i++ {
		_, _ = client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}})
	}
	fail = false
	if _, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}}); err != nil {
		t.Fatalf("success below threshold must reset breaker: %v", err)
	}
	fail = true
	if _, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}}); errors.Is(err, ErrCircuitOpen) {
		t.Fatal("breaker must have been reset by success")
	}

	// Expired cooldown lets the next call through again.
	client.breaker.mu.Lock()
	client.breaker.openUntil = time.Now().Add(-time.Second)
	client.breaker.mu.Unlock()
	fail = false
	if _, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "hi"}}); err != nil {
		t.Fatalf("expected call after cooldown expiry, got %v", err)
	}
}

func TestClientRefreshesInventoryAndRetriesRetiredModel(t *testing.T) {
	var modelRequests int
	var completionModels []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/models":
			modelRequests++
			model := "retired-model"
			if modelRequests > 1 {
				model = "replacement-model"
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"data": []map[string]any{{"id": model}}})
		case "/v1/chat/completions":
			var payload map[string]any
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				t.Fatal(err)
			}
			model, _ := payload["model"].(string)
			completionModels = append(completionModels, model)
			if model == "retired-model" {
				http.Error(w, `{"error":{"code":"model_not_found"}}`, http.StatusNotFound)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{
				"choices": []map[string]any{{"message": map[string]any{"content": "ok"}}},
				"usage":   map[string]any{"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "cost_in_usd_ticks": 2500000},
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.VettingModel = "retired-model"
	cfg.VettingModelFallbacks = []string{"replacement-model"}
	client := NewClientForWorkload(cfg, WorkloadTerrorAnalysis)
	content, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "test"}})
	if err != nil {
		t.Fatal(err)
	}
	if content != "ok" || client.ResolvedModel() != "replacement-model" {
		t.Fatalf("unexpected retry result content=%q model=%q", content, client.ResolvedModel())
	}
	if modelRequests != 2 || len(completionModels) != 2 || completionModels[0] != "retired-model" || completionModels[1] != "replacement-model" {
		t.Fatalf("unexpected requests models=%d completions=%v", modelRequests, completionModels)
	}
}

func TestResolveAvailableModelUsesWorkloadPreference(t *testing.T) {
	models := []string{"text-embedding-3-large", "frontier-reasoning", "fast-mini-chat"}
	if got := resolveAvailableModel(models, "missing", nil, WorkloadAlertClassification); got != "fast-mini-chat" {
		t.Fatalf("expected fast classification model, got %q", got)
	}
	if got := resolveAvailableModel(models, "missing", []string{"frontier-reasoning"}, WorkloadTerrorAnalysis); got != "frontier-reasoning" {
		t.Fatalf("expected configured fallback, got %q", got)
	}
}

func TestClientCachesUnsupportedModelsEndpoint(t *testing.T) {
	var modelRequests int
	var completionRequests int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/models":
			modelRequests++
			http.NotFound(w, r)
		case "/v1/chat/completions":
			completionRequests++
			_ = json.NewEncoder(w).Encode(map[string]any{"choices": []map[string]any{{"message": map[string]any{"content": "ok"}}}})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.VettingModel = "gateway-model"
	client := NewClient(cfg)
	for i := 0; i < 2; i++ {
		if _, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "test"}}); err != nil {
			t.Fatal(err)
		}
	}
	if modelRequests != 1 || completionRequests != 2 {
		t.Fatalf("expected one negative-cached model probe and two completions, models=%d completions=%d", modelRequests, completionRequests)
	}
}

func TestClientUsesExplicitFallbackWhenInventoryIsForbidden(t *testing.T) {
	var completionModels []string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/models":
			http.Error(w, `{"code":"permission-denied"}`, http.StatusForbidden)
		case "/v1/chat/completions":
			var payload map[string]any
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				t.Fatal(err)
			}
			model, _ := payload["model"].(string)
			completionModels = append(completionModels, model)
			if model == "retired-model" {
				http.Error(w, `{"error":{"code":"model_not_found"}}`, http.StatusNotFound)
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"choices": []map[string]any{{"message": map[string]any{"content": "ok"}}}})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.VettingProvider = "custom"
	cfg.VettingModel = "retired-model"
	cfg.VettingModelFallbacks = []string{"replacement-model"}
	client := NewClientForWorkload(cfg, WorkloadTerrorAnalysis)
	content, err := client.Complete(context.Background(), []Message{{Role: "user", Content: "test"}})
	if err != nil {
		t.Fatal(err)
	}
	if content != "ok" || client.ResolvedModel() != "replacement-model" {
		t.Fatalf("unexpected fallback content=%q model=%q", content, client.ResolvedModel())
	}
	if len(completionModels) != 2 || completionModels[0] != "retired-model" || completionModels[1] != "replacement-model" {
		t.Fatalf("unexpected completion models %v", completionModels)
	}
}
