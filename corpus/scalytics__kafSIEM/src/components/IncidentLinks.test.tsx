import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IncidentLinks } from "@/components/IncidentLinks";
import type { Alert } from "@/types/alert";

vi.mock("@/hooks/useIncidentDetail", () => ({
  useIncidentDetail: () => ({ detail: null, isLoading: false, isAvailable: null }),
}));

function buildAlert(id: string, title: string, withIncident = true): Alert {
  return {
    alert_id: id,
    source_id: "src-" + id,
    source: {
      source_id: "src-" + id,
      authority_name: "CERT " + id,
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
    lat: 1,
    lng: 2,
    freshness_hours: 1,
    incident: withIncident
      ? {
          incident_id: "inc-test",
          member_count: 2,
          primary_alert_id: "a1",
          related_alert_ids: ["a2"],
          link_reasons: ["shared_cve:CVE-2026-1234"],
          shared_cves: ["CVE-2026-1234"],
        }
      : undefined,
  };
}

describe("IncidentLinks", () => {
  it("renders nothing without an incident cluster", () => {
    const { container } = render(
      <IncidentLinks alert={buildAlert("solo", "Solo alert", false)} alerts={[]} onSelectAlert={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("expands corroborating alerts and selects a peer", () => {
    const onSelectAlert = vi.fn();
    const primary = buildAlert("a1", "Primary advisory");
    const related = buildAlert("a2", "Related advisory");

    render(<IncidentLinks alert={primary} alerts={[primary, related]} onSelectAlert={onSelectAlert} />);

    expect(screen.getByText(/2 linked alerts/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /linked incident/i }));
    fireEvent.click(screen.getByRole("button", { name: /related advisory/i }));

    expect(onSelectAlert).toHaveBeenCalledWith("a2");
    expect(screen.getByText("Shared CVE-2026-1234")).toBeTruthy();
  });
});