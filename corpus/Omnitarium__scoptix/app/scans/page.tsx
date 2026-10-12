import { ScanJobStatus } from "@prisma/client";
import { ActiveScansPanel } from "@/components/active-scans-panel";
import { NewScanDialog } from "@/components/new-scan-dialog";
import { ScanHistoryPanel } from "@/components/scans/scan-history-panel";
import { ScansListHeader } from "@/components/scans/scans-list-header";
import { prisma } from "@/lib/prisma";
import { TablePagination, normalizePageSize } from "@/components/table-pagination";
import { countScanObservedFromDb } from "@/lib/scan-observed-counts";
import { formatScanDateTime } from "@/lib/scan-format";

export const dynamic = "force-dynamic";

const STATUS_STYLE: Record<string, string> = {
  COMPLETED: "bg-accent/15 text-accent",
  RUNNING: "bg-accent/25 text-cream",
  QUEUED: "bg-muted/15 text-muted",
  FAILED: "bg-warn/15 text-warn",
  CANCELLED: "bg-muted/10 text-muted",
  PAUSED: "bg-warn/10 text-warn",
};

/** URLs recorded in this scan's snapshot (scan_observed_url), not target-global totals. */
function formatSnapshotUrlProgress(urlCount: number) {
  if (urlCount <= 0) return "0/0";
  return `${urlCount.toLocaleString()}/${urlCount.toLocaleString()}`;
}

function asPosInt(v: string | null | undefined, fallback: number) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.floor(n));
}

function sp(v: string | string[] | undefined): string {
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v[0] ?? "";
  return "";
}

export default async function ScansPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const rawSp = (await searchParams) ?? {};
  const page = asPosInt(sp(rawSp.page) || null, 1);
  const perPage = normalizePageSize(sp(rawSp.perPage) || null, 15);
  const q = sp(rawSp.q);

  const searchFilter = q ? { targetDomain: { domainNormalized: { contains: q } } } : {};

  const activeScans = await prisma.scanJob.findMany({
    where: {
      status: { in: [ScanJobStatus.RUNNING, ScanJobStatus.QUEUED] },
      ...searchFilter,
    },
    orderBy: { createdAt: "desc" },
    include: { targetDomain: true },
  });

  const totalHistoryScans = await prisma.scanJob.count({
    where: {
      status: { notIn: [ScanJobStatus.RUNNING, ScanJobStatus.QUEUED] },
      ...searchFilter,
    },
  });

  const totalPages = Math.max(1, Math.ceil(totalHistoryScans / perPage));
  const safePage = Math.min(page, totalPages);

  const historyScans = await prisma.scanJob.findMany({
    where: {
      status: { notIn: [ScanJobStatus.RUNNING, ScanJobStatus.QUEUED] },
      ...searchFilter,
    },
    orderBy: { createdAt: "desc" },
    skip: (safePage - 1) * perPage,
    take: perPage,
    include: { targetDomain: true },
  });

  const snapshotByScanId = new Map(
    (
      await Promise.all(
        historyScans.map(async (scan) => {
          const snapshot = await countScanObservedFromDb(prisma, scan.id);
          return { id: scan.id, snapshot };
        }),
      )
    ).map((row) => [row.id, row.snapshot]),
  );

  const historyRows = historyScans.map((scan) => {
    const isCompleted = scan.status === ScanJobStatus.COMPLETED;
    const snapshot = snapshotByScanId.get(scan.id)!;

    return {
      id: scan.id,
      targetDomain: scan.targetDomain.domainNormalized,
      status: scan.status,
      statusClassName: STATUS_STYLE[scan.status] ?? "bg-muted/10 text-muted",
      phase: scan.phase ?? "—",
      progressLabel: formatSnapshotUrlProgress(snapshot.urls),
      findingsCount: snapshot.findings.toLocaleString(),
      finishedLabel: formatScanDateTime(scan.completedAt),
      createdLabel: formatScanDateTime(scan.createdAt),
      href: isCompleted ? `/scans/${scan.id}/observed` : `/scans/${scan.id}`,
    };
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ScansListHeader activeCount={activeScans.length} historyCount={totalHistoryScans} initialQuery={q} />

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <div className="space-y-6">
          {activeScans.length > 0 && (
            <ActiveScansPanel
              scans={activeScans.map((scan) => ({
                id: scan.id,
                status: scan.status,
                phase: scan.phase,
                progressCurrent: scan.progressCurrent,
                progressTotal: scan.progressTotal,
                observedUrlCount: scan.observedUrlCount,
                observedFindingCount: scan.observedFindingCount,
                createdAt: scan.createdAt.toISOString(),
                targetDomain: {
                  domainNormalized: scan.targetDomain.domainNormalized,
                },
              }))}
            />
          )}

          <div className="glass-panel overflow-hidden rounded-2xl">
            <div className="border-b border-line bg-[var(--table-header-bg)] px-5 py-4">
              <div className="text-[13px] font-semibold text-cream">Scan history</div>
              <div className="mt-1 text-[12px] text-muted">
                Review completed, failed, cancelled, and paused scans.
              </div>
            </div>

            {historyRows.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <div className="text-[13px] text-muted">
                  {activeScans.length > 0 ? "No previous scans yet." : "No scans yet."}
                </div>
                <div className="mt-2 text-[12px] text-muted">
                  Start a new scan to begin collecting URLs and findings.
                </div>
                <div className="mt-5 flex justify-center">
                  <NewScanDialog
                    buttonClassName="shadow-clay inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-accent to-accent-dim px-4 py-3 text-[13px] font-semibold text-void transition-transform hover:scale-[1.02]"
                  />
                </div>
              </div>
            ) : (
              <>
                <ScanHistoryPanel scans={historyRows} />
                <TablePagination
                  currentPage={safePage}
                  totalPages={totalPages}
                  totalItems={totalHistoryScans}
                  perPage={perPage}
                  basePath="/scans"
                  fixedParams={q ? { q } : {}}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
