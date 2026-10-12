package normalize

import (
	"testing"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

func TestBuildRelationAnchorsIndexesStructuredFeeds(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:  "kev-1",
			SourceID: "cisa-kev",
			Title:    "CVE-2026-9999: Known Exploited Vulnerability",
			Category: "cyber_advisory",
		},
		{
			AlertID:          "travel-1",
			SourceID:         "uk-fcdo-travel",
			Title:            "FCDO advises against all travel to Somalia",
			Category:         "travel_warning",
			EventCountryCode: "SO",
		},
		{
			AlertID:          "acled-1",
			SourceID:         "acled-conflict",
			Title:            "Armed clash in Mogadishu",
			Category:         "conflict_monitoring",
			EventCountryCode: "SO",
		},
		{
			AlertID:  "epss-1",
			SourceID: "first-epss",
			Title:    "CVE-2026-8888 exploitation probability 91.0% (EPSS)",
			Category: "cyber_advisory",
		},
		{
			AlertID:     "un-1",
			SourceID:    "un-sanctions",
			Title:       "UN sanctions: Islamic State entity listing",
			Subcategory: "sanctioned_actor:islamic_state",
			Category:    "terrorism_tip",
		},
	}
	anchors := BuildRelationAnchors(alerts)
	if _, ok := anchors.KEVCVEs["CVE-2026-9999"]; !ok {
		t.Fatalf("expected KEV CVE anchor, got %#v", anchors.KEVCVEs)
	}
	if _, ok := anchors.EPSSCVEs["CVE-2026-8888"]; !ok {
		t.Fatalf("expected EPSS CVE anchor, got %#v", anchors.EPSSCVEs)
	}
	if _, ok := anchors.SanctionedActors["Islamic State"]; !ok {
		t.Fatalf("expected sanctioned actor anchor, got %#v", anchors.SanctionedActors)
	}
	if _, ok := anchors.TravelWarningCountries["SO"]; !ok {
		t.Fatalf("expected travel warning country SO, got %#v", anchors.TravelWarningCountries)
	}
	if _, ok := anchors.ConflictDataCountries["SO"]; !ok {
		t.Fatalf("expected conflict data country SO, got %#v", anchors.ConflictDataCountries)
	}
}

func TestApplyAnchorCorroborationAddsExplainableReasons(t *testing.T) {
	anchors := RelationAnchors{
		KEVCVEs:                map[string]struct{}{"CVE-2026-9999": {}},
		EPSSCVEs:               map[string]struct{}{"CVE-2026-8888": {}},
		TravelWarningCountries: map[string]struct{}{"SO": {}},
		ConflictDataCountries:  map[string]struct{}{"SO": {}},
		KnownActors:            map[string]struct{}{"Islamic State": {}},
		SanctionedActors:       map[string]struct{}{"Islamic State": {}},
	}
	memberAlerts := []model.Alert{
		{
			AlertID:          "a1",
			SourceID:         "cert-a",
			Title:            "Mogadishu convoy ambush",
			Category:         "conflict_monitoring",
			EventCountryCode: "SO",
		},
	}
	reasons := ApplyAnchorCorroboration(
		[]string{"shared_cve:CVE-2026-9999", "shared_entity:Islamic State"},
		memberAlerts,
		[]string{"CVE-2026-9999", "CVE-2026-8888"},
		[]string{"Islamic State"},
		nil,
		anchors,
	)
	for _, expected := range []string{
		"anchor:kev:CVE-2026-9999",
		"anchor:epss:CVE-2026-8888",
		"anchor:known_actor:Islamic State",
		"anchor:sanctioned:Islamic State",
		"anchor:travel_warning:SO",
		"anchor:conflict_data:SO",
	} {
		if !containsString(reasons, expected) {
			t.Fatalf("expected %s in %#v", expected, reasons)
		}
	}
}

func TestApplyIncidentLinksAddsAnchorCorroboration(t *testing.T) {
	alerts := []model.Alert{
		{
			AlertID:   "kev",
			SourceID:  "cisa-kev",
			Title:     "CVE-2026-4242: Edge router exploitation",
			Category:  "cyber_advisory",
			Severity:  "critical",
			FirstSeen: "2026-04-10T10:00:00Z",
			LastSeen:  "2026-04-10T10:00:00Z",
			Triage:    &model.Triage{RelevanceScore: 0.9},
		},
		{
			AlertID:   "cert",
			SourceID:  "cert-b",
			Title:     "Emergency advisory CVE-2026-4242 under active exploitation",
			Category:  "cyber_advisory",
			Severity:  "high",
			FirstSeen: "2026-04-10T11:00:00Z",
			LastSeen:  "2026-04-10T11:00:00Z",
			Triage:    &model.Triage{RelevanceScore: 0.8},
		},
	}
	linked, summaries := ApplyIncidentLinks(alerts)
	if len(summaries) != 1 {
		t.Fatalf("expected one incident, got %d", len(summaries))
	}
	if !containsString(summaries[0].LinkReasons, "anchor:kev:CVE-2026-4242") {
		t.Fatalf("expected KEV corroboration, got %#v", summaries[0].LinkReasons)
	}
	var withLink *model.Alert
	for i := range linked {
		if linked[i].Incident != nil {
			withLink = &linked[i]
			break
		}
	}
	if withLink == nil || !containsString(withLink.Incident.LinkReasons, "anchor:kev:CVE-2026-4242") {
		t.Fatalf("expected primary incident link to carry KEV corroboration, got %#v", withLink)
	}
}

func containsString(values []string, target string) bool {
	for _, value := range values {
		if value == target {
			return true
		}
	}
	return false
}
