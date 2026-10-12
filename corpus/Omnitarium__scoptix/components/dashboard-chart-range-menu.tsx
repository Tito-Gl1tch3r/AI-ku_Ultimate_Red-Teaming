"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { ACTIVITY_RANGES, type ActivityRangeKey } from "@/lib/dashboard-stats";

type RangeParam = "findingsRange";

export function DashboardChartRangeMenu({
  param,
  current,
  siblingParams,
}: {
  param: RangeParam;
  current: ActivityRangeKey;
  siblingParams: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const currentLabel = ACTIVITY_RANGES.find((r) => r.key === current)?.label ?? "14 days";

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function hrefFor(key: ActivityRangeKey) {
    const p = new URLSearchParams(siblingParams);
    p.set(param, key);
    const q = p.toString();
    return q ? `/?${q}` : "/";
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 text-[12px] font-medium text-muted transition-colors hover:text-cream"
      >
        Last {currentLabel.toLowerCase()}
        <svg
          className={["size-4 transition-transform", open ? "rotate-180" : ""].join(" ")}
          aria-hidden
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="dashboard-range-menu absolute bottom-full left-0 z-20 mb-2 min-w-[10.5rem] overflow-hidden rounded-xl border border-line py-1 shadow-lift"
        >
          {ACTIVITY_RANGES.map((range) => {
            const selected = range.key === current;
            return (
              <li key={range.key} role="option" aria-selected={selected}>
                <Link
                  href={hrefFor(range.key)}
                  scroll={false}
                  onClick={() => setOpen(false)}
                  className={[
                    "block px-3 py-2 text-[12px] transition-colors",
                    selected
                      ? "bg-accent/12 font-medium text-cream"
                      : "text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                  ].join(" ")}
                >
                  Last {range.label.toLowerCase()}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
