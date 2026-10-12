import { FindingSource, Prisma, type PrismaClient } from "@prisma/client";

/**
 * Target-level finding identity: exact URL (via url_sha256) + type + source + snippet.
 * One character difference in URL text ⇒ different hash ⇒ counts as unique.
 */
export type TargetFindingDedupFilter = {
  findingType?: string;
  source?: FindingSource;
};

function dedupWhereSql(targetDomainId: string, filter?: TargetFindingDedupFilter): Prisma.Sql {
  const parts: Prisma.Sql[] = [Prisma.sql`f.target_domain_id = ${targetDomainId}`];
  if (filter?.findingType) {
    parts.push(Prisma.sql`f.finding_type = ${filter.findingType}`);
  }
  if (filter?.source) {
    parts.push(Prisma.sql`f.source = ${filter.source}::"FindingSource"`);
  }
  return Prisma.join(parts, " AND ");
}

export async function countDedupedTargetFindings(
  prisma: PrismaClient,
  targetDomainId: string,
  filter?: TargetFindingDedupFilter,
): Promise<number> {
  const where = dedupWhereSql(targetDomainId, filter);
  const rows = await prisma.$queryRaw<[{ count: bigint }]>`
    SELECT COUNT(*)::bigint AS count
    FROM (
      SELECT DISTINCT du.url_sha256, f.finding_type, f.source, f.snippet
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
    ) deduped
  `;
  return Number(rows[0]?.count ?? 0);
}

export async function groupDedupedTargetFindingsByType(
  prisma: PrismaClient,
  targetDomainId: string,
): Promise<{ findingType: string; count: number }[]> {
  const where = dedupWhereSql(targetDomainId);
  const rows = await prisma.$queryRaw<{ finding_type: string; count: bigint }[]>`
    SELECT finding_type, COUNT(*)::bigint AS count
    FROM (
      SELECT DISTINCT du.url_sha256, f.finding_type, f.source, f.snippet
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
    ) deduped
    GROUP BY finding_type
    ORDER BY count DESC, finding_type ASC
  `;
  return rows.map((r) => ({ findingType: r.finding_type, count: Number(r.count) }));
}

export async function findDedupedTargetFindingIds(
  prisma: PrismaClient,
  targetDomainId: string,
  opts: { skip: number; take: number; filter?: TargetFindingDedupFilter },
): Promise<string[]> {
  const where = dedupWhereSql(targetDomainId, opts.filter);
  const rows = await prisma.$queryRaw<{ id: string }[]>`
    WITH deduped AS (
      SELECT DISTINCT ON (du.url_sha256, f.finding_type, f.source, f.snippet)
        f.id,
        f.created_at
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
      ORDER BY
        du.url_sha256,
        f.finding_type,
        f.source,
        f.snippet NULLS FIRST,
        f.created_at DESC
    )
    SELECT id
    FROM deduped
    ORDER BY created_at DESC
    OFFSET ${opts.skip}
    LIMIT ${opts.take}
  `;
  return rows.map((r) => r.id);
}

function dedupScanWhereSql(scanJobId: string, filter?: TargetFindingDedupFilter): Prisma.Sql {
  const parts: Prisma.Sql[] = [Prisma.sql`f.scan_job_id = ${scanJobId}`];
  if (filter?.findingType) {
    parts.push(Prisma.sql`f.finding_type = ${filter.findingType}`);
  }
  if (filter?.source) {
    parts.push(Prisma.sql`f.source = ${filter.source}::"FindingSource"`);
  }
  return Prisma.join(parts, " AND ");
}

export async function countDedupedScanFindings(
  prisma: PrismaClient,
  scanJobId: string,
  filter?: TargetFindingDedupFilter,
): Promise<number> {
  const where = dedupScanWhereSql(scanJobId, filter);
  const rows = await prisma.$queryRaw<[{ count: bigint }]>`
    SELECT COUNT(*)::bigint AS count
    FROM (
      SELECT DISTINCT du.url_sha256, f.finding_type, f.source, f.snippet
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
    ) deduped
  `;
  return Number(rows[0]?.count ?? 0);
}

export async function groupDedupedScanFindingsByType(
  prisma: PrismaClient,
  scanJobId: string,
): Promise<{ findingType: string; count: number }[]> {
  const where = dedupScanWhereSql(scanJobId);
  const rows = await prisma.$queryRaw<{ finding_type: string; count: bigint }[]>`
    SELECT finding_type, COUNT(*)::bigint AS count
    FROM (
      SELECT DISTINCT du.url_sha256, f.finding_type, f.source, f.snippet
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
    ) deduped
    GROUP BY finding_type
    ORDER BY count DESC, finding_type ASC
  `;
  return rows.map((r) => ({ findingType: r.finding_type, count: Number(r.count) }));
}

export async function findDedupedScanFindingIds(
  prisma: PrismaClient,
  scanJobId: string,
  opts: { skip: number; take: number; filter?: TargetFindingDedupFilter },
): Promise<string[]> {
  const where = dedupScanWhereSql(scanJobId, opts.filter);
  const rows = await prisma.$queryRaw<{ id: string }[]>`
    WITH deduped AS (
      SELECT DISTINCT ON (du.url_sha256, f.finding_type, f.source, f.snippet)
        f.id,
        f.created_at
      FROM analysis_finding f
      INNER JOIN discovered_url du ON du.id = f.discovered_url_id
      WHERE ${where}
      ORDER BY
        du.url_sha256,
        f.finding_type,
        f.source,
        f.snippet NULLS FIRST,
        f.created_at DESC
    )
    SELECT id
    FROM deduped
    ORDER BY created_at DESC
    OFFSET ${opts.skip}
    LIMIT ${opts.take}
  `;
  return rows.map((r) => r.id);
}

export async function syncTargetCachedFindingCount(
  prisma: PrismaClient,
  targetDomainId: string,
): Promise<number> {
  const findingCount = await countDedupedTargetFindings(prisma, targetDomainId);
  await prisma.targetDomain.update({
    where: { id: targetDomainId },
    data: { cachedFindingCount: findingCount },
  });
  return findingCount;
}
