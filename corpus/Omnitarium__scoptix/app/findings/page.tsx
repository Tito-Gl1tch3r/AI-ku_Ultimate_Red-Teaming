import Link from "next/link";
import { EngineProvider } from "@prisma/client";
import { FindingsFiltersPanel } from "@/components/findings/findings-filters-panel";
import type { FindingsFilterOption } from "@/components/findings/findings-filter-dropdown";
import { FindingsListHeader } from "@/components/findings/findings-list-header";
import { AccentDonutChart } from "@/components/scans/accent-donut-chart";
import { ScanMetricCards } from "@/components/scans/scan-metric-cards";
import { TablePagination, normalizePageSize } from "@/components/table-pagination";
import {
  IconAlertTriangle,
  IconChevronRight,
  IconClock,
  IconFileText,
  IconGlobe,
  IconLink,
} from "@/components/ui-icons";
import { findingsSearchWhere } from "@/lib/findings-search-query";
import { prisma } from "@/lib/prisma";
import { formatScanDateTime, shortScanId } from "@/lib/scan-format";
import type { SummarySourceSlice } from "@/lib/scan-summary";

export const dynamic = "force-dynamic";

const ENGINE_SOURCE_COLORS: Record<string, string> = {
  VirusTotal: "#9333ea",
  Wayback: "#22c55e",
};

function asPosInt(v: string | undefined, fallback: number) {
  const n = Number(v);
  return Number.isFinite(n) && n >= 1 ? Math.floor(n) : fallback;
}

function formatEngineLabel(engine: EngineProvider) {
  if (engine === "VIRUSTOTAL") return "VirusTotal";
  if (engine === "WAYBACK_MACHINE") return "Wayback";
  if (engine === "URLSCAN") return "URLScan";
  return engine;
}

const ENGINE_VALUES = new Set<string>(Object.values(EngineProvider));

function parseDateParam(v: string | undefined): string | undefined {
  if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return undefined;
  const d = new Date(`${v}T00:00:00.000Z`);
  if (Number.isNaN(d.getTime())) return undefined;
  return v;
}

function createdAtRange(from?: string, to?: string) {
  if (!from && !to) return {};
  const range: { gte?: Date; lte?: Date } = {};
  if (from) range.gte = new Date(`${from}T00:00:00.000Z`);
  if (to) range.lte = new Date(`${to}T23:59:59.999Z`);
  return { createdAt: range };
}

export default async function FindingsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = (await searchParams) ?? {};
  const typeFilter = typeof sp.type === "string" ? sp.type : undefined;
  const sourceFilter = typeof sp.source === "string" ? sp.source : undefined;
  const engineFilter =
    typeof sp.engine === "string" && ENGINE_VALUES.has(sp.engine)
      ? (sp.engine as EngineProvider)
      : undefined;
  const targetFilter = typeof sp.target === "string" ? sp.target : undefined;
  const scanFilter = typeof sp.scan === "string" ? sp.scan : undefined;
  const keyword = typeof sp.q === "string" ? sp.q.trim() : "";
  const dateFrom = parseDateParam(typeof sp.from === "string" ? sp.from : undefined);
  const dateTo = parseDateParam(typeof sp.to === "string" ? sp.to : undefined);
  const page = asPosInt(typeof sp.page === "string" ? sp.page : undefined, 1);
  const perPage = normalizePageSize(typeof sp.perPage === "string" ? sp.perPage : undefined);

  const dateFilter = createdAtRange(dateFrom, dateTo);
  const searchWhere = findingsSearchWhere(keyword);

  const where = {
    ...(typeFilter ? { findingType: typeFilter } : {}),
    ...(sourceFilter ? { source: sourceFilter as "URL_STRING" | "RESPONSE_BODY" } : {}),
    ...(targetFilter ? { targetDomainId: targetFilter } : {}),
    ...(scanFilter ? { scanJobId: scanFilter } : {}),
    ...(engineFilter
      ? { discoveredUrl: { engines: { has: engineFilter } } }
      : {}),
    ...dateFilter,
    ...(searchWhere ?? {}),
  };

  const statsWhere = {
    ...(typeFilter ? { findingType: typeFilter } : {}),
    ...(targetFilter ? { targetDomainId: targetFilter } : {}),
    ...(scanFilter ? { scanJobId: scanFilter } : {}),
    ...(engineFilter
      ? { discoveredUrl: { engines: { has: engineFilter } } }
      : {}),
    ...dateFilter,
    ...(searchWhere ?? {}),
  };

  const [
    total,
    typeGroups,
    scanJobGroups,
    targetGroups,
    urlStringCount,
    responseBodyCount,
    engineRows,
    scanIdGroups,
    virusTotalCount,
    waybackCount,
  ] = await Promise.all([
    prisma.analysisFinding.count({ where }),
    prisma.analysisFinding.groupBy({
      by: ["findingType"],
      _count: { _all: true },
      orderBy: { _count: { findingType: "desc" } },
    }),
    prisma.analysisFinding.groupBy({
      by: ["scanJobId"],
      where: { ...where, scanJobId: { not: null } },
      _count: { _all: true },
    }),
    prisma.analysisFinding.groupBy({
      by: ["targetDomainId"],
      where,
      _count: { _all: true },
    }),
    prisma.analysisFinding.count({
      where: { ...statsWhere, source: "URL_STRING" },
    }),
    prisma.analysisFinding.count({
      where: { ...statsWhere, source: "RESPONSE_BODY" },
    }),
    prisma.analysisFinding.findMany({
      where,
      select: { discoveredUrl: { select: { engines: true } } },
      take: 5000,
    }),
    prisma.analysisFinding.groupBy({
      by: ["scanJobId"],
      where: { ...where, scanJobId: { not: null } },
    }),
    prisma.analysisFinding.count({
      where: {
        ...where,
        discoveredUrl: { engines: { has: EngineProvider.VIRUSTOTAL } },
      },
    }),
    prisma.analysisFinding.count({
      where: {
        ...where,
        discoveredUrl: { engines: { has: EngineProvider.WAYBACK_MACHINE } },
      },
    }),
  ]);

  const scanIds = scanIdGroups
    .map((g) => g.scanJobId)
    .filter((id): id is string => id != null);

  const scanRows =
    scanIds.length > 0
      ? await prisma.scanJob.findMany({
          where: { id: { in: scanIds } },
          select: { id: true, createdAt: true, completedAt: true },
          orderBy: { createdAt: "desc" },
          take: 50,
        })
      : [];

  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const safePage = Math.min(page, totalPages);

  const findings = await prisma.analysisFinding.findMany({
    where,
    orderBy: { createdAt: "desc" },
    skip: (safePage - 1) * perPage,
    take: perPage,
    include: {
      discoveredUrl: {
        select: {
          urlText: true,
          externalSeenAt: true,
          engines: true,
          targetDomain: { select: { domainNormalized: true, id: true } },
        },
      },
    },
  });

  const allFindingCount = typeGroups.reduce((sum, group) => sum + group._count._all, 0);
  const scansCount = scanJobGroups.length;
  const targetsCount = targetGroups.length;

  const targetDomains =
    targetGroups.length > 0
      ? await prisma.targetDomain.findMany({
          where: { id: { in: targetGroups.map((g) => g.targetDomainId) } },
          select: { id: true, domainNormalized: true },
        })
      : [];
  const targetDomainById = new Map(
    targetDomains.map((t) => [t.id, t.domainNormalized] as const),
  );

  const engineSet = new Set<EngineProvider>();
  for (const row of engineRows) {
    for (const engine of row.discoveredUrl.engines) {
      engineSet.add(engine);
    }
  }
  const engines = [...engineSet].sort((a, b) =>
    formatEngineLabel(a).localeCompare(formatEngineLabel(b)),
  );

  const fixedParams: Record<string, string> = {};
  if (typeFilter) fixedParams.type = typeFilter;
  if (sourceFilter) fixedParams.source = sourceFilter;
  if (engineFilter) fixedParams.engine = engineFilter;
  if (targetFilter) fixedParams.target = targetFilter;
  if (scanFilter) fixedParams.scan = scanFilter;
  if (keyword) fixedParams.q = keyword;
  if (dateFrom) fixedParams.from = dateFrom;
  if (dateTo) fixedParams.to = dateTo;

  function filterUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const t = "type" in overrides ? overrides.type : typeFilter;
    const s = "source" in overrides ? overrides.source : sourceFilter;
    const e = "engine" in overrides ? overrides.engine : engineFilter;
    const tg = "target" in overrides ? overrides.target : targetFilter;
    const sc = "scan" in overrides ? overrides.scan : scanFilter;
    const q = "q" in overrides ? overrides.q : keyword || undefined;
    const from = "from" in overrides ? overrides.from : dateFrom;
    const to = "to" in overrides ? overrides.to : dateTo;
    const pg = overrides.page ?? "1";
    p.set("perPage", String(perPage));
    if (t) p.set("type", t);
    if (s) p.set("source", s);
    if (e) p.set("engine", e);
    if (tg) p.set("target", tg);
    if (sc) p.set("scan", sc);
    if (q) p.set("q", q);
    if (from) p.set("from", from);
    if (to) p.set("to", to);
    if (pg !== "1") p.set("page", pg);
    const qs = p.toString();
    return `/findings${qs ? `?${qs}` : ""}`;
  }

  const typeOptions: FindingsFilterOption[] = [
    {
      label: "All types",
      href: filterUrl({ type: undefined, page: "1" }),
      selected: !typeFilter,
    },
    ...typeGroups.map((g) => ({
      label: `${g.findingType} (${g._count._all.toLocaleString()})`,
      href: filterUrl({ type: g.findingType, page: "1" }),
      selected: typeFilter === g.findingType,
    })),
  ];

  const sourceOptions: FindingsFilterOption[] = [
    {
      label: "All Sources",
      href: filterUrl({ source: undefined, page: "1" }),
      selected: !sourceFilter,
    },
    {
      label: "URL String",
      href: filterUrl({ source: "URL_STRING", page: "1" }),
      selected: sourceFilter === "URL_STRING",
    },
    {
      label: "Response Body",
      href: filterUrl({ source: "RESPONSE_BODY", page: "1" }),
      selected: sourceFilter === "RESPONSE_BODY",
    },
  ];

  const engineOptions: FindingsFilterOption[] = [
    {
      label: "All engines",
      href: filterUrl({ engine: undefined, page: "1" }),
      selected: !engineFilter,
    },
    ...engines.map((engine) => ({
      label: formatEngineLabel(engine),
      href: filterUrl({ engine, page: "1" }),
      selected: engineFilter === engine,
    })),
  ];

  const targetOptions: FindingsFilterOption[] = [
    {
      label: "All targets",
      href: filterUrl({ target: undefined, page: "1" }),
      selected: !targetFilter,
    },
    ...targetGroups
      .map((g) => ({
        id: g.targetDomainId,
        domain: targetDomainById.get(g.targetDomainId) ?? g.targetDomainId,
        count: g._count._all,
      }))
      .sort((a, b) => a.domain.localeCompare(b.domain))
      .map((t) => ({
        label: `${t.domain} (${t.count.toLocaleString()})`,
        href: filterUrl({ target: t.id, page: "1" }),
        selected: targetFilter === t.id,
      })),
  ];

  const scanOptions: FindingsFilterOption[] = [
    {
      label: "All scans",
      href: filterUrl({ scan: undefined, page: "1" }),
      selected: !scanFilter,
    },
    ...scanRows.map((scan) => ({
      label: `${formatScanDateTime(scan.completedAt ?? scan.createdAt)} · ${shortScanId(scan.id)}`,
      href: filterUrl({ scan: scan.id, page: "1" }),
      selected: scanFilter === scan.id,
    })),
  ];

  const sourceEngineTotal = virusTotalCount + waybackCount;
  const sourceSlices: SummarySourceSlice[] = (() => {
    if (sourceEngineTotal <= 0) return [];

    const entries = [
      { label: "VirusTotal", count: virusTotalCount },
      { label: "Wayback", count: waybackCount },
    ].sort((a, b) => b.count - a.count);

    const slices = entries.map((entry) => ({
      label: entry.label,
      count: entry.count,
      percent: Math.round((entry.count / sourceEngineTotal) * 100),
      color: ENGINE_SOURCE_COLORS[entry.label] ?? "#9ca3af",
    }));

    const percentSum = slices.reduce((sum, slice) => sum + slice.percent, 0);
    if (percentSum !== 100 && slices.length > 0) {
      slices[0] = { ...slices[0], percent: slices[0].percent + (100 - percentSum) };
    }

    return slices;
  })();

  const metricCards = [
    {
      icon: IconFileText,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: allFindingCount.toLocaleString(),
      label: "Total Findings",
    },
    {
      icon: IconGlobe,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: targetsCount.toLocaleString(),
      label: "Targets",
    },
    {
      icon: IconClock,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: scansCount.toLocaleString(),
      label: "Scans",
    },
    {
      icon: IconLink,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: urlStringCount.toLocaleString(),
      label: "URL String Findings",
    },
    {
      icon: IconAlertTriangle,
      iconBg: "scx-metric-icon-badge--success",
      iconColor: "",
      value: responseBodyCount.toLocaleString(),
      label: "Response Body Findings",
    },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <FindingsListHeader findingCount={allFindingCount} />

      <div className="min-h-0 flex-1 overflow-y-auto px-6 pt-5 pb-5 xl:flex xl:flex-col xl:overflow-hidden">
        <div className="flex flex-col gap-6 xl:min-h-0 xl:flex-1 xl:flex-row xl:overflow-hidden">
          {/* LEFT COLUMN */}
          <div className="flex min-h-0 min-w-0 flex-col gap-6 xl:flex-[8] xl:min-h-0 2xl:flex-[9]">
            <div className="shrink-0 space-y-6">
            {/* ── Filter pills ── */}
            <div className="relative">
              <div
                className={[
                  "flex items-center gap-2 overflow-x-auto pb-1 pr-8",
                  "whitespace-nowrap",
                  "flex-nowrap",
                ].join(" ")}
              >
                <Link
                  href={filterUrl({ type: undefined })}
                  className={[
                    "flex-shrink-0 rounded-lg border px-3 py-1.5 text-[12px] transition-colors",
                    !typeFilter
                      ? "border-accent/60 border-b-2 bg-accent/10 text-cream"
                      : "border-line text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                  ].join(" ")}
                >
                  All ({allFindingCount.toLocaleString()})
                </Link>
                {typeGroups.map((g) => (
                  <Link
                    key={g.findingType}
                    href={filterUrl({ type: g.findingType })}
                    className={[
                      "flex-shrink-0 rounded-lg border px-3 py-1.5 text-[12px] transition-colors",
                      typeFilter === g.findingType
                        ? "border-accent/60 border-b-2 bg-accent/10 text-cream"
                        : "border-line text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                    ].join(" ")}
                  >
                    {g.findingType} ({g._count._all.toLocaleString()})
                  </Link>
                ))}
              </div>

              <div
                aria-hidden
                className="pointer-events-none absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-black/10 to-transparent"
              >
                <div className="flex h-full items-center justify-end pr-1.5 text-muted">
                  <IconChevronRight className="size-4" />
                </div>
              </div>
            </div>

            {/* ── Source filter ── */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                Source:
              </span>
              {[
                { label: "All", value: undefined },
                { label: "URL String", value: "URL_STRING" },
                { label: "Response Body", value: "RESPONSE_BODY" },
              ].map((opt) => (
                <Link
                  key={opt.label}
                  href={filterUrl({ source: opt.value })}
                  className={[
                    "rounded-lg border px-3 py-1.5 text-[11px] transition-colors",
                    sourceFilter === opt.value || (!sourceFilter && !opt.value)
                      ? "border-accent/40 bg-accent/8 text-cream"
                      : "border-line text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                  ].join(" ")}
                >
                  {opt.label}
                </Link>
              ))}
            </div>

            <ScanMetricCards metrics={metricCards} layout="flex-equal" />
            </div>

            {/* ── Table ── */}
            <div className="min-h-0 xl:flex-1 xl:overflow-y-auto">
            <div className="glass-panel overflow-hidden rounded-2xl">
              {/* Header */}
              <div className="hidden border-b border-line bg-[var(--table-header-bg)] px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted lg:grid lg:grid-cols-12 lg:gap-x-4 lg:gap-y-3">
                <div className="col-span-1">Type</div>
                <div className="col-span-1">Engines</div>
                <div className="col-span-5">URL</div>
                <div className="col-span-2 pr-2">Snippet</div>
                <div className="col-span-1 pl-3">Source</div>
                <div className="col-span-2">Date</div>
              </div>

              <div className="divide-y divide-line">
                {findings.length === 0 ? (
                  <div className="px-5 py-8 text-center text-[13px] text-muted">
                    No findings match this filter.
                  </div>
                ) : (
                  findings.map((f) => (
                    <div
                      key={f.id}
                      className="flex flex-col gap-2 px-5 py-4 lg:grid lg:grid-cols-12 lg:items-start lg:gap-x-4 lg:gap-y-3"
                    >
                      <div className="col-span-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-accent">
                          {f.findingType}
                        </div>
                      </div>
                      <div className="col-span-1 text-[10px] text-muted">
                        {f.discoveredUrl.engines
                          .map((e) => formatEngineLabel(e))
                          .join(", ")}
                      </div>
                      <div className="col-span-5 min-w-0">
                        <div
                          className="break-all font-mono text-[11px] text-cream/90"
                          title={f.discoveredUrl.urlText}
                        >
                          {f.discoveredUrl.urlText}
                        </div>
                        <Link
                          href={`/targets/${f.discoveredUrl.targetDomain.id}`}
                          className="mt-1 text-[10px] text-accent/70 hover:text-accent hover:underline"
                        >
                          {f.discoveredUrl.targetDomain.domainNormalized}
                        </Link>
                      </div>
                      <div className="col-span-2 min-w-0 pr-2">
                        {f.snippet ? (
                          <div
                            className="break-all rounded-md border border-line bg-black/15 px-2 py-1.5 font-mono text-[10px] text-cream/80"
                            title={f.snippet}
                          >
                            {f.snippet}
                          </div>
                        ) : (
                          <span className="text-[11px] text-muted">—</span>
                        )}
                      </div>
                      <div className="col-span-1 pl-3">
                        <span className="text-[9px] font-medium tracking-wide text-muted">
                          {f.source === "URL_STRING" ? "URL" : "Body"}
                        </span>
                      </div>
                      <div className="col-span-2 font-mono text-[10px] text-muted">
                        <div title="Date found by our scanner">
                          Found: {formatScanDateTime(f.createdAt)}
                        </div>
                        {f.discoveredUrl.externalSeenAt && (
                          <div
                            title="Date reported in threat intel"
                            className="mt-1 text-accent/70"
                          >
                            Intel: {formatScanDateTime(f.discoveredUrl.externalSeenAt)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <TablePagination
                currentPage={safePage}
                totalPages={totalPages}
                totalItems={total}
                perPage={perPage}
                basePath="/findings"
                fixedParams={fixedParams}
              />
            </div>
            </div>
          </div>

          {/* RIGHT COLUMN */}
          <div className="flex w-full shrink-0 flex-col gap-6 xl:min-h-0 xl:w-[300px] xl:overflow-y-auto">
            <div className="glass-panel rounded-2xl p-5">
              <h3 className="mb-4 text-sm font-bold text-cream">Source</h3>
              {sourceSlices.length === 0 ? (
                <div className="text-[12px] text-muted">No data.</div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="shrink-0">
                    <AccentDonutChart
                      slices={sourceSlices}
                      total={sourceEngineTotal}
                      centerLabel="Findings"
                      ring="thin"
                      size="sm"
                      texture
                      sourceGradients
                    />
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    {sourceSlices.map((slice) => (
                      <div
                        key={slice.label}
                        className="flex min-w-0 items-center justify-between gap-2 text-[11px]"
                      >
                        <div className="flex min-w-0 items-center gap-1.5">
                          <span
                            className="size-2 shrink-0 rounded-full"
                            style={{ backgroundColor: slice.color }}
                            aria-hidden
                          />
                          <span className="truncate text-cream" title={slice.label}>
                            {slice.label}
                          </span>
                        </div>
                        <span className="shrink-0 tabular-nums text-muted">
                          {slice.percent}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <FindingsFiltersPanel
              clearAllHref={filterUrl({
                type: undefined,
                source: undefined,
                engine: undefined,
                target: undefined,
                scan: undefined,
                q: undefined,
                from: undefined,
                to: undefined,
              })}
              dateFrom={dateFrom}
              dateTo={dateTo}
              typeOptions={typeOptions}
              engineOptions={engineOptions}
              sourceOptions={sourceOptions}
              targetOptions={targetOptions}
              scanOptions={scanOptions}
              keyword={keyword}
              perPage={perPage}
              activeFilters={{
                type: typeFilter,
                source: sourceFilter,
                engine: engineFilter,
                target: targetFilter,
                scan: scanFilter,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
