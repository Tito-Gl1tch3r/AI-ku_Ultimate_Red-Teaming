"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { IconSearch, IconX } from "@/components/ui-icons";

type GlobalSearchBarProps = {
  initialQuery: string;
  placeholder?: string;
  basePath: string;
};

export function GlobalSearchBar({ initialQuery, placeholder = "Search...", basePath }: GlobalSearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const p = new URLSearchParams();
    if (query.trim()) p.set("q", query.trim());
    router.push(`${basePath}?${p.toString()}`);
  }

  function handleClear() {
    setQuery("");
    router.push(basePath);
  }

  return (
    <form onSubmit={handleSearch} className="flex items-center gap-2">
      <div className="relative">
        <IconSearch className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted size-3.5" />
        <input
          name="q"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className="ui-input-field h-9 w-[min(100%,220px)] rounded-lg border border-line pl-8 pr-9 text-[12px] text-cream outline-none placeholder:text-muted focus:ring-1 focus:ring-accent/30"
        />
        {initialQuery.trim().length > 0 && (
          <button
            type="button"
            onClick={handleClear}
            title="Clear search"
            aria-label="Clear search"
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted transition-colors hover:bg-warn/10 hover:text-warn"
          >
            <IconX className="size-3.5" />
          </button>
        )}
      </div>
    </form>
  );
}
