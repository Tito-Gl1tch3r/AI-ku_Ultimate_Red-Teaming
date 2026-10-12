"use client";

import { useState, useCallback, useRef, useId, useMemo } from "react";
import {
  toDiscoveryChartPoints,
  type DiscoveryChartPoint,
} from "@/lib/discovery-chart";

/* ── theme-aware palette ──────────────────────────────────────── */
const URL_COLOR = "var(--color-accent)";
const FINDING_COLOR = "var(--chart-finding, #a78bfa)";
const SUBDOMAIN_COLOR = "#38bdf8";

/* ── layout constants ─────────────────────────────────────────── */
const W = 460;
const H = 272;
const PAD = { top: 26, right: 48, bottom: 40, left: 48 };
const PLOT_X_INSET = 16;

export type DiscoveryChartVariant = "target-history" | "platform-activity";

type SeriesKey = "urlCount" | "findingCount" | "subdomainCount";

/* ── helpers ───────────────────────────────────────────────────── */
function niceYMax(maxVal: number) {
  if (maxVal <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(maxVal));
  const normalized = maxVal / magnitude;
  let nice = 10;
  if (normalized <= 1) nice = 1;
  else if (normalized <= 2) nice = 2;
  else if (normalized <= 5) nice = 5;
  return nice * magnitude;
}

function formatTick(value: number) {
  if (value >= 1_000_000) {
    const m = value / 1_000_000;
    return Number.isInteger(m) ? `${m}M` : `${m.toFixed(1)}M`;
  }
  if (value >= 1000) {
    const k = value / 1000;
    return Number.isInteger(k) ? `${k}k` : `${k.toFixed(1)}k`;
  }
  return value.toLocaleString();
}

type Coord = { x: number; y: number; value: number; point: DiscoveryChartPoint };

function seriesX(index: number, count: number, plotWidth: number) {
  if (count <= 1) return plotWidth / 2;
  const innerWidth = plotWidth - PLOT_X_INSET * 2;
  return PLOT_X_INSET + (index / (count - 1)) * innerWidth;
}

function seriesPoints(
  points: DiscoveryChartPoint[],
  valueKey: SeriesKey,
  plotWidth: number,
  plotHeight: number,
  yMax: number,
): Coord[] {
  const n = points.length;
  return points.map((point, index) => {
    const x = seriesX(index, n, plotWidth);
    const value = point[valueKey];
    const y = plotHeight - (value / yMax) * plotHeight;
    return { x: PAD.left + x, y: PAD.top + y, value, point };
  });
}

function smoothPath(coords: Coord[], tension = 0.35): string {
  if (coords.length === 0) return "";
  if (coords.length === 1) return `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`;
  if (coords.length === 2) {
    return `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)} L ${coords[1].x.toFixed(2)} ${coords[1].y.toFixed(2)}`;
  }

  let d = `M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`;

  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[Math.max(i - 1, 0)];
    const p1 = coords[i];
    const p2 = coords[i + 1];
    const p3 = coords[Math.min(i + 2, coords.length - 1)];

    const cp1x = p1.x + ((p2.x - p0.x) * tension) / 3;
    const cp1y = p1.y + ((p2.y - p0.y) * tension) / 3;
    const cp2x = p2.x - ((p3.x - p1.x) * tension) / 3;
    const cp2y = p2.y - ((p3.y - p1.y) * tension) / 3;

    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }

  return d;
}

function smoothAreaPath(coords: Coord[], baselineY: number): string {
  if (coords.length === 0) return "";
  const line = smoothPath(coords);
  const last = coords[coords.length - 1];
  const first = coords[0];
  return `${line} L ${last.x.toFixed(2)} ${baselineY.toFixed(2)} L ${first.x.toFixed(2)} ${baselineY.toFixed(2)} Z`;
}

function yTicks(yMax: number, steps = 4) {
  const step = yMax / steps;
  return Array.from({ length: steps + 1 }, (_, i) => i * step);
}

function LegendPill({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line/60 bg-void/50 px-2.5 py-0.5 text-[10px] font-medium text-muted backdrop-blur-sm">
      <span
        className="size-2 shrink-0 rounded-full shadow-sm"
        style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}44` }}
      />
      {label}
    </span>
  );
}

function MetricSnapshotCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="scx-summary-inner-item group relative overflow-hidden px-3 py-2.5">
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{ background: `linear-gradient(135deg, ${color}, transparent 70%)` }}
      />
      <div className="relative">
        <div className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</div>
        <div
          className={[
            "mt-1 text-lg font-bold tabular-nums",
            label === "URLs" ? "text-accent" : "",
          ].join(" ")}
          style={label === "URLs" ? undefined : { color }}
        >
          {value.toLocaleString()}
        </div>
      </div>
    </div>
  );
}

function SinglePointSnapshot({
  point,
  showUrls,
  showSubdomains,
  variant,
}: {
  point: DiscoveryChartPoint;
  showUrls: boolean;
  showSubdomains: boolean;
  variant: DiscoveryChartVariant;
}) {
  const isPlatform = variant === "platform-activity";

  return (
    <div className={isPlatform ? "grid grid-cols-2 gap-3" : "flex flex-1 flex-col justify-center gap-4"}>
      {!isPlatform ? (
        <p className="text-[12px] leading-relaxed text-muted">
          One completed scan so far. Run another scan on this target to see how discovery changes over time.
        </p>
      ) : null}
      <div
        className={[
          isPlatform ? "contents" : "grid gap-3",
          isPlatform || (!showUrls && showSubdomains)
            ? isPlatform
              ? ""
              : "grid-cols-2"
            : showSubdomains
              ? "grid-cols-1 sm:grid-cols-3"
              : "grid-cols-2",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {showUrls ? (
          <MetricSnapshotCard label="URLs" value={point.urlCount} color={URL_COLOR} />
        ) : null}
        {showSubdomains ? (
          <MetricSnapshotCard
            label="Subdomains"
            value={point.subdomainCount}
            color={SUBDOMAIN_COLOR}
          />
        ) : null}
        <MetricSnapshotCard label="Findings" value={point.findingCount} color={FINDING_COLOR} />
      </div>
    </div>
  );
}

type TooltipData = {
  x: number;
  y: number;
  label: string;
  urls: number;
  subdomains: number;
  findings: number;
  isCurrent: boolean;
  showUrls: boolean;
  showSubdomains: boolean;
};

function ChartTooltip({ data }: { data: TooltipData }) {
  const left = data.x < W / 2;
  const rowCount = (data.showUrls ? 1 : 0) + (data.showSubdomains ? 1 : 0) + 1;
  const boxHeight = 52 + rowCount * 18;

  return (
    <g>
      <line
        x1={data.x}
        y1={PAD.top}
        x2={data.x}
        y2={PAD.top + H - PAD.top - PAD.bottom}
        stroke="var(--color-line)"
        strokeOpacity={0.5}
        strokeDasharray="2 3"
        strokeWidth={1}
      />
      <foreignObject
        x={left ? data.x + 10 : data.x - 148}
        y={Math.max(PAD.top, data.y - 56)}
        width={138}
        height={boxHeight}
        style={{ overflow: "visible" }}
      >
        <div
          className="rounded-lg border border-line/80 p-2 text-[10px] shadow-lg backdrop-blur-md"
          style={{
            background: "var(--glass-panel-bg)",
            boxShadow: "var(--shadow-glass)",
          }}
        >
          <div className="mb-1.5 font-semibold text-cream">
            {data.label}
            {data.isCurrent && (
              <span className="ml-1 text-[9px] font-normal text-accent">(current)</span>
            )}
          </div>
          {data.showUrls ? (
            <div className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full" style={{ backgroundColor: URL_COLOR }} />
              <span className="text-muted">URLs:</span>
              <span className="ml-auto font-semibold tabular-nums text-cream">
                {data.urls.toLocaleString()}
              </span>
            </div>
          ) : null}
          {data.showSubdomains ? (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="size-1.5 rounded-full" style={{ backgroundColor: SUBDOMAIN_COLOR }} />
              <span className="text-muted">Subdomains:</span>
              <span className="ml-auto font-semibold tabular-nums text-cream">
                {data.subdomains.toLocaleString()}
              </span>
            </div>
          ) : null}
          <div className="mt-0.5 flex items-center gap-1.5">
            <span className="size-1.5 rounded-full" style={{ backgroundColor: FINDING_COLOR }} />
            <span className="text-muted">Findings:</span>
            <span className="ml-auto font-semibold tabular-nums text-cream">
              {data.findings.toLocaleString()}
            </span>
          </div>
        </div>
      </foreignObject>
    </g>
  );
}

function SeriesDots({
  coords,
  color,
  glowId,
  seriesLabel,
  hoveredIndex,
}: {
  coords: Coord[];
  color: string;
  glowId: string;
  seriesLabel: string;
  hoveredIndex: number | null;
}) {
  return coords.map(({ x, y, value, point }, idx) => {
    const isHovered = hoveredIndex === idx;
    const r = point.isCurrent ? 4 : 3;
    return (
      <g key={`${seriesLabel}-${point.pointId}`} className="transition-opacity duration-200">
        <circle
          cx={x}
          cy={y}
          r={isHovered ? r + 4 : r + 2}
          fill={color}
          opacity={isHovered ? 0.2 : point.isCurrent ? 0.12 : 0.06}
          className="transition-all duration-200"
        />
        <circle
          cx={x}
          cy={y}
          r={isHovered ? r + 1 : r}
          fill="var(--color-lift)"
          stroke={color}
          strokeWidth={isHovered ? 2.5 : 2}
          className="transition-all duration-200"
          filter={isHovered ? `url(#${glowId})` : undefined}
        />
        <title>{`${point.label}: ${value.toLocaleString()} ${seriesLabel}${point.isCurrent ? " (current)" : ""}`}</title>
      </g>
    );
  });
}

export function DiscoveryOverTimeChart({
  points: rawPoints,
  variant = "target-history",
}: {
  points: Parameters<typeof toDiscoveryChartPoints>[0];
  variant?: DiscoveryChartVariant;
}) {
  const uid = useId().replace(/:/g, "");
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const points = useMemo(() => toDiscoveryChartPoints(rawPoints), [rawPoints]);
  const isPlatform = variant === "platform-activity";
  const showUrls = !isPlatform;
  const showSubdomains = isPlatform;

  const plotWidth = W - PAD.left - PAD.right;
  const plotHeight = H - PAD.top - PAD.bottom;
  const baselineY = PAD.top + plotHeight;

  const singleAxis = isPlatform;

  const leftMax = niceYMax(
    Math.max(
      ...points.map((p) =>
        isPlatform
          ? Math.max(p.subdomainCount, p.findingCount)
          : Math.max(p.urlCount, showSubdomains ? p.subdomainCount : 0),
      ),
      1,
    ),
  );
  const findingMax = singleAxis
    ? leftMax
    : niceYMax(Math.max(...points.map((p) => p.findingCount), 1));

  const urlCoords = showUrls
    ? seriesPoints(points, "urlCount", plotWidth, plotHeight, leftMax)
    : [];
  const subdomainCoords = showSubdomains
    ? seriesPoints(points, "subdomainCount", plotWidth, plotHeight, leftMax)
    : [];
  const findingCoords = seriesPoints(
    points,
    "findingCount",
    plotWidth,
    plotHeight,
    singleAxis ? leftMax : findingMax,
  );

  const urlLine = smoothPath(urlCoords);
  const subdomainLine = smoothPath(subdomainCoords);
  const findingLine = smoothPath(findingCoords);
  const urlArea = smoothAreaPath(urlCoords, baselineY);
  const subdomainArea = smoothAreaPath(subdomainCoords, baselineY);
  const findingArea = smoothAreaPath(findingCoords, baselineY);

  const gridTicks = yTicks(leftMax);

  const title = isPlatform ? "Discovery over time" : "Target History";
  const subtitle = isPlatform
    ? points.length <= 1
      ? "Subdomains & findings over time"
      : `Subdomains & findings · ${points.length} periods`
    : points.length <= 1
      ? "URLs & findings on this target"
      : `Last ${points.length} completed scans · same target`;

  const ariaLabel =
    points.length === 0
      ? `${title}: no data yet`
      : `${title}: ${points
          .map((p) =>
            isPlatform
              ? `${p.label} subdomains ${p.subdomainCount}, findings ${p.findingCount}`
              : `${p.label} URLs ${p.urlCount}${showSubdomains ? `, subdomains ${p.subdomainCount}` : ""}, findings ${p.findingCount}`,
          )
          .join("; ")}`;

  const hoverCoords = showUrls ? urlCoords : subdomainCoords;

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (points.length < 2 || !svgRef.current || hoverCoords.length === 0) return;
      const rect = svgRef.current.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * W;
      let closest = 0;
      let minDist = Infinity;
      for (let i = 0; i < hoverCoords.length; i++) {
        const dist = Math.abs(hoverCoords[i].x - mouseX);
        if (dist < minDist) {
          minDist = dist;
          closest = i;
        }
      }
      setHoveredIndex(minDist < 40 ? closest : null);
    },
    [points.length, hoverCoords],
  );

  const handleMouseLeave = useCallback(() => setHoveredIndex(null), []);

  const tooltipData: TooltipData | null =
    hoveredIndex !== null && hoverCoords[hoveredIndex]
      ? {
          x: hoverCoords[hoveredIndex].x,
          y: Math.min(
            hoverCoords[hoveredIndex].y,
            findingCoords[hoveredIndex]?.y ?? hoverCoords[hoveredIndex].y,
            subdomainCoords[hoveredIndex]?.y ?? hoverCoords[hoveredIndex].y,
          ),
          label: points[hoveredIndex].label,
          urls: points[hoveredIndex].urlCount,
          subdomains: points[hoveredIndex].subdomainCount,
          findings: points[hoveredIndex].findingCount,
          isCurrent: Boolean(points[hoveredIndex].isCurrent),
          showUrls,
          showSubdomains,
        }
      : null;

  const ids = {
    urlFill: `disc-url-fill-${uid}`,
    findFill: `disc-find-fill-${uid}`,
    subFill: `disc-sub-fill-${uid}`,
    glowUrl: `dot-glow-url-${uid}`,
    glowFind: `dot-glow-find-${uid}`,
    glowSub: `dot-glow-sub-${uid}`,
  };

  return (
    <div className={isPlatform ? "" : "flex h-full min-h-[260px] flex-col"}>
      {!isPlatform ? (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">{title}</h2>
            <p className="mt-0.5 text-[11px] text-muted">{subtitle}</p>
          </div>
          {points.length >= 2 ? (
            <div className="flex flex-wrap items-center gap-1.5">
              {showUrls ? <LegendPill color={URL_COLOR} label="URLs" /> : null}
              {showSubdomains ? <LegendPill color={SUBDOMAIN_COLOR} label="Subdomains" /> : null}
              <LegendPill color={FINDING_COLOR} label="Findings" />
            </div>
          ) : null}
        </div>
      ) : points.length >= 2 ? (
        <div className="mb-2 flex flex-wrap items-center justify-end gap-1.5">
          {showSubdomains ? <LegendPill color={SUBDOMAIN_COLOR} label="Subdomains" /> : null}
          <LegendPill color={FINDING_COLOR} label="Findings" />
        </div>
      ) : null}

      {points.length === 0 ? (
        <p className={isPlatform ? "text-[12px] text-muted" : "flex flex-1 items-center text-[12px] text-muted"}>
          {isPlatform
            ? "No findings or subdomains in this period yet."
            : "Complete a scan to start tracking URLs and findings for this target."}
        </p>
      ) : points.length === 1 ? (
        <SinglePointSnapshot
          point={points[0]}
          showUrls={showUrls}
          showSubdomains={showSubdomains}
          variant={variant}
        />
      ) : (
        <div className={isPlatform ? "h-36" : "flex flex-1 flex-col overflow-hidden"}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className={isPlatform ? "dashboard-area-chart select-none" : "h-full w-full select-none"}
            role="img"
            aria-label={ariaLabel}
            preserveAspectRatio="xMidYMid meet"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <defs>
              <linearGradient id={ids.urlFill} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={URL_COLOR} stopOpacity={0.18} />
                <stop offset="60%" stopColor={URL_COLOR} stopOpacity={0.06} />
                <stop offset="100%" stopColor={URL_COLOR} stopOpacity={0.01} />
              </linearGradient>
              <linearGradient id={ids.subFill} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={SUBDOMAIN_COLOR} stopOpacity={0.14} />
                <stop offset="60%" stopColor={SUBDOMAIN_COLOR} stopOpacity={0.04} />
                <stop offset="100%" stopColor={SUBDOMAIN_COLOR} stopOpacity={0.005} />
              </linearGradient>
              <linearGradient id={ids.findFill} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={FINDING_COLOR} stopOpacity={0.15} />
                <stop offset="60%" stopColor={FINDING_COLOR} stopOpacity={0.04} />
                <stop offset="100%" stopColor={FINDING_COLOR} stopOpacity={0.005} />
              </linearGradient>
              <filter id={ids.glowUrl} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id={ids.glowSub} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id={ids.glowFind} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {gridTicks.map((tick) => {
              const y = PAD.top + plotHeight - (tick / leftMax) * plotHeight;
              const isBaseline = tick === 0;
              return (
                <g key={`grid-${tick}`}>
                  {!isBaseline ? (
                    <line
                      x1={PAD.left}
                      y1={y}
                      x2={PAD.left + plotWidth}
                      y2={y}
                      stroke="var(--color-line)"
                      strokeOpacity={0.5}
                      strokeDasharray="3 3"
                      strokeWidth={1}
                    />
                  ) : null}
                  <text
                    x={PAD.left - 8}
                    y={y + 3}
                    textAnchor="end"
                    fill="var(--color-muted)"
                    fontSize={8.5}
                    opacity={0.75}
                  >
                    {formatTick(tick)}
                  </text>
                  {!singleAxis ? (
                    <text
                      x={PAD.left + plotWidth + 8}
                      y={y + 3}
                      textAnchor="start"
                      fill="var(--color-muted)"
                      fontSize={8.5}
                      opacity={0.75}
                    >
                      {formatTick((tick / leftMax) * findingMax)}
                    </text>
                  ) : null}
                </g>
              );
            })}

            <line
              x1={PAD.left}
              y1={baselineY}
              x2={PAD.left + plotWidth}
              y2={baselineY}
              stroke="var(--color-line)"
              strokeOpacity={0.9}
              strokeWidth={1.25}
            />
            <line
              x1={PAD.left}
              y1={baselineY}
              x2={PAD.left}
              y2={PAD.top}
              stroke="var(--color-line)"
              strokeOpacity={0.9}
              strokeWidth={1.25}
            />

            <text
              x={PAD.left - 8}
              y={PAD.top - 12}
              textAnchor="end"
              fontSize={8}
              fontWeight={600}
              fill={singleAxis ? "var(--color-muted)" : isPlatform ? SUBDOMAIN_COLOR : URL_COLOR}
              opacity={0.7}
            >
              {singleAxis ? "Count" : isPlatform ? "Subdomains" : showSubdomains ? "URLs / Sub" : "URLs"}
            </text>
            {!singleAxis ? (
              <text
                x={PAD.left + plotWidth + 8}
                y={PAD.top - 12}
                textAnchor="start"
                fontSize={8}
                fontWeight={600}
                fill={FINDING_COLOR}
                opacity={0.7}
              >
                Findings
              </text>
            ) : null}

            {findingArea ? (
              <path
                d={findingArea}
                fill={`url(#${ids.findFill})`}
                className="transition-opacity duration-300"
                opacity={hoveredIndex !== null ? 0.7 : 1}
              />
            ) : null}
            {subdomainArea ? (
              <path
                d={subdomainArea}
                fill={`url(#${ids.subFill})`}
                className="transition-opacity duration-300"
                opacity={hoveredIndex !== null ? 0.65 : 0.9}
              />
            ) : null}
            {urlArea ? (
              <path
                d={urlArea}
                fill={`url(#${ids.urlFill})`}
                className="transition-opacity duration-300"
                opacity={hoveredIndex !== null ? 0.7 : 1}
              />
            ) : null}

            {findingLine ? (
              <path
                d={findingLine}
                fill="none"
                stroke={FINDING_COLOR}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                opacity={0.9}
              />
            ) : null}
            {subdomainLine ? (
              <path
                d={subdomainLine}
                fill="none"
                stroke={SUBDOMAIN_COLOR}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                opacity={0.85}
              />
            ) : null}
            {urlLine ? (
              <path
                d={urlLine}
                fill="none"
                stroke={URL_COLOR}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                opacity={0.9}
              />
            ) : null}

            {showUrls ? (
              <SeriesDots
                coords={urlCoords}
                color={URL_COLOR}
                glowId={ids.glowUrl}
                seriesLabel="URLs"
                hoveredIndex={hoveredIndex}
              />
            ) : null}
            {showSubdomains ? (
              <SeriesDots
                coords={subdomainCoords}
                color={SUBDOMAIN_COLOR}
                glowId={ids.glowSub}
                seriesLabel="subdomains"
                hoveredIndex={hoveredIndex}
              />
            ) : null}
            <SeriesDots
              coords={findingCoords}
              color={FINDING_COLOR}
              glowId={ids.glowFind}
              seriesLabel="findings"
              hoveredIndex={hoveredIndex}
            />

            {points.map((point, index) => {
              const x = PAD.left + seriesX(index, points.length, plotWidth);
              const isHovered = hoveredIndex === index;
              return (
                <text
                  key={`label-${point.pointId}`}
                  x={x}
                  y={H - 8}
                  textAnchor="middle"
                  fill={
                    isHovered || point.isCurrent ? "var(--color-cream)" : "var(--color-muted)"
                  }
                  fontSize={9}
                  fontWeight={isHovered || point.isCurrent ? 600 : 400}
                  className="transition-all duration-200"
                >
                  {point.label}
                </text>
              );
            })}

            {tooltipData ? <ChartTooltip data={tooltipData} /> : null}
          </svg>
        </div>
      )}
    </div>
  );
}
