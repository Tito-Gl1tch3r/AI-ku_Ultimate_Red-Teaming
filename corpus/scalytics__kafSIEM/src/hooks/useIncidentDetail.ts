import { useEffect, useState } from "react";
import { incidentDetailURL } from "@/agentops/lib/demo";
import type { IncidentDetail } from "@/types/incident";

export function useIncidentDetail(incidentId: string | undefined, enabled = true) {
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    if (!enabled || !incidentId) {
      setDetail(null);
      setIsLoading(false);
      return;
    }

    const resolvedIncidentId = incidentId;
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setIsLoading(true);
      try {
        const response = await fetch(
          `${incidentDetailURL(resolvedIncidentId)}?t=${Date.now()}`,
          { cache: "no-store", signal: controller.signal },
        );
        if (!response.ok) {
          throw new Error(`incident detail fetch failed: ${response.status}`);
        }
        const data = (await response.json()) as IncidentDetail;
        if (!cancelled) {
          setDetail(data);
          setIsAvailable(true);
          setIsLoading(false);
        }
      } catch (error) {
        if (cancelled || (error instanceof DOMException && error.name === "AbortError")) {
          return;
        }
        if (!cancelled) {
          setDetail(null);
          setIsAvailable(false);
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [incidentId, enabled]);

  return { detail, isLoading, isAvailable };
}