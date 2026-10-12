import {
  DashboardApiKeyUsageChart,
  DashboardFailedScanAlert,
  DashboardFindingsActivityChart,
} from "@/components/dashboard-charts";
import { DashboardGreeting } from "@/components/dashboard-greeting";
import { DashboardPeriodMenu } from "@/components/dashboard-period-menu";
import { DashboardInsightsRow } from "@/components/dashboard/dashboard-insights-row";
import { DashboardRecentScansRow } from "@/components/dashboard/dashboard-recent-scans-row";
import { DashboardStatCards } from "@/components/dashboard-stat-cards";
import { loadDashboardInsights } from "@/lib/dashboard-insights";
import { loadDashboardRecentScanVolumes } from "@/lib/dashboard-recent-scan-volumes";
import { TopBar } from "@/components/top-bar";
import {
  dashboardChartRangeParams,
  loadDashboardCharts,
  parseActivityRange,
} from "@/lib/dashboard-stats";
import {
  DEFAULT_DASHBOARD_PERIOD,
  dashboardPeriodSiblingParams,
  loadDashboardOverview,
  parseDashboardPeriod,
} from "@/lib/dashboard-overview";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{
    findingsRange?: string;
    range?: string;
    period?: string;
  }>;
}) {
  const params = await searchParams;
  const findingsRange = parseActivityRange(params.findingsRange ?? params.range);
  const periodKey = parseDashboardPeriod(params.period);
  const rangeParams: Record<string, string> = {
    ...dashboardChartRangeParams(findingsRange),
  };
  if (periodKey !== DEFAULT_DASHBOARD_PERIOD) rangeParams.period = periodKey;

  const periodSiblingParams = dashboardPeriodSiblingParams(rangeParams.findingsRange);

  const [charts, overview, insights, recentScanVolumes] = await Promise.all([
    loadDashboardCharts(prisma, { findingsRangeKey: findingsRange }),
    loadDashboardOverview(prisma, periodKey),
    loadDashboardInsights(prisma),
    loadDashboardRecentScanVolumes(prisma),
  ]);

  return (
    <>
      <TopBar breadcrumb="/ overview" />
      <main className="min-h-0 flex-1 overflow-y-auto px-6 py-8">
        <div className="flex items-end justify-between gap-4">
          <DashboardGreeting />
          <DashboardPeriodMenu current={periodKey} siblingParams={periodSiblingParams} />
        </div>

        <div className="mt-8 space-y-8">
          <DashboardFailedScanAlert count={charts.recentFailedCount} />

          <DashboardStatCards stats={overview.stats} periodLabel={overview.period.label} />

          <DashboardInsightsRow data={insights} />

          <DashboardRecentScansRow recentScanVolumes={recentScanVolumes} />

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <DashboardFindingsActivityChart
                points={charts.discoveryActivity}
                range={charts.findingsRange}
                siblingParams={rangeParams}
              />
            </div>
            <div className="xl:relative">
              <div className="h-full xl:absolute xl:inset-0">
                <DashboardApiKeyUsageChart rows={charts.apiKeyUsage} perKeyDailyCap={charts.perKeyDailyCap} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
