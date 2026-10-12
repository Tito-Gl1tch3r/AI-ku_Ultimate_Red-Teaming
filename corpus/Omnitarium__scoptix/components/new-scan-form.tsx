"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiUrl } from "@/lib/api-url";

/**
 * Simplified scan form: just type a domain/subdomain, toggle deep scan, click Start.
 * Auto-creates target, auto-detects engines, auto-detects domain vs subdomain.
 */
export function NewScanForm({ autoFocus = true }: { autoFocus?: boolean }) {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [deepScan, setDeepScan] = useState(false);
  const [skipListEnabled, setSkipListEnabled] = useState(false);
  const [skipListText, setSkipListText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = domain.trim();
    if (!trimmed || trimmed.length < 3) {
      setErr("Enter a valid domain or subdomain");
      return;
    }

    setBusy(true);
    setErr(null);
    try {
      const deepScanCategorySlugs = deepScan ? ["js"] : [];
      const skipList = skipListEnabled
        ? [...new Set(
            skipListText
              .split("\n")
              .map((l) => l.trim().toLowerCase())
              .filter(Boolean),
          )]
        : [];
      const r = await fetch(apiUrl("/api/quick-scan"), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          domain: trimmed,
          deepScan,
          deepScanCategorySlugs,
          skipList,
        }),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) throw new Error(j?.error ?? `HTTP ${r.status}`);
      router.push(`/scans/${j.scan.id}`);
      router.refresh();
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="target.com or sub.target.com"
          className="ui-input-field w-full rounded-xl border border-line px-4 py-3.5 font-mono text-[14px] text-cream placeholder:text-muted outline-none focus:ring-2 focus:ring-accent/30"
          autoFocus={autoFocus}
          spellCheck={false}
          autoComplete="off"
        />
        <div className="mt-2 text-[11px] text-muted">
          Domain → scans all subdomains. Subdomain → focused scan only.
        </div>
      </div>

      <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-line px-4 py-3 transition-colors hover:bg-[var(--nav-hover-bg)]">
        <input
          type="checkbox"
          checked={deepScan}
          onChange={(e) => setDeepScan(e.target.checked)}
          className="accent-accent"
        />
        <div>
          <div className="text-[13px] text-cream">Deep Scan</div>
          <div className="text-[11px] text-muted">
            Download JS files &amp; scan content for secrets (slower, uses more bandwidth)
          </div>
        </div>
      </label>

      <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-line px-4 py-3 transition-colors hover:bg-[var(--nav-hover-bg)]">
        <input
          type="checkbox"
          checked={skipListEnabled}
          onChange={(e) => setSkipListEnabled(e.target.checked)}
          className="accent-accent"
        />
        <div>
          <div className="text-[13px] text-cream">Skip List</div>
          <div className="text-[11px] text-muted">
            Exclude specific subdomains from recursive discovery. Only applies to root domain scans.
          </div>
        </div>
      </label>

      {skipListEnabled ? (
        <div>
          <textarea
            value={skipListText}
            onChange={(e) => setSkipListText(e.target.value)}
            placeholder={"x.example.com\nz.example.com"}
            rows={4}
            spellCheck={false}
            className="ui-input-field w-full rounded-xl border border-line px-4 py-3 font-mono text-[13px] text-cream placeholder:text-muted outline-none focus:ring-2 focus:ring-accent/30 resize-y"
          />
          <div className="mt-1.5 text-[11px] text-muted">
            One hostname per line.
          </div>
        </div>
      ) : null}

      {err ? (
        <div className="rounded-xl border border-warn/30 bg-warn/5 px-4 py-3 text-[12px] text-warn">
          {err}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={busy || domain.trim().length < 3}
        className="shadow-clay w-full rounded-xl bg-gradient-to-r from-accent to-accent-dim px-4 py-3.5 text-[14px] font-semibold text-void transition-opacity disabled:opacity-60"
      >
        {busy ? "Starting scan…" : "Start Scan"}
      </button>
    </form>
  );
}
