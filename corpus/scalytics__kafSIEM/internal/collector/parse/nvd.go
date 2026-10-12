// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"encoding/json"
	"fmt"
	"strings"
)

// NVDItem is a normalized CVE record from the NVD CVE 2.0 API.
type NVDItem struct {
	FeedItem
	CVEID        string
	CVSSScore    float64
	CVSSVector   string
	Vendor       string
	Product      string
	LastModified string
	VulnStatus   string
}

// ParseNVD parses the NVD CVE 2.0 JSON response.
func ParseNVD(body []byte) ([]NVDItem, error) {
	var doc struct {
		Vulnerabilities []struct {
			CVE struct {
				ID           string `json:"id"`
				Published    string `json:"published"`
				LastModified string `json:"lastModified"`
				VulnStatus   string `json:"vulnStatus"`
				Descriptions []struct {
					Lang  string `json:"lang"`
					Value string `json:"value"`
				} `json:"descriptions"`
				Metrics struct {
					CVSSMetricV31 []struct {
						CVSSData struct {
							BaseScore    float64 `json:"baseScore"`
							VectorString string  `json:"vectorString"`
						} `json:"cvssData"`
					} `json:"cvssMetricV31"`
					CVSSMetricV30 []struct {
						CVSSData struct {
							BaseScore    float64 `json:"baseScore"`
							VectorString string  `json:"vectorString"`
						} `json:"cvssData"`
					} `json:"cvssMetricV30"`
					CVSSMetricV2 []struct {
						CVSSData struct {
							BaseScore    float64 `json:"baseScore"`
							VectorString string  `json:"vectorString"`
						} `json:"cvssData"`
					} `json:"cvssMetricV2"`
				} `json:"metrics"`
				Affected []struct {
					AffectedData []struct {
						Vendor  string `json:"vendor"`
						Product string `json:"product"`
					} `json:"affectedData"`
				} `json:"affected"`
			} `json:"cve"`
		} `json:"vulnerabilities"`
	}
	if err := json.Unmarshal(body, &doc); err != nil {
		return nil, err
	}

	out := make([]NVDItem, 0, len(doc.Vulnerabilities))
	for _, row := range doc.Vulnerabilities {
		cve := row.CVE
		id := strings.TrimSpace(cve.ID)
		if id == "" {
			continue
		}
		if strings.EqualFold(strings.TrimSpace(cve.VulnStatus), "Rejected") {
			continue
		}
		summary := ""
		for _, desc := range cve.Descriptions {
			if strings.EqualFold(desc.Lang, "en") && strings.TrimSpace(desc.Value) != "" {
				summary = strings.TrimSpace(desc.Value)
				break
			}
		}
		score, vector := nvdCVSS(cve.Metrics)
		vendor, product := nvdVendorProduct(cve.Affected)
		title := fmt.Sprintf("%s: %s", id, truncateNVDText(summary, 120))
		if title == id+": " {
			title = id + " vulnerability"
		}
		out = append(out, NVDItem{
			FeedItem: FeedItem{
				Title:     title,
				Link:      "https://nvd.nist.gov/vuln/detail/" + id,
				Published: firstNonEmpty(cve.LastModified, cve.Published),
				Summary:   summary,
				Tags:      []string{"cve", "nvd"},
			},
			CVEID:        id,
			CVSSScore:    score,
			CVSSVector:   vector,
			Vendor:       vendor,
			Product:      product,
			LastModified: strings.TrimSpace(cve.LastModified),
			VulnStatus:   strings.TrimSpace(cve.VulnStatus),
		})
	}
	return out, nil
}

func nvdCVSS(metrics struct {
	CVSSMetricV31 []struct {
		CVSSData struct {
			BaseScore    float64 `json:"baseScore"`
			VectorString string  `json:"vectorString"`
		} `json:"cvssData"`
	} `json:"cvssMetricV31"`
	CVSSMetricV30 []struct {
		CVSSData struct {
			BaseScore    float64 `json:"baseScore"`
			VectorString string  `json:"vectorString"`
		} `json:"cvssData"`
	} `json:"cvssMetricV30"`
	CVSSMetricV2 []struct {
		CVSSData struct {
			BaseScore    float64 `json:"baseScore"`
			VectorString string  `json:"vectorString"`
		} `json:"cvssData"`
	} `json:"cvssMetricV2"`
}) (float64, string) {
	if len(metrics.CVSSMetricV31) > 0 {
		return metrics.CVSSMetricV31[0].CVSSData.BaseScore, metrics.CVSSMetricV31[0].CVSSData.VectorString
	}
	if len(metrics.CVSSMetricV30) > 0 {
		return metrics.CVSSMetricV30[0].CVSSData.BaseScore, metrics.CVSSMetricV30[0].CVSSData.VectorString
	}
	if len(metrics.CVSSMetricV2) > 0 {
		return metrics.CVSSMetricV2[0].CVSSData.BaseScore, metrics.CVSSMetricV2[0].CVSSData.VectorString
	}
	return 0, ""
}

func nvdVendorProduct(affected []struct {
	AffectedData []struct {
		Vendor  string `json:"vendor"`
		Product string `json:"product"`
	} `json:"affectedData"`
}) (string, string) {
	for _, block := range affected {
		for _, row := range block.AffectedData {
			vendor := strings.TrimSpace(row.Vendor)
			product := strings.TrimSpace(row.Product)
			if vendor != "" && !strings.EqualFold(vendor, "n/a") {
				return vendor, product
			}
		}
	}
	return "", ""
}

func truncateNVDText(text string, max int) string {
	text = strings.Join(strings.Fields(text), " ")
	if len(text) <= max {
		return text
	}
	return strings.TrimSpace(text[:max]) + "..."
}
