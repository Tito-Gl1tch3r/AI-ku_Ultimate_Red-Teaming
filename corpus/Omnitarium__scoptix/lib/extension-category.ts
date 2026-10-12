import type { PrismaClient } from "@prisma/client";

export type SuffixRule = {
  suffix: string;
  extensionCategoryId: number;
};

export type SidebarExtensionCategory = {
  id: number;
  slug: string;
  displayName: string;
  iconKey: string | null;
};

export async function loadSidebarExtensionCategories(
  prisma: PrismaClient,
): Promise<SidebarExtensionCategory[]> {
  try {
    return await prisma.extensionCategory.findMany({
      select: { id: true, slug: true, displayName: true, iconKey: true },
      orderBy: [{ displayName: "asc" }, { slug: "asc" }],
    });
  } catch {
    // Graceful fallback during Next.js static build (where DB is unavailable)
    // or if the DB is temporarily unreachable.
    return [];
  }
}

export async function loadExtensionSuffixRules(
  prisma: PrismaClient,
): Promise<SuffixRule[]> {
  return prisma.extensionSuffixRule.findMany({
    select: { suffix: true, extensionCategoryId: true },
  });
}

/** Match stored pathname extension against current suffix rules (Settings). */
export function categoryIdForPathnameExtension(
  rules: SuffixRule[],
  pathnameExtension: string | null,
): number | null {
  if (!pathnameExtension) return null;
  const ext = pathnameExtension.toLowerCase();
  const hit = rules.find((r) => r.suffix === ext);
  return hit?.extensionCategoryId ?? null;
}

export function categorySlugForPathnameExtension(
  rules: SuffixRule[],
  pathnameExtension: string | null,
  categoryById: Map<number, { slug: string }>,
): string {
  const id = categoryIdForPathnameExtension(rules, pathnameExtension);
  if (id == null) return "uncategorized";
  return categoryById.get(id)?.slug.toLowerCase() ?? "uncategorized";
}

/** Pathname-based category filter (shared by scan_observed_url and discovered_url). */
export type PathnameCategoryWhere = {
  pathnameExtension?:
    | string
    | null
    | { in: string[] }
    | { notIn: string[] };
  OR?: Array<{
    pathnameExtension?: string | null | { notIn: string[] };
  }>;
};

/**
 * Prisma filter for URL tabs: category chips reflect current suffix rules,
 * not snapshot extension_category_id written at scan time.
 */
export function urlCategoryPathnameWhere(
  activeCategoryId: number | null,
  suffixRules: SuffixRule[],
): PathnameCategoryWhere {
  if (activeCategoryId === null) return {};

  const allSuffixes = [...new Set(suffixRules.map((r) => r.suffix))];

  if (activeCategoryId === -1) {
    if (allSuffixes.length === 0) {
      return { pathnameExtension: null };
    }
    return {
      OR: [
        { pathnameExtension: null },
        { pathnameExtension: { notIn: allSuffixes } },
      ],
    };
  }

  const suffixes = suffixRules
    .filter((r) => r.extensionCategoryId === activeCategoryId)
    .map((r) => r.suffix);

  if (suffixes.length === 0) {
    return { pathnameExtension: { in: [] } };
  }
  return { pathnameExtension: { in: suffixes } };
}

export type UrlCategoryCounts = {
  countByCategoryId: Map<number, number>;
  uncategorizedCount: number;
  categorizedCount: number;
};

export async function countObservedUrlsByCategory(
  prisma: PrismaClient,
  scanJobId: string,
): Promise<UrlCategoryCounts> {
  const rows = await prisma.$queryRaw<
    { extension_category_id: number | null; count: bigint }[]
  >`
    SELECT esr.extension_category_id, COUNT(*)::bigint AS count
    FROM scan_observed_url sou
    LEFT JOIN extension_suffix_rule esr ON esr.suffix = sou.pathname_extension
    WHERE sou.scan_job_id = ${scanJobId}
    GROUP BY esr.extension_category_id
  `;

  return rowsToCategoryCounts(rows);
}

export async function countDiscoveredUrlsByCategory(
  prisma: PrismaClient,
  targetDomainId: string,
): Promise<UrlCategoryCounts> {
  const rows = await prisma.$queryRaw<
    { extension_category_id: number | null; count: bigint }[]
  >`
    SELECT esr.extension_category_id, COUNT(*)::bigint AS count
    FROM discovered_url du
    LEFT JOIN extension_suffix_rule esr ON esr.suffix = du.pathname_extension
    WHERE du.target_domain_id = ${targetDomainId}
    GROUP BY esr.extension_category_id
  `;

  return rowsToCategoryCounts(rows);
}

function rowsToCategoryCounts(
  rows: { extension_category_id: number | null; count: bigint }[],
): UrlCategoryCounts {
  const countByCategoryId = new Map<number, number>();
  let uncategorizedCount = 0;
  let categorizedCount = 0;

  for (const row of rows) {
    const n = Number(row.count);
    if (row.extension_category_id == null) {
      uncategorizedCount += n;
    } else {
      countByCategoryId.set(row.extension_category_id, n);
      categorizedCount += n;
    }
  }

  return { countByCategoryId, uncategorizedCount, categorizedCount };
}
