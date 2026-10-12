// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"encoding/csv"
	"fmt"
	"io"
	"net/url"
	"strings"
)

// URLhausItem is a recent malicious URL from abuse.ch URLhaus.
type URLhausItem struct {
	FeedItem
	URLID    string
	Threat   string
	URL      string
	Host     string
	Status   string
	Reporter string
}

// ParseURLhausRecent parses the URLhaus recent CSV dump.
func ParseURLhausRecent(body []byte, limit int) ([]URLhausItem, error) {
	if limit <= 0 {
		limit = 40
	}
	reader := csv.NewReader(strings.NewReader(string(body)))
	reader.FieldsPerRecord = -1
	reader.ReuseRecord = true

	var rows []URLhausItem
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if len(record) < 6 {
			continue
		}
		if strings.HasPrefix(strings.TrimSpace(record[0]), "#") {
			continue
		}
		if strings.EqualFold(strings.TrimSpace(record[0]), "id") {
			continue
		}
		id := strings.TrimSpace(record[0])
		dateAdded := strings.TrimSpace(record[1])
		rawURL := strings.TrimSpace(record[2])
		status := ""
		if len(record) > 3 {
			status = strings.TrimSpace(record[3])
		}
		threat := ""
		if len(record) > 5 {
			threat = strings.TrimSpace(record[5])
		}
		reporter := ""
		if len(record) > 8 {
			reporter = strings.TrimSpace(record[8])
		} else if len(record) > 7 {
			reporter = strings.TrimSpace(record[7])
		}
		host := urlhausHost(rawURL)
		if id == "" || rawURL == "" {
			continue
		}
		if status != "" && !strings.EqualFold(status, "online") {
			continue
		}
		titleThreat := threat
		if titleThreat == "" {
			titleThreat = "malware"
		}
		rows = append(rows, URLhausItem{
			FeedItem: FeedItem{
				Title:     fmt.Sprintf("URLhaus %s URL: %s", titleThreat, host),
				Link:      "https://urlhaus.abuse.ch/url/" + id + "/",
				Published: dateAdded,
				Summary:   fmt.Sprintf("Active %s distribution at %s reported by %s", titleThreat, rawURL, reporter),
				Tags:      []string{"urlhaus", strings.ToLower(titleThreat)},
			},
			URLID:    id,
			Threat:   titleThreat,
			URL:      rawURL,
			Host:     host,
			Status:   status,
			Reporter: reporter,
		})
		if len(rows) >= limit {
			break
		}
	}
	return rows, nil
}

func urlhausHost(raw string) string {
	parsed, err := url.Parse(strings.TrimSpace(raw))
	if err != nil || parsed.Host == "" {
		return strings.TrimSpace(raw)
	}
	return parsed.Host
}
