"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { TechHostsPanel } from "@/components/scans/tech-hosts-panel";
import type { ScanTechRow } from "@/components/scans/scan-tech-tab";

type TechHostsPanelContextValue = {
  tech: ScanTechRow | null;
  openTechPanel: (tech: ScanTechRow) => void;
  closeTechPanel: () => void;
};

const TechHostsPanelContext = createContext<TechHostsPanelContextValue | null>(null);

export function TechHostsPanelProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [tech, setTech] = useState<ScanTechRow | null>(null);

  const closeTechPanel = useCallback(() => setTech(null), []);
  const openTechPanel = useCallback((next: ScanTechRow) => {
    if (!next) return;
    setTech(next);
  }, []);

  useEffect(() => {
    setTech(null);
  }, [pathname]);

  const value = useMemo(
    () => ({ tech, openTechPanel, closeTechPanel }),
    [tech, openTechPanel, closeTechPanel],
  );

  return (
    <TechHostsPanelContext.Provider value={value}>
      {children}
      {tech ? <TechHostsPanel tech={tech} onClose={closeTechPanel} /> : null}
    </TechHostsPanelContext.Provider>
  );
}

export function useTechHostsPanel() {
  const ctx = useContext(TechHostsPanelContext);
  if (!ctx) {
    throw new Error("useTechHostsPanel must be used within TechHostsPanelProvider");
  }
  return ctx;
}
