"use client";

import { useState } from "react";
import type { SummarySourceSlice } from "@/lib/scan-summary";
import {
  DonutCircleClip,
  DonutTexturedSegment,
  DonutWaterPattern,
  donutClipPathId,
  donutTexturePatternId,
} from "@/components/scans/donut-chart-texture";

const SIZE = 160;
const CX = 80;
const CY = 80;
const OUTER_R = 80;

/** Inner radius: larger value = thinner ring (tangkai). */
const RING_INNER = {
  default: 48,
  thin: 54,
} as const;

const TEXTURE_PATTERN_ID = donutTexturePatternId("scx-donut");
const CLIP_PATH_ID = donutClipPathId("scx-donut");

const GRADIENT_135 = {
  gradientUnits: "userSpaceOnUse" as const,
  x1: 0,
  y1: 0,
  x2: SIZE,
  y2: SIZE,
};

function segmentFill(label: string, fallbackColor: string, sourceGradients: boolean) {
  if (!sourceGradients) return fallbackColor;
  if (label === "Wayback Machine" || label === "Wayback") return "url(#scx-donut-green)";
  if (label === "VirusTotal") return "url(#scx-donut-purple)";
  return fallbackColor;
}

function polar(r: number, degFromTop: number) {
  const rad = ((degFromTop - 90) * Math.PI) / 180;
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
}

function donutSegmentPath(startDeg: number, endDeg: number, innerR: number) {
  const sweep = endDeg - startDeg;
  const large = sweep > 180 ? 1 : 0;
  const o1 = polar(OUTER_R, startDeg);
  const o2 = polar(OUTER_R, endDeg);
  const i2 = polar(innerR, endDeg);
  const i1 = polar(innerR, startDeg);
  return [
    `M ${o1.x.toFixed(2)} ${o1.y.toFixed(2)}`,
    `A ${OUTER_R} ${OUTER_R} 0 ${large} 1 ${o2.x.toFixed(2)} ${o2.y.toFixed(2)}`,
    `L ${i2.x.toFixed(2)} ${i2.y.toFixed(2)}`,
    `A ${innerR} ${innerR} 0 ${large} 0 ${i1.x.toFixed(2)} ${i1.y.toFixed(2)}`,
    "Z",
  ].join(" ");
}

function centerInsetPercent(innerR: number) {
  return `${((OUTER_R - innerR) / SIZE) * 100}%`;
}

const CHART_SIZE = {
  md: { box: "size-40", total: "text-lg" },
  sm: { box: "size-36", total: "text-base" },
} as const;

function DonutSliceTooltip({ slice }: { slice: SummarySourceSlice }) {
  return (
    <div
      className="pointer-events-none absolute left-1/2 top-0 z-20 -translate-x-1/2 -translate-y-[calc(100%+6px)] rounded-lg border border-line/80 px-2.5 py-1.5 text-[10px] shadow-lg backdrop-blur-md"
      style={{
        background: "var(--glass-panel-bg)",
        boxShadow: "var(--shadow-glass)",
      }}
      role="tooltip"
    >
      <div className="flex items-center gap-1.5 whitespace-nowrap">
        <span
          className="size-2 shrink-0 rounded-full"
          style={{ backgroundColor: slice.color }}
          aria-hidden
        />
        <span className="font-semibold text-cream">{slice.label}</span>
        <span className="font-semibold tabular-nums text-cream">{slice.count.toLocaleString()}</span>
      </div>
    </div>
  );
}

export function AccentDonutChart({
  slices,
  total,
  centerLabel,
  ring = "default",
  size = "md",
  texture = false,
  sourceGradients = false,
}: {
  slices: SummarySourceSlice[];
  total: number;
  centerLabel: string;
  /** `thin` = narrower ring; outer diameter unchanged. */
  ring?: keyof typeof RING_INNER;
  size?: keyof typeof CHART_SIZE;
  /** Soft ripple overlay on ring segments. */
  texture?: boolean;
  /** VT purple + Wayback green gradients (same as sources donut). */
  sourceGradients?: boolean;
}) {
  const innerR = RING_INNER[ring];
  const dim = CHART_SIZE[size];
  const [hovered, setHovered] = useState<SummarySourceSlice | null>(null);

  let cursor = 0;
  const segments = slices.map((slice) => {
    const start = cursor;
    cursor += slice.percent;
    const startDeg = (start / 100) * 360;
    let endDeg = (cursor / 100) * 360;
    if (endDeg - startDeg >= 359.99) endDeg = startDeg + 359.99;
    return {
      slice,
      path: donutSegmentPath(startDeg, endDeg, innerR),
      fill: segmentFill(slice.label, slice.color, sourceGradients),
    };
  });

  return (
    <div
      className={[
        "relative shrink-0 rounded-full shadow-[0_2px_8px_color-mix(in_srgb,var(--color-accent)_22%,transparent)]",
        dim.box,
      ].join(" ")}
      role="img"
      aria-label={`${centerLabel}: ${slices.map((s) => `${s.label} ${s.count.toLocaleString()}`).join(", ")}`}
      onMouseLeave={() => setHovered(null)}
    >
      {hovered ? <DonutSliceTooltip slice={hovered} /> : null}
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="size-full" aria-hidden>
        <defs>
          {sourceGradients ? (
            <>
              <linearGradient id="scx-donut-green" {...GRADIENT_135}>
                <stop offset="0%" stopColor="#15803d" />
                <stop offset="100%" stopColor="#22c55e" />
              </linearGradient>
              <linearGradient id="scx-donut-purple" {...GRADIENT_135}>
                <stop offset="0%" stopColor="#7c3aed" />
                <stop offset="100%" stopColor="#9333ea" />
              </linearGradient>
            </>
          ) : null}
          <DonutCircleClip id={CLIP_PATH_ID} />
          {texture ? <DonutWaterPattern id={TEXTURE_PATTERN_ID} /> : null}
        </defs>
        <g clipPath={`url(#${CLIP_PATH_ID})`}>
          {segments.map((seg) => (
            <g key={seg.slice.label}>
              {texture ? (
                <DonutTexturedSegment
                  path={seg.path}
                  fill={seg.fill}
                  patternId={TEXTURE_PATTERN_ID}
                />
              ) : (
                <path d={seg.path} fill={seg.fill} />
              )}
              <path
                d={seg.path}
                fill="transparent"
                className="cursor-pointer"
                onMouseEnter={() => setHovered(seg.slice)}
                aria-hidden
              />
            </g>
          ))}
        </g>
      </svg>
      <div
        className="scx-donut-center pointer-events-none absolute flex flex-col items-center justify-center rounded-full bg-lift"
        style={{ inset: centerInsetPercent(innerR) }}
      >
        <span className={[dim.total, "font-bold leading-none text-cream tabular-nums"].join(" ")}>
          {total.toLocaleString()}
        </span>
        <span className="mt-0.5 text-[10px] font-medium text-muted">{centerLabel}</span>
      </div>
    </div>
  );
}
