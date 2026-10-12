import { NextResponse } from "next/server";
import { FindingSource } from "@prisma/client";
import {
  getObservedAvailability,
  getObservedScanSummary,
  normalizeSkip,
  normalizeTake,
} from "@/lib/scan-observed";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const scan = await getObservedScanSummary(id);

  if (!scan) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const { searchParams } = new URL(req.url);
  const take = normalizeTake(searchParams.get("take"));
  const skip = normalizeSkip(searchParams.get("skip"));
  const findingType = searchParams.get("findingType")?.trim() || undefined;
  const sourceRaw = searchParams.get("source")?.trim() || undefined;
  const source =
    sourceRaw === "URL_STRING"
      ? FindingSource.URL_STRING
      : sourceRaw === "RESPONSE_BODY"
        ? FindingSource.RESPONSE_BODY
        : undefined;

  const where = {
    scanJobId: id,
    ...(findingType ? { findingType } : {}),
    ...(source ? { source } : {}),
  } as const;

  const [findings, total] = await Promise.all([
    prisma.analysisFinding.findMany({
      where,
      take,
      skip,
      orderBy: { createdAt: "desc" },
      include: {
        discoveredUrl: {
          select: {
            id: true,
            urlText: true,
            externalSeenAt: true,
            engines: true,
          },
        },
      },
    }),
    prisma.analysisFinding.count({ where }),
  ]);

  return NextResponse.json({
    scan: {
      id: scan.id,
      status: scan.status,
      targetDomainId: scan.targetDomainId,
      targetDomain: scan.targetDomain,
      observedVersion: scan.observedVersion,
    },
    availability: getObservedAvailability(scan),
    pagination: {
      take,
      skip,
      total,
    },
    findings,
  });
}
