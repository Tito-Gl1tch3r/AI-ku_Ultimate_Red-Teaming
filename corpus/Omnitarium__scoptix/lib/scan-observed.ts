import type { Prisma } from "@prisma/client";
import { ScanJobStatus } from "@prisma/client";
import { prisma } from "@/lib/prisma";

const VT_SCAN_PHASES = new Set(["T1_APEX", "T2_SUBDOMAINS"]);

export type ObservedAvailabilityState = "ready" | "legacy_unavailable";

export type ObservedAvailability = {
  findings: ObservedAvailabilityState;
  subdomains: ObservedAvailabilityState;
  urls: ObservedAvailabilityState;
  ips: ObservedAvailabilityState;
};

export type ObservedScanSummary = Prisma.ScanJobGetPayload<{
  include: {
    targetDomain: {
      select: {
        id: true;
        domainNormalized: true;
        cachedSubdomainCount: true;
      };
    };
  };
}>;

export type ScanSummaryContext = Pick<ObservedScanSummary, "observedVersion">;

export function normalizeTake(raw: string | null, fallback = 50, max = 200) {
  const n = Number(raw ?? "");
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(1, Math.floor(n)));
}

export function normalizeSkip(raw: string | null, fallback = 0) {
  const n = Number(raw ?? "");
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.floor(n));
}

export async function getObservedScanSummary(scanId: string) {
  return prisma.scanJob.findUnique({
    where: { id: scanId },
    include: {
      targetDomain: {
        select: {
          id: true,
          domainNormalized: true,
          cachedSubdomainCount: true,
        },
      },
    },
  });
}

/** True when observed snapshot has data worth opening before the full scan completes. */
export function canViewPartialObservedResults(scan: {
  status: string;
  phase?: string | null;
  observedUrlCount?: number | null;
  observedFindingCount?: number | null;
}): boolean {
  const hasObservedData =
    (scan.observedUrlCount ?? 0) > 0 || (scan.observedFindingCount ?? 0) > 0;

  if (scan.status === ScanJobStatus.COMPLETED) return true;

  if (scan.status === ScanJobStatus.CANCELLED) return hasObservedData;

  if (scan.status !== ScanJobStatus.RUNNING) return false;

  if (hasObservedData) return true;

  return Boolean(scan.phase && !VT_SCAN_PHASES.has(scan.phase));
}

export function partialObservedPhaseLabel(phase: string | null | undefined): string | null {
  if (!phase) return null;
  if (phase === "T3_WAYBACK_APEX" || phase === "T4_WAYBACK_SUBDOMAINS") {
    return "VirusTotal finished · Wayback Machine in progress";
  }
  if (phase === "T6_ANALYSIS") return "Analyzing collected URLs";
  return null;
}

export function getObservedAvailability(
  scan: Pick<ObservedScanSummary, "observedVersion">,
): ObservedAvailability {
  const hasSnapshot = (scan.observedVersion ?? 0) >= 1;

  return {
    findings: "ready",
    subdomains: hasSnapshot ? "ready" : "legacy_unavailable",
    urls: hasSnapshot ? "ready" : "legacy_unavailable",
    ips: hasSnapshot ? "ready" : "legacy_unavailable",
  };
}
