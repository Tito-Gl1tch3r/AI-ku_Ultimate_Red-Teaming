// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/model"
)

const sectorIncidentWindowHours = 7 * 24

var sectorKeywordGroups = map[string][]string{
	"energy": {
		"energy sector", "power grid", "electric grid", "electricity grid", "electric utility",
		"grid operator", "transmission operator", "distribution operator", "renewable energy",
		"wind farm", "solar farm", "power plant",
	},
	"ics": {
		"ics", "scada", "plc", "hmi", "dcs", "operational technology", "industrial control",
		"industrial control system", "process control", "ot network", "ot security",
	},
	"oil_gas": {
		"oil and gas", "oil & gas", "pipeline", "refinery", "upstream", "downstream", "petrochemical",
		"lng terminal", "gas terminal",
	},
	"nuclear": {
		"nuclear plant", "nuclear facility", "nuclear power", "reactor", "npp",
	},
	"water": {
		"water utility", "wastewater", "water treatment", "drinking water",
	},
}

// extractSectorTargets returns normalized sector slugs detected in alert text.
func extractSectorTargets(alert model.Alert) []string {
	if alert.Category != "cyber_advisory" {
		return nil
	}
	text := " " + strings.ToLower(strings.Join([]string{alert.Title, alert.Subcategory}, "\n")) + " "
	out := make([]string, 0, 2)
	for sector, keywords := range sectorKeywordGroups {
		for _, keyword := range keywords {
			keyword = strings.ToLower(strings.TrimSpace(keyword))
			if keyword == "" {
				continue
			}
			if sectorKeywordMatches(text, keyword) {
				out = appendUniqueString(out, sector)
				break
			}
		}
	}
	return uniqueSorted(out)
}

func shouldSectorLink(left, right incidentFingerprints) bool {
	if left.alert.Category != "cyber_advisory" || right.alert.Category != "cyber_advisory" {
		return false
	}
	if left.alert.SourceID == right.alert.SourceID {
		return false
	}
	if hoursApart(left.ts, right.ts) > sectorIncidentWindowHours {
		return false
	}
	return len(intersectStrings(left.sectors, right.sectors)) > 0
}

func formatTargetsSectorReason(sector string) string {
	return "targets_sector:" + strings.TrimSpace(sector)
}

func sectorKeywordMatches(text, keyword string) bool {
	padded := " " + strings.TrimSpace(text) + " "
	return strings.Contains(padded, " "+keyword+" ")
}
