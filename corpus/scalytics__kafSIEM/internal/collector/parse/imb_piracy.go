// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	imbRegionRe  = regexp.MustCompile(`(?m)^(?:[A-Z][A-Z /&()-]{4,}|Red Sea / Gulf of Aden / Somalia / Arabian Sea / Indian Ocean)`)
	imbHTMLTagRe = regexp.MustCompile(`(?is)<[^>]+>`)
)

// ParseIMBPiracyWarnings extracts regional piracy advisories from the IMB PRC page.
func ParseIMBPiracyWarnings(body string, pageURL string, limit int) []FeedItem {
	if limit <= 0 {
		limit = 20
	}
	text := imbHTMLTagRe.ReplaceAllString(body, "\n")
	text = strings.ReplaceAll(text, "&#8211;", "-")
	lines := make([]string, 0, 256)
	for _, line := range strings.Split(text, "\n") {
		line = strings.Join(strings.Fields(strings.TrimSpace(line)), " ")
		if len(line) < 24 {
			continue
		}
		lines = append(lines, line)
	}
	if len(lines) == 0 {
		return nil
	}

	regions := make([]string, 0, 16)
	regionIdx := make([]int, 0, 16)
	for i, line := range lines {
		if isIMBRegionHeading(line) {
			regions = append(regions, line)
			regionIdx = append(regionIdx, i)
		}
	}
	if len(regionIdx) == 0 {
		return filterIMBPiracyLines(lines, "Global", pageURL, limit)
	}

	out := make([]FeedItem, 0, limit)
	for r := 0; r < len(regionIdx); r++ {
		start := regionIdx[r] + 1
		end := len(lines)
		if r+1 < len(regionIdx) {
			end = regionIdx[r+1]
		}
		region := regions[r]
		chunk := lines[start:end]
		for _, item := range filterIMBPiracyLines(chunk, region, pageURL, limit-len(out)) {
			out = append(out, item)
			if len(out) >= limit {
				return out
			}
		}
	}
	return out
}

func isIMBRegionHeading(line string) bool {
	upper := strings.ToUpper(strings.TrimSpace(line))
	switch upper {
	case "PIRACY AND ARMED ROBBERY PRONE AREAS AND WARNINGS", "PIRACY AND ARMED ROBBERY PRONE AREAS AND WARNINGS - ICC - COMMERCIAL CRIME SERVICES":
		return false
	}
	if imbRegionRe.MatchString(line) && strings.ToUpper(line) == line && len(line) < 120 {
		return true
	}
	if strings.HasPrefix(upper, "RED SEA / GULF OF ADEN") {
		return true
	}
	if strings.Contains(upper, "WEST AFRICA") || strings.Contains(upper, "EAST AFRICA") {
		return true
	}
	return false
}

func filterIMBPiracyLines(lines []string, region string, pageURL string, limit int) []FeedItem {
	if limit <= 0 {
		return nil
	}
	keywords := []string{
		"advised", "warning", "vigilant", "kidnap", "hijack", "pirate", "piracy",
		"robbery", "houthi", "missile", "boarding", "attack", "incident", "risk",
	}
	out := make([]FeedItem, 0, limit)
	seen := make(map[string]struct{})
	for _, line := range lines {
		lower := strings.ToLower(line)
		if !containsAnyIMB(lower, keywords...) {
			continue
		}
		if _, ok := seen[line]; ok {
			continue
		}
		seen[line] = struct{}{}
		title := fmt.Sprintf("IMB %s: %s", strings.TrimSpace(region), truncateNVDText(line, 100))
		out = append(out, FeedItem{
			Title:   title,
			Link:    pageURL,
			Summary: line,
			Tags:    []string{"imb", "piracy", strings.ToLower(strings.ReplaceAll(region, " ", "-"))},
		})
		if len(out) >= limit {
			break
		}
	}
	return out
}

func containsAnyIMB(text string, parts ...string) bool {
	for _, part := range parts {
		if strings.Contains(text, part) {
			return true
		}
	}
	return false
}
