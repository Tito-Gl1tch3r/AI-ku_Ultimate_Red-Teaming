import Link from "next/link";
import { DashboardQuickActionsCard } from "@/components/dashboard/dashboard-quick-actions-card";
import { TargetFavicon } from "@/components/dashboard/target-favicon";
import { IconArrowRight } from "@/components/ui-icons";
import {
  RECENT_SCAN_VOLUME_COUNT,
  type DashboardRecentScanVolumeRow,
} from "@/lib/dashboard-recent-scan-volumes";

const cardEyebrowClass =
  "text-[10px] font-semibold uppercase tracking-[0.2em] text-accent";
const footerLinkClass =
  "inline-flex items-center text-[12px] font-medium text-accent hover:text-accent-dim";

function MetricCell({
  count,
  barPct,
  fillClass,
  trackClass,
}: {
  count: number;
  barPct: number;
  fillClass: string;
  trackClass: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
      <div className={`flex h-1.5 shrink-0 items-center ${trackClass}`} aria-hidden>
        {count > 0 && barPct > 0 ? (
          <div className={`h-full rounded-full ${fillClass}`} style={{ width: `${barPct}%` }} />
        ) : null}
      </div>
      <span
        className={[
          "shrink-0 text-[12px] font-normal tabular-nums",
          count === 0 ? "text-muted" : "text-cream",
        ].join(" ")}
      >
        {count.toLocaleString()}
      </span>
    </div>
  );
}

function RecentScanVolumeCard({ rows }: { rows: DashboardRecentScanVolumeRow[] }) {
  return (
    <div className="glass-panel flex h-full flex-col rounded-2xl px-5 py-4 md:px-6 md:py-5">
      <h2 className={cardEyebrowClass}>Last {RECENT_SCAN_VOLUME_COUNT} scans</h2>
      <p className="mt-1 mb-2.5 text-[12px] text-muted">Ranked by URLs</p>

      {rows.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-line px-4 py-8 text-[12px] text-muted">
          No scans yet. Start a scan to compare volumes here.
        </div>
      ) : (
        <div className="min-w-0 flex-1 overflow-x-auto">
          <div className="min-w-[520px]">
            <div className="grid grid-cols-12 gap-3 border-b border-line pb-1.5 text-[10px] font-bold text-muted">
              <div className="col-span-3">Target</div>
              <div className="col-span-3">Urls</div>
              <div className="col-span-3">Findings</div>
              <div
                className="col-span-3 leading-tight"
                title="Subdomains that have URLs in this scan (not total target inventory)"
              >
                Subdomains with URLs
              </div>
            </div>

            <div className="flex flex-col">
              {rows.map((row, idx) => {
                const isLast = idx === rows.length - 1;

                return (
                  <Link
                    key={row.scanId}
                    href={row.href}
                    className={[
                      "grid grid-cols-12 gap-3 py-1.5 transition-colors hover:bg-white/[0.03] sm:items-center",
                      isLast ? "" : "border-b border-line",
                    ].join(" ")}
                    title={`${row.status} · ${row.createdLabel}`}
                  >
                    <div className="col-span-3 flex min-w-0 items-center">
                      <span className="mr-3 inline-flex shrink-0">
                        <TargetFavicon domain={row.domain} />
                      </span>
                      <span className="truncate text-[12px] font-medium text-cream">
                        {row.domain}
                      </span>
                    </div>

                    <div className="col-span-3">
                      <MetricCell
                        count={row.urls}
                        barPct={row.urlsBarPct}
                        fillClass="bg-accent"
                        trackClass="w-full max-w-[7rem]"
                      />
                    </div>

                    <div className="col-span-3">
                      <MetricCell
                        count={row.findings}
                        barPct={row.findingsBarPct}
                        fillClass="bg-gradient-to-r from-warn to-[color-mix(in_srgb,var(--color-warn)_65%,#f87171)]"
                        trackClass="w-full max-w-[7rem]"
                      />
                    </div>

                    <div className="col-span-3">
                      <MetricCell
                        count={row.subdomains}
                        barPct={row.subdomainsBarPct}
                        fillClass="bg-[color-mix(in_srgb,#3b82f6_88%,var(--color-accent))]"
                        trackClass="w-full max-w-[7rem]"
                      />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="scx-summary-card-footer">
        <Link href="/scans" className={footerLinkClass}>
          View all scans
          <IconArrowRight className="ml-1 size-3.5" />
        </Link>
      </div>
    </div>
  );
}

export function DashboardRecentScansRow({
  recentScanVolumes,
}: {
  recentScanVolumes: DashboardRecentScanVolumeRow[];
}) {
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div className="xl:col-span-2">
        <RecentScanVolumeCard rows={recentScanVolumes} />
      </div>
      <DashboardQuickActionsCard />
    </div>
  );
}
