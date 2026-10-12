import { useMemo, useState } from "react";
import { GitBranch, ShieldAlert, Radar } from "lucide-react";
import { useIncidents } from "@/hooks/useIncidents";
import {
  attackTypeBadge,
  attackTypeLabels,
  attackTypeOrder,
  groupIncidentsByAttackType,
  normalizeAttackType,
  type AttackType,
} from "@/lib/attack-types";
import { formatLinkReason, geographyEvidenceLabel, geographyLabel, isGeographyReason } from "@/lib/incident-links";
import { detectSpikes, type ActivitySpike } from "@/lib/activity-spikes";
import { countryRegion } from "@/lib/country-centroids";
import type { Alert } from "@/types/alert";
import type { IncidentSummary } from "@/types/incident";

interface Props {
  alerts: Alert[];
  historicalAlerts: Alert[];
  regionFilter: string;
  onSelectIncident: (incident: IncidentSummary) => void;
  onPreviewIncident?: (incident: IncidentSummary | null) => void;
}

const SPIKE_RECENCY_MS = 48 * 60 * 60 * 1000;

// The relations list is global while the map honors the region filter; flag
// clusters whose event geography falls entirely outside the current map view.
function incidentOutsideRegion(incident: IncidentSummary, regionFilter: string): boolean {
  if (regionFilter === "all" || !incident.countries?.length) return false;
  if (regionFilter.startsWith("country:")) {
    return !incident.countries.includes(regionFilter.slice(8));
  }
  return !incident.countries.some((code) => {
    const region = countryRegion(code);
    if (!region) return false;
    if (regionFilter === "Asia-Pacific") {
      return region === "Asia-Pacific" || region === "Asia" || region === "Oceania";
    }
    return region === regionFilter;
  });
}

export function IncidentRelationsPanel({
  alerts,
  historicalAlerts,
  regionFilter,
  onSelectIncident,
  onPreviewIncident,
}: Props) {
  const { incidents, isLoading, isAvailable } = useIncidents(100);
  const [attackFilter, setAttackFilter] = useState<AttackType | "all">("all");

  const spikesByCountry = useMemo(() => {
    const map = new Map<string, ActivitySpike>();
    for (const spike of detectSpikes([...alerts, ...historicalAlerts])) {
      map.set(spike.countryCode, spike);
    }
    return map;
  }, [alerts, historicalAlerts]);

  const grouped = useMemo(() => groupIncidentsByAttackType(incidents), [incidents]);
  const visible = useMemo(() => {
    if (attackFilter === "all") return incidents;
    return grouped[attackFilter] ?? [];
  }, [attackFilter, grouped, incidents]);

  const attackCounts = useMemo(
    () =>
      attackTypeOrder
        .map((type) => ({ type, count: grouped[type]?.length ?? 0 }))
        .filter((entry) => entry.count > 0),
    [grouped],
  );

  return (
    <section className="flex h-full flex-col overflow-hidden rounded-[1.6rem] border border-siem-border bg-siem-panel/90 shadow-[0_24px_80px_rgba(0,0,0,0.28)]">
      <div className="border-b border-siem-border/80 px-4 py-3">
        <div className="flex items-center gap-2 text-4xs uppercase tracking-[0.2em] text-siem-muted">
          <GitBranch size={10} />
          Attack relations
        </div>
        <div className="mt-1 text-xs text-siem-text">Corroborated clusters across cyber, terror, maritime, and conflict feeds.</div>
      </div>

      <div className="border-b border-siem-border/80 px-3 py-2">
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setAttackFilter("all")}
            className={`rounded-full border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] ${
              attackFilter === "all" ? "border-siem-accent/45 bg-siem-accent/12 text-siem-text" : "border-siem-border text-siem-muted"
            }`}
          >
            All ({incidents.length})
          </button>
          {attackCounts.map(({ type, count }) => (
            <button
              key={type}
              type="button"
              onClick={() => setAttackFilter(type)}
              className={`rounded-full border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] ${
                attackFilter === type ? attackTypeBadge[type] : "border-siem-border text-siem-muted"
              }`}
            >
              {attackTypeLabels[type]} ({count})
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="text-sm text-siem-muted">Loading relation clusters...</div>
        ) : visible.length === 0 ? (
          <div className="rounded-lg border border-siem-border bg-black/20 px-3 py-4 text-sm text-siem-muted">
            {isAvailable
              ? "No corroborated attack clusters in the current index. Clusters form when cyber, terror, or conflict alerts share CVEs, actors, or geography across sources."
              : "Incidents API unavailable. Run make dev-start or make demo-osint."}
          </div>
        ) : (
          visible.map((incident) => (
            <IncidentRelationCard
              key={incident.incident_id}
              incident={incident}
              spike={findIncidentSpike(incident, spikesByCountry)}
              outsideRegion={incidentOutsideRegion(incident, regionFilter)}
              onSelectIncident={onSelectIncident}
              onPreviewIncident={onPreviewIncident}
            />
          ))
        )}
      </div>
    </section>
  );
}

// A spike only corroborates a cluster that is itself still moving: the
// incident's event geography must overlap a spiking country and the cluster
// must have been active within the spike-detection horizon.
function findIncidentSpike(
  incident: IncidentSummary,
  spikesByCountry: Map<string, ActivitySpike>,
): ActivitySpike | null {
  if (!incident.countries?.length) return null;
  const lastSeen = Date.parse(incident.last_seen);
  if (Number.isNaN(lastSeen) || Date.now() - lastSeen > SPIKE_RECENCY_MS) return null;
  for (const country of incident.countries) {
    const spike = spikesByCountry.get(country.toUpperCase());
    if (spike) return spike;
  }
  return null;
}

function IncidentRelationCard({
  incident,
  spike,
  outsideRegion,
  onSelectIncident,
  onPreviewIncident,
}: {
  incident: IncidentSummary;
  spike: ActivitySpike | null;
  outsideRegion: boolean;
  onSelectIncident: (incident: IncidentSummary) => void;
  onPreviewIncident?: (incident: IncidentSummary | null) => void;
}) {
  const attackType = normalizeAttackType(incident.attack_type);
  const sourceCount = incident.source_count ?? 0;
  const countLabel =
    sourceCount > 0 && sourceCount !== incident.member_count
      ? `${sourceCount} sources · ${incident.member_count} alerts`
      : sourceCount > 0
        ? `${sourceCount} sources`
        : `${incident.member_count} alerts`;
  const geography = geographyEvidenceLabel(incident.link_reasons) ?? geographyLabel(incident.countries);
  const reasons = (incident.link_reasons ?? [])
    .filter((reason) => !geography || !isGeographyReason(reason))
    .slice(0, 3);

  return (
    <button
      type="button"
      onClick={() => onSelectIncident(incident)}
      onMouseEnter={() => onPreviewIncident?.(incident)}
      onMouseLeave={() => onPreviewIncident?.(null)}
      onFocus={() => onPreviewIncident?.(incident)}
      onBlur={() => onPreviewIncident?.(null)}
      className="w-full rounded-xl border border-siem-border bg-siem-panel-strong px-3 py-3 text-left transition-colors hover:border-siem-accent/35 hover:bg-siem-accent/8"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`rounded-full border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] whitespace-nowrap ${attackTypeBadge[attackType]}`}>
              {attackTypeLabels[attackType]}
            </span>
            <span className="rounded-full border border-siem-border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] whitespace-nowrap text-siem-muted">
              {countLabel}
            </span>
            {spike ? (
              <span
                className={`rounded-full border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] whitespace-nowrap ${
                  spike.level === "surge"
                    ? "border-rose-400/45 bg-rose-400/12 text-rose-200"
                    : "border-amber-400/45 bg-amber-400/12 text-amber-200"
                }`}
              >
                Spike ×{spike.ratio} · {spike.countryCode}
              </span>
            ) : null}
            {outsideRegion ? (
              <span className="rounded-full border border-siem-border px-1.5 py-0.5 text-4xs uppercase tracking-[0.08em] whitespace-nowrap text-siem-muted/80">
                Outside map region
              </span>
            ) : null}
          </div>
          <div className="mt-2 text-xs font-medium text-siem-text line-clamp-2">{incident.title}</div>
          <div className="mt-1 font-mono text-xxs text-siem-muted truncate">{incident.incident_id}</div>
        </div>
        {attackType === "cyber" ? <ShieldAlert size={16} className="shrink-0 text-cyan-300" /> : <Radar size={16} className="shrink-0 text-orange-300" />}
      </div>

      {reasons.length > 0 || geography ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {reasons.map((reason) => (
            <span key={reason} className="rounded-full border border-siem-border px-2 py-0.5 text-xxs text-siem-muted">
              {formatLinkReason(reason)}
            </span>
          ))}
          {geography ? (
            <span className="rounded-full border border-siem-border px-2 py-0.5 text-xxs text-siem-muted">{geography}</span>
          ) : null}
        </div>
      ) : null}
    </button>
  );
}
