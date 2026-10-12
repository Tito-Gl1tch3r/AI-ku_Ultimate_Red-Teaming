"use client";

import Link from "next/link";
import {
  IconArrowDown,
  IconArrowUp,
  IconArrowUpDown,
} from "@/components/ui-icons";
import {
  buildSubdomainSortHref,
  SUBDOMAIN_SORT_FIELD_LABELS,
  SUBDOMAIN_SORTABLE_FIELDS,
  nextSubdomainSort,
  type SubdomainSortField,
  type SubdomainTableSort,
} from "@/lib/subdomain-table-sort";

function SortHeaderButton({
  field,
  sort,
  basePath,
  fixedParams,
}: {
  field: SubdomainSortField;
  sort: SubdomainTableSort;
  basePath: string;
  fixedParams: Record<string, string>;
}) {
  const active = sort.field === field;
  const href = buildSubdomainSortHref(basePath, fixedParams, nextSubdomainSort(field, sort));
  const SortIcon = active ? (sort.dir === "asc" ? IconArrowUp : IconArrowDown) : IconArrowUpDown;

  return (
    <Link
      href={href}
      className={[
        "inline-flex min-w-0 items-center gap-1 transition-colors hover:text-cream",
        active ? "text-cream" : "text-muted",
      ].join(" ")}
      aria-label={`Sort by ${SUBDOMAIN_SORT_FIELD_LABELS[field]}${active ? `, ${sort.dir === "asc" ? "ascending" : "descending"}` : ""}`}
    >
      <span className="truncate">{SUBDOMAIN_SORT_FIELD_LABELS[field]}</span>
      <SortIcon className={["size-3 shrink-0", active ? "text-accent" : "opacity-45"].join(" ")} />
    </Link>
  );
}

export function SubdomainTableHeader({
  sort,
  basePath,
  fixedParams,
  observedScanView = false,
}: {
  sort: SubdomainTableSort;
  basePath: string;
  fixedParams: Record<string, string>;
  observedScanView?: boolean;
}) {
  return (
    <>
      <div className="hidden border-b border-line bg-[var(--table-header-bg)] px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted sm:grid sm:grid-cols-12 sm:gap-3">
        <div className="col-span-4">
          <SortHeaderButton field="hostname" sort={sort} basePath={basePath} fixedParams={fixedParams} />
        </div>
        <div className="col-span-2">
          <SortHeaderButton field="ipCount" sort={sort} basePath={basePath} fixedParams={fixedParams} />
        </div>
        <div className="col-span-3">
          <SortHeaderButton field="latestIp" sort={sort} basePath={basePath} fixedParams={fixedParams} />
        </div>
        <div className="col-span-2">
          <SortHeaderButton field="lastResolved" sort={sort} basePath={basePath} fixedParams={fixedParams} />
        </div>
        <div className="col-span-1" aria-hidden />
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-[var(--table-header-bg)] px-5 py-2.5 sm:hidden">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Sort</span>
        {SUBDOMAIN_SORTABLE_FIELDS.map((field) => {
          let label = SUBDOMAIN_SORT_FIELD_LABELS[field];
          if (field === "ipCount" && observedScanView) {
            label = "Scan IPs";
          }
          return (
            <Link
              key={field}
              href={buildSubdomainSortHref(basePath, fixedParams, nextSubdomainSort(field, sort))}
              className={[
                "rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition-colors",
                sort.field === field
                  ? "border-accent/35 bg-accent/10 text-cream"
                  : "border-line text-muted hover:border-line hover:bg-[var(--nav-hover-bg)] hover:text-cream",
              ].join(" ")}
            >
              {label}
              {sort.field === field ? (sort.dir === "asc" ? " ↑" : " ↓") : ""}
            </Link>
          );
        })}
      </div>
    </>
  );
}
