import Link from "next/link";
import type { ReactNode } from "react";
import { ScanJobStatus } from "@prisma/client";
import { AccentDonutChart } from "@/components/scans/accent-donut-chart";
import {
  TargetFindingsRankRow,
  TargetFindingsTableHeader,
} from "@/components/scans/summary-rank-row";
import {
  IconAlertTriangle,
  IconArrowLeftRight,
  IconArrowRight,
  IconCheckCircle,
  IconClock,
  IconGlobe,
  IconLink,
  IconList,
  IconServer,
} from "@/components/ui-icons";
import type { DashboardInsightsData } from "@/lib/dashboard-insights";

const cardEyebrowClass =
  "text-[10px] font-semibold uppercase tracking-[0.2em] text-accent";
const footerLinkClass =
  "inline-flex items-center text-[12px] font-medium text-accent hover:text-accent-dim";

const STATUS_STYLE: Record<string, string> = {
  COMPLETED: "bg-accent/15 text-accent",
  RUNNING: "bg-accent/25 text-cream",
  QUEUED: "bg-muted/15 text-muted",
  FAILED: "bg-warn/15 text-warn",
  CANCELLED: "bg-muted/10 text-muted",
  PAUSED: "bg-warn/10 text-warn",
};

function ChangeMetricLine({
  icon,
  label,
  value,
  mono = false,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center text-[12px] font-medium text-cream">
        <span className="mr-2.5 shrink-0 text-accent">{icon}</span>
        {label}
      </div>
      <span
        className={[
          "max-w-[52%] shrink-0 truncate text-right text-[12px] font-normal tabular-nums text-cream/70",
          mono ? "font-mono" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

export function DashboardInsightsRow({ data }: { data: DashboardInsightsData }) {
  const scan = data.lastScan;

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <section className="scx-summary-card flex min-h-[300px] flex-col">
        <h2 className={`mb-2.5 ${cardEyebrowClass}`}>Targets with Most Findings</h2>
        {data.topTargetsByFindings.length === 0 ? (
          <p className="py-6 text-center text-[12px] text-muted">No targets yet.</p>
        ) : (
          <div className="flex-1">
            <TargetFindingsTableHeader />
            <div className="space-y-0.5">
              {data.topTargetsByFindings.map((row) => (
                <TargetFindingsRankRow
                  key={row.targetId}
                  domain={row.domain}
                  href={`/targets/${row.targetId}`}
                  count={row.count}
                  barWidthPercent={row.barWidthPercent}
                />
              ))}
            </div>
          </div>
        )}
        <div className="scx-summary-card-footer">
          <Link href="/targets" className={footerLinkClass}>
            View all targets
            <IconArrowRight className="ml-1 size-3.5" />
          </Link>
        </div>
      </section>

      <section className="scx-summary-card flex min-h-[300px] flex-col">
        <h2 className={`mb-2.5 ${cardEyebrowClass}`}>Last Scan Summary</h2>
        {!scan ? (
          <p className="text-[12px] leading-relaxed text-muted">
            No scans have been run yet. Start a scan to see results here.
          </p>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Link
                href={scan.href}
                className="truncate font-mono text-[13px] font-semibold text-cream hover:text-accent"
              >
                {scan.domain}
              </Link>
              <span
                className={[
                  "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
                  STATUS_STYLE[scan.status] ?? "bg-muted/10 text-muted",
                ].join(" ")}
              >
                {scan.status === ScanJobStatus.COMPLETED && (
                  <IconCheckCircle className="mr-1 size-3" />
                )}
                {scan.status}
              </span>
            </div>
            <p className="mb-4 text-[11px] text-muted">Scanned {scan.scannedAt}</p>
            <div className="space-y-2.5">
              <ChangeMetricLine
                icon={<IconAlertTriangle className="size-3.5" />}
                label="Findings"
                value={scan.findings.toLocaleString()}
              />
              <ChangeMetricLine
                icon={<IconLink className="size-3.5" />}
                label="URLs"
                value={scan.urls.toLocaleString()}
              />
              <ChangeMetricLine
                icon={<IconGlobe className="size-3.5" />}
                label="Subdomains"
                value={scan.subdomains.toLocaleString()}
              />
              <ChangeMetricLine
                icon={<IconServer className="size-3.5" />}
                label="IP Addresses"
                value={scan.ips.toLocaleString()}
              />
              <hr className="my-1 border-line" />
              <ChangeMetricLine
                icon={<IconClock className="size-3.5" />}
                label="Duration"
                value={scan.duration}
              />
              <ChangeMetricLine
                icon={<IconList className="size-3.5" />}
                label="Scan ID"
                value={scan.scanIdShort}
                mono
              />
            </div>
            <Link href={scan.href} className="scx-summary-compare-btn mt-6">
              <IconArrowLeftRight className="mr-2 size-3.5" />
              View scan results
              <IconArrowRight className="ml-2 size-3.5" />
            </Link>
          </>
        )}
      </section>

      <section className="scx-summary-card flex min-h-[300px] flex-col">
        <h2 className={`mb-2.5 ${cardEyebrowClass}`}>Findings by Type</h2>
        {data.findingsTotal === 0 ? (
          <p className="text-[12px] text-muted">No findings discovered yet.</p>
        ) : (
          <div className="-mt-1 flex min-h-0 flex-1 flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex shrink-0 justify-center sm:justify-start">
              <AccentDonutChart
                slices={data.findingTypeSlices}
                total={data.findingsTotal}
                centerLabel="Findings"
                ring="thin"
                size="sm"
                texture
              />
            </div>
            <div className="min-h-0 min-w-0 flex-1">
              <div className="max-h-[220px] space-y-2 overflow-y-auto pr-1">
                {data.findingTypes.map((row) => (
                  <div
                    key={row.label}
                    className="grid grid-cols-[minmax(0,1fr)_4.5rem_3rem] items-center gap-x-3 text-[12px]"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <span
                        className="size-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: row.color }}
                        aria-hidden
                      />
                      <span className="truncate font-medium text-cream" title={row.label}>
                        {row.label}
                      </span>
                    </div>
                    <span className="text-right font-normal tabular-nums text-cream">
                      {row.count.toLocaleString()}
                    </span>
                    <span className="text-right font-normal tabular-nums text-muted">
                      {row.percent}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="scx-summary-card-footer">
          <Link href="/findings" className={footerLinkClass}>
            View all findings
            <IconArrowRight className="ml-1 size-3.5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
