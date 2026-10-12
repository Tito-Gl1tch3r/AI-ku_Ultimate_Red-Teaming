"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api-url";
import {
  canViewPartialObservedResults,
  partialObservedPhaseLabel,
} from "@/lib/scan-observed";
import { formatScanDateTime } from "@/lib/scan-format";

type ScanData = {
  id: string;
  status: string;
  phase: string | null;
  progressCurrent: number | null;
  progressTotal: number | null;
  errorMessage: string | null;
  observedUrlCount?: number | null;
  observedFindingCount?: number | null;
  targetDomainId: string;
  targetDomain?: { domainNormalized: string };
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
};

export function ScanDetailClient({ id }: { id: string }) {
  const [scan, setScan] = useState<ScanData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const r = await fetch(apiUrl(`/api/scans/${id}`), { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        if (active) setScan(j.scan);
      } catch (e) {
        if (active) setErr(e instanceof Error ? e.message : "Failed");
      }
    }
    void poll();
    const iv = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(iv);
    };
  }, [id]);

  async function handleCancel() {
    if (!confirm("Are you sure you want to stop this scan?")) return;
    setCancelling(true);
    try {
      const r = await fetch(apiUrl(`/api/scans/${id}/cancel`), { method: "POST" });
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        throw new Error(j?.error ?? `HTTP ${r.status}`);
      }
      const j = await r.json();
      setScan(j.scan);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setCancelling(false);
    }
  }

  if (err) {
    return (
      <div className="rounded-xl border border-warn/30 bg-warn/5 px-4 py-4 text-[13px] text-warn">
        Error: {err}
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="flex items-center gap-3 py-8">
        <div className="live-dot size-2 rounded-full bg-accent" />
        <span className="text-[13px] text-muted">Loading scan data…</span>
      </div>
    );
  }

  const isRunning = scan.status === "RUNNING" || scan.status === "QUEUED";
  const isCompleted = scan.status === "COMPLETED";
  const isFailed = scan.status === "FAILED";
  const isCancelled = scan.status === "CANCELLED";
  const pct =
    scan.progressTotal && scan.progressTotal > 0
      ? Math.round(((scan.progressCurrent ?? 0) / scan.progressTotal) * 100)
      : 0;

  const phaseLabels: Record<string, string> = {
    T1_APEX: "Phase 1 — VirusTotal (root domain)",
    T2_SUBDOMAINS: "Phase 2 — VirusTotal (subdomains)",
    T3_WAYBACK_APEX: "Phase 3 — Wayback Machine (root)",
    T4_WAYBACK_SUBDOMAINS: "Phase 4 — Wayback Machine (subdomains)",
    T5_CONSOLIDATE: "Phase 5 — Consolidating",
    T5B_WAPPALYZER: "Phase 5B — Wappalyzer",
    T5C_CVE_MATCH: "Phase 5C — CVE Matching",
    T6_ANALYSIS: "Phase 6 — Analyzing URLs",
  };

  const canViewObserved = canViewPartialObservedResults(scan);
  const partialPhaseHint = partialObservedPhaseLabel(scan.phase);

  return (
    <div className="space-y-6">
      {/* ── Status Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {isRunning ? (
            <div className="live-dot size-3 rounded-full bg-accent" />
          ) : isCompleted ? (
            <div className="size-3 rounded-full bg-accent" />
          ) : isCancelled ? (
            <div className="size-3 rounded-full bg-muted" />
          ) : (
            <div className="size-3 rounded-full bg-warn" />
          )}
          <div>
            <div className="text-[16px] font-semibold text-cream">
              {scan.targetDomain?.domainNormalized ?? "—"}
            </div>
            <div className="mt-0.5 text-[12px] text-muted">
              {scan.status}
              {scan.phase ? ` · ${phaseLabels[scan.phase] ?? scan.phase}` : ""}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isRunning && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="rounded-xl border border-warn/40 bg-warn/10 px-5 py-3 text-[13px] font-semibold text-warn transition-colors hover:bg-warn/20 disabled:opacity-60"
            >
              {cancelling ? "Stopping…" : "Stop Scan"}
            </button>
          )}

          {canViewObserved && (
            <Link
              href={`/scans/${scan.id}/observed`}
              className="shadow-clay inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-accent to-accent-dim px-5 py-3 text-[13px] font-semibold text-void transition-transform hover:scale-[1.02]"
            >
              {isCompleted ? "View Snapshot" : "View results so far"}
            </Link>
          )}

          {isCompleted && (
            <>
              <Link
                href={`/scans/${scan.id}/compare`}
                className="rounded-xl border border-line px-4 py-3 text-[13px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
              >
                Compare With Previous
              </Link>
              <Link
                href={`/targets/${scan.targetDomainId}`}
                className="rounded-xl border border-line px-4 py-3 text-[13px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
              >
                Current Target State
              </Link>
            </>
          )}
        </div>
      </div>

      {/* ── Progress Bar ── */}
      {isRunning && (
        <div className="space-y-3">
          {canViewObserved && !isCompleted && (
            <div className="rounded-xl border border-accent/25 bg-accent/5 px-4 py-3 text-[13px] text-cream">
              {partialPhaseHint ?? "Early results are available."}{" "}
              <Link href={`/scans/${scan.id}/observed`} className="font-semibold text-accent underline-offset-2 hover:underline">
                Open observed snapshot
              </Link>{" "}
              to review early results while the scan continues.
            </div>
          )}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-muted">
              <span>{(scan.progressCurrent ?? 0).toLocaleString()} / {(scan.progressTotal ?? 0).toLocaleString()}</span>
              <span className="font-mono">{pct}%</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-line/30">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent-dim to-accent transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Completed Summary ── */}
      {isCompleted && (
        <div className="rounded-xl border border-accent/20 bg-accent/5 px-5 py-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
            Scan Complete
          </div>
          <div className="mt-2 text-[13px] text-cream">
            Processed {(scan.progressTotal ?? 0).toLocaleString()} items. Open the
            scan snapshot for point-in-time results, compare it with another run,
            or jump to the target&apos;s current aggregate state.
          </div>
          {scan.completedAt && (
            <div className="mt-2 text-[11px] text-muted">
              Finished at {formatScanDateTime(scan.completedAt)}
            </div>
          )}
        </div>
      )}

      {/* ── Failed Message ── */}
      {isFailed && (
        <div className="rounded-xl border border-warn/30 bg-warn/5 px-5 py-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-warn">
            Scan Failed
          </div>
          <div className="mt-2 font-mono text-[12px] text-cream">
            {scan.errorMessage ?? "Unknown error"}
          </div>
          <Link
            href="/scans"
            className="mt-4 inline-block rounded-xl border border-line px-4 py-2.5 text-[12px] text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            ← Back to Scans
          </Link>
        </div>
      )}

      {/* ── Cancelled Message ── */}
      {isCancelled && (
        <div className="rounded-xl border border-muted/30 bg-muted/5 px-5 py-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Scan Cancelled
          </div>
          <div className="mt-2 text-[13px] text-cream">
            This scan was stopped by the user.
            {(scan.progressCurrent ?? 0) > 0 && (
              <> Processed {(scan.progressCurrent ?? 0).toLocaleString()} of {(scan.progressTotal ?? 0).toLocaleString()} items before stopping.</>
            )}
          </div>
          <Link
            href="/scans"
            className="mt-4 inline-block rounded-xl border border-line px-4 py-2.5 text-[12px] text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            ← Back to Scans
          </Link>
        </div>
      )}

      {/* ── Metadata ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Scan ID", id.slice(0, 8) + "…"],
          ["Created", formatScanDateTime(scan.createdAt)],
          ["Started", formatScanDateTime(scan.startedAt)],
          ["Finished", formatScanDateTime(scan.completedAt)],
        ].map(([label, val]) => (
          <div key={label} className="rounded-xl border border-line bg-black/10 px-3 py-2.5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">
              {label}
            </div>
            <div className="mt-1 font-mono text-[11px] text-cream">{val}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
