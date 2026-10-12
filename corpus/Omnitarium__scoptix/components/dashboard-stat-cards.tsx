import type { ComponentType } from "react";
import {
  IconAlertTriangle,
  IconArrowDown,
  IconArrowUp,
  IconGlobe,
  IconLink,
} from "@/components/ui-icons";
import { IconScans, IconTargets } from "@/components/nav-icons";
import type { DashboardStatRow } from "@/lib/dashboard-overview";

const STAT_ICONS: Record<DashboardStatRow["key"], ComponentType<{ className?: string }>> = {
  targets: IconTargets,
  scans: IconScans,
  subdomains: IconGlobe,
  urls: IconLink,
  findings: IconAlertTriangle,
};

function formatChange(percent: number): string {
  const abs = Math.abs(percent);
  if (percent > 0) return `+ ${abs}%`;
  if (percent < 0) return `- ${abs}%`;
  return "0%";
}

export function DashboardStatCards({
  stats,
  periodLabel,
}: {
  stats: DashboardStatRow[];
  periodLabel: string;
}) {
  const vsLabel = `vs ${periodLabel.toLowerCase()}`;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
      {stats.map((stat) => {
        const Icon = STAT_ICONS[stat.key];
        const up = stat.changePercent > 0;
        const down = stat.changePercent < 0;
        const flat = stat.changePercent === 0;

        return (
          <div
            key={stat.key}
            className="dashboard-stat-card glass-panel flex items-center gap-3 rounded-2xl border border-line p-4 shadow-glass transition-shadow hover:shadow-lift"
          >
            <div className="scx-metric-icon-badge--success mr-0 shrink-0 rounded-full p-2.5">
              <Icon className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xl font-bold leading-tight text-cream tabular-nums">
                {stat.value.toLocaleString()}
              </p>
              <p className="text-[12px] font-medium text-muted">{stat.label}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end">
              <span
                className={[
                  "flex items-center text-[10px] font-bold tabular-nums",
                  up ? "text-accent" : down ? "text-warn" : "text-muted",
                ].join(" ")}
              >
                {!flat && up ? <IconArrowUp className="mr-0.5 size-3 stroke-[3]" /> : null}
                {!flat && down ? <IconArrowDown className="mr-0.5 size-3 stroke-[3]" /> : null}
                {formatChange(stat.changePercent)}
              </span>
              <span className="mt-0.5 text-[10px] text-muted">{vsLabel}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
