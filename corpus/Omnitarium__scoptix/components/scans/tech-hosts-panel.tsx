"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { IconArrowUpRight, IconX } from "@/components/ui-icons";
import { TechIcon } from "@/components/scans/tech-icon";
import type { ScanTechRow } from "@/components/scans/scan-tech-tab";

const HOSTS_PER_PAGE = 10;

function hostHref(hostname: string) {
  const h = hostname.trim();
  if (!h) return "#";
  if (/^https?:\/\//i.test(h)) return h;
  return `https://${h}`;
}

export function TechHostsPanel({
  tech,
  onClose,
}: {
  tech: ScanTechRow;
  onClose: () => void;
}) {
  const [mounted, setMounted] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [tech]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  if (!mounted) return null;

  const totalPages = Math.max(1, Math.ceil(tech.hosts.length / HOSTS_PER_PAGE));
  const safePage = Math.min(page, totalPages);
  const pagedHosts = tech.hosts.slice(
    (safePage - 1) * HOSTS_PER_PAGE,
    safePage * HOSTS_PER_PAGE,
  );

  return createPortal(
    <>
      <div className="fixed inset-0 z-[90] bg-void/50" aria-hidden onClick={onClose} />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="tech-panel-title"
        className="glass-panel fixed inset-y-0 right-0 z-[100] flex w-full max-w-[560px] flex-col rounded-none border-l border-line shadow-lift"
      >
        {/* Header */}
        <div className="shrink-0 border-b border-line px-5 pb-4 pt-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-[12px] font-medium text-muted">Technology</h2>
              <div className="mt-1.5 flex min-w-0 items-center gap-2">
                <TechIcon name={tech.name} iconName={tech.iconName} size={22} />
                {tech.website ? (
                  <a
                    href={tech.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    id="tech-panel-title"
                    className="min-w-0 truncate text-[18px] font-bold leading-tight tracking-tight text-cream hover:text-accent"
                  >
                    {tech.name}
                  </a>
                ) : (
                  <p
                    id="tech-panel-title"
                    className="min-w-0 truncate text-[18px] font-bold leading-tight tracking-tight text-cream"
                  >
                    {tech.name}
                  </p>
                )}
              </div>
              {tech.categories.length > 0 ? (
                <p className="mt-2 text-[11px] leading-relaxed text-muted">
                  {tech.categories.join(" · ")}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close panel"
              className="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
            >
              <IconX className="size-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {/* Summary */}
          <div className="mb-6">
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted">Summary</h3>
            <div className="mt-3 grid grid-cols-2">
              <div className="min-w-0 pr-3 text-left">
                <div className="text-[10px] font-medium text-muted">Hosts</div>
                <div className="mt-1 text-[11px] font-medium leading-snug text-cream">
                  {tech.hostCount.toLocaleString()}
                </div>
              </div>
              <div className="min-w-0 border-l border-line pl-3 text-left">
                <div className="text-[10px] font-medium text-muted">Versions detected</div>
                <div className="mt-1 text-[11px] font-medium leading-snug text-cream">
                  {tech.versions.length > 0 ? tech.versions.join(", ") : "—"}
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6 border-t border-line" aria-hidden />

          {/* Hosts table — mirrors the "Historical IP Addresses" table style */}
          <div className="mb-3 text-left">
            <h3 className="text-[13px] font-semibold text-cream">Hosts running {tech.name}</h3>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              Subdomains where this technology was fingerprinted in this scan.
            </p>
          </div>

          {tech.hosts.length === 0 ? (
            <p className="py-3 text-left text-[12px] text-muted">No hosts.</p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-line text-left">
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,0.7fr)_auto] items-center gap-x-2 border-b border-line bg-[var(--table-header-bg)] px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-wider text-muted">
                <div>Host</div>
                <div>Version</div>
                <div />
              </div>

              <div className="divide-y divide-line">
                {pagedHosts.map((h) => (
                  <div
                    key={h.hostnameNormalized}
                    className="group grid grid-cols-[minmax(0,1fr)_minmax(0,0.7fr)_auto] items-center gap-x-2 px-2 py-1 text-left"
                  >
                    <div
                      className="min-w-0 truncate font-mono text-[10px] text-cream"
                      title={h.hostnameNormalized}
                    >
                      {h.hostnameNormalized}
                    </div>
                    <div className="min-w-0 truncate font-mono text-[10px] text-muted tabular-nums">
                      {h.version ?? "—"}
                    </div>
                    <a
                      href={hostHref(h.hostnameNormalized)}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Visit ${h.hostnameNormalized}`}
                      title={`Visit ${h.hostnameNormalized}`}
                      className="flex size-5 items-center justify-center rounded text-muted transition-colors hover:bg-[var(--nav-hover-bg)] hover:text-cream"
                    >
                      <IconArrowUpRight className="size-3" />
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          <TechPanelSimplePagination
            page={safePage}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
      </aside>
    </>,
    document.body,
  );
}

function TechPanelSimplePagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="mt-1 flex items-center justify-between border-t border-line px-2 py-1 text-[10px] text-muted">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="rounded px-1.5 py-0.5 font-medium transition-colors hover:text-cream disabled:opacity-30"
      >
        Prev
      </button>
      <span className="font-mono tabular-nums">
        {page} / {totalPages}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="rounded px-1.5 py-0.5 font-medium transition-colors hover:text-cream disabled:opacity-30"
      >
        Next
      </button>
    </div>
  );
}
