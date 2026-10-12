import Link from "next/link";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { CategoryDetailHeader } from "@/components/categories/category-detail-header";
import { CategoryUrlScanCell } from "@/components/categories/category-url-scan-cell";
import { ExtensionBadge } from "@/components/extension-badge";
import { ScanMetricCards } from "@/components/scans/scan-metric-cards";
import { TablePagination, normalizePageSize } from "@/components/table-pagination";
import { UrlFiltersToolbar } from "@/components/url-filters-toolbar";
import { IconArrowUpRight, IconClock, IconGlobe, IconLink } from "@/components/ui-icons";
import {
  fetchCategoryUrlStats,
  findDedupedCategoryUrls,
  loadCategorySuffixes,
} from "@/lib/category-urls";
import { normalizeExcludeKeywords } from "@/lib/url-exclude-query";
import {
  categoryUrlTabPreserveToFixedParams,
  parseCsvParam,
  type UrlTabFilterParams,
} from "@/lib/url-tab-params";
import { formatScanDateTime, urlPathFilename } from "@/lib/scan-format";

export const dynamic = "force-dynamic";

function sp(v: string | string[] | undefined): string {
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v[0] ?? "";
  return "";
}

function asPosInt(v: string | null | undefined, fallback: number) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1, Math.floor(n));
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { slug } = await params;
  const rawSp = (await searchParams) ?? {};
  const q = sp(rawSp.q);
  const hideSubRaw = parseCsvParam(rawSp.hideSub);
  const hideKwRaw = parseCsvParam(rawSp.hideKw);
  const page = asPosInt(sp(rawSp.page) || null, 1);
  const perPage = normalizePageSize(sp(rawSp.perPage) || null, 15);

  const category = await prisma.extensionCategory.findUnique({
    where: { slug },
  });

  if (!category) {
    notFound();
  }

  const categorySuffixes = await loadCategorySuffixes(prisma, category.id);
  const hideKw = normalizeExcludeKeywords(hideKwRaw);

  const validatedHideSubs =
    hideSubRaw.length > 0 && categorySuffixes.length > 0
      ? await prisma.subdomain.findMany({
          where: {
            id: { in: hideSubRaw },
            observedUrls: {
              some: { pathnameExtension: { in: categorySuffixes } },
            },
          },
          select: { id: true, hostnameNormalized: true },
          orderBy: { hostnameNormalized: "asc" },
        })
      : [];

  const hideSubIds = validatedHideSubs.map((s) => s.id);

  const urlFilters = {
    categorySuffixes,
    q,
    hideSubIds,
    hideKw,
  };

  const urlTabPreserve: UrlTabFilterParams = {
    perPage,
    q: q || undefined,
    hideSub: hideSubIds.length > 0 ? hideSubIds : undefined,
    hideKw: hideKw.length > 0 ? hideKw : undefined,
  };

  const categoryBasePath = `/categories/${slug}`;
  const urlFixedParams = categoryUrlTabPreserveToFixedParams(urlTabPreserve);

  const [urlStats, subdomainPickerRows] = await Promise.all([
    fetchCategoryUrlStats(prisma, urlFilters),
    categorySuffixes.length > 0
      ? prisma.scanObservedUrl.findMany({
          where: {
            pathnameExtension: { in: categorySuffixes },
            subdomainId: { not: null },
          },
          distinct: ["subdomainId"],
          select: {
            subdomain: {
              select: { id: true, hostnameNormalized: true },
            },
          },
        })
      : Promise.resolve([]),
  ]);

  const {
    totalUrls,
    uniqueTargets,
    uniqueScans,
    extensionBreakdown: extGroups,
    topTargets,
  } = urlStats;

  const totalPages = Math.max(1, Math.ceil(totalUrls / perPage));
  const safePage = Math.min(page, totalPages);

  const urls = await findDedupedCategoryUrls(prisma, urlFilters, {
    skip: (safePage - 1) * perPage,
    take: perPage,
  });

  const extensionBreakdown = extGroups
    .map((g) => ({
      ext: g.ext,
      count: g.count,
      percent: totalUrls > 0 ? (g.count / totalUrls) * 100 : 0,
    }))
    .sort((a, b) => b.count - a.count);

  const maxExtensionCount = extensionBreakdown[0]?.count ?? 0;

  const domainById = new Map(
    topTargets.length > 0
      ? (
          await prisma.targetDomain.findMany({
            where: { id: { in: topTargets.map((g) => g.targetDomainId) } },
            select: { id: true, domainNormalized: true },
          })
        ).map((d) => [d.id, d.domainNormalized] as const)
      : [],
  );

  const topTargetsWithDomain = topTargets
    .map((item) => ({
      domain: domainById.get(item.targetDomainId) ?? item.targetDomainId,
      count: item.count,
      percent: totalUrls > 0 ? (item.count / totalUrls) * 100 : 0,
    }))
    .filter((item) => item.domain);

  const maxTargetCount = topTargetsWithDomain[0]?.count ?? 0;

  const subdomainPickerOptions = subdomainPickerRows
    .map((row) => row.subdomain)
    .filter((s): s is { id: string; hostnameNormalized: string } => s != null)
    .sort((a, b) => a.hostnameNormalized.localeCompare(b.hostnameNormalized));

  const metricCards = [
    {
      icon: IconLink,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: totalUrls.toLocaleString(),
      label: "Total URLs",
    },
    {
      icon: IconGlobe,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: uniqueTargets.toLocaleString(),
      label: "Targets",
    },
    {
      icon: IconClock,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: uniqueScans.toLocaleString(),
      label: "Scans",
    },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <CategoryDetailHeader
        displayName={category.displayName}
        slug={category.slug}
        iconKey={category.iconKey}
        totalUrls={totalUrls}
        uniqueTargets={uniqueTargets}
        uniqueScans={uniqueScans}
        extensionCount={extensionBreakdown.length}
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-6 pt-5 pb-5 xl:flex xl:flex-col xl:overflow-hidden">
        <div className="flex flex-col gap-6 xl:min-h-0 xl:flex-1 xl:flex-row xl:overflow-hidden">
          {/* Main Table Area */}
          <div className="min-h-0 min-w-0 xl:flex-[8] xl:overflow-y-auto 2xl:flex-[9]">
            <div className="glass-panel overflow-hidden rounded-2xl">
              <div className="hidden border-b border-line bg-[var(--table-header-bg)] px-5 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted lg:grid lg:grid-cols-[minmax(0,6fr)_minmax(0,1.75fr)_minmax(0,1fr)_minmax(0,1.25fr)_minmax(0,2fr)] lg:gap-2">
                <div>URL</div>
                <div>Domain</div>
                <div>Ext</div>
                <div>Scan</div>
                <div>Found Date</div>
              </div>

              <div className="divide-y divide-line">
                {urls.length === 0 ? (
                  <div className="px-5 py-8 text-center text-[13px] text-muted">
                    No URLs found for this category.
                  </div>
                ) : (
                  urls.map((u) => {
                    const filename = urlPathFilename(u.urlText);
                    return (
                    <div
                      key={u.urlSha256}
                      className="flex flex-col gap-1.5 px-5 py-2.5 lg:grid lg:grid-cols-[minmax(0,6fr)_minmax(0,1.75fr)_minmax(0,1fr)_minmax(0,1.25fr)_minmax(0,2fr)] lg:items-center lg:gap-2"
                    >
                      <div className="min-w-0 pr-[5ch]">
                        <div className="inline-flex max-w-full min-w-0 items-start gap-px">
                          <span
                            className="min-w-0 truncate font-mono text-[11px] text-cream/90"
                            title={u.urlText}
                          >
                            {u.urlText}
                          </span>
                          <a
                            href={u.urlText}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-px shrink-0 text-muted transition-colors hover:text-accent"
                            aria-label={`Open ${u.urlText}`}
                            title="Open URL"
                          >
                            <IconArrowUpRight className="size-3" />
                          </a>
                        </div>
                        {filename ? (
                          <div
                            className="mt-0.5 truncate font-mono text-[10px] text-muted"
                            title={filename}
                          >
                            {filename}
                          </div>
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <Link
                          href={`/targets/${u.targetDomainId}`}
                          className="truncate text-[11px] text-accent/80 hover:text-accent hover:underline"
                        >
                          {u.targetDomain}
                        </Link>
                      </div>
                      <div>
                        <ExtensionBadge ext={u.pathnameExtension} />
                      </div>
                      <div className="min-w-0 font-mono text-[10px] text-muted">
                        <CategoryUrlScanCell
                          latestScanJobId={u.latestScanJobId}
                          scanCount={u.scanCount}
                          observations={u.observations.map((obs) => ({
                            scanJobId: obs.scanJobId,
                            scanCreatedAt: obs.scanCreatedAt.toISOString(),
                          }))}
                        />
                      </div>
                      <div className="font-mono text-[10px] text-muted">
                        {formatScanDateTime(u.latestScanCreatedAt)}
                      </div>
                    </div>
                    );
                  })
                )}
              </div>

              {totalUrls > 0 && (
                <TablePagination
                  basePath={categoryBasePath}
                  fixedParams={urlFixedParams}
                  pageParam="page"
                  currentPage={safePage}
                  totalPages={totalPages}
                  perPage={perPage}
                  totalItems={totalUrls}
                />
              )}
            </div>
          </div>

          {/* Right Sidebar Area */}
          <div className="min-h-0 space-y-6 xl:flex-[4] xl:overflow-y-auto 2xl:flex-[3]">
            <div className="glass-panel rounded-2xl p-4">
              <UrlFiltersToolbar
                hrefContext={{ scope: "category", slug }}
                preserve={urlTabPreserve}
                initialQuery={q}
                initialHideSubIds={hideSubIds}
                initialHideKw={hideKw}
                subdomainOptions={subdomainPickerOptions}
                resolvedHiddenSubdomains={validatedHideSubs}
                totalUrls={totalUrls}
                currentPage={safePage}
                totalPages={totalPages}
                showSummary={false}
                integratedControls
              />
            </div>

            <ScanMetricCards metrics={metricCards} layout="row" />

            {/* Extension Breakdown */}
            <div className="glass-panel overflow-hidden rounded-2xl">
              <div className="border-b border-line bg-[var(--table-header-bg)] px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                Extension Breakdown
              </div>
              <div className="p-5">
                {extensionBreakdown.length === 0 ? (
                  <div className="text-[12px] text-muted">No data.</div>
                ) : (
                  <div className="grid grid-cols-[minmax(0,3.25rem)_minmax(0,1fr)_auto] items-center gap-x-1 gap-y-3 text-[11px]">
                    {extensionBreakdown.flatMap((item) => {
                      const barFillPercent =
                        maxExtensionCount > 0
                          ? (item.count / maxExtensionCount) * 100
                          : 0;
                      const isMaxBar =
                        maxExtensionCount > 0 && item.count === maxExtensionCount;

                      return [
                        <span
                          key={`${item.ext}-label`}
                          className="truncate font-mono text-cream/90"
                          title={item.ext}
                        >
                          {item.ext}
                        </span>,
                        <div
                          key={`${item.ext}-bar`}
                          className={[
                            "relative mr-5 h-1.5 min-w-0 overflow-hidden rounded-full",
                            isMaxBar ? "bg-accent" : "bg-muted/35",
                          ].join(" ")}
                          role="presentation"
                          aria-hidden
                        >
                          {!isMaxBar ? (
                            <div
                              className="absolute inset-y-0 left-0 rounded-full bg-accent transition-all duration-500"
                              style={{ width: `${barFillPercent}%` }}
                            />
                          ) : null}
                        </div>,
                        <span
                          key={`${item.ext}-count`}
                          className="shrink-0 tabular-nums leading-none text-muted whitespace-nowrap"
                        >
                          {item.count.toLocaleString()} ({item.percent.toFixed(1)}%)
                        </span>,
                      ];
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Top Targets */}
            <div className="glass-panel overflow-hidden rounded-2xl">
              <div className="border-b border-line bg-[var(--table-header-bg)] px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                Top Targets
              </div>
              <div className="p-5">
                {topTargetsWithDomain.length === 0 ? (
                  <div className="text-[12px] text-muted">No data.</div>
                ) : (
                  <div className="space-y-2">
                    {topTargetsWithDomain.map((item) => {
                      const barFillPercent =
                        maxTargetCount > 0 ? (item.count / maxTargetCount) * 100 : 0;
                      const isMaxBar = maxTargetCount > 0 && item.count === maxTargetCount;

                      return (
                        <div key={item.domain} className="space-y-0.5">
                          <div className="text-[11px] leading-tight text-cream/90 break-all">
                            {item.domain}
                          </div>
                          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-1 text-[11px]">
                            <div
                              className={[
                                "relative mr-5 h-1.5 min-w-0 overflow-hidden rounded-full",
                                isMaxBar ? "bg-accent" : "bg-muted/35",
                              ].join(" ")}
                              role="presentation"
                              aria-hidden
                            >
                              {!isMaxBar ? (
                                <div
                                  className="absolute inset-y-0 left-0 rounded-full bg-accent transition-all duration-500"
                                  style={{ width: `${barFillPercent}%` }}
                                />
                              ) : null}
                            </div>
                            <span className="shrink-0 tabular-nums leading-none text-muted whitespace-nowrap">
                              {item.count.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
