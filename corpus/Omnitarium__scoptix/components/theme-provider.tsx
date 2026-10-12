"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  readStoredAccentHue,
  readStoredThemeMode,
  SCX_DEFAULT_ACCENT_HUE,
  SCX_STORAGE_ACCENT_HUE,
  SCX_STORAGE_THEME,
  type ThemeMode,
} from "@/lib/scx-theme";

type Ctx = {
  theme: ThemeMode;
  setTheme: (t: ThemeMode) => void;
  accentHue: number;
  setAccentHue: (n: number) => void;
};

const ThemeContext = createContext<Ctx | null>(null);

function applyThemeToDom(theme: ThemeMode, accentHue: number) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.setProperty("--color-accent", `oklch(0.72 0.12 ${accentHue})`);
  document.documentElement.style.setProperty("--color-accent-dim", `oklch(0.58 0.11 ${accentHue})`);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("scoptix");
  const [accentHue, setAccentHueState] = useState<number>(SCX_DEFAULT_ACCENT_HUE);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const storedTheme = readStoredThemeMode();
    setThemeState(storedTheme);
    setAccentHueState(readStoredAccentHue(storedTheme));
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    applyThemeToDom(theme, accentHue);
    try {
      localStorage.setItem(SCX_STORAGE_THEME, theme);
      localStorage.setItem(SCX_STORAGE_ACCENT_HUE, String(accentHue));
    } catch {
      // ignore
    }
  }, [ready, theme, accentHue]);

  const setTheme = useCallback((t: ThemeMode) => setThemeState(t), []);
  const setAccentHue = useCallback((n: number) => setAccentHueState(Math.max(0, Math.min(360, Math.round(n)))), []);

  const value = useMemo(() => ({ theme, setTheme, accentHue, setAccentHue }), [theme, accentHue, setTheme, setAccentHue]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const v = useContext(ThemeContext);
  if (!v) throw new Error("useTheme must be used within ThemeProvider");
  return v;
}
