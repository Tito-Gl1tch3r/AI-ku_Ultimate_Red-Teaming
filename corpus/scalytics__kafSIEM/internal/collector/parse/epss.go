// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"encoding/csv"
	"fmt"
	"io"
	"sort"
	"strings"
)

// EPSSItem is a CVE with an exploitation probability score.
type EPSSItem struct {
	FeedItem
	CVEID      string
	EPSS       float64
	Percentile float64
}

// ParseEPSS parses the FIRST EPSS CSV feed and returns the highest-scoring CVE rows.
func ParseEPSS(body []byte, minScore float64, limit int) ([]EPSSItem, error) {
	if minScore <= 0 {
		minScore = 0.35
	}
	if limit <= 0 {
		limit = 40
	}
	reader := csv.NewReader(strings.NewReader(string(body)))
	reader.FieldsPerRecord = -1
	reader.ReuseRecord = true

	var rows []EPSSItem
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if len(record) < 3 {
			continue
		}
		cve := strings.ToUpper(strings.TrimSpace(record[0]))
		if !strings.HasPrefix(cve, "CVE-") {
			continue
		}
		epss, err := parseEPSSFloat(record[1])
		if err != nil {
			continue
		}
		percentile, _ := parseEPSSFloat(record[2])
		if epss < minScore {
			continue
		}
		rows = append(rows, EPSSItem{
			FeedItem: FeedItem{
				Title:     fmt.Sprintf("%s exploitation probability %.1f%% (EPSS)", cve, epss*100),
				Link:      "https://nvd.nist.gov/vuln/detail/" + cve,
				Published: "",
				Summary:   fmt.Sprintf("FIRST EPSS score %.4f (percentile %.4f) for %s", epss, percentile, cve),
				Tags:      []string{"cve", "epss"},
			},
			CVEID:      cve,
			EPSS:       epss,
			Percentile: percentile,
		})
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].EPSS == rows[j].EPSS {
			return rows[i].CVEID < rows[j].CVEID
		}
		return rows[i].EPSS > rows[j].EPSS
	})
	if len(rows) > limit {
		rows = rows[:limit]
	}
	return rows, nil
}

func parseEPSSFloat(raw string) (float64, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return 0, fmt.Errorf("empty")
	}
	var value float64
	_, err := fmt.Sscanf(raw, "%f", &value)
	return value, err
}
