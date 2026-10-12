import { ScanJobStatus, type PrismaClient } from "@prisma/client";
import { resolveScanObservedCounts } from "@/lib/scan-observed-counts";
import { formatScanDateTime } from "@/lib/scan-format";

export const RECENT_SCAN_VOLUME_COUNT = 7;

export type DashboardRecentScanVolumeRow = {
  scanId: string;
  domain: string;
  status: ScanJobStatus;
  createdLabel: string;
  href: string;
  findings: number;
  urls: number;
  subdomains: number;
  findingsBarPct: number;
  urlsBarPct: number;
  subdomainsBarPct: number;
};

function barWidthPercent(count: number, max: number): number {
  if (max <= 0 || count <= 0) return 0;
  return Math.max(4, Math.round((count / max) * 100));
}

export async function loadDashboardRecentScanVolumes(
  prisma: PrismaClient,
): Promise<DashboardRecentScanVolumeRow[]> {
  const recentScans = await prisma.scanJob.findMany({
    orderBy: { createdAt: "desc" },
    take: RECENT_SCAN_VOLUME_COUNT,
    select: {
      id: true,
      status: true,
      createdAt: true,
      completedAt: true,
      observedFindingCount: true,
      observedSubdomainCount: true,
      observedUrlCount: true,
      targetDomain: { select: { domainNormalized: true } },
    },
  });

  const withCounts = await Promise.all(
    recentScans.map(async (scan) => ({
      scan,
      counts: await resolveScanObservedCounts(prisma, scan),
    })),
  );

  withCounts.sort((a, b) => {
    if (b.counts.urls !== a.counts.urls) return b.counts.urls - a.counts.urls;
    if (b.counts.findings !== a.counts.findings) return b.counts.findings - a.counts.findings;
    return b.scan.createdAt.getTime() - a.scan.createdAt.getTime();
  });

  const maxFindings = Math.max(0, ...withCounts.map((r) => r.counts.findings));
  const maxUrls = Math.max(0, ...withCounts.map((r) => r.counts.urls));
  const maxSubdomains = Math.max(0, ...withCounts.map((r) => r.counts.subdomains));

  return withCounts.map(({ scan, counts }) => {
    const { findings, urls, subdomains } = counts;
    const isCompleted = scan.status === ScanJobStatus.COMPLETED;

    return {
      scanId: scan.id,
      domain: scan.targetDomain.domainNormalized,
      status: scan.status,
      createdLabel: formatScanDateTime(scan.completedAt ?? scan.createdAt),
      href: isCompleted ? `/scans/${scan.id}/observed` : `/scans/${scan.id}`,
      findings,
      urls,
      subdomains,
      findingsBarPct: barWidthPercent(findings, maxFindings),
      urlsBarPct: barWidthPercent(urls, maxUrls),
      subdomainsBarPct: barWidthPercent(subdomains, maxSubdomains),
    };
  });
}
