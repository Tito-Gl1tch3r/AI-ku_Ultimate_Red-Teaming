package normalize

import (
	"testing"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

func TestApplyIncidentLinksCrossSource(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:   "a1",
			SourceID:  "src-a",
			Title:     "Mogadishu market attack kills twelve civilians",
			Category:  "terrorism_tip",
			Severity:  "high",
			FirstSeen: "2026-04-10T10:00:00Z",
			LastSeen:  "2026-04-10T10:00:00Z",
		},
		{
			AlertID:   "a2",
			SourceID:  "src-b",
			Title:     "Mogadishu market attack leaves twelve civilians dead",
			Category:  "terrorism_tip",
			Severity:  "high",
			FirstSeen: "2026-04-10T11:00:00Z",
			LastSeen:  "2026-04-10T11:00:00Z",
		},
	}

	linked, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected 1 incident summary, got %d", len(summaries))
	}
	if summaries[0].MemberCount != 2 {
		t.Fatalf("expected 2 members, got %d", summaries[0].MemberCount)
	}

	var withLink *model.Alert
	for i := range linked {
		if linked[i].Incident != nil {
			withLink = &linked[i]
			break
		}
	}
	if withLink == nil {
		t.Fatal("expected primary alert to carry incident link")
	}
	if len(withLink.Incident.RelatedAlertIDs) != 1 {
		t.Fatalf("expected 1 related alert, got %v", withLink.Incident.RelatedAlertIDs)
	}
}

func TestApplyIncidentLinksCVE(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:   "c1",
			SourceID:  "cert-a",
			Title:     "CISA adds CVE-2026-1234 to KEV catalog",
			Category:  "cyber_advisory",
			Severity:  "critical",
			FirstSeen: "2026-04-10T10:00:00Z",
			LastSeen:  "2026-04-10T10:00:00Z",
		},
		{
			AlertID:   "c2",
			SourceID:  "cert-b",
			Title:     "Patch advisory for CVE-2026-1234 in edge routers",
			Category:  "cyber_advisory",
			Severity:  "high",
			FirstSeen: "2026-04-10T12:00:00Z",
			LastSeen:  "2026-04-10T12:00:00Z",
		},
	}

	_, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected 1 CVE incident, got %d", len(summaries))
	}
	if len(summaries[0].CVEs) == 0 || summaries[0].CVEs[0] != "CVE-2026-1234" {
		t.Fatalf("expected CVE-2026-1234 in summary, got %v", summaries[0].CVEs)
	}
}

func TestFinalizeActiveAlertsCrossSourceBeforeDedup(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:   "a1",
			SourceID:  "src-a",
			Title:     "Mogadishu market attack kills twelve civilians",
			Category:  "terrorism_tip",
			Severity:  "high",
			FirstSeen: "2026-04-10T10:00:00Z",
			LastSeen:  "2026-04-10T10:00:00Z",
		},
		{
			AlertID:   "a2",
			SourceID:  "src-b",
			Title:     "Mogadishu market attack leaves twelve civilians dead",
			Category:  "terrorism_tip",
			Severity:  "high",
			FirstSeen: "2026-04-10T11:00:00Z",
			LastSeen:  "2026-04-10T11:00:00Z",
		},
	}

	finalized, summaries, suppressed := FinalizeActiveAlerts(alerts)
	if suppressed != 0 {
		t.Fatalf("expected incident members to remain in feed, got %d suppressed", suppressed)
	}
	if len(finalized) != 2 {
		t.Fatalf("expected both incident members in active feed, got %d", len(finalized))
	}
	if len(summaries) != 1 || summaries[0].MemberCount != 2 {
		t.Fatalf("expected incident with 2 members, got %#v", summaries)
	}
	if finalized[0].Incident == nil {
		t.Fatal("expected primary alert to retain incident metadata")
	}
	if len(finalized[0].Incident.RelatedAlertIDs) != 1 {
		t.Fatalf("expected one related alert id, got %#v", finalized[0].Incident.RelatedAlertIDs)
	}
}

func TestCollectCountriesIgnoresPublisherGeography(t *testing.T) {
	idx := map[string]model.Alert{
		"a": {AlertID: "a", EventCountryCode: "in"},
		"b": {AlertID: "b", Source: model.SourceMetadata{CountryCode: "GB"}},
		"c": {AlertID: "c", EventCountryCode: "IN"},
	}
	got := collectCountries([]string{"a", "b", "c"}, idx)
	if len(got) != 1 || got[0] != "IN" {
		t.Fatalf("expected event geography only [IN], got %v", got)
	}
}

func TestApplyIncidentLinksAddsCyberSharedCountry(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:          "foxit-de-a",
			SourceID:         "cert-de-a",
			Title:            "Foxit PDF Editor und PDF Reader mehrere Schwachstellen",
			Category:         "cyber_advisory",
			Severity:         "high",
			EventCountryCode: "DE",
			FirstSeen:        "2026-04-10T10:00:00Z",
			LastSeen:         "2026-04-10T10:00:00Z",
		},
		{
			AlertID:          "foxit-de-b",
			SourceID:         "cert-de-b",
			Title:            "Foxit PDF Editor PDF Reader mehrere Schwachstellen",
			Category:         "cyber_advisory",
			Severity:         "high",
			EventCountryCode: "DE",
			FirstSeen:        "2026-04-10T11:00:00Z",
			LastSeen:         "2026-04-10T11:00:00Z",
		},
	}

	_, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected 1 cyber incident, got %d", len(summaries))
	}
	if !containsString(summaries[0].LinkReasons, "shared_country:DE") {
		t.Fatalf("expected shared_country:DE in %#v", summaries[0].LinkReasons)
	}
}

func TestApplyIncidentLinksAddsGeographicSpread(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:          "cve-de",
			SourceID:         "cert-de",
			Title:            "CVE-2026-1234 exploited against edge routers",
			Category:         "cyber_advisory",
			Severity:         "critical",
			EventCountryCode: "DE",
			FirstSeen:        "2026-04-10T10:00:00Z",
			LastSeen:         "2026-04-10T10:00:00Z",
		},
		{
			AlertID:          "cve-fr",
			SourceID:         "cert-fr",
			Title:            "Patch advisory for CVE-2026-1234 in edge routers",
			Category:         "cyber_advisory",
			Severity:         "high",
			EventCountryCode: "FR",
			FirstSeen:        "2026-04-10T11:00:00Z",
			LastSeen:         "2026-04-10T11:00:00Z",
		},
	}

	_, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected 1 spread incident, got %d", len(summaries))
	}
	if !containsString(summaries[0].LinkReasons, "geographic_spread:DE,FR") {
		t.Fatalf("expected geographic_spread:DE,FR in %#v", summaries[0].LinkReasons)
	}
}

func TestMaxMemberSeverityEscalates(t *testing.T) {
	members := []model.Alert{
		{Severity: "medium"},
		{Severity: "critical"},
		{Severity: "high"},
	}
	if got := maxMemberSeverity(members, "high"); got != "critical" {
		t.Fatalf("expected critical, got %s", got)
	}
	if got := maxMemberSeverity(nil, "high"); got != "high" {
		t.Fatalf("expected fallback high, got %s", got)
	}
}

func TestExtractCVEs(t *testing.T) {
	got := extractCVEs("Critical CVE-2026-9999 and cve-2026-1111 advisories")
	if len(got) != 2 || got[0] != "CVE-2026-1111" || got[1] != "CVE-2026-9999" {
		t.Fatalf("unexpected CVE extraction: %v", got)
	}
}
