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
import { HostnameSightingPanel } from "@/components/hostname-sighting-panel";

export type OpenHostnamePanelOptions = {
  /** When set, panel sightings are limited to this observed scan. */
  scanJobId?: string;
};

type HostnameSightingPanelContextValue = {
  hostnameNormalized: string | null;
  targetDomainId: string | null;
  openHostnamePanel: (targetDomainId: string, hostnameNormalized: string, options?: OpenHostnamePanelOptions) => void;
  closeHostnamePanel: () => void;
};

const HostnameSightingPanelContext = createContext<HostnameSightingPanelContextValue | null>(null);

export function HostnameSightingPanelProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [hostnameNormalized, setHostnameNormalized] = useState<string | null>(null);
  const [targetDomainId, setTargetDomainId] = useState<string | null>(null);
  const [scanJobId, setScanJobId] = useState<string | null>(null);

  const closeHostnamePanel = useCallback(() => {
    setHostnameNormalized(null);
    setTargetDomainId(null);
    setScanJobId(null);
  }, []);

  const openHostnamePanel = useCallback((domainId: string, hostname: string, options?: OpenHostnamePanelOptions) => {
    if (!domainId || !hostname) return;
    setTargetDomainId(domainId);
    setHostnameNormalized(hostname);
    setScanJobId(options?.scanJobId?.trim() || null);
  }, []);

  useEffect(() => {
    setHostnameNormalized(null);
    setTargetDomainId(null);
    setScanJobId(null);
  }, [pathname]);

  const value = useMemo(
    () => ({ hostnameNormalized, targetDomainId, openHostnamePanel, closeHostnamePanel }),
    [hostnameNormalized, targetDomainId, openHostnamePanel, closeHostnamePanel],
  );

  return (
    <HostnameSightingPanelContext.Provider value={value}>
      {children}
      {hostnameNormalized && targetDomainId ? (
        <HostnameSightingPanel
          targetDomainId={targetDomainId}
          hostnameNormalized={hostnameNormalized}
          scanJobId={scanJobId}
          onClose={closeHostnamePanel}
        />
      ) : null}
    </HostnameSightingPanelContext.Provider>
  );
}

export function useHostnameSightingPanel() {
  const ctx = useContext(HostnameSightingPanelContext);
  if (!ctx) {
    throw new Error("useHostnameSightingPanel must be used within HostnameSightingPanelProvider");
  }
  return ctx;
}
