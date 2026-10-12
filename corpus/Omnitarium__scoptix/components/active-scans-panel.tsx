"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { canViewPartialObservedResults } from "@/lib/scan-observed";
import { formatScanDateTime } from "@/lib/scan-format";

const DEFAULT_VISIBLE_SCANS = 3;

const STATUS_STYLE: Record<string, string> = {
  RUNNING: "bg-accent/25 text-cream",
  QUEUED: "bg-muted/15 text-muted",
};

type ActiveScanItem = {
  id: string;
  status: string;
  phase: string | null;
  progressCurrent: number | null;
  progressTotal: number | null;
  observedUrlCount?: number | null;
  observedFindingCount?: number | null;
  createdAt: string;
  targetDomain: {
    domainNormalized: string;
  };
};

function formatProgress(scan: ActiveScanItem) {
  const current = scan.progressCurrent ?? 0;
  const total = scan.progressTotal ?? 0;

  if (scan.status === "QUEUED" && current === 0 && total === 0) {
    return "Waiting to start";
  }

  return `${current.toLocaleString()}/${total.toLocaleString()}`;
}

export function ActiveScansPanel({ scans }: { scans: ActiveScanItem[] }) {
  const [expanded, setExpanded] = useState(false);

  const runningCount = useMemo(
    () => scans.filter((scan) => scan.status === "RUNNING").length,
    [scans],
  );
  const queuedCount = useMemo(
    () => scans.filter((scan) => scan.status === "QUEUED").length,
    [scans],
  );

  const hiddenCount = Math.max(scans.length - DEFAULT_VISIBLE_SCANS, 0);
  const visibleScans = expanded ? scans : scans.slice(0, DEFAULT_VISIBLE_SCANS);

  return (
    <section className="glass-panel overflow-hidden rounded-2xl">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line bg-[var(--table-header-bg)] px-5 py-4">
        <div>
          <div className="text-[13px] font-semibold text-cream">
            Active Scans ({scans.length})
          </div>
          <div className="mt-1 text-[12px] text-muted">
            {runningCount} running
            {queuedCount > 0 ? ` · ${queuedCount} queued` : ""}
          </div>
        </div>

        {hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="rounded-lg border border-line px-3 py-2 text-[12px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            {expanded ? "Show less" : `Show ${hiddenCount} more`}
          </button>
        )}
      </div>

      <div className="divide-y divide-line">
        {visibleScans.map((scan) => {
          const statusCls = STATUS_STYLE[scan.status] ?? "bg-muted/10 text-muted";
          const observedHref = canViewPartialObservedResults(scan)
            ? `/scans/${scan.id}/observed`
            : `/scans/${scan.id}`;

          return (
            <div
              key={scan.id}
              className="px-5 py-4 transition-colors hover:bg-white/[0.03]"
            >
              <Link href={observedHref} className="block">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-mono text-[12px] text-cream">
                    {scan.targetDomain.domainNormalized}
                  </div>
                  <div className="mt-1 text-[10px] text-muted">
                    Created {formatScanDateTime(scan.createdAt)}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span
                    className={`inline-block rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase ${statusCls}`}
                  >
                    {scan.status}
                  </span>
                  <span className="hidden text-[12px] font-medium text-accent sm:inline">
                    {canViewPartialObservedResults(scan) ? "View results" : "Open"}
                  </span>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-md border border-line bg-black/10 px-2.5 py-1 font-mono text-muted">
                  {scan.phase ?? "Waiting"}
                </span>
                <span className="rounded-md border border-line bg-black/10 px-2.5 py-1 font-mono text-muted">
                  {formatProgress(scan)}
                </span>
              </div>
              </Link>
              {scan.status === "RUNNING" && canViewPartialObservedResults(scan) && (
                <Link
                  href={`/scans/${scan.id}`}
                  className="mt-2 inline-block text-[11px] text-muted underline-offset-2 hover:text-cream hover:underline"
                >
                  Job progress
                </Link>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
