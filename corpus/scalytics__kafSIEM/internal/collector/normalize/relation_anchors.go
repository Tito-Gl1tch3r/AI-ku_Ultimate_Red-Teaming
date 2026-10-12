// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

// RelationAnchors indexes authoritative open-data signals from the active alert
// batch. Incident clusters are corroborated against these anchors with explicit
// link reasons — no LLM clustering.
type RelationAnchors struct {
	KEVCVEs                map[string]struct{}
	EPSSCVEs               map[string]struct{}
	TravelWarningCountries map[string]struct{}
	ConflictDataCountries  map[string]struct{}
	KnownActors            map[string]struct{}
	SanctionedActors       map[string]struct{}
	MalwareIOCs            map[string]struct{}
}

func BuildRelationAnchors(alerts []model.Alert) RelationAnchors {
	anchors := RelationAnchors{
		KEVCVEs:                make(map[string]struct{}),
		EPSSCVEs:               make(map[string]struct{}),
		TravelWarningCountries: make(map[string]struct{}),
		ConflictDataCountries:  make(map[string]struct{}),
		KnownActors:            knownActorCanonicals(),
		SanctionedActors:       make(map[string]struct{}),
		MalwareIOCs:            make(map[string]struct{}),
	}
	for _, alert := range alerts {
		if isMalwareFeedSource(alert) {
			for _, ioc := range extractMalwareIOCs(alert) {
				anchors.MalwareIOCs[ioc] = struct{}{}
			}
		}
		switch {
		case isKEVSource(alert):
			for _, cve := range extractCVEs(alert.Title) {
				anchors.KEVCVEs[cve] = struct{}{}
			}
		case isEPSSSource(alert):
			for _, cve := range extractCVEs(alert.Title) {
				anchors.EPSSCVEs[cve] = struct{}{}
			}
		case isSanctionsSource(alert):
			if actor := MatchActorInText(strings.Join([]string{alert.Title, alert.Subcategory}, "\n")); actor != "" {
				anchors.SanctionedActors[actor] = struct{}{}
			}
		case alert.Category == "travel_warning":
			if code := incidentCountryCode(alert); code != "" {
				anchors.TravelWarningCountries[code] = struct{}{}
			}
		case isConflictDataSource(alert):
			if code := incidentCountryCode(alert); code != "" {
				anchors.ConflictDataCountries[code] = struct{}{}
			}
		}
	}
	return anchors
}

func ApplyAnchorCorroboration(
	reasons []string,
	memberAlerts []model.Alert,
	sharedCVEs []string,
	sharedEntities []string,
	sharedMalware []string,
	anchors RelationAnchors,
) []string {
	out := append([]string{}, reasons...)

	for _, cve := range sharedCVEs {
		normalized := strings.ToUpper(strings.TrimSpace(cve))
		if normalized == "" {
			continue
		}
		if _, ok := anchors.KEVCVEs[normalized]; ok {
			out = appendUniqueString(out, "anchor:kev:"+normalized)
		}
		if _, ok := anchors.EPSSCVEs[normalized]; ok {
			out = appendUniqueString(out, "anchor:epss:"+normalized)
		}
	}

	for _, entity := range sharedEntities {
		normalized := strings.TrimSpace(entity)
		if normalized == "" {
			continue
		}
		if _, ok := anchors.KnownActors[normalized]; ok {
			out = appendUniqueString(out, "anchor:known_actor:"+normalized)
		}
		if _, ok := anchors.SanctionedActors[normalized]; ok {
			out = appendUniqueString(out, "anchor:sanctioned:"+normalized)
		}
	}

	for _, ioc := range sharedMalware {
		normalized := strings.TrimSpace(ioc)
		if normalized == "" {
			continue
		}
		if _, ok := anchors.MalwareIOCs[normalized]; ok {
			out = appendUniqueString(out, "anchor:malware:"+normalized)
		}
	}

	for _, alert := range memberAlerts {
		code := incidentCountryCode(alert)
		if code == "" {
			continue
		}
		if _, ok := anchors.TravelWarningCountries[code]; ok && travelCorroborationCategory(alert.Category) {
			out = appendUniqueString(out, "anchor:travel_warning:"+strings.ToUpper(code))
		}
		if _, ok := anchors.ConflictDataCountries[code]; ok && conflictCorroborationCategory(alert.Category) {
			out = appendUniqueString(out, "anchor:conflict_data:"+strings.ToUpper(code))
		}
	}

	return uniqueSorted(out)
}

func isKEVSource(alert model.Alert) bool {
	sourceID := strings.ToLower(strings.TrimSpace(alert.SourceID))
	return sourceID == "cisa-kev" || strings.Contains(sourceID, "kev")
}

func isEPSSSource(alert model.Alert) bool {
	return strings.EqualFold(strings.TrimSpace(alert.SourceID), "first-epss")
}

func isSanctionsSource(alert model.Alert) bool {
	sourceID := strings.ToLower(strings.TrimSpace(alert.SourceID))
	return strings.Contains(sourceID, "sanctions") || strings.Contains(sourceID, "ofac-sdn") || sourceID == "opensanctions"
}

func isConflictDataSource(alert model.Alert) bool {
	sourceID := strings.ToLower(strings.TrimSpace(alert.SourceID))
	return strings.Contains(sourceID, "acled") || strings.Contains(sourceID, "ucdp")
}

func incidentCountryCode(alert model.Alert) string {
	if code := strings.ToUpper(strings.TrimSpace(alert.EventCountryCode)); code != "" {
		return code
	}
	if code := strings.ToUpper(strings.TrimSpace(alert.Source.CountryCode)); code != "" {
		return code
	}
	return ""
}

func travelCorroborationCategory(category string) bool {
	switch category {
	case "terrorism_tip", "conflict_monitoring", "travel_warning", "humanitarian_security", "maritime_security", "public_safety":
		return true
	default:
		return false
	}
}

func conflictCorroborationCategory(category string) bool {
	switch category {
	case "terrorism_tip", "conflict_monitoring", "humanitarian_security", "maritime_security":
		return true
	default:
		return false
	}
}

func knownActorCanonicals() map[string]struct{} {
	dict := loadEntityDict()
	if dict == nil {
		return map[string]struct{}{}
	}
	out := make(map[string]struct{}, len(dict.phrases))
	for _, phrase := range dict.phrases {
		if phrase.canonical == "" {
			continue
		}
		out[phrase.canonical] = struct{}{}
	}
	return out
}
