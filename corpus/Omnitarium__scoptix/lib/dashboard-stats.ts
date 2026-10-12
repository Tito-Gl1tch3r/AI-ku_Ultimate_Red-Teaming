import { EngineProvider, ScanJobStatus, type PrismaClient } from "@prisma/client";
import { buildDashboardDiscoveryPoints, type DiscoveryChartPoint } from "@/lib/discovery-chart";
import { PER_KEY_PER_DAY, resolveUsageCounters } from "@/lib/quota-constants";

export type ActivityBucket = { key: string; label: string; count: number };

export type StatusCount = { status: string; count: number };

export type ApiKeyUsageRow = { label: string; usage: number; isDisabled: boolean };

export type ActivityRangeKey = "14d" | "30d" | "90d" | "180d" | "365d";

export type ActivityRangeConfig = {
  key: ActivityRangeKey;
  label: string;
  days: number;
  bucket: "day" | "week" | "month";
  subtitleUnit: string;
};

export const ACTIVITY_RANGES: ActivityRangeConfig[] = [
  { key: "14d", label: "14 days", days: 14, bucket: "day", subtitleUnit: "day" },
  { key: "30d", label: "1 month", days: 30, bucket: "day", subtitleUnit: "day" },
  { key: "90d", label: "3 months", days: 90, bucket: "week", subtitleUnit: "week" },
  { key: "180d", label: "6 months", days: 180, bucket: "week", subtitleUnit: "week" },
  { key: "365d", label: "1 year", days: 365, bucket: "month", subtitleUnit: "month" },
];

const RANGE_BY_KEY = Object.fromEntries(ACTIVITY_RANGES.map((r) => [r.key, r])) as Record<
  ActivityRangeKey,
  ActivityRangeConfig
>;

export const DEFAULT_ACTIVITY_RANGE: ActivityRangeKey = "14d";

export function parseActivityRange(input: string | undefined): ActivityRangeKey {
  if (input && input in RANGE_BY_KEY) return input as ActivityRangeKey;
  return DEFAULT_ACTIVITY_RANGE;
}

export function getActivityRangeConfig(key: ActivityRangeKey): ActivityRangeConfig {
  return RANGE_BY_KEY[key];
}

/** Query params for sibling chart ranges (preserved when one chart changes range). */
export function dashboardChartRangeParams(
  findingsRange: ActivityRangeKey,
): Record<string, string> {
  const params: Record<string, string> = {};
  if (findingsRange !== DEFAULT_ACTIVITY_RANGE) params.findingsRange = findingsRange;
  return params;
}

export type ActivitySeriesSource =
  | "scan_job"
  | "analysis_finding"
  | "discovered_url"
  | "subdomain";

export async function loadActivitySeriesForRange(
  prisma: PrismaClient,
  rangeKey: ActivityRangeKey,
  source: ActivitySeriesSource,
): Promise<{ buckets: ActivityBucket[]; range: ActivityRangeConfig }> {
  const range = getActivityRangeConfig(rangeKey);
  const since = activitySince(range);
  const buckets = await loadActivitySeries(prisma, range, source, since);
  return { buckets, range };
}

function utcToday(now = new Date()): Date {
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

function startOfUtcWeek(d: Date): Date {
  const utc = utcToday(d);
  const day = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() - (day - 1));
  return utc;
}

function formatDayLabel(d: Date, isToday: boolean): string {
  if (isToday) return "Today";
  return d.toLocaleDateString("en-US", { month: "numeric", day: "numeric", timeZone: "UTC" });
}

function buildUtcDayRange(dayCount: number, now = new Date()): ActivityBucket[] {
  const buckets: ActivityBucket[] = [];
  for (let i = dayCount - 1; i >= 0; i--) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - i));
    buckets.push({
      key: d.toISOString().slice(0, 10),
      label: formatDayLabel(d, i === 0),
      count: 0,
    });
  }
  return buckets;
}

function buildUtcWeekRange(since: Date, now = new Date()): ActivityBucket[] {
  const buckets: ActivityBucket[] = [];
  let cur = startOfUtcWeek(since);
  const end = startOfUtcWeek(now);

  while (cur.getTime() <= end.getTime()) {
    buckets.push({
      key: cur.toISOString().slice(0, 10),
      label: cur.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }),
      count: 0,
    });
    cur = new Date(Date.UTC(cur.getUTCFullYear(), cur.getUTCMonth(), cur.getUTCDate() + 7));
  }

  return buckets;
}

function buildUtcMonthRange(since: Date, now = new Date()): ActivityBucket[] {
  const buckets: ActivityBucket[] = [];
  let y = since.getUTCFullYear();
  let m = since.getUTCMonth();
  const endY = now.getUTCFullYear();
  const endM = now.getUTCMonth();

  while (y < endY || (y === endY && m <= endM)) {
    const d = new Date(Date.UTC(y, m, 1));
    buckets.push({
      key: d.toISOString().slice(0, 10),
      label: d.toLocaleDateString("en-US", { month: "short", timeZone: "UTC" }),
      count: 0,
    });
    m += 1;
    if (m > 11) {
      m = 0;
      y += 1;
    }
  }

  return buckets;
}

function buildActivityBuckets(range: ActivityRangeConfig, now = new Date()): ActivityBucket[] {
  const since = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - (range.days - 1)),
  );

  if (range.bucket === "day") return buildUtcDayRange(range.days, now);
  if (range.bucket === "week") return buildUtcWeekRange(since, now);
  return buildUtcMonthRange(since, now);
}

function activitySince(range: ActivityRangeConfig, now = new Date()): Date {
  return new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - (range.days - 1)),
  );
}

function mergeBuckets(buckets: ActivityBucket[], rows: { key: string; count: number }[]): ActivityBucket[] {
  const map = new Map(rows.map((r) => [r.key, r.count]));
  return buckets.map((b) => ({ ...b, count: map.get(b.key) ?? 0 }));
}

function rawBucketKey(day: Date | string): string {
  if (day instanceof Date) return day.toISOString().slice(0, 10);
  return String(day).slice(0, 10);
}

async function loadActivitySeries(
  prisma: PrismaClient,
  range: ActivityRangeConfig,
  source: ActivitySeriesSource,
  since: Date,
): Promise<ActivityBucket[]> {
  type RawBucketCount = { bucket: Date; count: number };

  const trunc = range.bucket === "month" ? "month" : range.bucket === "week" ? "week" : "day";
  const template = buildActivityBuckets(range);

  const rows = await (async () => {
    switch (source) {
      case "scan_job":
        return prisma.$queryRaw<RawBucketCount[]>`
          SELECT (date_trunc(${trunc}, created_at AT TIME ZONE 'UTC'))::date AS bucket,
                 COUNT(*)::int AS count
          FROM scan_job
          WHERE created_at >= ${since}
          GROUP BY 1
        `;
      case "analysis_finding":
        return prisma.$queryRaw<RawBucketCount[]>`
          SELECT (date_trunc(${trunc}, created_at AT TIME ZONE 'UTC'))::date AS bucket,
                 COUNT(*)::int AS count
          FROM analysis_finding
          WHERE created_at >= ${since}
          GROUP BY 1
        `;
      case "discovered_url":
        return prisma.$queryRaw<RawBucketCount[]>`
          SELECT (date_trunc(${trunc}, created_at AT TIME ZONE 'UTC'))::date AS bucket,
                 COUNT(*)::int AS count
          FROM discovered_url
          WHERE created_at >= ${since}
          GROUP BY 1
        `;
      case "subdomain":
        return prisma.$queryRaw<RawBucketCount[]>`
          SELECT (date_trunc(${trunc}, first_seen_at AT TIME ZONE 'UTC'))::date AS bucket,
                 COUNT(*)::int AS count
          FROM subdomain
          WHERE first_seen_at >= ${since}
          GROUP BY 1
        `;
    }
  })();

  return mergeBuckets(
    template,
    rows.map((r) => ({ key: rawBucketKey(r.bucket), count: Number(r.count) })),
  );
}

export async function loadDashboardCharts(
  prisma: PrismaClient,
  opts: {
    findingsRangeKey?: ActivityRangeKey;
  } = {},
) {
  const findingsRangeKey = opts.findingsRangeKey ?? DEFAULT_ACTIVITY_RANGE;
  const failedSince = new Date(Date.now() - 86_400_000);

  const [findingsSeries, subdomainSeries, apiKeys, recentFailedCount] = await Promise.all([
    loadActivitySeriesForRange(prisma, findingsRangeKey, "analysis_finding"),
    loadActivitySeriesForRange(prisma, findingsRangeKey, "subdomain"),
    prisma.apiKey.findMany({
      where: { provider: EngineProvider.VIRUSTOTAL },
      orderBy: { createdAt: "asc" },
      select: {
        label: true,
        usageCount: true,
        usageCountDate: true,
        usageCountWeekly: true,
        usageWeekKey: true,
        usageCountMonthly: true,
        usageMonthKey: true,
        isDisabled: true,
      },
    }),
    prisma.scanJob.count({
      where: { status: ScanJobStatus.FAILED, createdAt: { gte: failedSince } },
    }),
  ]);

  const discoveryActivity: DiscoveryChartPoint[] = buildDashboardDiscoveryPoints(
    findingsSeries.buckets,
    findingsSeries.buckets,
    subdomainSeries.buckets,
  );

  return {
    findingsRange: findingsSeries.range,
    discoveryActivity,
    apiKeyUsage: apiKeys.map((k) => ({
      label: k.label,
      usage: resolveUsageCounters(k).daily,
      isDisabled: k.isDisabled,
    })),
    recentFailedCount,
    perKeyDailyCap: PER_KEY_PER_DAY,
  };
}

/** @deprecated Use ActivityBucket */
export type DayCount = ActivityBucket;

/** @deprecated Use DEFAULT_ACTIVITY_RANGE */
export const ACTIVITY_DAYS = 14;
