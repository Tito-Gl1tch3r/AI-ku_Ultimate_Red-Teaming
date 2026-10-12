"use client";

import { useHostnameSightingPanel } from "@/components/hostname-sighting-panel-provider";
import { formatScanDateTime } from "@/lib/scan-format";
import type { ReactNode } from "react";

import { IconChevronRight } from "@/components/ui-icons";

export type TargetSubdomainRowData = {
  id: string;
  hostnameNormalized: string;
  ipCount: number;
  latestIp: string | null;
  lastResolvedAt: Date | null;
  hasUrlBadge?: ReactNode;
};

export function TargetSubdomainRow({
  row,
  targetDomainId,
}: {
  row: TargetSubdomainRowData;
  targetDomainId: string;
}) {
  const { openHostnamePanel } = useHostnameSightingPanel();

  return (
    <button
      type="button"
      onClick={() => openHostnamePanel(targetDomainId, row.hostnameNormalized)}
      className="group flex w-full flex-col gap-1 px-5 py-3 text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:bg-white/5 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent/35 sm:grid sm:grid-cols-12 sm:items-center sm:gap-3"
    >
      <div className="col-span-4 min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <div className="truncate font-mono text-[12px] text-cream group-hover:text-accent">
            {row.hostnameNormalized}
          </div>
          {row.hasUrlBadge}
        </div>
      </div>
      <div className="col-span-2 min-w-0 truncate font-mono text-[11px] text-muted">
        {row.ipCount.toLocaleString()}
      </div>
      <div className="col-span-3 min-w-0 truncate font-mono text-[11px] text-cream">
        {row.latestIp || "—"}
      </div>
      <div className="col-span-2 min-w-0 truncate font-mono text-[11px] text-muted tabular-nums">
        {formatScanDateTime(row.lastResolvedAt)}
      </div>
      <div className="col-span-1 flex items-center justify-end text-muted md:justify-center">
        <IconChevronRight className="size-4 shrink-0 opacity-60 group-hover:text-accent group-hover:opacity-100 transition-all" aria-hidden />
      </div>
    </button>
  );
}
