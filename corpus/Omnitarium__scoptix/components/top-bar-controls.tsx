"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { useTheme } from "@/components/theme-provider";

function utcTimeHms() {
  return new Date().toISOString().slice(11, 19);
}

/** Accent slider, theme switcher, and UTC clock (shared by TopBar and scan header). */
export function TopBarControls({ compact }: { compact?: boolean }) {
  const { theme, setTheme, accentHue, setAccentHue } = useTheme();
  const [clock, setClock] = useState(utcTimeHms);

  useEffect(() => {
    const id = window.setInterval(() => setClock(utcTimeHms()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className={["flex flex-wrap items-center", compact ? "gap-2" : "gap-3 sm:gap-4"].join(" ")}>
      <nav
        className="flex items-center rounded-lg border border-line bg-[var(--tab-bg)] p-0.5 text-[10px] font-medium shadow-sm"
        aria-label="Theme"
      >
        <button
          type="button"
          className={[
            "rounded-md px-2 py-0.5 transition-colors",
            theme === "scoptix" ? "bg-white/[0.08] text-cream" : "text-muted hover:text-cream",
          ].join(" ")}
          onClick={() => setTheme("scoptix")}
        >
          Scoptix
        </button>
        <button
          type="button"
          className={[
            "rounded-md px-2 py-0.5 transition-colors",
            theme === "dark" ? "bg-white/[0.08] text-cream" : "text-muted hover:text-cream",
          ].join(" ")}
          onClick={() => setTheme("dark")}
        >
          Dark
        </button>
        <button
          type="button"
          className={[
            "rounded-md px-2 py-0.5 transition-colors",
            theme === "light-mist" ? "bg-white/[0.08] text-cream" : "text-muted hover:text-cream",
          ].join(" ")}
          onClick={() => setTheme("light-mist")}
        >
          Mist
        </button>
      </nav>

      <div
        className={[
          "flex items-center gap-2 rounded-lg border border-line bg-[var(--tab-bg)]",
          compact ? "px-2 py-1" : "rounded-xl px-3 py-1.5",
        ].join(" ")}
      >
        <span className="text-[10px] font-medium text-muted">Accent</span>
        <input
          aria-label="Accent hue"
          type="range"
          min={0}
          max={360}
          value={accentHue}
          onChange={(e) => setAccentHue(Number(e.target.value))}
          className="scx-accent-hue-slider w-20"
          style={{ "--slider-fill": `${(accentHue / 360) * 100}%` } as CSSProperties}
        />
      </div>

      <div className="font-mono text-[11px] text-muted">
        <span suppressHydrationWarning>
          UTC <span className="text-cream/80" suppressHydrationWarning>{clock}Z</span>
        </span>
      </div>
    </div>
  );
}
