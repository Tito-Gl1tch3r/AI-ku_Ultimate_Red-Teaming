import { NextResponse } from "next/server";
import {
  getObservedAvailability,
  getObservedScanSummary,
  normalizeSkip,
  normalizeTake,
} from "@/lib/scan-observed";
import type { Prisma } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { subdomainHostnameSearchWhere } from "@/lib/subdomain-search-query";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const scan = await getObservedScanSummary(id);

  if (!scan) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const availability = getObservedAvailability(scan);
  if (availability.subdomains !== "ready") {
    return NextResponse.json({
      scan: {
        id: scan.id,
        status: scan.status,
        targetDomainId: scan.targetDomainId,
        targetDomain: scan.targetDomain,
        observedVersion: scan.observedVersion,
      },
      availability,
      pagination: {
        take: 0,
        skip: 0,
        total: 0,
      },
      subdomains: [],
    });
  }

  const { searchParams } = new URL(req.url);
  const take = normalizeTake(searchParams.get("take"));
  const skip = normalizeSkip(searchParams.get("skip"));
  const q = searchParams.get("q")?.trim() || undefined;

  const where: Prisma.ScanObservedSubdomainWhereInput = {
    scanJobId: id,
    ...(q ? (subdomainHostnameSearchWhere(q) ?? {}) : {}),
  };

  const [subdomains, total] = await Promise.all([
    prisma.scanObservedSubdomain.findMany({
      where,
      take,
      skip,
      orderBy: { hostnameNormalized: "asc" },
      include: {
        subdomain: {
          select: {
            id: true,
            firstSeenAt: true,
            lastSeenAt: true,
          },
        },
      },
    }),
    prisma.scanObservedSubdomain.count({ where }),
  ]);

  return NextResponse.json({
    scan: {
      id: scan.id,
      status: scan.status,
      targetDomainId: scan.targetDomainId,
      targetDomain: scan.targetDomain,
      observedVersion: scan.observedVersion,
    },
    availability,
    pagination: {
      take,
      skip,
      total,
    },
    subdomains,
  });
}
