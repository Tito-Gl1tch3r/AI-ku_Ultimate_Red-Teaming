"use client";

import { useEffect, useId, useRef, useState } from "react";
import { IconChevronDown } from "@/components/ui-icons";
import {
  CATEGORY_ICON_OPTIONS,
  type CategoryIconKey,
  getCategoryIconComponent,
} from "@/lib/category-icons";

type CategoryIconPickerProps = {
  value: CategoryIconKey;
  onChange: (key: CategoryIconKey) => void;
  disabled?: boolean;
  align?: "start" | "end";
  className?: string;
};

export function CategoryIconPicker({
  value,
  onChange,
  disabled,
  align = "end",
  className = "",
}: CategoryIconPickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  const SelectedIcon = getCategoryIconComponent(value);
  const selectedLabel =
    CATEGORY_ICON_OPTIONS.find((opt) => opt.key === value)?.label ?? "Icon";

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
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

  function select(key: CategoryIconKey) {
    onChange(key);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className={["relative w-full sm:w-[9.5rem] sm:shrink-0", className].join(" ")}>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">Icon</div>
      <button
        type="button"
        disabled={disabled}
        aria-expanded={open}
        aria-controls={listId}
        aria-haspopup="listbox"
        onClick={() => setOpen((v) => !v)}
        className="extension-input-field mt-2 flex h-11 w-full items-center gap-2 rounded-xl px-3 text-left disabled:opacity-50"
      >
        <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-lg border border-line bg-white/[0.04] text-accent">
          <SelectedIcon className="size-3" />
        </span>
        <span className="min-w-0 flex-1 truncate text-[12px] text-cream">{selectedLabel}</span>
        <IconChevronDown
          className={["size-3 shrink-0 text-muted transition-transform", open ? "rotate-180" : ""].join(
            " ",
          )}
        />
      </button>

      {open ? (
        <div
          id={listId}
          role="listbox"
          aria-label="Category icon"
          className={[
            "scx-category-icon-popover",
            align === "end" ? "scx-category-icon-popover--end" : "",
          ].join(" ")}
        >
          <div className="grid grid-cols-6 gap-1 p-2">
            {CATEGORY_ICON_OPTIONS.map((opt) => {
              const Icon = getCategoryIconComponent(opt.key);
              const selected = value === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  title={opt.label}
                  onClick={() => select(opt.key)}
                  className={[
                    "flex size-8 items-center justify-center rounded-lg border transition-colors",
                    selected
                      ? "border-accent/50 bg-accent/15 text-accent"
                      : "border-transparent text-muted hover:border-line hover:bg-[var(--nav-hover-bg)] hover:text-cream",
                  ].join(" ")}
                >
                  <Icon className="size-3.5 shrink-0" />
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
