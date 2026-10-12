/*
 * kafSIEM
 * Portions derived from novatechflow/osint-siem and cyberdude88/osint-siem.
 * See NOTICE for provenance and LICENSE for repository-local terms.
 */

import { describe, expect, it, vi } from "vitest";
import L from "leaflet";
import caddyfile from "../../docker/Caddyfile?raw";
import globeSource from "../components/GlobeView.tsx?raw";
import mobileSource from "../mobile/MobileMapView.tsx?raw";
import {
  addDarkBasemap,
  MAP_MAX_ZOOM,
  OPENFREEMAP_ATTRIBUTION,
  OPENFREEMAP_DARK_STYLE,
  OPENFREEMAP_TILE_ORIGIN,
} from "./basemap";

vi.mock("@maplibre/maplibre-gl-leaflet", () => ({
  maplibreGL: () => ({
    addTo(map: L.Map) {
      return map;
    },
  }),
}));

describe("basemap", () => {
  it("uses OpenFreeMap dark vector style, not CARTO raster tiles", () => {
    expect(OPENFREEMAP_TILE_ORIGIN).toBe("https://tiles.openfreemap.org");
    expect(OPENFREEMAP_DARK_STYLE).toBe("https://tiles.openfreemap.org/styles/dark");
    expect(OPENFREEMAP_DARK_STYLE).not.toMatch(/carto/i);
  });

  it("attributes OpenFreeMap, OpenMapTiles, and OpenStreetMap", () => {
    expect(OPENFREEMAP_ATTRIBUTION).toContain("openfreemap.org");
    expect(OPENFREEMAP_ATTRIBUTION).toContain("openmaptiles.org");
    expect(OPENFREEMAP_ATTRIBUTION).toContain("openstreetmap.org/copyright");
    expect(OPENFREEMAP_ATTRIBUTION).not.toMatch(/carto/i);
  });

  it("wires desktop and mobile maps through addDarkBasemap", () => {
    for (const src of [globeSource, mobileSource]) {
      expect(src).toContain("addDarkBasemap");
      expect(src).toContain("OPENFREEMAP_ATTRIBUTION");
      expect(src).toContain("maxZoom: MAP_MAX_ZOOM");
      expect(src).not.toMatch(/cartocdn|carto\.com/i);
      expect(src).not.toContain("tile.openstreetmap.org");
    }
  });

  it("sets a finite maxZoom so markercluster can attach", () => {
    const el = document.createElement("div");
    document.body.appendChild(el);
    const map = L.map(el, { center: [0, 0], zoom: 3 });
    expect(Number.isFinite(map.getMaxZoom())).toBe(false);
    addDarkBasemap(map);
    expect(map.getMaxZoom()).toBe(MAP_MAX_ZOOM);
    map.remove();
    el.remove();
  });

  it("allows OpenFreeMap over CSP and drops CARTO tile hosts", () => {
    const csp = caddyfile.match(/Content-Security-Policy "([^"]+)"/)?.[1];
    expect(csp).toBeDefined();
    expect(csp).toContain(`connect-src 'self' ${OPENFREEMAP_TILE_ORIGIN}`);
    expect(csp).toContain(`img-src 'self' data: blob: ${OPENFREEMAP_TILE_ORIGIN}`);
    expect(caddyfile).not.toMatch(/cartocdn/i);
  });
});
