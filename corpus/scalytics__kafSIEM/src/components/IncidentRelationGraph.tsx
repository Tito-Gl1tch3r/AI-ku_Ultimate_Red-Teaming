import type { IncidentDetail } from "@/types/incident";
import { formatLinkReason, reportLag } from "@/lib/incident-links";
import { categoryLabels } from "@/lib/severity";

interface Props {
  detail: IncidentDetail;
  currentAlertId: string;
  onSelectAlert: (alertId: string) => void;
}

export function IncidentRelationGraph({ detail, currentAlertId, onSelectAlert }: Props) {
  const primaryId = detail.primary_alert_id;
  const nodes = detail.graph?.nodes ?? [];
  const edges = detail.graph?.edges ?? [];
  const timeline = detail.timeline ?? [];
  const geo = detail.geo;

  return (
    <div className="space-y-3">
      {geo?.country_codes?.length ? (
        <div>
          <div className="text-2xs uppercase tracking-wider text-siem-muted">Geography</div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {(geo.countries?.length ? geo.countries : geo.country_codes).map((label) => (
              <span
                key={label}
                className="rounded-full border border-siem-border px-2 py-0.5 text-xxs text-siem-muted"
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {nodes.length > 0 ? (
        <div>
          <div className="text-2xs uppercase tracking-wider text-siem-muted">Relation graph</div>
          <div className="mt-2 space-y-2 rounded-lg border border-siem-border bg-black/20 p-3">
            {nodes.map((node) => {
              const isCurrent = node.id === currentAlertId;
              const isPrimary = node.id === primaryId || node.role === "primary";
              const isAlert = node.kind === "alert" || !node.kind;
              const kindLabel =
                node.kind === "actor"
                  ? "actor"
                  : node.kind === "cve"
                    ? "vulnerability"
                    : node.kind === "malware"
                      ? "malware ioc"
                      : node.kind === "sector"
                        ? "sector"
                        : node.kind === "country"
                          ? "geography"
                          : isPrimary
                            ? "primary"
                            : "member";
              const content = (
                <>
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-siem-text truncate">{node.label}</div>
                    <div className="text-xxs text-siem-muted">
                      {node.country_code || kindLabel}
                      {isAlert ? ` · ${isPrimary ? "primary" : "member"}` : ""}
                    </div>
                  </div>
                  {isAlert ? <span className="shrink-0 font-mono text-xxs uppercase text-siem-muted">{node.severity}</span> : null}
                </>
              );
              if (!isAlert) {
                return (
                  <div key={node.id} className="rounded-md border border-dashed border-siem-border/80 px-2.5 py-2">
                    {content}
                  </div>
                );
              }
              return (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => onSelectAlert(node.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-2 text-left ${
                    isCurrent ? "border-siem-accent/50 bg-siem-accent/10" : "border-siem-border/70 hover:border-siem-accent/30"
                  }`}
                >
                  {content}
                </button>
              );
            })}
            {edges.map((edge) => (
              <div key={`${edge.from}-${edge.to}-${edge.reason}`} className="pl-4 text-xxs text-siem-muted">
                {edge.from.slice(0, 8)} → {edge.to.slice(0, 8)} · {formatLinkReason(edge.reason)}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {timeline.length > 0 ? (
        <div>
          <div className="text-2xs uppercase tracking-wider text-siem-muted">Timeline</div>
          <div className="mt-2 space-y-2">
            {timeline.map((entry, index) => {
              const lag = index === 0 ? null : reportLag(timeline[0].first_seen, entry.first_seen);
              return (
              <button
                key={entry.alert_id}
                type="button"
                onClick={() => onSelectAlert(entry.alert_id)}
                className="block w-full rounded-lg border border-siem-border bg-black/20 px-3 py-2 text-left hover:border-siem-accent/40"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xxs text-siem-muted">{(entry.first_seen ?? "").replace("T", " ").replace("Z", " UTC")}</span>
                  <span className="flex items-center gap-1.5">
                    {index === 0 ? (
                      <span className="rounded-full border border-siem-accent/40 bg-siem-accent/10 px-1.5 text-xxs text-siem-text">first report</span>
                    ) : lag ? (
                      <span className="font-mono text-xxs text-siem-muted">{lag}</span>
                    ) : null}
                    <span className="text-xxs uppercase tracking-wider text-siem-muted">{entry.role || "member"}</span>
                  </span>
                </div>
                <div className="mt-1 text-xs font-medium text-siem-text line-clamp-2">{entry.title}</div>
                <div className="mt-1 text-xxs text-siem-muted">
                  {entry.authority_name} · {categoryLabels[entry.category as keyof typeof categoryLabels] ?? entry.category}
                </div>
              </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}