"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { IconCalendar, IconChevronDown } from "@/components/ui-icons";
import { DASHBOARD_PERIODS, type DashboardPeriodKey } from "@/lib/dashboard-overview";

export function DashboardPeriodMenu({
  current,
  siblingParams,
}: {
  current: DashboardPeriodKey;
  siblingParams: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const currentLabel = DASHBOARD_PERIODS.find((p) => p.key === current)?.label ?? "Last 7 days";

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

  function hrefFor(key: DashboardPeriodKey) {
    const p = new URLSearchParams(siblingParams);
    p.set("period", key);
    const q = p.toString();
    return q ? `/?${q}` : "/";
  }

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        className="dashboard-period-trigger inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-[11px] font-medium text-cream shadow-sm transition-colors hover:bg-[var(--nav-hover-bg)]"
      >
        <IconCalendar className="size-3.5 text-muted" />
        {currentLabel}
        <IconChevronDown
          className={["size-3.5 text-muted transition-transform", open ? "rotate-180" : ""].join(" ")}
        />
      </button>

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="dashboard-range-menu absolute right-0 top-full z-20 mt-1.5 min-w-[9.5rem] overflow-hidden rounded-lg border border-line py-0.5 shadow-lift"
        >
          {DASHBOARD_PERIODS.map((period) => {
            const selected = period.key === current;
            return (
              <li key={period.key} role="option" aria-selected={selected}>
                <Link
                  href={hrefFor(period.key)}
                  scroll={false}
                  onClick={() => setOpen(false)}
                  className={[
                    "block px-2.5 py-1.5 text-[11px] transition-colors",
                    selected
                      ? "bg-accent/12 font-medium text-cream"
                      : "text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                  ].join(" ")}
                >
                  {period.label}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
