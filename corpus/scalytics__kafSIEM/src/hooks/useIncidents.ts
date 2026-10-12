import { useEffect, useState } from "react";
import { incidentsURL } from "@/agentops/lib/demo";
import type { IncidentSummary, IncidentsListResponse } from "@/types/incident";
const POLL_MS = 15000;

export function useIncidents(limit = 50) {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAvailable, setIsAvailable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${incidentsURL()}?limit=${limit}&t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`incidents fetch failed: ${response.status}`);
        }
        const data = (await response.json()) as IncidentsListResponse;
        if (!cancelled) {
          setIncidents(Array.isArray(data.items) ? data.items : []);
          setIsAvailable(true);
          setIsLoading(false);
        }
      } catch {
        if (!cancelled) {
          setIsAvailable(false);
          setIsLoading(false);
        }
      }
    }

    load();
    const intervalId = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [limit]);

  return { incidents, isLoading, isAvailable };
}