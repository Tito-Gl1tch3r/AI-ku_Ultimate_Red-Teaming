import { describe, expect, it } from "vitest";
import {
  formatLinkReason,
  geographyEvidenceLabel,
  geographyLabel,
  incidentSummaryLine,
  isGeographyReason,
  isIncidentAnchor,
  isIncidentPrimary,
  mergeIncidentPeers,
  reportLag,
  resolveIncidentPeers,
} from "@/lib/incident-links";
import type { Alert } from "@/types/alert";

function alert(id: string, title: string): Alert {
  return {
    alert_id: id,
    source_id: "src",
    source: {
      source_id: "src",
      authority_name: "CERT",
      country: "United States",
      country_code: "US",
      region: "North America",
      authority_type: "cert",
      base_url: "https://example.test",
    },
    title,
    canonical_url: "https://example.test/" + id,
    first_seen: "2026-04-10T10:00:00Z",
    last_seen: "2026-04-10T10:00:00Z",
    status: "active",
    category: "cyber_advisory",
    severity: "high",
    region_tag: "NA",
    lat: 0,
    lng: 0,
    freshness_hours: 1,
    incident: {
      incident_id: "inc-abc",
      member_count: 2,
      primary_alert_id: "a1",
      related_alert_ids: ["a2"],
      link_reasons: ["shared_cve:CVE-2026-1234"],
      shared_cves: ["CVE-2026-1234"],
    },
  };
}

describe("incident-links", () => {
  it("resolves related alerts from the active feed", () => {
    const primary = alert("a1", "Primary");
    const related = alert("a2", "Related");
    const peers = resolveIncidentPeers(primary, [primary, related]);
    expect(peers).toHaveLength(1);
    expect(peers[0]?.alert_id).toBe("a2");
  });

  it("formats link reasons for display", () => {
    expect(formatLinkReason("shared_cve:CVE-2026-1234")).toContain("CVE-2026-1234");
    expect(formatLinkReason("shared_entity:Islamic State")).toContain("Islamic State");
    expect(formatLinkReason("anchor:kev:CVE-2026-1234")).toContain("CISA KEV");
    expect(formatLinkReason("anchor:conflict_data:SO")).toContain("Conflict dataset");
  });

  it("detects incident anchors", () => {
    expect(isIncidentAnchor(alert("a1", "Primary"))).toBe(true);
    expect(isIncidentAnchor({ ...alert("solo", "Solo"), incident: undefined })).toBe(false);
  });

  it("detects primary vs member roles", () => {
    const primary = alert("a1", "Primary");
    const member = {
      ...alert("a2", "Member"),
      incident: {
        ...alert("a2", "Member").incident!,
        role: "member" as const,
        primary_alert_id: "a1",
      },
    };
    expect(isIncidentPrimary(primary)).toBe(true);
    expect(isIncidentPrimary(member)).toBe(false);
  });

  it("returns empty peers when related ids are absent from feed", () => {
    const primary = alert("a1", "Primary");
    expect(resolveIncidentPeers(primary, [primary])).toEqual([]);
  });

  it("merges local and API peers without duplicates", () => {
    const primary = alert("a1", "Primary");
    const localPeer = alert("a2", "Local peer");
    const remotePeer = alert("a3", "Remote peer");
    const merged = mergeIncidentPeers(primary, [primary, localPeer], [localPeer, remotePeer]);
    expect(merged.map((item) => item.alert_id).sort()).toEqual(["a2", "a3"]);
  });

  it("builds a compact summary line", () => {
    const line = incidentSummaryLine({
      incident_id: "inc-abc",
      member_count: 3,
      shared_cves: ["CVE-2026-1234"],
    });
    expect(line).toContain("3 linked alerts");
    expect(line).toContain("CVE-2026-1234");
  });

  it("labels country footprint for a single country", () => {
    expect(geographyLabel(["AU"])).toBe("Footprint (AU)");
  });

  it("labels country footprint for multiple countries", () => {
    expect(geographyLabel(["FR", "de", "BE", "FR"])).toBe("Footprint (BE, DE, FR)");
  });

  it("labels explicit geography relation evidence", () => {
    expect(geographyEvidenceLabel(["cross_source:jaccard:0.82", "shared_country:AU"])).toBe("Shared geography (AU)");
    expect(geographyEvidenceLabel(["geographic_spread:BE,DE,FR"])).toBe("Geographic spread (BE, DE, FR)");
  });

  it("returns null when no countries are known", () => {
    expect(geographyLabel(undefined)).toBeNull();
    expect(geographyLabel([])).toBeNull();
  });

  it("formats report lag against the first report", () => {
    const base = "2026-04-10T10:00:00Z";
    expect(reportLag(base, "2026-04-10T10:45:00Z")).toBe("+45m");
    expect(reportLag(base, "2026-04-10T14:12:00Z")).toBe("+4.2h");
    expect(reportLag(base, "2026-04-13T10:00:00Z")).toBe("+3d");
    expect(reportLag(base, base)).toBeNull();
    expect(reportLag(base, "not-a-date")).toBeNull();
  });

  it("identifies geography link reasons", () => {
    expect(isGeographyReason("shared_country:AU")).toBe(true);
    expect(isGeographyReason("geographic_spread:BE,DE,FR")).toBe(true);
    expect(isGeographyReason("shared_cve:CVE-2026-1234")).toBe(false);
  });
});
