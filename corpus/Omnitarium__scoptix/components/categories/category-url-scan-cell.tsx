"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { formatScanDateTime, shortScanId } from "@/lib/scan-format";

export type CategoryUrlScanObservation = {
  scanJobId: string;
  scanCreatedAt: string;
};

export function CategoryUrlScanCell({
  latestScanJobId,
  scanCount,
  observations,
}: {
  latestScanJobId: string;
  scanCount: number;
  observations: CategoryUrlScanObservation[];
}) {
  const extraCount = Math.max(0, scanCount - 1);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative flex min-w-0 items-center gap-1">
      <Link
        href={`/scans/${latestScanJobId}`}
        className="min-w-0 truncate font-mono hover:text-cream hover:underline"
        title={shortScanId(latestScanJobId)}
      >
        {shortScanId(latestScanJobId)}
      </Link>
      {extraCount > 0 ? (
        <button
          type="button"
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 rounded border border-line bg-lift px-1 py-px font-mono text-[9px] tabular-nums text-muted transition-colors hover:border-accent/40 hover:text-cream"
          title={`Observed in ${scanCount} scans`}
        >
          +{extraCount}
        </button>
      ) : null}

      {open && extraCount > 0 ? (
        <div
          id={panelId}
          role="dialog"
          aria-label={`Observed in ${scanCount} scans`}
          className="absolute left-0 top-full z-50 mt-1 min-w-[14rem] overflow-hidden rounded-lg border border-line bg-panel py-2 shadow-lift ring-1 ring-line/60"
        >
          <div className="border-b border-line px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted">
            Observed in {scanCount} scans
          </div>
          <ul className="max-h-48 overflow-y-auto py-1">
            {observations.map((obs, index) => (
              <li key={`${obs.scanJobId}-${obs.scanCreatedAt}`}>
                <Link
                  href={`/scans/${obs.scanJobId}`}
                  onClick={() => setOpen(false)}
                  className={[
                    "flex items-center justify-between gap-3 px-3 py-1.5 font-mono text-[10px] transition-colors hover:bg-[var(--nav-hover-bg)]",
                    index === 0 ? "text-cream" : "text-muted hover:text-cream",
                  ].join(" ")}
                >
                  <span>{shortScanId(obs.scanJobId)}</span>
                  <span className="shrink-0 tabular-nums">
                    {formatScanDateTime(obs.scanCreatedAt)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
