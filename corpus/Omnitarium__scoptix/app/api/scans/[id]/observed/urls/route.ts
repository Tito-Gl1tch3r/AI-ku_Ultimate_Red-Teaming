import { NextResponse } from "next/server";
import {
  getObservedAvailability,
  getObservedScanSummary,
  normalizeSkip,
  normalizeTake,
} from "@/lib/scan-observed";
import { prisma } from "@/lib/prisma";
import {
  categorySlugForPathnameExtension,
  loadExtensionSuffixRules,
  urlCategoryPathnameWhere,
} from "@/lib/extension-category";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const scan = await getObservedScanSummary(id);

  if (!scan) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const availability = getObservedAvailability(scan);
  if (availability.urls !== "ready") {
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
      urls: [],
    });
  }

  const { searchParams } = new URL(req.url);
  const take = normalizeTake(searchParams.get("take"));
  const skip = normalizeSkip(searchParams.get("skip"));
  const q = searchParams.get("q")?.trim() || undefined;
  const categoryIdRaw = searchParams.get("extensionCategoryId");
  const categoryId =
    categoryIdRaw != null && categoryIdRaw !== ""
      ? Number(categoryIdRaw)
      : undefined;
  const uncategorizedOnly = searchParams.get("uncategorized") === "1";

  const [suffixRules, categories] = await Promise.all([
    loadExtensionSuffixRules(prisma),
    prisma.extensionCategory.findMany({
      select: { id: true, slug: true, displayName: true },
    }),
  ]);
  const categoryById = new Map(categories.map((c) => [c.id, c]));

  const activeCategoryId = uncategorizedOnly
    ? -1
    : Number.isInteger(categoryId)
      ? categoryId!
      : null;

  const where = {
    scanJobId: id,
    ...(q
      ? {
          urlText: {
            contains: q,
            mode: "insensitive" as const,
          },
        }
      : {}),
    ...urlCategoryPathnameWhere(activeCategoryId, suffixRules),
  };

  const [urlRows, total] = await Promise.all([
    prisma.scanObservedUrl.findMany({
      where,
      take,
      skip,
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        urlText: true,
        hostnameNormalized: true,
        pathnameExtension: true,
        createdAt: true,
      },
    }),
    prisma.scanObservedUrl.count({ where }),
  ]);

  const urls = urlRows.map((row) => {
    const slug = categorySlugForPathnameExtension(
      suffixRules,
      row.pathnameExtension,
      categoryById,
    );
    const category = categories.find((c) => c.slug.toLowerCase() === slug) ?? null;
    return {
      ...row,
      extensionCategory: category
        ? {
            id: category.id,
            slug: category.slug,
            displayName: category.displayName,
          }
        : null,
    };
  });

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
    urls,
  });
}
