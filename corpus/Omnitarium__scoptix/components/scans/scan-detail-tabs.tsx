import Link from "next/link";
import type { ComponentType } from "react";

export type ScanDetailTab = {
  key: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  href: string;
  count?: string | null;
  rotateIcon?: boolean;
};

export function ScanDetailTabs({
  tabs,
  activeKey,
}: {
  tabs: ScanDetailTab[];
  activeKey: string;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-center gap-x-6 border-b border-line">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.key === activeKey;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            className={["scx-scan-tab", active ? "scx-scan-tab-active" : ""].join(" ")}
          >
            <Icon className={["mr-1.5 size-3.5", tab.rotateIcon ? "rotate-45" : ""].join(" ")} />
            {tab.label}
            {tab.count != null && tab.count !== "" ? (
              <span className="ml-1 text-[10px] text-muted">({tab.count})</span>
            ) : null}
          </Link>
        );
      })}
    </div>
  );
}
