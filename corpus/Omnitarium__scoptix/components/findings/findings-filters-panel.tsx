"use client";

import Link from "next/link";
import {
  FindingsFilterDropdown,
  type FindingsFilterOption,
} from "@/components/findings/findings-filter-dropdown";
import { ThemeDateInput } from "@/components/ui/theme-date-input";
import { UrlSearchBar } from "@/components/url-search-bar";
import { isFindingsSearchQueryActive } from "@/lib/findings-search-query";
import { apiUrl } from "@/lib/api-url";

export function FindingsFiltersPanel({
  clearAllHref,
  typeOptions,
  engineOptions,
  sourceOptions,
  targetOptions,
  scanOptions,
  keyword,
  perPage,
  dateFrom,
  dateTo,
  activeFilters,
}: {
  clearAllHref: string;
  typeOptions: FindingsFilterOption[];
  engineOptions: FindingsFilterOption[];
  sourceOptions: FindingsFilterOption[];
  targetOptions: FindingsFilterOption[];
  scanOptions: FindingsFilterOption[];
  keyword: string;
  perPage: number;
  dateFrom?: string;
  dateTo?: string;
  activeFilters: {
    type?: string;
    source?: string;
    engine?: string;
    target?: string;
    scan?: string;
  };
}) {
  return (
    <div className="glass-panel flex flex-col gap-4 rounded-2xl p-5">
      <div className="mb-1 flex items-center justify-between">
        <h3 className="text-sm font-bold text-cream">Filters</h3>
        <Link
          href={clearAllHref}
          className="text-xs font-medium text-warn hover:text-warn/80"
        >
          Clear all
        </Link>
      </div>

      <div className="space-y-3">
        <FindingsFilterDropdown
          label="Type"
          placeholder="Select types"
          options={typeOptions}
        />
        <FindingsFilterDropdown
          label="Engine"
          placeholder="Select engines"
          options={engineOptions}
          disabled={engineOptions.length <= 1}
        />
        <FindingsFilterDropdown
          label="Source"
          placeholder="All Sources"
          options={sourceOptions}
        />
        <FindingsFilterDropdown
          label="Target"
          placeholder="Select targets"
          options={targetOptions}
          disabled={targetOptions.length <= 1}
        />
        <FindingsFilterDropdown
          label="Scan"
          placeholder="Select scans"
          options={scanOptions}
          disabled={scanOptions.length <= 1}
        />

        <form method="get" action={apiUrl("/findings")} className="space-y-3">
          <input type="hidden" name="perPage" value={String(perPage)} />
          {activeFilters.type ? (
            <input type="hidden" name="type" value={activeFilters.type} />
          ) : null}
          {activeFilters.source ? (
            <input type="hidden" name="source" value={activeFilters.source} />
          ) : null}
          {activeFilters.engine ? (
            <input type="hidden" name="engine" value={activeFilters.engine} />
          ) : null}
          {activeFilters.target ? (
            <input type="hidden" name="target" value={activeFilters.target} />
          ) : null}
          {activeFilters.scan ? (
            <input type="hidden" name="scan" value={activeFilters.scan} />
          ) : null}

          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-medium text-muted">Date Range</span>
            <div className="flex items-center gap-2">
              <ThemeDateInput
                id="findings-date-from"
                name="from"
                defaultValue={dateFrom}
                aria-label="Start date"
              />
              <span className="shrink-0 text-xs text-muted">~</span>
              <ThemeDateInput
                id="findings-date-to"
                name="to"
                defaultValue={dateTo}
                align="end"
                aria-label="End date"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-medium text-muted">Keyword</span>
            <UrlSearchBar
              initialQuery={keyword}
              layout="inline"
              submitMode="form"
              placeholder="Search URL or snippet…"
              dialogTitle="Advanced findings search"
              dialogDescription="Combine keywords with AND (all must match) or OR (either group). Searches URL and snippet fields."
              isQueryActive={isFindingsSearchQueryActive}
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="shadow-clay inline-flex w-full items-center justify-center rounded-lg bg-gradient-to-r from-accent to-accent-dim px-4 py-2 text-[12px] font-semibold text-white transition-transform hover:scale-[1.02]"
            >
              Apply Filters
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
