import Link from "next/link";
import { ScanJobStatus } from "@prisma/client";
import { PageHeader } from "@/components/page-header";
import { prisma } from "@/lib/prisma";
import { TopBar } from "@/components/top-bar";
import { formatScanDateTime } from "@/lib/scan-format";

export const dynamic = "force-dynamic";

export default async function ScanComparisonPickerPage() {
  const scans = await prisma.scanJob.findMany({
    where: { status: ScanJobStatus.COMPLETED },
    orderBy: { completedAt: "desc" },
    take: 100,
    include: { targetDomain: true },
  });

  return (
    <>
      <TopBar breadcrumb="/ scans / compare" />
      <main className="min-h-0 flex-1 overflow-y-auto px-8 py-8">
        <PageHeader
          eyebrow="Scans"
          title="Scan comparison"
          description="Pick a completed scan, then choose a baseline scan to diff findings, subdomains, and URLs."
        />

        <div className="mt-8 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
          <div className="border-b border-gray-100 bg-gray-50 px-5 py-4">
            <div className="text-sm font-semibold text-cream">Completed scans</div>
          </div>
          <div className="divide-y divide-gray-100">
            {scans.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-muted">No completed scans yet.</div>
            ) : (
              scans.map((scan) => (
                <Link
                  key={scan.id}
                  href={`/scans/${scan.id}/observed?tab=compare`}
                  className="flex flex-col gap-1 px-5 py-4 transition-colors hover:bg-gray-50 sm:flex-row sm:items-center sm:justify-between"
                >
                  <span className="font-medium text-cream">{scan.targetDomain.domainNormalized}</span>
                  <span className="text-sm text-muted">
                    Finished {formatScanDateTime(scan.completedAt)} · {scan.id.slice(0, 8)}
                  </span>
                </Link>
              ))
            )}
          </div>
        </div>
      </main>
    </>
  );
}
