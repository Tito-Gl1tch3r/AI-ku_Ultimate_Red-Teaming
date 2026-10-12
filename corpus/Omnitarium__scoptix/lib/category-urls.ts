import { Prisma, type PrismaClient } from "@prisma/client";
import { normalizeExcludeKeywords } from "@/lib/url-exclude-query";
import {
  isStructuredSearchQuery,
  isUrlSearchQueryActive,
  parseUrlSearchGroups,
} from "@/lib/url-search-query";

export type CategoryUrlObservation = {
  scanJobId: string;
  scanCreatedAt: Date;
};

export type DedupedCategoryUrlRow = {
  urlSha256: string;
  urlText: string;
  pathnameExtension: string | null;
  targetDomainId: string;
  targetDomain: string;
  latestScanJobId: string;
  latestScanCreatedAt: Date;
  scanCount: number;
  observations: CategoryUrlObservation[];
};

export type CategoryUrlStats = {
  totalUrls: number;
  uniqueTargets: number;
  uniqueScans: number;
  extensionBreakdown: { ext: string; count: number }[];
  topTargets: { targetDomainId: string; count: number }[];
};

export type CategoryUrlQueryFilters = {
  categorySuffixes: readonly string[];
  q: string;
  hideSubIds: readonly string[];
  hideKw: readonly string[];
};

export async function loadCategorySuffixes(
  prisma: PrismaClient,
  categoryId: number,
): Promise<string[]> {
  const rules = await prisma.extensionSuffixRule.findMany({
    where: { extensionCategoryId: categoryId },
    select: { suffix: true },
    orderBy: { suffix: "asc" },
  });
  return rules.map((r) => r.suffix);
}

function categorySuffixSql(suffixes: readonly string[]): Prisma.Sql {
  if (suffixes.length === 0) return Prisma.sql`FALSE`;
  return Prisma.sql`sou.pathname_extension IN (${Prisma.join(
    suffixes.map((s) => Prisma.sql`${s}`),
  )})`;
}

function categoryUrlSearchSql(q: string): Prisma.Sql {
  const trimmed = q.trim();
  if (!trimmed || !isUrlSearchQueryActive(trimmed)) return Prisma.sql`TRUE`;

  const groups = parseUrlSearchGroups(trimmed)
    .map((g) => g.filter((t) => t.length > 0))
    .filter((g) => g.length > 0);
  if (groups.length === 0) return Prisma.sql`TRUE`;

  if (!isStructuredSearchQuery(trimmed)) {
    const term = groups[0][0];
    return Prisma.sql`sou.url_text ILIKE ${`%${term}%`}`;
  }

  const orParts = groups.map((andTerms) => {
    const andParts = andTerms.map((term) => Prisma.sql`sou.url_text ILIKE ${`%${term}%`}`);
    return Prisma.sql`(${Prisma.join(andParts, " AND ")})`;
  });
  return Prisma.sql`(${Prisma.join(orParts, " OR ")})`;
}

function categoryUrlExcludeSql(
  subdomainIds: readonly string[],
  keywords: readonly string[],
): Prisma.Sql {
  const kws = normalizeExcludeKeywords(keywords);
  const subs = [...new Set(subdomainIds.filter(Boolean))];
  const parts: Prisma.Sql[] = [];

  if (subs.length > 0) {
    parts.push(
      Prisma.sql`(sou.subdomain_id IS NULL OR sou.subdomain_id NOT IN (${Prisma.join(subs)}))`,
    );
  }
  for (const kw of kws) {
    parts.push(Prisma.sql`sou.url_text NOT ILIKE ${`%${kw}%`}`);
  }

  if (parts.length === 0) return Prisma.sql`TRUE`;
  return Prisma.join(parts, " AND ");
}

function filteredSouWhere(filters: CategoryUrlQueryFilters): Prisma.Sql {
  return Prisma.sql`
    ${categorySuffixSql(filters.categorySuffixes)}
    AND ${categoryUrlSearchSql(filters.q)}
    AND ${categoryUrlExcludeSql(filters.hideSubIds, filters.hideKw)}
  `;
}

function filteredCte(filters: CategoryUrlQueryFilters): Prisma.Sql {
  return Prisma.sql`
    filtered AS (
      SELECT
        sou.url_sha256,
        sou.url_text,
        sou.pathname_extension,
        sou.target_domain_id,
        sou.scan_job_id,
        sj.created_at AS scan_created_at
      FROM scan_observed_url sou
      INNER JOIN scan_job sj ON sj.id = sou.scan_job_id
      WHERE ${filteredSouWhere(filters)}
    )
  `;
}

export async function countDedupedCategoryUrls(
  prisma: PrismaClient,
  filters: CategoryUrlQueryFilters,
): Promise<number> {
  if (filters.categorySuffixes.length === 0) return 0;

  const rows = await prisma.$queryRaw<[{ count: bigint }]>`
    WITH ${filteredCte(filters)}
    SELECT COUNT(*)::bigint AS count
    FROM (SELECT DISTINCT url_sha256 FROM filtered) deduped
  `;
  return Number(rows[0]?.count ?? 0);
}

export async function fetchCategoryUrlStats(
  prisma: PrismaClient,
  filters: CategoryUrlQueryFilters,
): Promise<CategoryUrlStats> {
  if (filters.categorySuffixes.length === 0) {
    return {
      totalUrls: 0,
      uniqueTargets: 0,
      uniqueScans: 0,
      extensionBreakdown: [],
      topTargets: [],
    };
  }

  const cte = filteredCte(filters);

  const [totalRow, targetRow, scanRow, extRows, domainRows] = await Promise.all([
    prisma.$queryRaw<[{ count: bigint }]>`
      WITH ${cte}
      SELECT COUNT(*)::bigint AS count
      FROM (SELECT DISTINCT url_sha256 FROM filtered) deduped
    `,
    prisma.$queryRaw<[{ count: bigint }]>`
      WITH ${cte}
      SELECT COUNT(DISTINCT target_domain_id)::bigint AS count
      FROM (SELECT DISTINCT ON (url_sha256) target_domain_id FROM filtered ORDER BY url_sha256) deduped
    `,
    prisma.$queryRaw<[{ count: bigint }]>`
      WITH ${cte}
      SELECT COUNT(DISTINCT scan_job_id)::bigint AS count FROM filtered
    `,
    prisma.$queryRaw<{ pathname_extension: string | null; count: bigint }[]>`
      WITH ${cte}
      SELECT pathname_extension, COUNT(DISTINCT url_sha256)::bigint AS count
      FROM filtered
      GROUP BY pathname_extension
      ORDER BY count DESC, pathname_extension ASC NULLS LAST
    `,
    prisma.$queryRaw<{ target_domain_id: string; count: bigint }[]>`
      WITH ${cte}
      SELECT target_domain_id, COUNT(DISTINCT url_sha256)::bigint AS count
      FROM filtered
      GROUP BY target_domain_id
      ORDER BY count DESC
      LIMIT 10
    `,
  ]);

  return {
    totalUrls: Number(totalRow[0]?.count ?? 0),
    uniqueTargets: Number(targetRow[0]?.count ?? 0),
    uniqueScans: Number(scanRow[0]?.count ?? 0),
    extensionBreakdown: extRows.map((r) => ({
      ext: r.pathname_extension || "unknown",
      count: Number(r.count),
    })),
    topTargets: domainRows.map((r) => ({
      targetDomainId: r.target_domain_id,
      count: Number(r.count),
    })),
  };
}

export async function findDedupedCategoryUrls(
  prisma: PrismaClient,
  filters: CategoryUrlQueryFilters,
  opts: { skip: number; take: number },
): Promise<DedupedCategoryUrlRow[]> {
  if (filters.categorySuffixes.length === 0 || opts.take <= 0) return [];

  const rows = await prisma.$queryRaw<
    {
      url_sha256: string;
      url_text: string;
      pathname_extension: string | null;
      target_domain_id: string;
      domain_normalized: string;
      latest_scan_job_id: string;
      latest_scan_created_at: Date;
      scan_count: number;
    }[]
  >`
    WITH ${filteredCte(filters)},
    per_scan AS (
      SELECT DISTINCT url_sha256, scan_job_id, scan_created_at
      FROM filtered
    ),
    deduped AS (
      SELECT DISTINCT ON (url_sha256)
        url_sha256,
        url_text,
        pathname_extension,
        target_domain_id,
        scan_job_id AS latest_scan_job_id,
        scan_created_at AS latest_scan_created_at
      FROM filtered
      ORDER BY url_sha256, scan_created_at DESC
    ),
    scan_counts AS (
      SELECT url_sha256, COUNT(*)::int AS scan_count
      FROM per_scan
      GROUP BY url_sha256
    )
    SELECT
      d.url_sha256,
      d.url_text,
      d.pathname_extension,
      d.target_domain_id,
      td.domain_normalized,
      d.latest_scan_job_id,
      d.latest_scan_created_at,
      sc.scan_count
    FROM deduped d
    INNER JOIN scan_counts sc ON sc.url_sha256 = d.url_sha256
    INNER JOIN target_domain td ON td.id = d.target_domain_id
    ORDER BY d.latest_scan_created_at DESC
    OFFSET ${opts.skip}
    LIMIT ${opts.take}
  `;

  if (rows.length === 0) return [];

  const hashes = rows.map((r) => r.url_sha256);
  const observations = await prisma.$queryRaw<
    { url_sha256: string; scan_job_id: string; scan_created_at: Date }[]
  >`
    WITH ${filteredCte(filters)}
    SELECT DISTINCT url_sha256, scan_job_id, scan_created_at
    FROM filtered
    WHERE url_sha256 IN (${Prisma.join(hashes)})
    ORDER BY url_sha256, scan_created_at DESC
  `;

  const obsByHash = new Map<string, CategoryUrlObservation[]>();
  for (const obs of observations) {
    const list = obsByHash.get(obs.url_sha256) ?? [];
    list.push({
      scanJobId: obs.scan_job_id,
      scanCreatedAt: obs.scan_created_at,
    });
    obsByHash.set(obs.url_sha256, list);
  }

  return rows.map((row) => ({
    urlSha256: row.url_sha256,
    urlText: row.url_text,
    pathnameExtension: row.pathname_extension,
    targetDomainId: row.target_domain_id,
    targetDomain: row.domain_normalized,
    latestScanJobId: row.latest_scan_job_id,
    latestScanCreatedAt: row.latest_scan_created_at,
    scanCount: row.scan_count,
    observations: obsByHash.get(row.url_sha256) ?? [],
  }));
}
