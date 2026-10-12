// Copyright 2024 ff, Scalytics, Inc. - https://www.scalytics.io
// SPDX-License-Identifier: Apache-2.0

package parse

import (
	"math"
	"strings"
	"testing"
)

func TestParseMOWASDetailPrefersGermanAndBuildsPortalLink(t *testing.T) {
	summary := MOWASMapItem{
		ID:        "mow.DE-BY-TS-W135-20260801-000",
		Version:   19,
		StartDate: "2026-08-01T03:00:03+02:00",
		Severity:  "Minor",
		Type:      "Update",
	}
	body := []byte(`{
      "identifier":"mow.DE-BY-TS-W135-20260801-000",
      "sent":"2026-08-01T03:30:03+02:00",
      "status":"Actual",
      "msgType":"Update",
      "info":[
        {"language":"en","headline":"Forest fire"},
        {"language":"de","category":["Fire"],"headline":"Waldbrand am Hochstaufen","description":"Gefahr für Leib und Leben.","instruction":"Meiden Sie das Gebiet.","severity":"Severe","urgency":"Immediate","certainty":"Observed","eventCode":[{"valueName":"profile:DE-BBK-EVENTCODE","value":"BBK-EVC-077"}],"parameter":[{"valueName":"sender_langname","value":"Integrierte Leitstelle Traunstein"}],"area":[{"areaDesc":"Bad Reichenhall"}]}
      ]
    }`)

	item, err := ParseMOWASDetail(body, summary, "https://warnung.bund.de")
	if err != nil {
		t.Fatal(err)
	}
	if item.Headline != "Waldbrand am Hochstaufen" {
		t.Fatalf("expected German headline, got %q", item.Headline)
	}
	if item.Issuer != "Integrierte Leitstelle Traunstein" || item.AreaDesc != "Bad Reichenhall" {
		t.Fatalf("missing issuer or area: %#v", item)
	}
	if item.Severity != "Severe" || item.EventCode != "BBK-EVC-077" {
		t.Fatalf("missing CAP severity or event code: %#v", item)
	}
	if !strings.HasPrefix(item.Link, "https://warnung.bund.de/meldungen/mow_DE-BY-TS-W135-20260801-000/") {
		t.Fatalf("expected human-facing portal URL, got %q", item.Link)
	}
	if strings.Contains(item.Link, "/api31/") || strings.HasSuffix(item.Link, ".json") {
		t.Fatalf("must not expose a raw API URL: %q", item.Link)
	}
}

func TestParseMOWASGeoJSONPolygonCentroid(t *testing.T) {
	body := []byte(`{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[10,50],[12,50],[12,52],[10,52],[10,50]]]},"properties":{}}]}`)
	lat, lng, ok, err := ParseMOWASGeoJSON(body)
	if err != nil {
		t.Fatal(err)
	}
	if !ok || math.Abs(lat-51) > 1e-9 || math.Abs(lng-11) > 1e-9 {
		t.Fatalf("expected centroid 51,11, got %f,%f ok=%v", lat, lng, ok)
	}
}

func TestParseMOWASMapDropsMissingIDsAndSortsNewestFirst(t *testing.T) {
	body := []byte(`[
      {"id":"old","startDate":"2026-08-01T01:00:00+02:00"},
      {"startDate":"2026-08-01T03:00:00+02:00"},
      {"id":"new","startDate":"2026-08-01T02:00:00+02:00"}
    ]`)
	items, err := ParseMOWASMap(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 2 || items[0].ID != "new" || items[1].ID != "old" {
		t.Fatalf("unexpected map ordering: %#v", items)
	}
}
