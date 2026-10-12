import Link from "next/link";
import type { ComponentType } from "react";
import { IconScans } from "@/components/nav-icons";
import {
  IconAlertTriangle,
  IconGlobe,
  IconTerminal,
} from "@/components/ui-icons";

const cardEyebrowClass =
  "text-[10px] font-semibold uppercase tracking-[0.2em] text-accent";

type QuickAction = {
  href: string;
  title: string;
  subtitle: string;
  Icon: ComponentType<{ className?: string }>;
};

const QUICK_ACTIONS: QuickAction[] = [
  {
    href: "/scans",
    title: "New scan",
    subtitle: "Start a scan",
    Icon: IconTerminal,
  },
  {
    href: "/findings",
    title: "All findings",
    subtitle: "Browse findings",
    Icon: IconAlertTriangle,
  },
  {
    href: "/scans",
    title: "All scans",
    subtitle: "Browse scan history",
    Icon: IconScans,
  },
  {
    href: "/targets",
    title: "All targets",
    subtitle: "View targets",
    Icon: IconGlobe,
  },
];

function QuickActionTile({ action }: { action: QuickAction }) {
  const { Icon } = action;

  return (
    <Link
      href={action.href}
      className="group flex h-full flex-col gap-3 rounded-xl border border-line bg-lift/50 p-4 pt-7 transition-all hover:border-accent/35 hover:bg-[var(--nav-hover-bg)] hover:shadow-lift focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
    >
      <Icon className="size-8 shrink-0 text-accent transition-transform group-hover:scale-105" />
      <div>
        <div className="text-[13px] font-semibold leading-tight text-cream">{action.title}</div>
        <div className="mt-1 text-[11px] leading-snug text-muted">{action.subtitle}</div>
      </div>
    </Link>
  );
}

export function DashboardQuickActionsCard() {
  return (
    <div className="glass-panel flex h-full flex-col rounded-2xl px-5 py-4 md:px-6 md:py-5">
      <h2 className={`mb-3 ${cardEyebrowClass}`}>Quick actions</h2>
      <div className="grid min-h-0 flex-1 grid-cols-2 gap-3">
        {QUICK_ACTIONS.map((action) => (
          <QuickActionTile key={action.title} action={action} />
        ))}
      </div>
    </div>
  );
}
