// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"regexp"
	"strings"
)

// SanctionsItem is a sanctions listing suitable for intelligence alerts.
type SanctionsItem struct {
	FeedItem
	RecordID   string
	ListType   string
	Programs   []string
	ActorMatch string
	Country    string
	ListedOn   string
}

var (
	unIndividualRe = regexp.MustCompile(`(?is)<INDIVIDUAL>([\s\S]*?)</INDIVIDUAL>`)
	unEntityRe     = regexp.MustCompile(`(?is)<ENTITY>([\s\S]*?)</ENTITY>`)
	ofacEntryRe    = regexp.MustCompile(`(?is)<sdnEntry>([\s\S]*?)</sdnEntry>`)
	xmlTagRe       = func(tag string) *regexp.Regexp {
		return regexp.MustCompile(`(?is)<` + tag + `[^>]*>([\s\S]*?)</` + tag + `>`)
	}
)

var unTerrorListTypes = map[string]struct{}{
	"ISIL": {}, "AQ": {}, "AL-QAIDA": {}, "TALIBAN": {}, "AQSD": {}, "YEM": {},
	"LIBYA": {}, "SOM": {}, "QDe": {},
}

var ofacTerrorPrograms = map[string]struct{}{
	"SDGT": {}, "FTO": {}, "IRGC": {}, "IFSR": {}, "SDT": {}, "HRIT": {},
}

// ParseUNSanctionsXML extracts terrorism-relevant UN consolidated list rows.
func ParseUNSanctionsXML(body []byte, actorMatcher func(string) string, limit int) ([]SanctionsItem, error) {
	if limit <= 0 {
		limit = 80
	}
	text := string(body)
	out := make([]SanctionsItem, 0, limit)
	appendMatches := func(blocks [][]string, kind string) {
		for _, block := range blocks {
			if len(out) >= limit {
				return
			}
			item, ok := parseUNSanctionsBlock(block[1], kind, actorMatcher)
			if ok {
				out = append(out, item)
			}
		}
	}
	appendMatches(unEntityRe.FindAllStringSubmatch(text, -1), "entity")
	if len(out) < limit {
		appendMatches(unIndividualRe.FindAllStringSubmatch(text, -1), "individual")
	}
	return out, nil
}

func parseUNSanctionsBlock(block string, kind string, actorMatcher func(string) string) (SanctionsItem, bool) {
	dataID := xmlValue(block, "DATAID")
	first := xmlValue(block, "FIRST_NAME")
	second := xmlValue(block, "SECOND_NAME")
	listType := xmlValue(block, "UN_LIST_TYPE")
	listedOn := xmlValue(block, "LISTED_ON")
	comments := xmlValue(block, "COMMENTS1")
	aliases := collectXMLAliases(block, kind)
	country := xmlValue(block, "COUNTRY")
	if country == "" {
		country = xmlValue(block, "VALUE")
	}

	name := strings.TrimSpace(strings.TrimSpace(first) + " " + strings.TrimSpace(second))
	haystack := strings.Join([]string{name, strings.Join(aliases, " "), comments, listType}, "\n")
	actor := ""
	if actorMatcher != nil {
		actor = actorMatcher(haystack)
	}
	terrorList := isUNTerrorListType(listType)
	if actor == "" && !terrorList {
		return SanctionsItem{}, false
	}
	if name == "" {
		name = firstNonEmpty(actor, listType, dataID)
	}
	title := "UN sanctions listing: " + name
	if actor != "" {
		title = "UN sanctions: " + actor
	}
	link := "https://www.un.org/securitycouncil/sanctions/un-sc-consolidated-list"
	if dataID != "" {
		if kind == "entity" {
			link = "https://www.interpol.int/en/How-we-work/Notices/View-UN-Notices-Entities"
		} else {
			link = "https://www.interpol.int/en/How-we-work/Notices/View-UN-Notices-Individuals"
		}
	}
	tags := []string{"sanctions", "un"}
	if actor != "" {
		tags = append(tags, strings.ToLower(strings.ReplaceAll(actor, " ", "-")))
	}
	return SanctionsItem{
		FeedItem: FeedItem{
			Title:     title,
			Link:      link,
			Published: listedOn,
			Summary:   truncateSanctionsText(firstNonEmpty(comments, name), 400),
			Tags:      tags,
		},
		RecordID:   dataID,
		ListType:   listType,
		Programs:   []string{listType},
		ActorMatch: actor,
		Country:    country,
		ListedOn:   listedOn,
	}, true
}

// ParseOFACSDNXML extracts terrorism-program SDN rows from OFAC XML.
func ParseOFACSDNXML(body []byte, actorMatcher func(string) string, limit int) ([]SanctionsItem, error) {
	if limit <= 0 {
		limit = 80
	}
	text := string(body)
	matches := ofacEntryRe.FindAllStringSubmatch(text, -1)
	out := make([]SanctionsItem, 0, limit)
	for _, match := range matches {
		if len(out) >= limit {
			break
		}
		block := match[1]
		programs := collectXMLPrograms(block)
		if !hasOFACTerrorProgram(programs) {
			continue
		}
		uid := xmlValue(block, "uid")
		lastName := xmlValue(block, "lastName")
		firstName := xmlValue(block, "firstName")
		sdnType := xmlValue(block, "sdnType")
		aliases := collectOFACAliases(block)
		country := xmlValue(block, "country")
		name := strings.TrimSpace(strings.TrimSpace(firstName) + " " + strings.TrimSpace(lastName))
		haystack := strings.Join(append([]string{name, strings.Join(aliases, " "), strings.Join(programs, " ")}, sdnType), "\n")
		actor := ""
		if actorMatcher != nil {
			actor = actorMatcher(haystack)
		}
		titleName := firstNonEmpty(actor, name)
		if titleName == "" {
			continue
		}
		title := "OFAC SDN listing: " + titleName
		if actor != "" {
			title = "OFAC sanctions: " + actor
		}
		tags := []string{"sanctions", "ofac"}
		if actor != "" {
			tags = append(tags, strings.ToLower(strings.ReplaceAll(actor, " ", "-")))
		}
		out = append(out, SanctionsItem{
			FeedItem: FeedItem{
				Title:     title,
				Link:      "https://sanctionssearch.ofac.treas.gov/",
				Published: "",
				Summary:   truncateSanctionsText(name+" · programs: "+strings.Join(programs, ", "), 400),
				Tags:      tags,
			},
			RecordID:   uid,
			ListType:   sdnType,
			Programs:   programs,
			ActorMatch: actor,
			Country:    country,
		})
	}
	return out, nil
}

func xmlValue(block, tag string) string {
	re := xmlTagRe(tag)
	match := re.FindStringSubmatch(block)
	if len(match) < 2 {
		return ""
	}
	return strings.TrimSpace(match[1])
}

func collectXMLAliases(block, kind string) []string {
	tag := "ENTITY_ALIAS"
	if kind == "individual" {
		tag = "INDIVIDUAL_ALIAS"
	}
	re := regexp.MustCompile(`(?is)<` + tag + `>[\s\S]*?<ALIAS_NAME>([\s\S]*?)</ALIAS_NAME>[\s\S]*?</` + tag + `>`)
	matches := re.FindAllStringSubmatch(block, -1)
	out := make([]string, 0, len(matches))
	for _, match := range matches {
		if alias := strings.TrimSpace(match[1]); alias != "" {
			out = append(out, alias)
		}
	}
	return out
}

func collectOFACAliases(block string) []string {
	re := regexp.MustCompile(`(?is)<aka>[\s\S]*?<lastName>([\s\S]*?)</lastName>[\s\S]*?</aka>`)
	matches := re.FindAllStringSubmatch(block, -1)
	out := make([]string, 0, len(matches))
	for _, match := range matches {
		if alias := strings.TrimSpace(match[1]); alias != "" {
			out = append(out, alias)
		}
	}
	return out
}

func collectXMLPrograms(block string) []string {
	re := regexp.MustCompile(`(?is)<program>([\s\S]*?)</program>`)
	matches := re.FindAllStringSubmatch(block, -1)
	out := make([]string, 0, len(matches))
	seen := make(map[string]struct{})
	for _, match := range matches {
		program := strings.TrimSpace(match[1])
		if program == "" {
			continue
		}
		if _, ok := seen[program]; ok {
			continue
		}
		seen[program] = struct{}{}
		out = append(out, program)
	}
	return out
}

func isUNTerrorListType(listType string) bool {
	upper := strings.ToUpper(strings.TrimSpace(listType))
	if _, ok := unTerrorListTypes[upper]; ok {
		return true
	}
	return strings.Contains(upper, "ISIL") || strings.Contains(upper, "AL-QAIDA") || strings.Contains(upper, "TALIBAN")
}

func hasOFACTerrorProgram(programs []string) bool {
	for _, program := range programs {
		if _, ok := ofacTerrorPrograms[strings.ToUpper(strings.TrimSpace(program))]; ok {
			return true
		}
	}
	return false
}

func truncateSanctionsText(text string, max int) string {
	text = strings.Join(strings.Fields(text), " ")
	if len(text) <= max {
		return text
	}
	return strings.TrimSpace(text[:max]) + "..."
}
