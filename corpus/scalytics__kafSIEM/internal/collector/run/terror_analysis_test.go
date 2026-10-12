// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package run

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/config"
	"github.com/scalytics/kafSIEM/internal/collector/model"
)

func TestBuildTerrorAnalysisEvidenceCapsAndRanksWebDerivedSignals(t *testing.T) {
	now := time.Date(2026, 7, 20, 12, 0, 0, 0, time.UTC)
	alerts := make([]model.Alert, 0, 7)
	for i := 0; i < 6; i++ {
		severity := "medium"
		if i == 5 {
			severity = "critical"
		}
		alerts = append(alerts, terrorTestAlert("terror-"+string(rune('a'+i)), "NG", severity, now.Add(-time.Duration(i)*time.Hour)))
	}
	alerts = append(alerts, model.Alert{AlertID: "irrelevant", Title: "Routine agency meeting", LastSeen: now.Format(time.RFC3339)})
	statePath := writeTerrorTestState(t, alerts)
	cfg := config.Default()
	cfg.TerrorAnalysisMaxEvidence = 10
	cfg.TerrorAnalysisEvidenceHours = 72

	evidence := buildTerrorAnalysisEvidence(cfg, statePath, now)
	if len(evidence) != 4 {
		t.Fatalf("expected per-country cap of 4, got %d: %#v", len(evidence), evidence)
	}
	if evidence[0].AlertID != "terror-f" || !evidence[0].Material {
		t.Fatalf("expected critical evidence ranked first and material, got %#v", evidence[0])
	}
	for _, item := range evidence {
		if strings.Contains(item.Title, "https://") {
			t.Fatalf("evidence should contain compact titles, not fetched page content: %#v", item)
		}
	}
}

func TestParseTerrorAssessmentsRejectsUngroundedCountriesAndEvidence(t *testing.T) {
	evidence := []terrorEvidence{{AlertID: "a1", CountryCode: "ML"}}
	raw := `{"analyses":[
		{"country_code":"ML","risk_level":"high","confidence":0.8,"summary":"Corroborated activity increased.","evidence_ids":["a1","missing"]},
		{"country_code":"ZZ","risk_level":"critical","confidence":1,"summary":"Invented.","evidence_ids":["a1"]}
	]}`
	assessments, err := parseTerrorAssessments(raw, evidence)
	if err != nil {
		t.Fatal(err)
	}
	if len(assessments) != 1 || assessments[0].CountryCode != "ML" || len(assessments[0].EvidenceIDs) != 1 || assessments[0].EvidenceIDs[0] != "a1" {
		t.Fatalf("unexpected grounded assessments %#v", assessments)
	}
}

func TestTerrorAnalysisUsesCompactEvidenceCacheAndMaterialTrigger(t *testing.T) {
	now := time.Date(2026, 7, 20, 12, 0, 0, 0, time.UTC)
	var completionCalls int
	var lastPrompt string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/models":
			_ = json.NewEncoder(w).Encode(map[string]any{"data": []map[string]any{{"id": "analysis-model"}}})
		case "/v1/chat/completions":
			completionCalls++
			var payload struct {
				Messages []struct {
					Role    string `json:"role"`
					Content string `json:"content"`
				} `json:"messages"`
			}
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
				t.Fatal(err)
			}
			for _, message := range payload.Messages {
				if message.Role == "user" {
					lastPrompt = message.Content
				}
			}
			evidenceID := "a1"
			if strings.Contains(lastPrompt, "a2 |") {
				evidenceID = "a2"
			}
			_ = json.NewEncoder(w).Encode(map[string]any{
				"choices": []map[string]any{{"message": map[string]any{"content": `{"analyses":[{"country_code":"ML","risk_level":"high","confidence":0.85,"summary":"Recent evidence indicates elevated attack activity.","evidence_ids":["` + evidenceID + `"]}]}`}}},
				"usage":   map[string]any{"prompt_tokens": 180, "completion_tokens": 40, "total_tokens": 220},
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	dir := t.TempDir()
	statePath := filepath.Join(dir, "alerts-state.json")
	cachePath := filepath.Join(dir, "terror-analysis-llm.json")
	writeTerrorStateAtPath(t, statePath, []model.Alert{terrorTestAlert("a1", "ML", "high", now.Add(-time.Hour))})
	cfg := config.Default()
	cfg.VettingBaseURL = server.URL + "/v1"
	cfg.VettingAPIKey = "test-key"
	cfg.VettingModel = "analysis-model"
	cfg.VettingModelFallbacks = nil
	cfg.TerrorAnalysisRefreshHours = 24
	cfg.TerrorAnalysisUnchangedHours = 72

	assessments, err := refreshTerrorAnalysisFromLLM(context.Background(), cfg, cachePath, statePath, now)
	if err != nil || len(assessments) != 1 {
		t.Fatalf("first analysis failed assessments=%#v err=%v", assessments, err)
	}
	if completionCalls != 1 || len(lastPrompt) > 3000 || strings.Contains(lastPrompt, "example.invalid/full-article") || strings.Contains(lastPrompt, "%!(EXTRA") {
		t.Fatalf("expected one compact prompt, calls=%d length=%d prompt=%q", completionCalls, len(lastPrompt), lastPrompt)
	}
	if _, err := refreshTerrorAnalysisFromLLM(context.Background(), cfg, cachePath, statePath, now.Add(time.Hour)); err != nil {
		t.Fatal(err)
	}
	if completionCalls != 1 {
		t.Fatalf("unchanged evidence should reuse cache, calls=%d", completionCalls)
	}
	if terrorAnalysisNeedsRefresh(cfg, cachePath, statePath, now.Add(time.Hour)) {
		t.Fatal("unchanged evidence should not force the outer zone refresh")
	}

	writeTerrorStateAtPath(t, statePath, []model.Alert{
		terrorTestAlert("a1", "ML", "high", now.Add(-time.Hour)),
		terrorTestAlert("a2", "ML", "critical", now.Add(90*time.Minute)),
	})
	if !terrorAnalysisNeedsRefresh(cfg, cachePath, statePath, now.Add(2*time.Hour)) {
		t.Fatal("material new evidence should force the outer zone refresh")
	}
	if _, err := refreshTerrorAnalysisFromLLM(context.Background(), cfg, cachePath, statePath, now.Add(2*time.Hour)); err != nil {
		t.Fatal(err)
	}
	if completionCalls != 2 {
		t.Fatalf("material new evidence should trigger early analysis, calls=%d", completionCalls)
	}
	cache, _ := readTerrorAnalysisCache(cachePath)
	if cache.Model != "analysis-model" || len(cache.EvidenceIDs) != 2 {
		t.Fatalf("unexpected persisted analysis cache %#v", cache)
	}
}

func terrorTestAlert(id, countryCode, severity string, observedAt time.Time) model.Alert {
	return model.Alert{
		AlertID:          id,
		SourceID:         "official-counterterror-feed",
		Title:            "Terrorist bomb blast attack reported by security authorities " + id,
		CanonicalURL:     "https://example.invalid/full-article-with-long-query",
		FirstSeen:        observedAt.Format(time.RFC3339),
		LastSeen:         observedAt.Format(time.RFC3339),
		Category:         "terrorism_tip",
		Severity:         severity,
		SignalLane:       model.SignalLaneIntel,
		EventCountryCode: countryCode,
		Source: model.SourceMetadata{
			SourceID:      "official-counterterror-feed",
			CountryCode:   countryCode,
			AuthorityType: "government",
		},
	}
}

func writeTerrorTestState(t *testing.T, alerts []model.Alert) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "alerts-state.json")
	writeTerrorStateAtPath(t, path, alerts)
	return path
}

func writeTerrorStateAtPath(t *testing.T, path string, alerts []model.Alert) {
	t.Helper()
	body, err := json.Marshal(alerts)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, body, 0o644); err != nil {
		t.Fatal(err)
	}
}
