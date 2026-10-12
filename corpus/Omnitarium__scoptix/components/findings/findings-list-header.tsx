import { TopBarControls } from "@/components/top-bar-controls";
import { IconShield } from "@/components/ui-icons";

type FindingsListHeaderProps = {
  findingCount: number;
};

export function FindingsListHeader({ findingCount }: FindingsListHeaderProps) {
  return (
    <header className="scx-scan-header shrink-0">
      <div className="flex items-stretch justify-between gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 text-[11px] font-bold text-muted">Findings</div>
          <div className="mb-3 flex items-center gap-3">
            <h1 className="scx-scan-header-title truncate font-bold text-cream">Findings</h1>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
            <span className="inline-flex items-center rounded-full bg-accent/15 px-2 py-0.5 text-[10px] font-medium uppercase text-accent-dim">
              <IconShield className="mr-1 size-3" />
              All Findings
            </span>
            <span>Total: {findingCount.toLocaleString()}</span>
            <span aria-hidden>•</span>
            <span>
              Sensitive data detected in URL strings and downloaded content across all targets.
            </span>
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-end justify-between gap-2">
          <TopBarControls compact />
        </div>
      </div>
    </header>
  );
}
