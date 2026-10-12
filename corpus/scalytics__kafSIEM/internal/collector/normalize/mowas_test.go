// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"testing"
	"time"

	"github.com/scalytics/kafSIEM/internal/collector/config"
	"github.com/scalytics/kafSIEM/internal/collector/model"
	"github.com/scalytics/kafSIEM/internal/collector/parse"
)

func TestMOWASAlertPreservesIdentitySeverityGeographyAndPortalLink(t *testing.T) {
	now := time.Date(2026, 8, 1, 8, 0, 0, 0, time.UTC)
	meta := model.RegistrySource{
		Type:      "bbk-mowas-json",
		Category:  "public_safety",
		RegionTag: "DE",
		Source: model.SourceMetadata{
			SourceID:      "bbk-mowas",
			AuthorityName: "BBK Modular Warning System (MoWaS)",
			Country:       "Germany",
			CountryCode:   "DE",
			Region:        "Europe",
			AuthorityType: "public_safety_program",
			BaseURL:       "https://warnung.bund.de",
		},
	}
	item := parse.MOWASItem{
		Identifier:  "mow.DE-BY-TS-W135-20260801-000",
		MessageType: "Update",
		Headline:    "Waldbrand am Hochstaufen",
		Description: "Gefahr für Leib und Leben.",
		Instruction: "Meiden Sie das Gebiet.",
		Issuer:      "Integrierte Leitstelle Traunstein",
		Published:   "2026-08-01T07:30:00Z",
		Severity:    "Severe",
		EventCode:   "BBK-EVC-077",
		Categories:  []string{"Fire"},
		Lat:         47.755,
		Lng:         12.8505,
		Link:        "https://warnung.bund.de/meldungen/mow_DE-BY-TS-W135-20260801-000/Waldbrand_am_Hochstaufen/",
	}
	alert := MOWASAlert(Context{Config: config.Default(), Now: now}, meta, item)
	if alert == nil {
		t.Fatal("expected alert")
	}
	if alert.AlertID != "bbk-mowas:mow.DE-BY-TS-W135-20260801-000" {
		t.Fatalf("unexpected stable alert ID %q", alert.AlertID)
	}
	if alert.Status != "updated" || alert.Severity != "high" {
		t.Fatalf("expected updated/high, got %s/%s", alert.Status, alert.Severity)
	}
	if alert.Source.AuthorityName != item.Issuer {
		t.Fatalf("expected issuing authority attribution, got %q", alert.Source.AuthorityName)
	}
	if alert.Lat != item.Lat || alert.Lng != item.Lng || alert.EventGeoSource != "warning-area-centroid" {
		t.Fatalf("unexpected geography: %#v", alert)
	}
	if alert.CanonicalURL != item.Link || alert.Reporting.URL != item.Link {
		t.Fatalf("expected portal URL on alert and reporting metadata: %#v", alert)
	}
}

func TestMOWASCancellationAndSirenTestAreInformational(t *testing.T) {
	cancel := parse.MOWASItem{MessageType: "Cancel", Severity: "Extreme"}
	if got := mowasSeverity(cancel); got != "info" {
		t.Fatalf("expected cancellation to be info, got %q", got)
	}
	if got := mowasStatus(cancel.MessageType); got != "updated" {
		t.Fatalf("expected cancellation lifecycle to remain visible as updated, got %q", got)
	}
	testAlert := parse.MOWASItem{MessageType: "Alert", Severity: "Severe", EventCode: "BBK-EVC-060"}
	if got := mowasSeverity(testAlert); got != "info" {
		t.Fatalf("expected siren test to be info, got %q", got)
	}
	liveWording := parse.MOWASItem{MessageType: "Alert", Severity: "Minor", Headline: "Funktionsüberprüfung der Sirenen und Funkmeldeempfänger"}
	if got := mowasSeverity(liveWording); got != "info" {
		t.Fatalf("expected live siren-test wording to be info, got %q", got)
	}
}

func TestFilterActiveKeepsCurrentMOWASWarningsRegardlessOfStartDate(t *testing.T) {
	cfg := config.Default()
	cfg.MaxFreshnessHours = 72
	alerts := []model.Alert{{
		AlertID:        "bbk-mowas:long-running",
		SourceID:       "bbk-mowas",
		Category:       "public_safety",
		FreshnessHours: 24 * 200,
		Triage:         &model.Triage{RelevanceScore: 1},
	}}
	active, filtered := FilterActive(cfg, alerts)
	if len(active) != 1 || len(filtered) != 0 {
		t.Fatalf("expected provider-current MoWaS warning to bypass generic freshness cap, active=%#v filtered=%#v", active, filtered)
	}
}
