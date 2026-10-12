import type { PrismaClient } from "@prisma/client";

export type DashboardPeriodKey = "7d" | "14d" | "30d" | "90d";

export type DashboardPeriodConfig = {
  key: DashboardPeriodKey;
  label: string;
  days: number;
};

export const DASHBOARD_PERIODS: DashboardPeriodConfig[] = [
  { key: "7d", label: "Last 7 days", days: 7 },
  { key: "14d", label: "Last 14 days", days: 14 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
];

const PERIOD_BY_KEY = Object.fromEntries(DASHBOARD_PERIODS.map((p) => [p.key, p])) as Record<
  DashboardPeriodKey,
  DashboardPeriodConfig
>;

export const DEFAULT_DASHBOARD_PERIOD: DashboardPeriodKey = "7d";

export function parseDashboardPeriod(input: string | undefined): DashboardPeriodKey {
  if (input && input in PERIOD_BY_KEY) return input as DashboardPeriodKey;
  return DEFAULT_DASHBOARD_PERIOD;
}

export type DashboardStatKey = "targets" | "scans" | "subdomains" | "urls" | "findings";

export type DashboardStatRow = {
  key: DashboardStatKey;
  label: string;
  value: number;
  /** Whole percent vs previous period; 0 when prior period had no activity. */
  changePercent: number;
};

function utcPeriodBounds(days: number, now = new Date()) {
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  const currentStart = new Date(end);
  currentStart.setUTCDate(currentStart.getUTCDate() - days);
  const previousStart = new Date(currentStart);
  previousStart.setUTCDate(previousStart.getUTCDate() - days);
  return { previousStart, currentStart, end };
}

function percentChange(current: number, previous: number): number {
  if (previous <= 0) return 0;
  return Math.round(((current - previous) / previous) * 100);
}

async function countInWindow(
  prisma: PrismaClient,
  key: DashboardStatKey,
  start: Date,
  end: Date,
): Promise<number> {
  const where = { gte: start, lt: end };
  switch (key) {
    case "targets":
      return prisma.targetDomain.count({ where: { createdAt: where } });
    case "scans":
      return prisma.scanJob.count({ where: { createdAt: where } });
    case "subdomains":
      return prisma.subdomain.count({ where: { firstSeenAt: where } });
    case "urls":
      return prisma.discoveredUrl.count({ where: { createdAt: where } });
    case "findings":
      return prisma.analysisFinding.count({ where: { createdAt: where } });
  }
}

export async function loadDashboardOverview(
  prisma: PrismaClient,
  periodKey: DashboardPeriodKey,
): Promise<{ period: DashboardPeriodConfig; stats: DashboardStatRow[] }> {
  const period = PERIOD_BY_KEY[periodKey];
  const { previousStart, currentStart, end } = utcPeriodBounds(period.days);

  const [targetCount, scanCount, aggregates] = await Promise.all([
    prisma.targetDomain.count(),
    prisma.scanJob.count(),
    prisma.targetDomain.aggregate({
      _sum: {
        cachedSubdomainCount: true,
        cachedUrlCount: true,
        cachedFindingCount: true,
      },
    }),
  ]);

  const totals: Record<DashboardStatKey, number> = {
    targets: targetCount,
    scans: scanCount,
    subdomains: aggregates._sum.cachedSubdomainCount ?? 0,
    urls: aggregates._sum.cachedUrlCount ?? 0,
    findings: aggregates._sum.cachedFindingCount ?? 0,
  };

  const keys: DashboardStatKey[] = ["targets", "scans", "subdomains", "urls", "findings"];
  const labels: Record<DashboardStatKey, string> = {
    targets: "Targets",
    scans: "Scans",
    subdomains: "Subdomains",
    urls: "URLs",
    findings: "Findings",
  };

  const windowCounts = await Promise.all(
    keys.map(async (key) => {
      const [current, previous] = await Promise.all([
        countInWindow(prisma, key, currentStart, end),
        countInWindow(prisma, key, previousStart, currentStart),
      ]);
      return { key, current, previous };
    }),
  );

  const stats: DashboardStatRow[] = windowCounts.map(({ key, current, previous }) => ({
    key,
    label: labels[key],
    value: totals[key],
    changePercent: percentChange(current, previous),
  }));

  return { period, stats };
}

/** Preserve chart range params when changing dashboard period. */
export function dashboardPeriodSiblingParams(findingsRange?: string): Record<string, string> {
  const params: Record<string, string> = {};
  if (findingsRange) params.findingsRange = findingsRange;
  return params;
}
