package normalize

import (
	"testing"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

func TestBuildIncidentOverview(t *testing.T) {
	summary := model.IncidentSummary{
		IncidentID:     "inc-test",
		Title:          "Primary title",
		PrimaryAlertID: "a1",
		AlertIDs:       []string{"a1", "a2"},
		LinkReasons:    []string{"shared_cve:CVE-2026-1234"},
		Countries:      []string{"SO"},
		Entities:       []string{"Regional Cell"},
		CVEs:           []string{"CVE-2026-1234"},
	}
	alerts := []model.Alert{
		{
			AlertID: "a1",
			Title:   "Primary title",
			Source: model.SourceMetadata{
				AuthorityName: "Source A",
				CountryCode:   "SO",
				Country:       "Somalia",
			},
			FirstSeen:        "2026-04-10T10:00:00Z",
			Category:         "conflict_monitoring",
			Severity:         "high",
			EventCountryCode: "SO",
			EventCountry:     "Somalia",
			Incident:         &model.IncidentLink{Role: "primary"},
		},
		{
			AlertID: "a2",
			Title:   "Corroborating title",
			Source: model.SourceMetadata{
				AuthorityName: "Source B",
				CountryCode:   "SO",
				Country:       "Somalia",
			},
			FirstSeen:        "2026-04-10T11:00:00Z",
			Category:         "conflict_monitoring",
			Severity:         "medium",
			EventCountryCode: "SO",
			Incident:         &model.IncidentLink{Role: "member"},
		},
	}

	geo, timeline, graph := BuildIncidentOverview(summary, alerts)
	if len(geo.CountryCodes) != 1 || geo.CountryCodes[0] != "SO" {
		t.Fatalf("unexpected geo: %#v", geo)
	}
	if len(timeline) != 2 || timeline[0].AlertID != "a1" {
		t.Fatalf("unexpected timeline: %#v", timeline)
	}
	if len(graph.Nodes) < 4 {
		t.Fatalf("expected alert + entity/country nodes, got %#v", graph.Nodes)
	}
	if len(graph.Edges) < 2 {
		t.Fatalf("expected corroboration and relation edges, got %#v", graph.Edges)
	}
}

func TestBuildIncidentOverviewKeepsEvidenceEdgesPerAlert(t *testing.T) {
	summary := model.IncidentSummary{
		IncidentID:     "inc-test",
		Title:          "Primary title",
		PrimaryAlertID: "a1",
		AlertIDs:       []string{"a1", "a2", "a3"},
		LinkReasons:    []string{"shared_cve:CVE-2026-1234", "shared_country:SO"},
		Countries:      []string{"FR", "SO"},
		CVEs:           []string{"CVE-2026-1234"},
		Malware:        []string{"evil-c2.example"},
		Sectors:        []string{"energy"},
	}
	alerts := []model.Alert{
		{
			AlertID:          "a1",
			Title:            "CVE-2026-1234 advisory for evil-c2.example against energy sector",
			SourceID:         "cert-a",
			FirstSeen:        "2026-04-10T10:00:00Z",
			Category:         "cyber_advisory",
			Severity:         "high",
			EventCountryCode: "SO",
			EventCountry:     "Somalia",
		},
		{
			AlertID:          "a2",
			Title:            "CVE-2026-1234 exploited in energy sector",
			SourceID:         "cert-b",
			FirstSeen:        "2026-04-10T11:00:00Z",
			Category:         "cyber_advisory",
			Severity:         "medium",
			EventCountryCode: "SO",
		},
		{
			AlertID:          "a3",
			Title:            "Mogadishu airport security incident disrupts flights",
			SourceID:         "security-feed",
			FirstSeen:        "2026-04-10T12:00:00Z",
			Category:         "conflict_monitoring",
			Severity:         "medium",
			EventCountryCode: "FR",
		},
	}

	geo, _, graph := BuildIncidentOverview(summary, alerts)
	if len(geo.CountryCodes) != 2 || geo.CountryCodes[0] != "FR" || geo.CountryCodes[1] != "SO" {
		t.Fatalf("unexpected country codes: %#v", geo)
	}
	if len(geo.Countries) != 2 || geo.Countries[0] != "FR" || geo.Countries[1] != "Somalia" {
		t.Fatalf("expected country labels to align with country codes: %#v", geo)
	}
	if !hasGraphEdge(graph, "a1", "cve:CVE-2026-1234", "exploits:cve:CVE-2026-1234") {
		t.Fatalf("expected a1 CVE edge, got %#v", graph.Edges)
	}
	if hasGraphEdge(graph, "a3", "cve:CVE-2026-1234", "exploits:cve:CVE-2026-1234") {
		t.Fatalf("did not expect a3 CVE edge: %#v", graph.Edges)
	}
	if hasGraphEdge(graph, "a3", "malware:evil-c2.example", "shared_malware:evil-c2.example") {
		t.Fatalf("did not expect a3 malware edge: %#v", graph.Edges)
	}
	if hasGraphEdge(graph, "a3", "sector:energy", "targets_sector:energy") {
		t.Fatalf("did not expect a3 sector edge: %#v", graph.Edges)
	}
}

func TestApplyIncidentLinksSharedCountry(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:          "g1",
			SourceID:         "src-a",
			Title:            "Mogadishu airport security incident disrupts flights",
			Category:         "conflict_monitoring",
			Severity:         "high",
			EventCountryCode: "SO",
			FirstSeen:        "2026-04-10T10:00:00Z",
			LastSeen:         "2026-04-10T10:00:00Z",
		},
		{
			AlertID:          "g2",
			SourceID:         "src-b",
			Title:            "Mogadishu airport security incident causes flight delays",
			Category:         "conflict_monitoring",
			Severity:         "medium",
			EventCountryCode: "SO",
			FirstSeen:        "2026-04-10T11:00:00Z",
			LastSeen:         "2026-04-10T11:00:00Z",
		},
	}
	_, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected shared-country incident, got %d", len(summaries))
	}
	found := false
	for _, reason := range summaries[0].LinkReasons {
		if reason == "shared_country:SO" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected shared_country:SO in %#v", summaries[0].LinkReasons)
	}
}

func hasGraphEdge(graph model.IncidentGraph, from, to, reason string) bool {
	for _, edge := range graph.Edges {
		if edge.From == from && edge.To == to && edge.Reason == reason {
			return true
		}
	}
	return false
}
