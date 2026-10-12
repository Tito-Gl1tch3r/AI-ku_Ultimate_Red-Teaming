// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package output

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/scalytics/kafSIEM/internal/collector/config"
	"github.com/scalytics/kafSIEM/internal/collector/model"
	"github.com/scalytics/kafSIEM/internal/collector/normalize"
)

func TestWriteOutputs(t *testing.T) {
	dir := t.TempDir()
	cfg := config.Default()
	cfg.OutputPath = filepath.Join(dir, "alerts.json")
	cfg.FilteredOutputPath = filepath.Join(dir, "filtered.json")
	cfg.StateOutputPath = filepath.Join(dir, "state.json")
	cfg.SourceHealthOutputPath = filepath.Join(dir, "health.json")
	cfg.ZoneBriefingsOutputPath = filepath.Join(dir, "zone-briefings.json")
	cfg.ReplacementQueuePath = filepath.Join(dir, "replacement.json")

	err := Write(cfg, []model.Alert{{AlertID: "a"}}, []model.Alert{{AlertID: "b"}}, []model.Alert{{AlertID: "c"}}, []model.SourceHealthEntry{{SourceID: "s", Status: "ok"}}, model.DuplicateAudit{}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{cfg.OutputPath, cfg.FilteredOutputPath, cfg.StateOutputPath, cfg.SourceHealthOutputPath} {
		if _, err := os.Stat(path); err != nil {
			t.Fatalf("expected output file %s: %v", path, err)
		}
	}

	if err := WriteZoneBriefings(cfg.ZoneBriefingsOutputPath, []model.ZoneBriefingRecord{{LensID: "gaza", Title: "Gaza", Source: "UCDP GED"}}); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(cfg.ZoneBriefingsOutputPath); err != nil {
		t.Fatalf("expected output file %s: %v", cfg.ZoneBriefingsOutputPath, err)
	}
}

func TestWriteRegressionEmbedsIncidentArtifacts(t *testing.T) {
	dir := t.TempDir()
	cfg := config.Default()
	cfg.OutputPath = filepath.Join(dir, "alerts.json")
	cfg.FilteredOutputPath = filepath.Join(dir, "filtered.json")
	cfg.StateOutputPath = filepath.Join(dir, "state.json")
	cfg.SourceHealthOutputPath = filepath.Join(dir, "health.json")

	active := []model.Alert{
		{
			AlertID:   "a1",
			SourceID:  "src-a",
			Title:     "Critical patch for CVE-2026-9001 in industrial gateways",
			Category:  "cyber_advisory",
			Severity:  "critical",
			FirstSeen: "2026-04-10T10:00:00Z",
			LastSeen:  "2026-04-10T10:00:00Z",
		},
		{
			AlertID:   "a2",
			SourceID:  "src-b",
			Title:     "CERT warns operators about CVE-2026-9001 exploitation",
			Category:  "cyber_advisory",
			Severity:  "high",
			FirstSeen: "2026-04-10T11:00:00Z",
			LastSeen:  "2026-04-10T11:00:00Z",
		},
	}
	finalized, incidents, _ := normalize.FinalizeActiveAlerts(active)
	if err := Write(cfg, finalized, nil, finalized, nil, model.DuplicateAudit{}, nil, incidents); err != nil {
		t.Fatal(err)
	}

	incidentsPath := incidentsOutputPath(cfg.OutputPath)
	rawIncidents, err := os.ReadFile(incidentsPath)
	if err != nil {
		t.Fatalf("read incidents.json: %v", err)
	}
	var writtenIncidents []model.IncidentSummary
	if err := json.Unmarshal(rawIncidents, &writtenIncidents); err != nil {
		t.Fatal(err)
	}
	if len(writtenIncidents) != 1 {
		t.Fatalf("expected one incident index row, got %d", len(writtenIncidents))
	}

	rawAlerts, err := os.ReadFile(cfg.OutputPath)
	if err != nil {
		t.Fatal(err)
	}
	var written []model.Alert
	if err := json.Unmarshal(rawAlerts, &written); err != nil {
		t.Fatal(err)
	}
	annotated := 0
	primaries := 0
	for _, alert := range written {
		if alert.Incident != nil {
			annotated++
			if len(alert.Incident.RelatedAlertIDs) != 1 {
				t.Fatalf("expected one related alert id, got %#v", alert.Incident.RelatedAlertIDs)
			}
			if alert.Incident.Role == "primary" {
				primaries++
			}
		}
	}
	if annotated != 2 {
		t.Fatalf("expected both cluster members annotated, got %d", annotated)
	}
	if primaries != 1 {
		t.Fatalf("expected exactly one primary member, got %d", primaries)
	}
}
