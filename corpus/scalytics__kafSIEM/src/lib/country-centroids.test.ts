import { describe, expect, it } from "vitest";
import { countryCentroid, countryRegion, withCentroidCoords } from "./country-centroids";
import type { Alert } from "@/types/alert";

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: "a1",
    source_id: "src",
    status: "active",
    title: "Test",
    canonical_url: "https://example.test",
    category: "cyber_advisory",
    severity: "high",
    first_seen: "2026-07-08T10:00:00Z",
    last_seen: "2026-07-08T10:00:00Z",
    region_tag: "",
    freshness_hours: 0,
    lat: 0,
    lng: 0,
    source: {
      source_id: "src",
      authority_name: "Test",
      country: "Test",
      country_code: "",
      region: "",
    },
    ...overrides,
  } as Alert;
}

describe("countryCentroid", () => {
  it("resolves known codes case-insensitively", () => {
    expect(countryCentroid("au")).toEqual([-25.7, 134.5]);
    expect(countryCentroid("DE")).toEqual([51.1, 10.4]);
  });

  it("returns null for unknown or empty codes", () => {
    expect(countryCentroid("ZZ")).toBeNull();
    expect(countryCentroid(undefined)).toBeNull();
  });
});

describe("countryRegion", () => {
  it("maps codes onto map regions", () => {
    expect(countryRegion("AU")).toBe("Asia-Pacific");
    expect(countryRegion("DE")).toBe("Europe");
    expect(countryRegion("US")).toBe("North America");
    expect(countryRegion("SA")).toBe("Middle East");
  });
});

describe("withCentroidCoords", () => {
  it("keeps geocoded alerts untouched", () => {
    const alert = makeAlert({ lat: -33.9, lng: 151.2 });
    expect(withCentroidCoords(alert)).toBe(alert);
  });

  it("places ungeocoded alerts at the event country centroid", () => {
    const alert = makeAlert({ event_country_code: "AU" });
    const placed = withCentroidCoords(alert);
    expect([placed.lat, placed.lng]).toEqual([-25.7, 134.5]);
  });

  it("falls back to the source country when no event country is set", () => {
    const alert = makeAlert({ source: { ...makeAlert().source, country_code: "JP" } });
    const placed = withCentroidCoords(alert);
    expect([placed.lat, placed.lng]).toEqual([37.6, 138.0]);
  });

  it("leaves alerts without any resolvable country at 0,0", () => {
    const alert = makeAlert();
    const placed = withCentroidCoords(alert);
    expect([placed.lat, placed.lng]).toEqual([0, 0]);
  });
});
