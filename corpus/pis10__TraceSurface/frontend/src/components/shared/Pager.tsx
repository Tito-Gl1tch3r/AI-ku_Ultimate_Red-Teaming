
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PagerProps = {
  total: number;
  page: number;
  pageSize: number;
  pageSizes?: number[];
  onChange: (next: { page: number; pageSize: number }) => void;
};

export function Pager({ total, page, pageSize, pageSizes = [50, 200, 500], onChange }: PagerProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(page, pageCount);
  const numbers = Array.from(new Set([1, pageCount, current - 1, current, current + 1]))
    .filter((item) => item >= 1 && item <= pageCount)
    .sort((a, b) => a - b);
  const from = total ? (current - 1) * pageSize + 1 : 0;
  const to = Math.min(current * pageSize, total);
  const visible: Array<number | "..."> = [];
  let prev = 0;
  for (const item of numbers) {
    if (item - prev > 1) visible.push("...");
    visible.push(item);
    prev = item;
  }

  return (
    <footer className="pager">
      <div className="min-w-[120px]">
        {from}-{to} / {total}
      </div>
      <div className="flex items-center gap-1.5">
        <Button variant="subtle" size="sm" disabled={current <= 1} onClick={() => onChange({ page: current - 1, pageSize })}>
          <ChevronLeft className="h-3.5 w-3.5" />
          Prev
        </Button>
        {visible.map((item, index) =>
          item === "..." ? (
            <span key={`ellipsis-${index}`} className="px-2 text-text-4">
              ...
            </span>
          ) : (
            <button
              key={item}
              type="button"
              className={cn(
                "h-7 min-w-7 rounded border border-transparent px-2 text-text-3 transition-colors hover:border-line-2 hover:text-text",
                item === current && "border-brand bg-[var(--brand-soft)] font-semibold text-brand",
              )}
              onClick={() => onChange({ page: item, pageSize })}
            >
              {item}
            </button>
          ),
        )}
        <Button variant="subtle" size="sm" disabled={current >= pageCount} onClick={() => onChange({ page: current + 1, pageSize })}>
          Next
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
      <label className="flex items-center gap-2">
        每页
        <select
          className="h-7 rounded border border-line-2 bg-surface-content px-2 text-text outline-none"
          value={pageSize}
          onChange={(event) => onChange({ page: 1, pageSize: Number(event.target.value) })}
        >
          {pageSizes.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
    </footer>
  );
}
