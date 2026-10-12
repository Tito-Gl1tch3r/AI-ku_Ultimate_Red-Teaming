"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { IconChevronDown } from "@/components/ui-icons";

export type FindingsFilterOption = {
  label: string;
  href: string;
  selected?: boolean;
};

const DROPDOWN_PREVIEW_LIMIT = 7;

function filterOptions(options: FindingsFilterOption[], query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return options;
  return options.filter((opt) => opt.label.toLowerCase().includes(q));
}

function OptionLink({
  opt,
  onSelect,
}: {
  opt: FindingsFilterOption;
  onSelect: () => void;
}) {
  return (
    <Link
      href={opt.href}
      scroll={false}
      onClick={onSelect}
      className={[
        "block px-3 py-1.5 text-xs transition-colors",
        opt.selected
          ? "bg-accent/12 font-medium text-cream"
          : "text-muted hover:bg-[var(--nav-hover-bg)] hover:text-cream",
      ].join(" ")}
    >
      {opt.label}
    </Link>
  );
}

export function FindingsFilterDropdown({
  label,
  placeholder,
  options,
  disabled,
}: {
  label: string;
  placeholder: string;
  options: FindingsFilterOption[];
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [modalQuery, setModalQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDialogElement>(null);
  const listId = useId();
  const modalTitleId = useId();

  const selected = options.find((opt) => opt.selected);
  const filtered = filterOptions(options, query);
  const preview = filtered.slice(0, DROPDOWN_PREVIEW_LIMIT);
  const showViewMore = options.length > DROPDOWN_PREVIEW_LIMIT;
  const modalFiltered = filterOptions(options, modalQuery);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!modalOpen) return;
    const dialog = modalRef.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, [modalOpen]);

  function openDropdown() {
    if (disabled) return;
    setOpen(true);
    setQuery("");
    requestAnimationFrame(() => inputRef.current?.select());
  }

  function closeDropdown() {
    setOpen(false);
    setQuery("");
  }

  function openModal() {
    setModalQuery(query);
    closeDropdown();
    setModalOpen(true);
  }

  function closeModal() {
    modalRef.current?.close();
    setModalOpen(false);
    setModalQuery("");
  }

  function onOptionSelect() {
    closeDropdown();
    closeModal();
  }

  const inputValue = open ? query : (selected?.label ?? "");

  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="text-[11px] font-medium text-muted">{label}</span>
        <div ref={rootRef} className="relative">
          <div
            className={[
              "flex items-center rounded-md border border-line bg-lift transition-colors",
              disabled ? "cursor-not-allowed opacity-60" : "hover:border-accent/35",
              open ? "border-accent/35 ring-1 ring-accent/20" : "",
            ].join(" ")}
          >
            <input
              ref={inputRef}
              type="text"
              role="combobox"
              disabled={disabled}
              value={inputValue}
              placeholder={placeholder}
              aria-expanded={open}
              aria-haspopup="listbox"
              aria-controls={listId}
              onFocus={openDropdown}
              onClick={openDropdown}
              onChange={(e) => {
                setQuery(e.target.value);
                if (!open) setOpen(true);
              }}
              className="min-w-0 flex-1 bg-transparent px-3 py-1.5 text-xs text-cream outline-none placeholder:text-muted disabled:cursor-not-allowed"
            />
            <button
              type="button"
              disabled={disabled}
              tabIndex={-1}
              onClick={() => (open ? closeDropdown() : openDropdown())}
              className="shrink-0 px-2 py-1.5 text-muted"
              aria-label={`Toggle ${label} options`}
            >
              <IconChevronDown
                className={[
                  "size-4 transition-transform",
                  open ? "rotate-180" : "",
                ].join(" ")}
              />
            </button>
          </div>

          {open && !disabled ? (
            <ul
              id={listId}
              role="listbox"
              className="dashboard-range-menu absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-lg border border-line py-0.5 shadow-lift"
            >
              {preview.length === 0 ? (
                <li className="px-3 py-2 text-xs text-muted">No matches.</li>
              ) : (
                preview.map((opt) => (
                  <li key={`${opt.label}-${opt.href}`} role="option" aria-selected={opt.selected}>
                    <OptionLink opt={opt} onSelect={onOptionSelect} />
                  </li>
                ))
              )}
              {showViewMore ? (
                <li className="border-t border-line/60">
                  <button
                    type="button"
                    onClick={openModal}
                    className="block w-full px-3 py-2 text-left text-xs font-medium text-accent transition-colors hover:bg-[var(--nav-hover-bg)]"
                  >
                    View more…
                  </button>
                </li>
              ) : null}
            </ul>
          ) : null}
        </div>
      </div>

      {modalOpen ? (
        <dialog
          ref={modalRef}
          onClose={() => {
            setModalOpen(false);
            setModalQuery("");
          }}
          className="url-search-dialog w-[min(100%,420px)] max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-[var(--glass-panel-bg)] p-0 text-cream shadow-glass backdrop:bg-void/70"
          aria-labelledby={modalTitleId}
        >
          <div className="border-b border-line px-4 py-3">
            <h2 id={modalTitleId} className="text-[13px] font-semibold text-cream">
              {label}
            </h2>
            <input
              type="text"
              value={modalQuery}
              onChange={(e) => setModalQuery(e.target.value)}
              placeholder={`Search ${label.toLowerCase()}…`}
              autoFocus
              className="ui-input-field mt-2 w-full rounded-lg border border-line px-3 py-2 text-[12px] text-cream outline-none placeholder:text-muted focus:ring-1 focus:ring-accent/30"
            />
          </div>

          <ul className="max-h-64 overflow-y-auto py-1">
            {modalFiltered.length === 0 ? (
              <li className="px-4 py-3 text-[12px] text-muted">No matches.</li>
            ) : (
              modalFiltered.map((opt) => (
                <li key={`modal-${opt.label}-${opt.href}`}>
                  <OptionLink opt={opt} onSelect={onOptionSelect} />
                </li>
              ))
            )}
          </ul>

          <div className="flex justify-end border-t border-line px-4 py-3">
            <button
              type="button"
              onClick={closeModal}
              className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
            >
              Close
            </button>
          </div>
        </dialog>
      ) : null}
    </>
  );
}
