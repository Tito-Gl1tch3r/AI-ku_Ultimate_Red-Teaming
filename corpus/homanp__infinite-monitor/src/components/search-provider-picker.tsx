"use client";

import { useEffect, useRef, useState } from "react";
import { Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { useSettingsStore } from "@/store/settings-store";
import { SEARCH_PROVIDERS, type SearchProvider } from "@/lib/web-search";

export function SearchProviderPicker({ disabled }: { disabled?: boolean }) {
  const searchProvider = useSettingsStore((s) => s.searchProvider);
  const setSearchProvider = useSettingsStore((s) => s.setSearchProvider);
  const apiKeys = useSettingsStore((s) => s.apiKeys);
  const setApiKey = useSettingsStore((s) => s.setApiKey);

  const [open, setOpen] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const activeProvider = SEARCH_PROVIDERS.find((p) => p.id === searchProvider);
  const hasKey = searchProvider ? !!apiKeys[searchProvider] : false;

  function handleToggle(id: SearchProvider, checked: boolean) {
    if (checked) {
      setSearchProvider(id);
      setKeyInput("");
    } else {
      setSearchProvider(null);
    }
  }

  function handleSaveKey() {
    if (!searchProvider || !keyInput.trim()) return;
    setApiKey(searchProvider, keyInput.trim());
    setKeyInput("");
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className={cn(
          "inline-flex h-7 items-center gap-1.5 px-2 text-xs transition-colors cursor-pointer",
          searchProvider
            ? "text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800"
            : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <Globe className="size-3.5" />
        {activeProvider && (
          <span>{activeProvider.name}</span>
        )}
        {searchProvider && !hasKey && (
          <span className="size-1.5 rounded-full bg-yellow-500/70 shrink-0" />
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-1 z-50 min-w-[220px] border border-zinc-700 bg-zinc-900 shadow-xl">
          <div className="px-2.5 py-2 text-[10px] uppercase tracking-wider text-zinc-500">
            Search provider
          </div>
          {SEARCH_PROVIDERS.map((p) => {
            const isActive = searchProvider === p.id;
            return (
              <label
                key={p.id}
                className={cn(
                  "flex w-full items-center gap-2.5 px-2.5 py-2 text-xs transition-colors cursor-pointer",
                  isActive
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                )}
              >
                <span className="flex-1">{p.name}</span>
                <Switch
                  checked={isActive}
                  onCheckedChange={(checked) => handleToggle(p.id, checked)}
                />
              </label>
            );
          })}

          {searchProvider && !hasKey && (
            <div className="border-t border-zinc-800 p-2.5">
              <div className="flex items-center gap-1.5">
                <input
                  type="password"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveKey()}
                  placeholder={activeProvider?.placeholder ?? "API key…"}
                  className="flex-1 bg-zinc-950 border border-zinc-800 text-xs px-2 py-1.5 text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
                />
                <button
                  type="button"
                  onClick={handleSaveKey}
                  className="px-2 py-1.5 text-xs uppercase tracking-wider bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                >
                  Save
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
