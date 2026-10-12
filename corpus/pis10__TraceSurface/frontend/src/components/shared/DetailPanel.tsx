
import type { ReactNode } from "react";
import { useResizablePanel } from "@/hooks/use-resizable-panel";
import { cn } from "@/lib/utils";

type DetailPanelProps = {
  className?: string;
  children: ReactNode;
};

export function DetailPanel({ className, children }: DetailPanelProps) {
  const { onPointerDown, widthStyle } = useResizablePanel();

  return (
    <aside className={cn("detail-panel", className)} style={widthStyle}>
      <div
        className="detail-resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整详情面板宽度"
        onPointerDown={onPointerDown}
      />
      {children}
    </aside>
  );
}
