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
const INNER_R = 48;

const TEXTURE_PATTERN_ID = donutTexturePatternId("sources-donut");
const CLIP_PATH_ID = donutClipPathId("sources-donut");

/** Satu arah 135° untuk seluruh chart — hindari gradient “mengikuti” bentuk tiap irisan (efek air). */
const GRADIENT_135 = {
  gradientUnits: "userSpaceOnUse" as const,
  x1: 0,
  y1: 0,
  x2: SIZE,
  y2: SIZE,
};

function segmentFillId(label: string, fallbackColor: string) {
  if (label === "Wayback Machine") return "url(#sources-donut-green)";
  if (label === "VirusTotal") return "url(#sources-donut-purple)";
  return fallbackColor;
}

function polar(r: number, degFromTop: number) {
  const rad = ((degFromTop - 90) * Math.PI) / 180;
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
}

function donutSegmentPath(startDeg: number, endDeg: number) {
  const sweep = endDeg - startDeg;
  const large = sweep > 180 ? 1 : 0;
  const o1 = polar(OUTER_R, startDeg);
  const o2 = polar(OUTER_R, endDeg);
  const i2 = polar(INNER_R, endDeg);
  const i1 = polar(INNER_R, startDeg);
  return [
    `M ${o1.x.toFixed(2)} ${o1.y.toFixed(2)}`,
    `A ${OUTER_R} ${OUTER_R} 0 ${large} 1 ${o2.x.toFixed(2)} ${o2.y.toFixed(2)}`,
    `L ${i2.x.toFixed(2)} ${i2.y.toFixed(2)}`,
    `A ${INNER_R} ${INNER_R} 0 ${large} 0 ${i1.x.toFixed(2)} ${i1.y.toFixed(2)}`,
    "Z",
  ].join(" ");
}

export function SourcesDonutChart({
  sources,
  total,
}: {
  sources: SummarySourceSlice[];
  total: number;
}) {
  let cursor = 0;
  const segments = sources.map((slice) => {
    const start = cursor;
    cursor += slice.percent;
    const startDeg = (start / 100) * 360;
    let endDeg = (cursor / 100) * 360;
    if (endDeg - startDeg >= 359.99) endDeg = startDeg + 359.99;
    return {
      key: slice.label,
      path: donutSegmentPath(startDeg, endDeg),
      fill: segmentFillId(slice.label, slice.color),
    };
  });

  return (
    <div
      className="relative size-40 shrink-0 rounded-full shadow-[0_2px_8px_rgba(34,197,94,0.2)]"
      role="img"
      aria-label={`URL sources: ${sources.map((s) => `${s.label} ${s.percent}%`).join(", ")}`}
    >
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="size-full" aria-hidden>
        <defs>
          <linearGradient id="sources-donut-green" {...GRADIENT_135}>
            <stop offset="0%" stopColor="#15803d" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
          <linearGradient id="sources-donut-purple" {...GRADIENT_135}>
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#9333ea" />
          </linearGradient>
          <DonutCircleClip id={CLIP_PATH_ID} />
          <DonutWaterPattern id={TEXTURE_PATTERN_ID} />
        </defs>
        <g clipPath={`url(#${CLIP_PATH_ID})`}>
          {segments.map((seg) => (
            <g key={seg.key}>
              <DonutTexturedSegment
                path={seg.path}
                fill={seg.fill}
                patternId={TEXTURE_PATTERN_ID}
              />
            </g>
          ))}
        </g>
      </svg>
      <div className="scx-donut-center absolute inset-8 flex flex-col items-center justify-center rounded-full bg-lift">
        <span className="text-lg font-bold leading-none text-cream">
          {total.toLocaleString()}
        </span>
        <span className="mt-0.5 text-[10px] font-medium text-muted">URLs</span>
      </div>
    </div>
  );
}
