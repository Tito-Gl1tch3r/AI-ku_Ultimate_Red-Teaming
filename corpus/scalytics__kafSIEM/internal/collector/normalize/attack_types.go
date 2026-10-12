// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

// ClassifyAttackType maps a corroborated incident cluster to an analyst-facing
// attack lens used in the public OSINT relations demo.
func ClassifyAttackType(summary model.IncidentSummary, memberAlerts []model.Alert) string {
	if len(memberAlerts) == 0 {
		return inferAttackTypeFromSummary(summary)
	}

	cyber := hasCyberSignals(summary) || hasCategory(memberAlerts, "cyber_advisory")
	terror := hasTerrorSignals(summary, memberAlerts)
	hazard := hasHazardSignals(memberAlerts)
	maritime := hasCategory(memberAlerts, "maritime_security")
	conflict := hasCategory(memberAlerts, "conflict_monitoring", "humanitarian_security")
	travel := hasCategory(memberAlerts, "travel_warning")

	switch {
	case cyber && (terror || conflict):
		return "hybrid"
	case cyber:
		return "cyber"
	case terror:
		return "terror"
	case hazard:
		return "hazard"
	case maritime:
		return "maritime"
	case conflict:
		return "conflict"
	case travel:
		return "travel"
	default:
		return inferAttackTypeFromSummary(summary)
	}
}

var hazardSubcategories = map[string]struct{}{
	"flood":          {},
	"wildfire":       {},
	"storm":          {},
	"natural_hazard": {},
	"hazard_warning": {},
}

var hazardTitleKeywords = []string{
	"surf warning", "hazardous surf", "marine weather", "weather warning",
	"forest fire", "bushfire", "wildfire", "flood", "storm", "cyclone",
	"hurricane", "typhoon", "earthquake", "tsunami", "eruption", "heatwave",
	"heat wave", "landslide", "avalanche",
}

// hasHazardSignals separates natural-hazard and weather advisories from the
// threat lenses: a hazardous surf warning must not surface as a maritime
// threat in the public Relations panel. Every member has to look like a
// hazard (category, subcategory, or title keyword) so mixed clusters keep
// their threat lens.
func hasHazardSignals(memberAlerts []model.Alert) bool {
	if hasCategory(memberAlerts, "environmental_disaster", "emergency_management") {
		return true
	}
	for _, alert := range memberAlerts {
		if !isHazardAlert(alert) {
			return false
		}
	}
	return len(memberAlerts) > 0
}

func isHazardAlert(alert model.Alert) bool {
	if _, ok := hazardSubcategories[strings.ToLower(alert.Subcategory)]; ok {
		return true
	}
	title := strings.ToLower(alert.Title)
	for _, keyword := range hazardTitleKeywords {
		if strings.Contains(title, keyword) {
			return true
		}
	}
	return false
}

func inferAttackTypeFromSummary(summary model.IncidentSummary) string {
	if hasCyberSignals(summary) {
		return "cyber"
	}
	if len(summary.Entities) > 0 {
		return "terror"
	}
	switch summary.Category {
	case "cyber_advisory":
		return "cyber"
	case "environmental_disaster", "emergency_management":
		return "hazard"
	case "maritime_security":
		return "maritime"
	case "conflict_monitoring", "humanitarian_security":
		return "conflict"
	case "travel_warning":
		return "travel"
	case "terrorism_tip":
		return "terror"
	default:
		return "general"
	}
}

func hasCyberSignals(summary model.IncidentSummary) bool {
	if len(summary.CVEs) > 0 || len(summary.Malware) > 0 || len(summary.Sectors) > 0 {
		return true
	}
	return hasReasonPrefix(summary.LinkReasons,
		"shared_cve:",
		"shared_malware:",
		"targets_sector:",
		"anchor:kev:",
		"anchor:epss:",
		"anchor:malware:",
	)
}

func hasTerrorSignals(summary model.IncidentSummary, memberAlerts []model.Alert) bool {
	if hasCategory(memberAlerts, "terrorism_tip") {
		return true
	}
	return hasReasonPrefix(summary.LinkReasons,
		"shared_entity:",
		"sanctioned_entity:",
		"anchor:sanctioned:",
		"anchor:known_actor:",
	)
}

func hasCategory(alerts []model.Alert, categories ...string) bool {
	allowed := make(map[string]struct{}, len(categories))
	for _, category := range categories {
		allowed[category] = struct{}{}
	}
	for _, alert := range alerts {
		if _, ok := allowed[alert.Category]; ok {
			return true
		}
	}
	return false
}

func hasReasonPrefix(reasons []string, prefixes ...string) bool {
	for _, reason := range reasons {
		for _, prefix := range prefixes {
			if strings.HasPrefix(reason, prefix) {
				return true
			}
		}
	}
	return false
}

func isKnownThreatActor(actor string) bool {
	actor = strings.TrimSpace(actor)
	if actor == "" {
		return false
	}
	anchors := knownActorCanonicals()
	_, ok := anchors[actor]
	return ok
}
