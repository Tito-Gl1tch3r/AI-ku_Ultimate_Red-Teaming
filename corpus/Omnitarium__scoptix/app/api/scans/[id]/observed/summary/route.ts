import { NextResponse } from "next/server";
import {
  getObservedAvailability,
  getObservedScanSummary,
} from "@/lib/scan-observed";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const scan = await getObservedScanSummary(id);

  if (!scan) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const availability = getObservedAvailability(scan);
  const observedFindingCount =
    scan.observedFindingCount ??
    (await prisma.analysisFinding.count({ where: { scanJobId: id } }));

  return NextResponse.json({
    scan: {
      id: scan.id,
      status: scan.status,
      phase: scan.phase,
      targetDomainId: scan.targetDomainId,
      targetDomain: scan.targetDomain,
      createdAt: scan.createdAt,
      startedAt: scan.startedAt,
      completedAt: scan.completedAt,
      observedVersion: scan.observedVersion,
      observedFindingCount,
      observedSubdomainCount:
        availability.subdomains === "ready"
          ? scan.observedSubdomainCount ?? 0
          : null,
      observedUrlCount:
        availability.urls === "ready" ? scan.observedUrlCount ?? 0 : null,
    },
    availability,
  });
}
