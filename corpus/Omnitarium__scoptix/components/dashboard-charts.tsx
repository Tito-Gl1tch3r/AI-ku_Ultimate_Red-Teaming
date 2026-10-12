import type { ReactNode } from "react";
import Link from "next/link";
import {
  DashboardDiscoveryAreaChart,
  DashboardDiscoveryChartLegend,
} from "@/components/dashboard-discovery-area-chart";
import { DashboardChartRangeMenu } from "@/components/dashboard-chart-range-menu";
import { hasDiscoveryActivity, type DiscoveryChartPoint } from "@/lib/discovery-chart";
import type { ActivityRangeConfig, ApiKeyUsageRow } from "@/lib/dashboard-stats";

function ChartFooter({
  range,
  siblingParams,
  trailing,
}: {
  range: ActivityRangeConfig;
  siblingParams: Record<string, string>;
  trailing?: ReactNode;
}) {
  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
      <DashboardChartRangeMenu param="findingsRange" current={range.key} siblingParams={siblingParams} />
      {trailing ?? null}
    </div>
  );
}

function activitySubtitle(range: ActivityRangeConfig, noun: string): string {
  return `${noun} per ${range.subtitleUnit} · last ${range.label.toLowerCase()}`;
}

function activityEmptyLabel(range: ActivityRangeConfig, noun: string): string {
  return `No ${noun} in the last ${range.label.toLowerCase()}.`;
}

export function DashboardFindingsActivityChart({
  points,
  range,
  siblingParams,
}: {
  points: DiscoveryChartPoint[];
  range: ActivityRangeConfig;
  siblingParams: Record<string, string>;
}) {
  const totalSubdomains = points.reduce((sum, p) => sum + p.subdomainCount, 0);
  const totalFindings = points.reduce((sum, p) => sum + p.findingCount, 0);
  const hasActivity = hasDiscoveryActivity(points);

  return (
    <div className="glass-panel flex h-full flex-col overflow-visible rounded-2xl p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
            Discovery over time
          </div>
          <div className="mt-1 text-[12px] text-muted">
            {activitySubtitle(range, "Subdomains and findings")}
          </div>
        </div>
        <div className="text-right">
          <div className="flex flex-wrap justify-end gap-x-4 gap-y-1 font-mono text-[13px] tabular-nums text-muted">
            <span>
              <span className="text-cream">{totalSubdomains.toLocaleString()}</span> subdomains
            </span>
            <span>
              <span className="text-cream">{totalFindings.toLocaleString()}</span> findings
            </span>
          </div>
        </div>
      </div>

      {!hasActivity ? (
        <div className="mt-8 flex flex-1 items-center justify-center rounded-xl border border-dashed border-line px-4 py-10 text-center text-[12px] text-muted">
          {activityEmptyLabel(range, "findings or subdomains")}
        </div>
      ) : (
        <div className="relative z-10 flex-1 overflow-visible">
          <DashboardDiscoveryAreaChart points={points} />
        </div>
      )}

      <ChartFooter
        range={range}
        siblingParams={siblingParams}
        trailing={<DashboardDiscoveryChartLegend />}
      />
    </div>
  );
}

export function DashboardApiKeyUsageChart({
  rows,
  perKeyDailyCap,
}: {
  rows: ApiKeyUsageRow[];
  perKeyDailyCap: number;
}) {
  const active = rows.filter((r) => !r.isDisabled).length;
  const exhausted = rows.filter((r) => !r.isDisabled && r.usage >= perKeyDailyCap).length;

  return (
    <div className="glass-panel flex h-full flex-col rounded-2xl p-5 md:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">API keys</div>
          <div className="mt-1 text-[12px] text-muted">VirusTotal daily usage · UTC</div>
        </div>
        <Link
          href="/settings?tab=network"
          className="shrink-0 rounded-lg border border-line px-2.5 py-1 text-[10px] font-medium text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
        >
          Manage
        </Link>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-muted">
        <span>
          <span className="font-mono text-cream">{active}</span> active
        </span>
        {exhausted > 0 ? (
          <span className="text-warn">
            <span className="font-mono">{exhausted}</span> at daily cap
          </span>
        ) : null}
      </div>

      {rows.length === 0 ? (
        <div className="mt-6 flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line px-4 py-8 text-center">
          <p className="text-[12px] text-muted">No API keys configured.</p>
          <Link
            href="/settings?tab=network"
            className="rounded-xl border border-line px-3 py-2 text-[12px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            Add keys in Settings
          </Link>
        </div>
      ) : (
        <div className="mt-5 min-h-0 flex-1 space-y-3 overflow-y-auto pr-2 sm:max-h-[300px] xl:max-h-none">
          {rows.map((row) => {
            const pct = Math.min(100, Math.round((row.usage / perKeyDailyCap) * 100));
            const atCap = row.usage >= perKeyDailyCap;

            return (
              <div key={row.label}>
                <div className="flex items-center justify-between gap-2 text-[11px]">
                  <span className="truncate font-mono text-cream">{row.label}</span>
                  <span className={`shrink-0 font-mono ${atCap ? "text-warn" : "text-muted"}`}>
                    {row.usage}/{perKeyDailyCap}
                  </span>
                </div>
                <div className="dashboard-meter mt-1.5">
                  <div
                    className={`dashboard-meter-fill ${atCap ? "bg-warn" : row.isDisabled ? "bg-muted/35" : "bg-accent"}`}
                    style={{ width: `${row.isDisabled ? 0 : Math.max(pct, row.usage > 0 ? 4 : 0)}%` }}
                  />
                </div>
                {row.isDisabled ? (
                  <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">Disabled</div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function DashboardFailedScanAlert({ count }: { count: number }) {
  if (count <= 0) return null;

  return (
    <div className="rounded-2xl border border-warn/30 bg-warn/5 px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-warn">Attention</div>
          <p className="mt-1 text-[13px] text-cream">
            {count.toLocaleString()} failed scan{count === 1 ? "" : "s"} in the last 24 hours.
          </p>
        </div>
        <Link
          href="/scans"
          className="rounded-xl border border-warn/30 px-3 py-2 text-[12px] font-medium text-warn transition-colors hover:bg-warn/10"
        >
          View scans
        </Link>
      </div>
    </div>
  );
}
