// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package normalize

import (
	"fmt"
	"strings"

	"github.com/scalytics/kafSIEM/internal/collector/model"
	"github.com/scalytics/kafSIEM/internal/collector/parse"
)

// MatchActorInText returns the longest known actor canonical name found in text.
func MatchActorInText(text string) string {
	dict := loadEntityDict()
	if dict == nil {
		return ""
	}
	tokens := tokenize(text)
	best := ""
	bestLen := 0
	for _, phrase := range dict.phrases {
		if !usableEntityPhrase(phrase) {
			continue
		}
		if !containsEntityPhrase(tokens, phrase.tokens) {
			continue
		}
		if len(phrase.tokens) > bestLen {
			best = phrase.canonical
			bestLen = len(phrase.tokens)
		}
	}
	return best
}

func containsEntityPhrase(tokens []string, phrase []string) bool {
	if len(phrase) == 0 || len(tokens) < len(phrase) {
		return false
	}
	for i := 0; i <= len(tokens)-len(phrase); i++ {
		matched := true
		for j := range phrase {
			if tokens[i+j] != phrase[j] {
				matched = false
				break
			}
		}
		if matched {
			return true
		}
	}
	return false
}

func NVDAlert(ctx Context, meta model.RegistrySource, item parse.NVDItem) *model.Alert {
	publishedAt := parseDate(item.Published)
	if publishedAt.IsZero() {
		publishedAt = ctx.Now
	}
	if !isFresh(ctx.Config, publishedAt, ctx.Now) {
		return nil
	}
	if item.CVSSScore > 0 && item.CVSSScore < 7 {
		return nil
	}
	alert := baseAlert(ctx, meta, item.Title, item.Link, item.Title+"\n"+item.Summary, publishedAt)
	alert.Category = "cyber_advisory"
	if item.CVSSScore >= 9 {
		alert.Severity = "critical"
	} else if item.CVSSScore >= 7 {
		alert.Severity = "high"
	} else {
		alert.Severity = "medium"
	}
	tags := append([]string{}, item.Tags...)
	if item.Vendor != "" {
		tags = append(tags, strings.ToLower(item.Vendor))
	}
	alert.Triage = score(ctx.Config, alert, FeedContext{
		Summary:  item.Summary,
		Tags:     tags,
		FeedType: meta.Type,
	})
	assignSubcategory(&alert, item.Summary, item.Vendor, item.Product, item.CVEID)
	return &alert
}

func EPSSAlert(ctx Context, meta model.RegistrySource, item parse.EPSSItem) *model.Alert {
	alert := baseAlert(ctx, meta, item.Title, item.Link, item.Summary, ctx.Now)
	alert.Category = "cyber_advisory"
	if item.EPSS >= 0.7 {
		alert.Severity = "critical"
	} else if item.EPSS >= 0.5 {
		alert.Severity = "high"
	} else {
		alert.Severity = "medium"
	}
	alert.Triage = score(ctx.Config, alert, FeedContext{
		Summary:  item.Summary,
		Tags:     item.Tags,
		FeedType: meta.Type,
	})
	assignSubcategory(&alert, item.Summary, item.CVEID)
	return &alert
}

func URLhausAlert(ctx Context, meta model.RegistrySource, item parse.URLhausItem) *model.Alert {
	publishedAt := parseDate(item.Published)
	if publishedAt.IsZero() {
		publishedAt = ctx.Now
	}
	if !isFresh(ctx.Config, publishedAt, ctx.Now) {
		return nil
	}
	alert := baseAlert(ctx, meta, item.Title, item.Link, item.Summary, publishedAt)
	alert.Category = "cyber_advisory"
	alert.Severity = "high"
	alert.Triage = score(ctx.Config, alert, FeedContext{
		Summary:  item.Summary,
		Tags:     item.Tags,
		FeedType: meta.Type,
	})
	assignSubcategory(&alert, item.Summary, item.Threat, item.Host)
	return &alert
}

func SanctionsAlert(ctx Context, meta model.RegistrySource, item parse.SanctionsItem) *model.Alert {
	publishedAt := parseDate(item.ListedOn)
	if publishedAt.IsZero() {
		publishedAt = ctx.Now
	}
	alert := baseAlert(ctx, meta, item.Title, item.Link, item.Summary, publishedAt)
	alert.Category = "terrorism_tip"
	if item.ActorMatch != "" {
		alert.Category = "terrorism_tip"
		alert.Severity = "critical"
	} else {
		alert.Severity = "high"
	}
	if code := normalizeCountryCode(item.Country); code != "" {
		alert.EventCountryCode = code
		if name := countryNameFromCode(code); name != "" {
			alert.EventCountry = name
		}
		if gLat, gLng, _, ok := geocodeCountryCode(code); ok {
			alert.Lat, alert.Lng = jitterCC(gLat, gLng, meta.Source.SourceID+":"+item.RecordID, "capital", code)
			alert.EventGeoSource = "capital"
			alert.EventGeoConfidence = eventGeoConfidence("capital")
		}
	}
	tags := append([]string{}, item.Tags...)
	tags = append(tags, item.Programs...)
	alert.Triage = score(ctx.Config, alert, FeedContext{
		Summary:  item.Summary,
		Tags:     tags,
		FeedType: meta.Type,
	})
	assignSubcategory(&alert, item.Summary, strings.Join(item.Programs, " "), item.ActorMatch)
	if item.ActorMatch != "" {
		alert.Subcategory = "sanctioned_actor:" + strings.ToLower(strings.ReplaceAll(item.ActorMatch, " ", "_"))
	}
	return &alert
}

// NVDRecentURL builds a CVE 2.0 API URL for recently modified records.
func NVDRecentURL(base string, start string) string {
	base = strings.TrimSpace(base)
	if base == "" {
		base = "https://services.nvd.nist.gov/rest/json/cves/2.0"
	}
	sep := "?"
	if strings.Contains(base, "?") {
		sep = "&"
	}
	return fmt.Sprintf("%s%slastModStartDate=%s&resultsPerPage=200&noRejected", base, sep, start)
}
