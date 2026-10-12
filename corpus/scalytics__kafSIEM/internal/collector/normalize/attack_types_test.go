package normalize

import (
	"testing"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

func TestClassifyAttackTypeCyber(t *testing.T) {
	summary := model.IncidentSummary{
		CVEs:        []string{"CVE-2026-1234"},
		LinkReasons: []string{"shared_cve:CVE-2026-1234"},
		Category:    "cyber_advisory",
	}
	if got := ClassifyAttackType(summary, nil); got != "cyber" {
		t.Fatalf("expected cyber, got %s", got)
	}
}

func TestClassifyAttackTypeCyberCategoryCluster(t *testing.T) {
	summary := model.IncidentSummary{
		LinkReasons: []string{"cross_source:jaccard:0.83"},
		Category:    "cyber_advisory",
	}
	alerts := []model.Alert{
		{Category: "cyber_advisory"},
		{Category: "cyber_advisory"},
	}
	if got := ClassifyAttackType(summary, alerts); got != "cyber" {
		t.Fatalf("expected cyber, got %s", got)
	}
}

func TestClassifyAttackTypeTerrorCrossCategory(t *testing.T) {
	summary := model.IncidentSummary{
		Entities:    []string{"Al-Shabaab"},
		LinkReasons: []string{"cross_category_entity:Al-Shabaab"},
		Category:    "conflict_monitoring",
	}
	alerts := []model.Alert{
		{Category: "conflict_monitoring"},
		{Category: "terrorism_tip"},
	}
	if got := ClassifyAttackType(summary, alerts); got != "terror" {
		t.Fatalf("expected terror, got %s", got)
	}
}

func TestClassifyAttackTypeHazardOverMaritime(t *testing.T) {
	summary := model.IncidentSummary{
		LinkReasons: []string{"cross_source:jaccard:0.75", "shared_country:AU"},
		Category:    "maritime_security",
	}
	alerts := []model.Alert{
		{Category: "maritime_security", Title: "Hazardous Surf Warning for New South Wales"},
		{Category: "maritime_security", Title: "Marine weather warning issued for NSW coast"},
	}
	if got := ClassifyAttackType(summary, alerts); got != "hazard" {
		t.Fatalf("expected hazard, got %s", got)
	}
}

func TestClassifyAttackTypeHazardSubcategory(t *testing.T) {
	summary := model.IncidentSummary{
		LinkReasons: []string{"cross_source:jaccard:0.75"},
		Category:    "emergency_management",
	}
	alerts := []model.Alert{
		{Category: "emergency_management", Subcategory: "wildfire", Title: "Green forest fire notification in India"},
		{Category: "emergency_management", Subcategory: "wildfire", Title: "Forest fire notification for Uttarakhand"},
	}
	if got := ClassifyAttackType(summary, alerts); got != "hazard" {
		t.Fatalf("expected hazard, got %s", got)
	}
}

func TestClassifyAttackTypeMaritimeThreatStaysMaritime(t *testing.T) {
	summary := model.IncidentSummary{
		LinkReasons: []string{"cross_source:jaccard:0.71"},
		Category:    "maritime_security",
	}
	alerts := []model.Alert{
		{Category: "maritime_security", Title: "Armed boarding of tanker reported in Gulf of Guinea"},
		{Category: "maritime_security", Title: "Pirates board tanker off Gulf of Guinea coast"},
	}
	if got := ClassifyAttackType(summary, alerts); got != "maritime" {
		t.Fatalf("expected maritime, got %s", got)
	}
}

func TestShouldEntityLinkCrossCategoryKnownActor(t *testing.T) {
	left := incidentFingerprints{
		alert:  model.Alert{AlertID: "a1", SourceID: "src-a", Category: "conflict_monitoring"},
		actors: []string{"Al-Shabaab"},
	}
	right := incidentFingerprints{
		alert:  model.Alert{AlertID: "a2", SourceID: "src-b", Category: "terrorism_tip"},
		actors: []string{"Al-Shabaab"},
	}
	if !shouldEntityLink(left, right, []string{"Al-Shabaab"}) {
		t.Fatal("expected cross-category entity link for known actor")
	}
}
