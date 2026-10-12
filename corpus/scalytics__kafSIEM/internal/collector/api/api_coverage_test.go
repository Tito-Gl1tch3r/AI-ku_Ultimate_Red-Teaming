// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package api

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	agentopsstore "github.com/scalytics/kafSIEM/internal/agentops/store"
	"github.com/scalytics/kafSIEM/internal/sourcedb"
)

func TestStartAndStop(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, "127.0.0.1:0", os.Stderr, nil, "")
	if err := srv.Start(); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := srv.Stop(ctx); err != nil {
		t.Fatalf("stop: %v", err)
	}
}

func TestCORSMiddleware(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, []string{"https://app.example"}, "")
	handler := srv.srv.Handler

	cases := []struct {
		name   string
		method string
		origin string
		status int
	}{
		{"allowed origin", http.MethodGet, "https://app.example", http.StatusOK},
		{"disallowed origin", http.MethodGet, "https://evil.example", http.StatusForbidden},
		{"disallowed preflight", http.MethodOptions, "https://evil.example", http.StatusForbidden},
		{"allowed preflight", http.MethodOptions, "https://app.example", http.StatusNoContent},
		{"same origin", http.MethodGet, "", http.StatusOK},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(tc.method, "/api/health", nil)
			if tc.origin != "" {
				req.Header.Set("Origin", tc.origin)
			}
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, req)
			if w.Code != tc.status {
				t.Fatalf("status=%d want %d body=%s", w.Code, tc.status, w.Body.String())
			}
			if tc.status == http.StatusOK && tc.origin != "" && w.Header().Get("Access-Control-Allow-Origin") != tc.origin {
				t.Fatalf("missing CORS allow-origin header: %v", w.Header())
			}
		})
	}
}

func TestCORSMiddlewareEmptyAllowlistAllowsAnyOrigin(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	req.Header.Set("Origin", "https://anywhere.example")
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
	if w.Header().Get("Access-Control-Allow-Origin") != "https://anywhere.example" {
		t.Fatalf("expected origin echoed, got %v", w.Header())
	}
}

func TestBearerAuth(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "sekret")
	handler := srv.srv.Handler

	cases := []struct {
		name   string
		path   string
		header string
		status int
	}{
		{"missing token", "/api/digest", "", http.StatusUnauthorized},
		{"wrong token", "/api/digest", "Bearer nope", http.StatusUnauthorized},
		{"malformed header", "/api/digest", "Token sekret", http.StatusUnauthorized},
		{"correct token", "/api/digest", "Bearer sekret", http.StatusOK},
		{"health bypasses auth", "/api/health", "", http.StatusOK},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, tc.path, nil)
			if tc.header != "" {
				req.Header.Set("Authorization", tc.header)
			}
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, req)
			if w.Code != tc.status {
				t.Fatalf("status=%d want %d body=%s", w.Code, tc.status, w.Body.String())
			}
		})
	}
}

func TestClientIP(t *testing.T) {
	cases := []struct {
		name       string
		xff        string
		xri        string
		remoteAddr string
		want       string
	}{
		{"x-forwarded-for first hop", "203.0.113.7, 10.0.0.1", "", "10.0.0.2:1234", "203.0.113.7"},
		{"x-real-ip fallback", "", "198.51.100.9", "10.0.0.2:1234", "198.51.100.9"},
		{"remote addr fallback", "", "", "192.0.2.4:5678", "192.0.2.4"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
			req.RemoteAddr = tc.remoteAddr
			if tc.xff != "" {
				req.Header.Set("X-Forwarded-For", tc.xff)
			}
			if tc.xri != "" {
				req.Header.Set("X-Real-Ip", tc.xri)
			}
			if got := clientIP(req); got != tc.want {
				t.Fatalf("clientIP=%q want %q", got, tc.want)
			}
		})
	}
}

func TestRateLimiterEvictsStaleBuckets(t *testing.T) {
	rl := newRateLimiter(1, 1, 20*time.Millisecond)
	if !rl.allow("198.51.100.1") {
		t.Fatal("first request should be allowed")
	}
	deadline := time.Now().Add(2 * time.Second)
	for {
		rl.mu.Lock()
		remaining := len(rl.buckets)
		rl.mu.Unlock()
		if remaining == 0 {
			return
		}
		if time.Now().After(deadline) {
			t.Fatalf("expected stale bucket eviction, %d buckets remain", remaining)
		}
		time.Sleep(10 * time.Millisecond)
	}
}

func TestAgentOpsReplayReportsStartError(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	srv.ConfigureAgentOpsReplay(func(context.Context) (agentopsstore.ReplaySession, error) {
		return agentopsstore.ReplaySession{}, fmt.Errorf("replay backend down")
	})
	req := httptest.NewRequest(http.MethodPost, "/api/agentops/replay", nil)
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 on replay error, got %d: %s", w.Code, w.Body.String())
	}
}

func TestNoiseFeedbackCreateRejectsInvalidJSON(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	req := httptest.NewRequest(http.MethodPost, "/api/noise-feedback", bytes.NewBufferString("{not json"))
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
}

func TestOSINTIncidentsListClampsLimit(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	for _, limit := range []string{"abc", "-5", "9999"} {
		req := httptest.NewRequest(http.MethodGet, "/api/osint/incidents?limit="+limit, nil)
		w := httptest.NewRecorder()
		srv.srv.Handler.ServeHTTP(w, req)
		if w.Code != http.StatusOK {
			t.Fatalf("limit=%s status=%d body=%s", limit, w.Code, w.Body.String())
		}
	}
}

func writeStatsArtifact(t *testing.T, dir string, rows []conflictStatRow) string {
	t.Helper()
	path := filepath.Join(dir, "ucdp-conflict-stats.json")
	payload, err := json.Marshal(rows)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, payload, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestZoneBriefLLMHandlerValidation(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	handler := srv.srv.Handler

	post := func(body string) *httptest.ResponseRecorder {
		req := httptest.NewRequest(http.MethodPost, "/api/zone-brief-llm", bytes.NewBufferString(body))
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, req)
		return w
	}

	// No vetting API key configured.
	if w := post(`{"conflict_id":"c1"}`); w.Code != http.StatusPreconditionFailed {
		t.Fatalf("expected 412 without API key, got %d: %s", w.Code, w.Body.String())
	}

	dir := t.TempDir()
	srv.ConfigureZoneBriefLLM(ZoneBriefLLMConfig{RuntimeDir: dir, VettingAPIKey: "key"})

	if w := post(`{not json`); w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for invalid JSON, got %d", w.Code)
	}
	if w := post(`{}`); w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing ids, got %d", w.Code)
	}
	// Stats artifact missing.
	if w := post(`{"conflict_id":"c1"}`); w.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500 for missing stats artifact, got %d: %s", w.Code, w.Body.String())
	}

	writeStatsArtifact(t, dir, []conflictStatRow{{ConflictID: "other", CountryID: "999"}})
	if w := post(`{"conflict_id":"c1"}`); w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 for unknown conflict, got %d: %s", w.Code, w.Body.String())
	}
}

func TestZoneBriefLLMHandlerServesCachedNarrative(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	// Fresh cached narrative: both fields present, analysis younger than 7d,
	// so the handler must serve it without calling the LLM.
	now := time.Now().UTC().Format(time.RFC3339)
	if err := db.UpsertZoneBriefLLM(context.Background(), sourcedb.ZoneBriefLLM{
		CountryID:           "svr-123",
		Title:               "Testland conflict",
		HistoricalSummary:   "Long-running border dispute.",
		CurrentAnalysis:     "Situation stable this week.",
		HistoricalUpdatedAt: now,
		AnalysisUpdatedAt:   now,
	}); err != nil {
		t.Fatal(err)
	}

	dir := t.TempDir()
	statsPath := writeStatsArtifact(t, dir, []conflictStatRow{{ConflictID: "c1", CountryID: "svr-123", Title: "Testland conflict"}})

	srv := New(db, ":0", os.Stderr, nil, "")
	srv.ConfigureZoneBriefLLM(ZoneBriefLLMConfig{RuntimeDir: dir, VettingAPIKey: "key"})

	req := httptest.NewRequest(http.MethodPost, "/api/zone-brief-llm", bytes.NewBufferString(`{"country_id":"svr-123"}`))
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
	var resp map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if resp["historical_summary"] != "Long-running border dispute." {
		t.Fatalf("unexpected narrative: %v", resp)
	}
	if resp["refreshed_historical"] != false || resp["refreshed_analysis"] != false {
		t.Fatalf("cached narrative must not refresh: %v", resp)
	}

	// The artifact must be rewritten with the narrative embedded.
	rows, err := readConflictStatsArtifact(statsPath)
	if err != nil {
		t.Fatal(err)
	}
	if rows[0].HistoricalSummary != "Long-running border dispute." {
		t.Fatalf("artifact not updated: %+v", rows[0])
	}
}

func TestZoneBriefLLMHandlerRefreshesNarrative(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	llm := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"choices": []map[string]any{
				{"message": map[string]any{"content": "Generated narrative text."}},
			},
		})
	}))
	defer llm.Close()

	dir := t.TempDir()
	writeStatsArtifact(t, dir, []conflictStatRow{{
		ConflictID:       "c1",
		CountryID:        "svr-777",
		Title:            "Testland conflict",
		SideA:            "Government",
		SideB:            "Rebels",
		StartDate:        "1998-01-01",
		TypeOfConflict:   "internal",
		FatalitiesTotal:  1200,
		FatalitiesLatest: 40,
		FatalitiesYear:   2026,
		RecentEvents: []conflictRecentEvent{
			{Date: "2026-07-01", Title: "Clash near border", Location: "North", Fatalities: 4},
			{Date: "2026-07-02", Title: "Convoy ambush", Location: "East"},
			{Date: "2026-07-03", Title: "Village raid", Location: "South", Fatalities: 2},
			{Date: "2026-07-04", Title: "Beyond the three-event cap", Location: "West"},
		},
	}})

	srv := New(db, ":0", os.Stderr, nil, "")
	srv.ConfigureZoneBriefLLM(ZoneBriefLLMConfig{
		RuntimeDir:     dir,
		VettingBaseURL: llm.URL + "/v1",
		VettingAPIKey:  "key",
	})

	req := httptest.NewRequest(http.MethodPost, "/api/zone-brief-llm", bytes.NewBufferString(`{"conflict_id":"c1"}`))
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
	var resp map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if resp["refreshed_historical"] != true || resp["refreshed_analysis"] != true {
		t.Fatalf("expected both narratives refreshed: %v", resp)
	}
	if resp["historical_summary"] != "Generated narrative text." {
		t.Fatalf("unexpected narrative: %v", resp)
	}

	// The refreshed narrative must be persisted for the next request.
	stored, ok, err := db.GetZoneBriefLLM(context.Background(), "svr-777")
	if err != nil || !ok {
		t.Fatalf("expected persisted narrative, ok=%v err=%v", ok, err)
	}
	if stored.CurrentAnalysis != "Generated narrative text." {
		t.Fatalf("unexpected stored narrative: %+v", stored)
	}
}

func TestZoneBriefLLMHandlerSurfacesLLMFailure(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	llm := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, "boom", http.StatusBadGateway)
	}))
	defer llm.Close()

	dir := t.TempDir()
	writeStatsArtifact(t, dir, []conflictStatRow{{ConflictID: "c1", CountryID: "svr-888", Title: "Testland"}})

	srv := New(db, ":0", os.Stderr, nil, "")
	srv.ConfigureZoneBriefLLM(ZoneBriefLLMConfig{
		RuntimeDir:     dir,
		VettingBaseURL: llm.URL + "/v1",
		VettingAPIKey:  "key",
	})

	req := httptest.NewRequest(http.MethodPost, "/api/zone-brief-llm", bytes.NewBufferString(`{"conflict_id":"c1"}`))
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500 on LLM failure, got %d: %s", w.Code, w.Body.String())
	}
}

func TestEnsureZoneBriefLLMRequiresCountryID(t *testing.T) {
	db := testDB(t)
	defer db.Close()

	srv := New(db, ":0", os.Stderr, nil, "")
	if _, _, _, err := srv.ensureZoneBriefLLM(context.Background(), conflictStatRow{}); err == nil {
		t.Fatal("expected error for missing country_id")
	}
}

func TestConflictStatsArtifactRoundtrip(t *testing.T) {
	if _, err := readConflictStatsArtifact(""); err == nil {
		t.Fatal("expected error for empty path")
	}
	if _, err := readConflictStatsArtifact(filepath.Join(t.TempDir(), "missing.json")); err == nil {
		t.Fatal("expected error for missing file")
	}
	badPath := filepath.Join(t.TempDir(), "bad.json")
	if err := os.WriteFile(badPath, []byte("{not json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := readConflictStatsArtifact(badPath); err == nil {
		t.Fatal("expected error for invalid JSON")
	}

	if err := writeConflictStatsArtifact("", nil); err == nil {
		t.Fatal("expected error for empty write path")
	}
	path := filepath.Join(t.TempDir(), "nested", "stats.json")
	rows := []conflictStatRow{{ConflictID: "c1", CountryID: "1", Title: "Row"}}
	if err := writeConflictStatsArtifact(path, rows); err != nil {
		t.Fatal(err)
	}
	got, err := readConflictStatsArtifact(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0].ConflictID != "c1" {
		t.Fatalf("roundtrip mismatch: %+v", got)
	}
}

func TestFindConflictStat(t *testing.T) {
	rows := []conflictStatRow{
		{ConflictID: "c1", CountryID: "100"},
		{ConflictID: "c2", CountryID: "200"},
	}
	if row, idx := findConflictStat(rows, "c2", ""); idx != 1 || row.CountryID != "200" {
		t.Fatalf("by conflict id: idx=%d row=%+v", idx, row)
	}
	if row, idx := findConflictStat(rows, "", "100"); idx != 0 || row.ConflictID != "c1" {
		t.Fatalf("by country id: idx=%d row=%+v", idx, row)
	}
	if _, idx := findConflictStat(rows, "nope", "nope"); idx != -1 {
		t.Fatalf("expected -1 for unknown ids, got %d", idx)
	}
}

func TestDigestEndpointAllCountries(t *testing.T) {
	db := testDB(t)
	defer db.Close()
	seedAlerts(t, db)

	srv := New(db, ":0", os.Stderr, nil, "")
	req := httptest.NewRequest(http.MethodGet, "/api/digest?days=7&limit=5", nil)
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
	var resp struct {
		Days    int `json:"days"`
		Digests []struct {
			CountryCode string `json:"country_code"`
		} `json:"digests"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if resp.Days != 7 {
		t.Fatalf("unexpected days: %+v", resp)
	}
}

func TestSearchInvalidFTSQueryFallsBackToPhrase(t *testing.T) {
	db := testDB(t)
	defer db.Close()
	seedAlerts(t, db)

	srv := New(db, ":0", os.Stderr, nil, "")
	// Unbalanced quote forces an FTS syntax error, exercising the phrase fallback.
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/search?q=%s", "europol%22AND("), nil)
	w := httptest.NewRecorder()
	srv.srv.Handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK && w.Code != http.StatusInternalServerError {
		t.Fatalf("unexpected status=%d body=%s", w.Code, w.Body.String())
	}
}
