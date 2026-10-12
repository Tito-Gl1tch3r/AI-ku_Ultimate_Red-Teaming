"use client";

import { useCallback, useRef, useState } from "react";
import type { DiscoveryChartPoint } from "@/lib/discovery-chart";

const DASHBOARD_FINDING_COLOR = "var(--color-accent)";
const DASHBOARD_SUBDOMAIN_COLOR = "#38bdf8";
const VIEW_WIDTH = 100;
const VIEW_HEIGHT = 48;

function shouldShowBucketLabel(index: number, total: number): boolean {
  if (total <= 16) return true;
  if (index === total - 1) return true;
  const step = Math.max(1, Math.ceil(total / 12));
  return index % step === 0;
}

function bucketX(index: number, count: number) {
  return count <= 1 ? VIEW_WIDTH / 2 : (index / (count - 1)) * VIEW_WIDTH;
}

function LegendPill({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium text-muted">
      <span
        className="size-2 shrink-0 rounded-full shadow-sm"
        style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}44` }}
      />
      {label}
    </span>
  );
}

export function DashboardDiscoveryChartLegend() {
  return (
    <div className="flex flex-wrap items-center justify-end gap-1.5" aria-label="Chart legend">
      <LegendPill color={DASHBOARD_SUBDOMAIN_COLOR} label="Subdomains" />
      <LegendPill color={DASHBOARD_FINDING_COLOR} label="Findings" />
    </div>
  );
}

export function DashboardDiscoveryAreaChart({ points }: { points: DiscoveryChartPoint[] }) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const max = Math.max(
    ...points.map((p) => Math.max(p.subdomainCount, p.findingCount)),
    1,
  );
  const n = points.length;

  const seriesCoords = (value: (p: DiscoveryChartPoint) => number) =>
    points.map((point, index) => {
      const x = bucketX(index, n);
      const count = value(point);
      const y = VIEW_HEIGHT - (count / max) * (VIEW_HEIGHT - 4) - 2;
      return { x, y, point, count };
    });

  const subdomainCoords = seriesCoords((p) => p.subdomainCount);
  const findingCoords = seriesCoords((p) => p.findingCount);

  const linePath = (coords: { x: number; y: number }[]) =>
    coords.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");

  const areaPath = (coords: { x: number; y: number }[]) => {
    const line = linePath(coords);
    return coords.length > 0
      ? `${line} L ${VIEW_WIDTH} ${VIEW_HEIGHT} L 0 ${VIEW_HEIGHT} Z`
      : "";
  };

  const subdomainLine = linePath(subdomainCoords);
  const findingLine = linePath(findingCoords);
  const subdomainArea = areaPath(subdomainCoords);
  const findingArea = areaPath(findingCoords);

  const resolveHoveredIndex = useCallback(
    (clientX: number) => {
      if (!plotRef.current || n === 0) return null;
      const rect = plotRef.current.getBoundingClientRect();
      const relX = (clientX - rect.left) / rect.width;
      const viewX = relX * VIEW_WIDTH;

      if (n === 1) return 0;

      let closest = 0;
      let minDist = Infinity;
      for (let i = 0; i < n; i++) {
        const dist = Math.abs(bucketX(i, n) - viewX);
        if (dist < minDist) {
          minDist = dist;
          closest = i;
        }
      }

      const threshold = n > 1 ? VIEW_WIDTH / (n - 1) / 2 : VIEW_WIDTH;
      return minDist <= threshold ? closest : null;
    },
    [n],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      setHoveredIndex(resolveHoveredIndex(e.clientX));
    },
    [resolveHoveredIndex],
  );

  const handleMouseLeave = useCallback(() => setHoveredIndex(null), []);

  const hovered = hoveredIndex !== null ? points[hoveredIndex] : null;
  const hoverFraction =
    hoveredIndex !== null && n > 0 ? bucketX(hoveredIndex, n) / VIEW_WIDTH : 0;
  const hoverX = `${hoverFraction * 100}%`;
  const tooltipFlipLeft = hoverFraction > 0.55;

  return (
    <div className="mt-6 overflow-visible">
      <div
        ref={plotRef}
        className="relative overflow-visible"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          preserveAspectRatio="none"
          className="dashboard-area-chart cursor-crosshair"
          role="img"
          aria-label="Findings and subdomains area chart"
        >
          <defs>
            <linearGradient id="dashboardSubdomainAreaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={DASHBOARD_SUBDOMAIN_COLOR} stopOpacity="0.32" />
              <stop offset="100%" stopColor={DASHBOARD_SUBDOMAIN_COLOR} stopOpacity="0.02" />
            </linearGradient>
            <linearGradient id="dashboardFindingAreaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={DASHBOARD_FINDING_COLOR} stopOpacity="0.34" />
              <stop offset="100%" stopColor={DASHBOARD_FINDING_COLOR} stopOpacity="0.03" />
            </linearGradient>
          </defs>
          {hoveredIndex !== null ? (
            <line
              x1={bucketX(hoveredIndex, n)}
              y1={0}
              x2={bucketX(hoveredIndex, n)}
              y2={VIEW_HEIGHT}
              stroke="var(--color-line)"
              strokeOpacity={0.85}
              strokeWidth={0.6}
              strokeDasharray="1.5 2"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {subdomainArea ? <path d={subdomainArea} fill="url(#dashboardSubdomainAreaFill)" /> : null}
          {findingArea ? <path d={findingArea} fill="url(#dashboardFindingAreaFill)" /> : null}
          {subdomainLine ? (
            <path
              d={subdomainLine}
              fill="none"
              stroke={DASHBOARD_SUBDOMAIN_COLOR}
              strokeWidth="1.1"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {findingLine ? (
            <path
              d={findingLine}
              fill="none"
              stroke={DASHBOARD_FINDING_COLOR}
              strokeWidth="1.1"
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
          {hoveredIndex !== null ? (
            <>
              <circle
                cx={subdomainCoords[hoveredIndex].x}
                cy={subdomainCoords[hoveredIndex].y}
                r={1.8}
                fill="var(--color-lift)"
                stroke={DASHBOARD_SUBDOMAIN_COLOR}
                strokeWidth={0.9}
                vectorEffect="non-scaling-stroke"
              />
              <circle
                cx={findingCoords[hoveredIndex].x}
                cy={findingCoords[hoveredIndex].y}
                r={1.8}
                fill="var(--color-lift)"
                stroke={DASHBOARD_FINDING_COLOR}
                strokeWidth={0.9}
                vectorEffect="non-scaling-stroke"
              />
            </>
          ) : null}
        </svg>

        {hovered ? (
          <div
            className={[
              "pointer-events-none absolute z-50 min-w-[9.5rem] rounded-lg border border-[var(--glass-panel-border)] px-2.5 py-2 text-[10px] shadow-glass backdrop-blur-md",
              tooltipFlipLeft ? "-translate-x-[calc(100%+0.375rem)]" : "-translate-x-1/2",
            ].join(" ")}
            style={{
              left: hoverX,
              top: "0.35rem",
              background: "var(--glass-panel-bg)",
              boxShadow: "var(--shadow-glass)",
            }}
          >
            <div className="mb-1.5 font-semibold text-cream">{hovered.label}</div>
            <div className="flex items-center gap-1.5">
              <span
                className="size-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: DASHBOARD_SUBDOMAIN_COLOR }}
              />
              <span className="text-muted">Subdomains:</span>
              <span className="ml-auto font-semibold tabular-nums text-cream">
                {hovered.subdomainCount.toLocaleString()}
              </span>
            </div>
            <div className="mt-0.5 flex items-center gap-1.5">
              <span
                className="size-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: DASHBOARD_FINDING_COLOR }}
              />
              <span className="text-muted">Findings:</span>
              <span className="ml-auto font-semibold tabular-nums text-cream">
                {hovered.findingCount.toLocaleString()}
              </span>
            </div>
          </div>
        ) : null}
      </div>

      <div className="mt-2 flex gap-1">
        {points.map((point, index) => {
          const isHovered = hoveredIndex === index;
          return (
            <div
              key={`${point.pointId}-label`}
              className={[
                "min-w-0 flex-1 truncate text-center font-mono text-[9px]",
                isHovered ? "font-semibold text-cream" : "text-muted",
              ].join(" ")}
            >
              {shouldShowBucketLabel(index, points.length) ? point.label : ""}
            </div>
          );
        })}
      </div>
    </div>
  );
}
