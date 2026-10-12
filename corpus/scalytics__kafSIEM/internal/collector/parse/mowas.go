// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"encoding/json"
	"fmt"
	"math"
	"net/url"
	"sort"
	"strings"
)

// MOWASMapItem is the compact nationwide warning record published by
// warnung.bund.de. The version changes when an existing warning is updated.
type MOWASMapItem struct {
	ID          string            `json:"id"`
	Version     int               `json:"version"`
	StartDate   string            `json:"startDate"`
	ExpiresDate string            `json:"expiresDate"`
	Severity    string            `json:"severity"`
	Urgency     string            `json:"urgency"`
	Type        string            `json:"type"`
	I18NTitle   map[string]string `json:"i18nTitle"`
}

type mowasDetail struct {
	Identifier string      `json:"identifier"`
	Sender     string      `json:"sender"`
	Sent       string      `json:"sent"`
	Status     string      `json:"status"`
	MsgType    string      `json:"msgType"`
	Scope      string      `json:"scope"`
	Info       []mowasInfo `json:"info"`
}

type mowasInfo struct {
	Language    string       `json:"language"`
	Category    []string     `json:"category"`
	Event       string       `json:"event"`
	Urgency     string       `json:"urgency"`
	Severity    string       `json:"severity"`
	Certainty   string       `json:"certainty"`
	EventCode   []mowasValue `json:"eventCode"`
	Headline    string       `json:"headline"`
	Description string       `json:"description"`
	Instruction string       `json:"instruction"`
	Contact     string       `json:"contact"`
	Parameter   []mowasValue `json:"parameter"`
	Area        []mowasArea  `json:"area"`
}

type mowasValue struct {
	ValueName string `json:"valueName"`
	Value     string `json:"value"`
}

type mowasArea struct {
	AreaDesc string `json:"areaDesc"`
}

type mowasFeatureCollection struct {
	Features []mowasFeature `json:"features"`
}

type mowasFeature struct {
	Geometry mowasGeometry `json:"geometry"`
}

type mowasGeometry struct {
	Type        string          `json:"type"`
	Coordinates json.RawMessage `json:"coordinates"`
}

// MOWASItem is the normalized CAP-style warning consumed by the collector.
type MOWASItem struct {
	Identifier  string
	Version     int
	MessageType string
	Status      string
	Headline    string
	Description string
	Instruction string
	Contact     string
	Issuer      string
	AreaDesc    string
	Published   string
	Expires     string
	Severity    string
	Urgency     string
	Certainty   string
	EventCode   string
	Categories  []string
	Lat         float64
	Lng         float64
	Link        string
}

func ParseMOWASMap(body []byte) ([]MOWASMapItem, error) {
	var items []MOWASMapItem
	if err := json.Unmarshal(body, &items); err != nil {
		return nil, err
	}
	filtered := items[:0]
	for _, item := range items {
		if strings.TrimSpace(item.ID) == "" {
			continue
		}
		filtered = append(filtered, item)
	}
	sort.SliceStable(filtered, func(i, j int) bool {
		return filtered[i].StartDate > filtered[j].StartDate
	})
	return filtered, nil
}

func ParseMOWASDetail(body []byte, summary MOWASMapItem, portalBase string) (MOWASItem, error) {
	var detail mowasDetail
	if err := json.Unmarshal(body, &detail); err != nil {
		return MOWASItem{}, err
	}
	identifier := firstNonEmpty(detail.Identifier, summary.ID)
	if identifier == "" {
		return MOWASItem{}, fmt.Errorf("MoWaS warning has no identifier")
	}
	info, ok := preferredMOWASInfo(detail.Info)
	if !ok {
		return MOWASItem{}, fmt.Errorf("MoWaS warning %s has no info block", identifier)
	}
	headline := firstNonEmpty(info.Headline, summary.I18NTitle["de"], summary.I18NTitle["en"])
	if headline == "" {
		return MOWASItem{}, fmt.Errorf("MoWaS warning %s has no headline", identifier)
	}

	return MOWASItem{
		Identifier:  identifier,
		Version:     summary.Version,
		MessageType: firstNonEmpty(detail.MsgType, summary.Type),
		Status:      detail.Status,
		Headline:    headline,
		Description: info.Description,
		Instruction: info.Instruction,
		Contact:     info.Contact,
		Issuer:      mowasParameter(info.Parameter, "sender_langname"),
		AreaDesc:    joinMOWASAreas(info.Area),
		Published:   firstNonEmpty(detail.Sent, summary.StartDate),
		Expires:     summary.ExpiresDate,
		Severity:    firstNonEmpty(info.Severity, summary.Severity),
		Urgency:     firstNonEmpty(info.Urgency, summary.Urgency),
		Certainty:   info.Certainty,
		EventCode:   firstMOWASEventCode(info.EventCode),
		Categories:  append([]string(nil), info.Category...),
		Link:        MOWASPortalURL(portalBase, identifier, headline),
	}, nil
}

func preferredMOWASInfo(infos []mowasInfo) (mowasInfo, bool) {
	if len(infos) == 0 {
		return mowasInfo{}, false
	}
	for _, language := range []string{"de", "en"} {
		for _, info := range infos {
			if strings.EqualFold(strings.TrimSpace(info.Language), language) {
				return info, true
			}
		}
	}
	return infos[0], true
}

func firstMOWASEventCode(values []mowasValue) string {
	for _, value := range values {
		if strings.TrimSpace(value.Value) != "" {
			return strings.TrimSpace(value.Value)
		}
	}
	return ""
}

func mowasParameter(values []mowasValue, name string) string {
	for _, value := range values {
		if strings.EqualFold(strings.TrimSpace(value.ValueName), name) {
			return strings.TrimSpace(value.Value)
		}
	}
	return ""
}

func joinMOWASAreas(areas []mowasArea) string {
	values := make([]string, 0, len(areas))
	for _, area := range areas {
		if value := strings.TrimSpace(area.AreaDesc); value != "" {
			values = append(values, value)
		}
	}
	return strings.Join(values, "; ")
}

// MOWASPortalURL builds the human-facing official warning URL. Raw API URLs
// are deliberately never exposed as alert links.
func MOWASPortalURL(portalBase, identifier, headline string) string {
	base := strings.TrimRight(strings.TrimSpace(portalBase), "/")
	if base == "" {
		base = "https://warnung.bund.de"
	}
	id := strings.ReplaceAll(strings.TrimSpace(identifier), ".", "_")
	slug := strings.ReplaceAll(strings.TrimSpace(headline), "\"", "'")
	slug = strings.ReplaceAll(slug, " ", "_")
	if slug == "" {
		return base + "/meldungen/" + url.PathEscape(id) + "/"
	}
	return base + "/meldungen/" + url.PathEscape(id) + "/" + url.PathEscape(slug) + "/"
}

// ParseMOWASGeoJSON returns a representative point for the official warning
// area. Polygon centroids are area-weighted; points and multipoints are also
// accepted for forward compatibility.
func ParseMOWASGeoJSON(body []byte) (lat, lng float64, ok bool, err error) {
	var doc mowasFeatureCollection
	if err := json.Unmarshal(body, &doc); err != nil {
		return 0, 0, false, err
	}
	totalWeight := 0.0
	for _, feature := range doc.Features {
		featureLat, featureLng, weight, found, featureErr := geometryCentroid(feature.Geometry)
		if featureErr != nil {
			return 0, 0, false, featureErr
		}
		if !found {
			continue
		}
		if weight <= 0 {
			weight = 1
		}
		lat += featureLat * weight
		lng += featureLng * weight
		totalWeight += weight
	}
	if totalWeight == 0 {
		return 0, 0, false, nil
	}
	return lat / totalWeight, lng / totalWeight, true, nil
}

func geometryCentroid(geometry mowasGeometry) (lat, lng, weight float64, ok bool, err error) {
	switch strings.ToLower(strings.TrimSpace(geometry.Type)) {
	case "point":
		var point []float64
		if err := json.Unmarshal(geometry.Coordinates, &point); err != nil {
			return 0, 0, 0, false, err
		}
		if len(point) < 2 {
			return 0, 0, 0, false, nil
		}
		return point[1], point[0], 1, true, nil
	case "multipoint":
		var points [][]float64
		if err := json.Unmarshal(geometry.Coordinates, &points); err != nil {
			return 0, 0, 0, false, err
		}
		return averagePoints(points)
	case "polygon":
		var polygon [][][]float64
		if err := json.Unmarshal(geometry.Coordinates, &polygon); err != nil {
			return 0, 0, 0, false, err
		}
		return polygonCentroid(polygon)
	case "multipolygon":
		var polygons [][][][]float64
		if err := json.Unmarshal(geometry.Coordinates, &polygons); err != nil {
			return 0, 0, 0, false, err
		}
		for _, polygon := range polygons {
			polygonLat, polygonLng, polygonWeight, found, polygonErr := polygonCentroid(polygon)
			if polygonErr != nil {
				return 0, 0, 0, false, polygonErr
			}
			if !found {
				continue
			}
			lat += polygonLat * polygonWeight
			lng += polygonLng * polygonWeight
			weight += polygonWeight
		}
		if weight == 0 {
			return 0, 0, 0, false, nil
		}
		return lat / weight, lng / weight, weight, true, nil
	default:
		return 0, 0, 0, false, nil
	}
}

func polygonCentroid(polygon [][][]float64) (lat, lng, weight float64, ok bool, err error) {
	if len(polygon) == 0 {
		return 0, 0, 0, false, nil
	}
	ring := polygon[0]
	if len(ring) < 3 {
		return averagePoints(ring)
	}
	area2 := 0.0
	cx := 0.0
	cy := 0.0
	for i := 0; i < len(ring)-1; i++ {
		if len(ring[i]) < 2 || len(ring[i+1]) < 2 {
			continue
		}
		x1, y1 := ring[i][0], ring[i][1]
		x2, y2 := ring[i+1][0], ring[i+1][1]
		cross := x1*y2 - x2*y1
		area2 += cross
		cx += (x1 + x2) * cross
		cy += (y1 + y2) * cross
	}
	if math.Abs(area2) < 1e-12 {
		return averagePoints(ring)
	}
	return cy / (3 * area2), cx / (3 * area2), math.Abs(area2) / 2, true, nil
}

func averagePoints(points [][]float64) (lat, lng, weight float64, ok bool, err error) {
	count := 0.0
	for _, point := range points {
		if len(point) < 2 {
			continue
		}
		lng += point[0]
		lat += point[1]
		count++
	}
	if count == 0 {
		return 0, 0, 0, false, nil
	}
	return lat / count, lng / count, count, true, nil
}
