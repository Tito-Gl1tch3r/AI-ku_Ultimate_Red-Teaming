import Link from "next/link";
import type { ReactNode } from "react";
import { PageSizeSelect } from "@/components/page-size-select";
import { apiUrl } from "@/lib/api-url";

export const PAGE_SIZE_OPTIONS = [10, 15, 25, 50, 75, 100] as const;
export const DEFAULT_PAGE_SIZE = 10;

export function normalizePageSize(
  v: string | null | undefined,
  fallback: number = DEFAULT_PAGE_SIZE,
): number {
  const n = Number(v);
  if ((PAGE_SIZE_OPTIONS as readonly number[]).includes(n)) return n;
  if ((PAGE_SIZE_OPTIONS as readonly number[]).includes(fallback)) return fallback;
  return DEFAULT_PAGE_SIZE;
}

const pageNumBase =
  "inline-flex min-w-[1.75rem] items-center justify-center rounded-md px-1 py-1 font-mono text-[11px] transition-colors";
const pageNumActive = "bg-accent/12 text-cream ring-1 ring-accent/25";
const pageNumIdle = "text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream";

function buildHref(
  basePath: string,
  fixedParams: Record<string, string>,
  pageParam: string,
  page: number,
  perPage: number,
): string {
  const p = new URLSearchParams(fixedParams);
  if (page > 1) p.set(pageParam, String(page));
  else p.delete(pageParam);
  p.set("perPage", String(perPage));
  return `${basePath}?${p.toString()}`;
}

function getVisiblePages(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 0) return [];
  if (total <= 9) return Array.from({ length: total }, (_, i) => i + 1);

  const siblingCount = 2;
  const pages: (number | "ellipsis")[] = [1];
  const left = Math.max(2, current - siblingCount);
  const right = Math.min(total - 1, current + siblingCount);

  if (left > 2) pages.push("ellipsis");
  for (let i = left; i <= right; i++) pages.push(i);
  if (right < total - 1) pages.push("ellipsis");
  pages.push(total);

  return pages;
}

function IconChevronsLeft({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M11 17l-5-5 5-5M18 17l-5-5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconChevronLeft({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconChevronsRight({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M13 17l5-5-5-5M6 17l5-5-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NavControl({
  href,
  disabled,
  label,
  children,
}: {
  href: string;
  disabled?: boolean;
  label: string;
  children: ReactNode;
}) {
  if (disabled) {
    return (
      <span
        className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-muted/30"
        aria-disabled="true"
        title={label}
      >
        {children}
      </span>
    );
  }

  return (
    <Link
      href={href}
      aria-label={label}
      title={label}
      className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
    >
      {children}
    </Link>
  );
}

export type TablePaginationProps = {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  perPage: number;
  basePath: string;
  fixedParams: Record<string, string>;
  pageParam?: string;
};

export function TablePagination({
  currentPage,
  totalPages,
  totalItems,
  perPage,
  basePath,
  fixedParams,
  pageParam = "page",
}: TablePaginationProps) {
  if (totalItems === 0) return null;

  const visiblePages = getVisiblePages(currentPage, totalPages);
  const hrefFor = (page: number) => buildHref(basePath, fixedParams, pageParam, page, perPage);

  const pageSizeOptions = PAGE_SIZE_OPTIONS.map((size) => ({
    size,
    href: buildHref(basePath, fixedParams, pageParam, 1, size),
  }));

  const atStart = currentPage <= 1;
  const atEnd = currentPage >= totalPages;

  return (
    <div className="grid grid-cols-1 items-center gap-3 border-t border-line px-5 py-3 sm:grid-cols-[1fr_auto_1fr]">
      <div className="justify-self-start text-[11px] text-muted">
        Page <span className="font-mono text-cream">{currentPage.toLocaleString()}</span> of{" "}
        <span className="font-mono text-cream">{totalPages.toLocaleString()}</span>
      </div>

      <nav
        className="flex items-center justify-center gap-0.5 justify-self-center overflow-x-auto"
        aria-label="Pagination"
      >
        <NavControl href={hrefFor(1)} disabled={atStart} label="First page">
          <IconChevronsLeft />
        </NavControl>
        <NavControl href={hrefFor(currentPage - 1)} disabled={atStart} label="Previous page">
          <IconChevronLeft />
        </NavControl>

        <span className="mx-1 hidden h-4 w-px shrink-0 bg-line/80 sm:block" aria-hidden />

        {visiblePages.map((pg, idx) =>
          pg === "ellipsis" ? (
            <span key={`ellipsis-${idx}`} className="px-1 font-mono text-[11px] text-muted/70">
              …
            </span>
          ) : (
            <Link
              key={pg}
              href={hrefFor(pg)}
              aria-current={pg === currentPage ? "page" : undefined}
              className={[pageNumBase, pg === currentPage ? pageNumActive : pageNumIdle].join(" ")}
            >
              {pg.toLocaleString()}
            </Link>
          ),
        )}

        <span className="mx-1 hidden h-4 w-px shrink-0 bg-line/80 sm:block" aria-hidden />

        <NavControl href={hrefFor(currentPage + 1)} disabled={atEnd} label="Next page">
          <IconChevronRight />
        </NavControl>
        <NavControl href={hrefFor(totalPages)} disabled={atEnd} label="Last page">
          <IconChevronsRight />
        </NavControl>
      </nav>

      <div className="flex shrink-0 items-center justify-self-end gap-3 overflow-x-auto">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Rows</span>
          <PageSizeSelect value={perPage} options={pageSizeOptions} />
        </div>

        <form className="flex items-center gap-1.5" action={apiUrl(basePath)} method="get">
          {Object.entries(fixedParams).map(([key, value]) => (
            <input key={key} type="hidden" name={key} value={value} />
          ))}
          <input type="hidden" name="perPage" value={String(perPage)} />
          <label
            htmlFor={`${pageParam}-jump`}
            className="text-[10px] font-semibold uppercase tracking-wider text-muted"
          >
            Go to
          </label>
          <input
            id={`${pageParam}-jump`}
            name={pageParam}
            type="number"
            min={1}
            max={totalPages}
            defaultValue={currentPage}
            className="ui-input-field w-14 rounded-lg border border-line px-2 py-1.5 text-center font-mono text-[11px] text-cream outline-none focus:ring-1 focus:ring-accent/30"
          />
          <button
            type="submit"
            className="rounded-md px-2 py-1 text-[11px] font-medium text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            Go
          </button>
        </form>
      </div>
    </div>
  );
}
