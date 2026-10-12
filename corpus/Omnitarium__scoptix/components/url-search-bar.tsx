"use client";

import { useRouter } from "next/navigation";
import { forwardRef, useCallback, useEffect, useId, useImperativeHandle, useRef, useState } from "react";
import {
  buildAdvancedSearchString,
  isStructuredSearchQuery,
  isUrlSearchQueryActive,
  parseQueryToBuilderRows,
  type SearchBuilderRow,
} from "@/lib/url-search-query";
import { buildUrlsTabHref, type UrlTabHrefContext, type UrlTabFilterParams } from "@/lib/url-tab-params";

function IconSearch({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.75" />
      <path d="M20 20L16 16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function IconSliders({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M4 12h10M4 17h6"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <circle cx="17" cy="7" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="11" cy="12" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="17" r="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function IconX({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function IconPlus({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function IconTrash({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M5 7h14M9 7V5h6v2M8 7l1 12h6l1-12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function newRowId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export type UrlSearchBarHandle = {
  openBuilder: () => void;
};

type UrlSearchBarProps = {
  initialQuery: string;
  layout?: "default" | "inline";
  submitMode?: "navigate" | "form";
  placeholder?: string;
  dialogTitle?: string;
  dialogDescription?: string;
  isQueryActive?: (query: string) => boolean;
} & (
  | {
      submitMode: "form";
      hrefContext?: never;
      preserve?: never;
      buildHref?: never;
    }
  | {
      submitMode?: "navigate";
      hrefContext: UrlTabHrefContext;
      preserve: UrlTabFilterParams;
      buildHref?: never;
    }
  | {
      submitMode?: "navigate";
      buildHref: (query: string) => string;
      hrefContext?: never;
      preserve?: never;
    }
);

export const UrlSearchBar = forwardRef<UrlSearchBarHandle, UrlSearchBarProps>(function UrlSearchBar(
  {
    hrefContext,
    preserve,
    buildHref,
    initialQuery,
    layout = "default",
    submitMode = "navigate",
    placeholder = "Search URLs…",
    dialogTitle = "Advanced URL search",
    dialogDescription = "Combine keywords with AND (all must match) or OR (either group). Terms are quoted automatically.",
    isQueryActive = isUrlSearchQueryActive,
  },
  ref,
) {
  const router = useRouter();
  const dialogTitleId = useId();
  const [query, setQuery] = useState(initialQuery);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [advRows, setAdvRows] = useState<SearchBuilderRow[]>(() => parseQueryToBuilderRows(initialQuery));
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    setQuery(initialQuery);
    setAdvRows(parseQueryToBuilderRows(initialQuery));
  }, [initialQuery]);

  const navigate = useCallback(
    (q: string) => {
      if (buildHref) {
        router.push(buildHref(q));
        return;
      }
      router.push(
        buildUrlsTabHref(hrefContext!, {
          ...preserve!,
          q,
          page: 1,
        }),
      );
    },
    [router, hrefContext, preserve, buildHref],
  );

  function openBuilder() {
    setAdvRows(parseQueryToBuilderRows(query));
    setBuilderOpen(true);
    dialogRef.current?.showModal();
  }

  useImperativeHandle(ref, () => ({
    openBuilder,
  }));

  function closeBuilder() {
    setBuilderOpen(false);
    dialogRef.current?.close();
  }

  function handleSimpleSubmit(e: React.FormEvent) {
    e.preventDefault();
    navigate(query);
  }

  function handleApplyAdvanced() {
    const built = buildAdvancedSearchString(advRows);
    setQuery(built);
    closeBuilder();
    if (submitMode === "navigate") navigate(built);
  }

  function handleClear() {
    setQuery("");
    setAdvRows([{ id: "1", term: "", operator: "AND" }]);
    if (submitMode === "navigate") navigate("");
  }

  function handleResetBuilder() {
    setAdvRows([{ id: newRowId(), term: "", operator: "AND" }]);
  }

  const embedded = submitMode === "form";
  const hasActiveFilter = embedded
    ? query.trim().length > 0
    : initialQuery.trim().length > 0;
  const hintQuery = embedded ? query : initialQuery;
  const filterApplied = isQueryActive(hintQuery);
  const showTooShortHint =
    hintQuery.trim().length > 0 && !filterApplied && !isStructuredSearchQuery(hintQuery);

  const inline = layout === "inline";

  const controls = (
    <>
      <div className={inline || embedded ? "relative min-w-0 flex-1" : "relative"}>
        <IconSearch className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
        <input
          name={embedded ? "q" : undefined}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className={[
            "ui-input-field rounded-lg border border-line pl-8 pr-9 text-[12px] text-cream outline-none placeholder:text-muted focus:ring-1 focus:ring-accent/30",
            inline || embedded ? "h-9 w-full min-w-0 py-0" : "w-[min(100%,280px)] py-2",
          ].join(" ")}
        />
        <button
          type="button"
          onClick={openBuilder}
          title="Advanced search builder"
          aria-label="Open advanced search builder"
          aria-expanded={builderOpen}
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-accent"
        >
          <IconSliders className="h-3.5 w-3.5" />
        </button>
      </div>
      {!embedded ? (
        <button
          type="submit"
          className={[
            "inline-flex shrink-0 items-center justify-center rounded-lg border border-line px-3 text-[12px] font-medium text-cream transition-colors hover:bg-[var(--nav-hover-bg)]",
            inline ? "h-9 py-0" : "py-2",
          ].join(" ")}
        >
          Search
        </button>
      ) : null}
      {hasActiveFilter ? (
        <button
          type="button"
          onClick={handleClear}
          title="Clear search"
          aria-label="Clear search"
          className={[
            "inline-flex shrink-0 items-center justify-center rounded-lg border border-line text-muted transition-colors hover:border-warn/40 hover:bg-warn/10 hover:text-warn",
            inline || embedded ? "h-9 w-9 p-0" : "p-2",
          ].join(" ")}
        >
          <IconX />
        </button>
      ) : null}
    </>
  );

  const controlsClassName = inline || embedded
    ? "flex w-full min-w-0 flex-wrap items-center gap-2"
    : "flex flex-wrap items-center justify-end gap-2";

  return (
    <div
      className={
        inline || embedded
          ? "flex min-w-0 flex-1 flex-col gap-2"
          : "flex flex-col items-end gap-2"
      }
    >
      {embedded ? (
        <div className={controlsClassName}>{controls}</div>
      ) : (
        <form onSubmit={handleSimpleSubmit} className={controlsClassName}>
          {controls}
        </form>
      )}

      {showTooShortHint && (
        <p
          className={[
            "text-[10px] text-warn",
            inline ? "w-full" : "max-w-[min(100%,360px)] text-right",
          ].join(" ")}
        >
          Enter at least 3 characters for a simple search, or use Advanced for shorter terms.
        </p>
      )}

      <dialog
        ref={dialogRef}
        onClose={() => setBuilderOpen(false)}
        className="url-search-dialog w-[min(100%,440px)] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-[var(--glass-panel-bg)] p-0 text-cream shadow-glass backdrop:bg-void/70"
        aria-labelledby={dialogTitleId}
      >
        <div className="border-b border-line px-5 py-4">
          <h2 id={dialogTitleId} className="flex items-center gap-2 text-[14px] font-semibold text-cream">
            <IconSliders className="text-accent" />
            {dialogTitle}
          </h2>
          <p className="mt-1 text-[11px] text-muted">
            {dialogDescription}
          </p>
        </div>

        <div className="space-y-3 px-5 py-4">
          {advRows.map((row, idx) => (
            <div key={row.id} className="flex items-center gap-2">
              {idx > 0 ? (
                <select
                  value={row.operator}
                  onChange={(e) => {
                    const next = [...advRows];
                    next[idx] = { ...next[idx], operator: e.target.value as "AND" | "OR" };
                    setAdvRows(next);
                  }}
                  aria-label={`Operator before keyword ${idx + 1}`}
                  className="ui-input-field w-[76px] shrink-0 rounded-lg border border-line px-2 py-2 text-[11px] font-medium text-cream outline-none focus:ring-1 focus:ring-accent/30"
                >
                  <option value="AND">AND</option>
                  <option value="OR">OR</option>
                </select>
              ) : (
                <span className="w-[76px] shrink-0 text-center text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Match
                </span>
              )}
              <input
                value={row.term}
                onChange={(e) => {
                  const next = [...advRows];
                  next[idx] = { ...next[idx], term: e.target.value };
                  setAdvRows(next);
                }}
                placeholder={idx === 0 ? "e.g. admin" : "Keyword…"}
                className="ui-input-field min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-[12px] text-cream outline-none placeholder:text-muted focus:ring-1 focus:ring-accent/30"
              />
              {idx > 0 && (
                <button
                  type="button"
                  onClick={() => setAdvRows(advRows.filter((r) => r.id !== row.id))}
                  aria-label={`Remove keyword ${idx + 1}`}
                  className="shrink-0 rounded-lg p-2 text-muted transition-colors hover:bg-warn/10 hover:text-warn"
                >
                  <IconTrash />
                </button>
              )}
            </div>
          ))}

          <button
            type="button"
            onClick={() =>
              setAdvRows([...advRows, { id: newRowId(), term: "", operator: "AND" }])
            }
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-line py-2 text-[11px] font-medium text-accent/90 transition-colors hover:border-accent/40 hover:bg-accent/5 hover:text-accent"
          >
            <IconPlus />
            Add keyword
          </button>
        </div>

        <div className="flex items-center gap-2 border-t border-line px-5 py-4">
          <button
            type="button"
            onClick={handleResetBuilder}
            className="mr-auto text-[11px] text-muted transition-colors hover:text-cream"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={closeBuilder}
            className="rounded-lg border border-line px-3 py-2 text-[12px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleApplyAdvanced}
            className="rounded-lg bg-accent/15 px-4 py-2 text-[12px] font-semibold text-cream ring-1 ring-accent/25 transition-colors hover:bg-accent/25"
          >
            Apply search
          </button>
        </div>
      </dialog>
    </div>
  );
});
