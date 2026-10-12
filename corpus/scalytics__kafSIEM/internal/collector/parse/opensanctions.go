// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

// OpenSanctionsIndex is the dataset index published by OpenSanctions.
type OpenSanctionsIndex struct {
	LastChange  string `json:"last_change"`
	EntityCount int    `json:"entity_count"`
	Resources   []struct {
		Name string `json:"name"`
		URL  string `json:"url"`
	} `json:"resources"`
}

// ParseOpenSanctionsIndex resolves the NDJSON entities artifact URL from an index document.
func ParseOpenSanctionsIndex(body []byte) (OpenSanctionsIndex, string, error) {
	var doc OpenSanctionsIndex
	if err := json.Unmarshal(body, &doc); err != nil {
		return OpenSanctionsIndex{}, "", err
	}
	for _, resource := range doc.Resources {
		if strings.EqualFold(strings.TrimSpace(resource.Name), "entities.ftm.json") {
			url := strings.TrimSpace(resource.URL)
			if url != "" {
				return doc, url, nil
			}
		}
	}
	return doc, "", fmt.Errorf("entities.ftm.json resource not found")
}

// ParseOpenSanctionsEntities streams NDJSON entities and returns terrorism-relevant sanctions rows.
func ParseOpenSanctionsEntities(body io.Reader, actorMatcher func(string) string, limit int) ([]SanctionsItem, error) {
	if limit <= 0 {
		limit = 50
	}
	scanner := bufio.NewScanner(body)
	buf := make([]byte, 0, 1024*1024)
	scanner.Buffer(buf, 4*1024*1024)

	out := make([]SanctionsItem, 0, limit)
	for scanner.Scan() {
		if len(out) >= limit {
			break
		}
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		item, ok := parseOpenSanctionsEntity(line, actorMatcher)
		if ok {
			out = append(out, item)
		}
	}
	if err := scanner.Err(); err != nil {
		return out, err
	}
	return out, nil
}

func parseOpenSanctionsEntity(line string, actorMatcher func(string) string) (SanctionsItem, bool) {
	var entity struct {
		ID         string   `json:"id"`
		Caption    string   `json:"caption"`
		Schema     string   `json:"schema"`
		Datasets   []string `json:"datasets"`
		Properties struct {
			Name    []string `json:"name"`
			Alias   []string `json:"alias"`
			Topics  []string `json:"topics"`
			Country []string `json:"country"`
			Program []string `json:"programId"`
		} `json:"properties"`
	}
	if err := json.Unmarshal([]byte(line), &entity); err != nil {
		return SanctionsItem{}, false
	}

	topics := entity.Properties.Topics
	terrorTopic := hasOpenSanctionsTopic(topics, "crime.terror")
	sanctionTopic := hasOpenSanctionsTopic(topics, "sanction")
	if !terrorTopic && !sanctionTopic {
		return SanctionsItem{}, false
	}

	names := append([]string{}, entity.Properties.Name...)
	names = append(names, entity.Properties.Alias...)
	names = append(names, entity.Caption)
	haystack := strings.Join(names, "\n")
	actor := ""
	if actorMatcher != nil {
		actor = actorMatcher(haystack)
	}
	if !terrorTopic && actor == "" {
		return SanctionsItem{}, false
	}

	titleName := firstNonEmpty(actor, entity.Caption, firstNonEmpty(names...))
	if titleName == "" {
		return SanctionsItem{}, false
	}
	title := "OpenSanctions listing: " + titleName
	if actor != "" {
		title = "OpenSanctions sanctions: " + actor
	}
	programs := append([]string{}, entity.Properties.Program...)
	if len(programs) == 0 && len(entity.Datasets) > 0 {
		programs = append(programs, entity.Datasets[0])
	}
	country := ""
	if len(entity.Properties.Country) > 0 {
		country = entity.Properties.Country[0]
	}
	tags := []string{"sanctions", "opensanctions"}
	if terrorTopic {
		tags = append(tags, "terror")
	}
	if actor != "" {
		tags = append(tags, strings.ToLower(strings.ReplaceAll(actor, " ", "-")))
	}
	link := "https://www.opensanctions.org/entities/" + strings.TrimSpace(entity.ID) + "/"
	return SanctionsItem{
		FeedItem: FeedItem{
			Title:   title,
			Link:    link,
			Summary: truncateSanctionsText(titleName+" · topics: "+strings.Join(topics, ", "), 400),
			Tags:    tags,
		},
		RecordID:   entity.ID,
		ListType:   entity.Schema,
		Programs:   programs,
		ActorMatch: actor,
		Country:    country,
	}, true
}

func hasOpenSanctionsTopic(topics []string, want string) bool {
	want = strings.ToLower(strings.TrimSpace(want))
	for _, topic := range topics {
		if strings.EqualFold(strings.TrimSpace(topic), want) {
			return true
		}
	}
	return false
}
