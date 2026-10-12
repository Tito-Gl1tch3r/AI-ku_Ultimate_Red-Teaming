"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiUrl } from "@/lib/api-url";

export function NewTargetForm() {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(apiUrl("/api/targets"), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ domain }),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) throw new Error(j?.error ?? `HTTP ${r.status}`);
      setDomain("");
      router.refresh();
      router.push(`/targets/${j.target.id}`);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="text-[11px] font-medium uppercase tracking-wider text-muted">Domain</label>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="example.com"
          className="ui-input-field mt-2 w-full rounded-xl border border-line px-4 py-3 font-mono text-[12px] text-cream outline-none placeholder:text-muted focus:ring-2 focus:ring-accent/30"
        />
      </div>
      {err ? <div className="text-[12px] text-muted">{err}</div> : null}
      <button
        type="submit"
        disabled={busy || domain.trim().length < 3}
        className="shadow-clay w-full rounded-xl bg-gradient-to-r from-accent to-accent-dim px-4 py-3 text-[13px] font-semibold text-void disabled:opacity-60"
      >
        {busy ? "Saving…" : "Save target"}
      </button>
    </form>
  );
}
