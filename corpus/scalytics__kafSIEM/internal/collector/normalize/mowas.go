// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"html"
	"regexp"
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/model"
	"github.com/scalytics/kafSIEM/internal/collector/parse"
)

var mowasBreakRE = regexp.MustCompile(`(?i)<br\s*/?>`)

// MOWASAlert preserves the authoritative CAP lifecycle and severity while
// linking users to the human-facing warnung.bund.de portal.
func MOWASAlert(ctx Context, meta model.RegistrySource, item parse.MOWASItem) *model.Alert {
	if strings.TrimSpace(item.Identifier) == "" || strings.TrimSpace(item.Headline) == "" || strings.TrimSpace(item.Link) == "" {
		return nil
	}
	publishedAt := parseDate(item.Published)
	if publishedAt.IsZero() {
		publishedAt = ctx.Now
	}

	summary := cleanMOWASText(strings.Join([]string{item.Description, item.Instruction, item.AreaDesc}, "\n"))
	alert := baseAlert(ctx, meta, item.Headline, item.Link, item.Headline+"\n"+summary, publishedAt)
	alert.AlertID = meta.Source.SourceID + ":" + item.Identifier
	alert.Category = "public_safety"
	alert.Severity = mowasSeverity(item)
	alert.Status = mowasStatus(item.MessageType)
	alert.EventCountry = "Germany"
	alert.EventCountryCode = "DE"
	alert.RegionTag = "DE"
	if strings.TrimSpace(item.Issuer) != "" {
		alert.Source.AuthorityName = strings.TrimSpace(item.Issuer)
	}
	if item.Lat != 0 || item.Lng != 0 {
		alert.Lat = item.Lat
		alert.Lng = item.Lng
		alert.EventGeoSource = "warning-area-centroid"
		alert.EventGeoConfidence = 0.95
	}
	alert.Reporting = model.ReportingMetadata{
		Label: "View official warning",
		URL:   item.Link,
		Notes: "Official warning and current instructions on warnung.bund.de.",
	}

	tags := append([]string(nil), item.Categories...)
	tags = append(tags, item.EventCode, item.MessageType, item.Urgency, item.Certainty)
	relevance := 1.0
	reasoning := "Official current warning from Germany's modular warning system"
	if isMOWASInformational(item) {
		reasoning = "Official cancellation or warning-system test"
	}
	alert.Triage = &model.Triage{
		RelevanceScore:  relevance,
		Threshold:       ctx.Config.IncidentRelevanceThreshold,
		Confidence:      "high",
		Disposition:     "retained",
		PublicationType: "structured_incident_feed",
		Reasoning:       reasoning,
		Metadata: &model.TriageMetadata{
			Author: strings.TrimSpace(item.Issuer),
			Tags:   limitStrings(tags, 8),
		},
	}
	assignSubcategory(&alert, summary, strings.Join(tags, " "))
	return &alert
}

func mowasStatus(messageType string) string {
	switch strings.ToLower(strings.TrimSpace(messageType)) {
	case "update", "cancel":
		return "updated"
	default:
		return "active"
	}
}

func mowasSeverity(item parse.MOWASItem) string {
	if isMOWASInformational(item) {
		return "info"
	}
	switch strings.ToLower(strings.TrimSpace(item.Severity)) {
	case "extreme":
		return "critical"
	case "severe":
		return "high"
	case "moderate":
		return "medium"
	case "minor":
		return "low"
	default:
		return "medium"
	}
}

func isMOWASInformational(item parse.MOWASItem) bool {
	if strings.EqualFold(strings.TrimSpace(item.MessageType), "cancel") {
		return true
	}
	text := strings.ToLower(item.Headline + " " + item.Description + " " + item.EventCode)
	return strings.Contains(text, "probealarm") ||
		strings.Contains(text, "sirenentest") ||
		strings.Contains(text, "sirenenprobe") ||
		strings.Contains(text, "funktionsüberprüfung der sirenen") ||
		strings.Contains(text, "funktionsueberpruefung der sirenen") ||
		strings.Contains(text, "test warning") ||
		strings.Contains(text, "bbk-evc-060")
}

func cleanMOWASText(value string) string {
	value = mowasBreakRE.ReplaceAllString(value, "\n")
	value = html.UnescapeString(value)
	return strings.TrimSpace(value)
}
