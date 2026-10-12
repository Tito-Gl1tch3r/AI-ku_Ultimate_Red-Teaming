"use client";

import { useEffect, useState } from "react";
import { TopBarControls } from "@/components/top-bar-controls";
import { apiUrl } from "@/lib/api-url";

type KeyStatus = {
  total: number;
  exhausted: number;
};

export function TopBar({ breadcrumb }: { breadcrumb: string }) {
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null);

  // Poll API key status every 30s
  useEffect(() => {
    async function fetchKeys() {
      try {
        const r = await fetch(apiUrl("/api/settings/api-keys"), { cache: "no-store" });
        if (!r.ok) return;
        const j = await r.json();
        const keys = (j.keys ?? []) as { isDisabled: boolean }[];
        const total = keys.length;
        const exhausted = keys.filter((k) => k.isDisabled).length;
        setKeyStatus({ total, exhausted });
      } catch {
        /* ignore */
      }
    }
    void fetchKeys();
    const iv = setInterval(fetchKeys, 30_000);
    return () => clearInterval(iv);
  }, []);

  return (
    <header className="glass-panel shrink-0 border-b border-line px-6 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full border border-line bg-black/[0.04] px-2.5 py-1 text-[11px] text-muted dark:bg-white/[0.04]">
            <span className="live-dot size-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
            Live pipeline
          </span>
          <span className="truncate font-mono text-[12px] text-muted" title={breadcrumb}>
            {breadcrumb}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          {/* ── API Key Exhaustion Alert ── */}
          {keyStatus && keyStatus.exhausted > 0 && (
            <span className="flex items-center gap-1.5 rounded-full border border-warn/30 bg-warn/8 px-2.5 py-1 text-[10px] font-semibold text-warn">
              ⚠ {keyStatus.exhausted.toLocaleString()}/{keyStatus.total.toLocaleString()} keys exhausted
            </span>
          )}

          <TopBarControls />
        </div>
      </div>
    </header>
  );
}
