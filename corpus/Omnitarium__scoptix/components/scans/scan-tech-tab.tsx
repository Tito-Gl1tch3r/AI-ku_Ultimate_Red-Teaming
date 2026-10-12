"use client";

import { ScanPanelHeading } from "@/components/scans/scan-panel-heading";
import { TablePagination } from "@/components/table-pagination";
import { TechIcon } from "@/components/scans/tech-icon";
import { useTechHostsPanel } from "@/components/scans/tech-hosts-panel-provider";
import { IconChevronRight } from "@/components/ui-icons";

export type ScanTechHost = {
  hostnameNormalized: string;
  version: string | null;
};

export type ScanTechRow = {
  name: string;
  iconName: string | null;
  website: string | null;
  categories: string[];
  versions: string[];
  hosts: ScanTechHost[];
  hostCount: number;
};

export function ScanTechTab({
  technologies,
  totalItems,
  currentPage,
  totalPages,
  perPage,
  basePath,
  isCompleted,
}: {
  technologies: ScanTechRow[];
  totalItems: number;
  currentPage: number;
  totalPages: number;
  perPage: number;
  basePath: string;
  isCompleted: boolean;
}) {
  const tableFixedParams = { tab: "tech" };

  return (
    <div className="space-y-4">
      <div className="glass-panel overflow-hidden rounded-2xl">
        <div className="border-b border-line bg-[var(--table-header-bg)] px-5 py-4">
          <ScanPanelHeading
            title="Technologies fingerprinted in this scan"
            description={
              isCompleted
                ? "Software detected per subdomain, grouped by technology."
                : "Technologies detected so far for this in-progress or partial scan."
            }
          />
        </div>

        {/* Column header — mirrors the other tabs' header rows. */}
        <div className="hidden border-b border-line bg-[var(--table-header-bg)] px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted sm:grid sm:grid-cols-12 sm:gap-3">
          <div className="col-span-5">Technology</div>
          <div className="col-span-3">Versions</div>
          <div className="col-span-3">Categories</div>
          <div className="col-span-1 text-right">Hosts</div>
        </div>

        <div className="divide-y divide-line">
          {technologies.length === 0 ? (
            <div className="px-5 py-8 text-center text-[13px] text-muted">
              No technologies detected. Enable the Wappalyzer engine and re-run the scan.
            </div>
          ) : (
            technologies.map((t) => <ScanTechRowItem key={t.name} row={t} />)
          )}
        </div>

        <TablePagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalItems}
          perPage={perPage}
          basePath={basePath}
          fixedParams={tableFixedParams}
        />
      </div>
    </div>
  );
}

function ScanTechRowItem({ row }: { row: ScanTechRow }) {
  const { openTechPanel } = useTechHostsPanel();

  return (
    <button
      type="button"
      onClick={() => openTechPanel(row)}
      className="group flex w-full flex-col gap-2 px-5 py-3 text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:bg-white/5 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent/35 sm:grid sm:grid-cols-12 sm:items-center sm:gap-3"
    >
      {/* Technology name + icon */}
      <div className="col-span-5 flex min-w-0 items-center gap-2">
        <TechIcon name={row.name} iconName={row.iconName} size={16} />
        <span className="min-w-0 truncate font-mono text-[12px] text-cream group-hover:text-accent">
          {row.name}
        </span>
      </div>

      {/* Versions */}
      <div className="col-span-3 min-w-0">
        {row.versions.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {row.versions.slice(0, 3).map((v) => (
              <span
                key={v}
                className="rounded-md border border-line bg-white/[0.03] px-1.5 py-0.5 font-mono text-[10px] text-cream"
              >
                {v}
              </span>
            ))}
            {row.versions.length > 3 ? (
              <span className="px-1 py-0.5 font-mono text-[10px] text-muted">
                +{row.versions.length - 3}
              </span>
            ) : null}
          </div>
        ) : (
          <span className="font-mono text-[11px] text-muted">—</span>
        )}
      </div>

      {/* Categories */}
      <div
        className="col-span-3 min-w-0 truncate text-[11px] text-muted"
        title={row.categories.join(", ")}
      >
        {row.categories.length > 0 ? row.categories.join(", ") : "—"}
      </div>

      {/* Host count + chevron */}
      <div className="col-span-1 flex items-center justify-between gap-2 sm:justify-end">
        <span className="font-mono text-[11px] text-cream">
          {row.hostCount.toLocaleString()}
        </span>
        <IconChevronRight
          className="size-4 shrink-0 text-muted opacity-60 transition-all group-hover:text-accent group-hover:opacity-100"
          aria-hidden
        />
      </div>
    </button>
  );
}
