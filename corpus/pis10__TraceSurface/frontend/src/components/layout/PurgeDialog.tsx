
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { fmtDuration, fmtRelTime } from "@/lib/format";
import type { TargetSummary } from "@/types/api";

type PurgeDialogProps = {
  open: boolean;
  targets: TargetSummary[];
  onOpenChange: (open: boolean) => void;
  onDone: () => Promise<void> | void;
  toast: (message: string) => void;
};

export function PurgeDialog({ open, targets, onOpenChange, onDone, toast }: PurgeDialogProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [armed, setArmed] = useState(false);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? targets.filter((item) => item.target_url.toLowerCase().includes(needle)) : targets;
  }, [query, targets]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setSelected([]);
      setArmed(false);
    }
  }, [open]);

  useEffect(() => {
    if (!armed) return;
    const timer = window.setTimeout(() => setArmed(false), 5000);
    return () => window.clearTimeout(timer);
  }, [armed]);

  const toggle = (targetUrl: string, checked: boolean) => {
    setSelected((current) => (checked ? [...current, targetUrl] : current.filter((item) => item !== targetUrl)));
  };

  const purgeSelected = async () => {
    if (!selected.length) return;
    const confirmed = window.confirm(`确认清空以下 ${selected.length} 个 target 的数据？此操作不可恢复。\n\n${selected.join("\n")}`);
    if (!confirmed) return;
    const totals = { api_resolutions: 0, verifications: 0, files: 0, cdp_requests: 0 };
    for (const targetUrl of selected) {
      const result = await api.purgeTarget(targetUrl);
      totals.api_resolutions += result.counts.api_resolutions || 0;
      totals.verifications += result.counts.verifications || 0;
      totals.files += result.counts.files || 0;
      totals.cdp_requests += result.counts.cdp_requests || 0;
    }
    toast(`已删除 ${totals.api_resolutions} APIs · ${totals.verifications} 验证 · ${totals.files} files · CDP ${totals.cdp_requests}`);
    setSelected([]);
    await onDone();
  };

  const purgeAll = async () => {
    if (!armed) {
      setArmed(true);
      return;
    }
    const result = await api.purgeAll();
    const c = result.counts;
    toast(`已全部清空 · ${c.scans || 0} scans · ${c.api_resolutions || 0} APIs · ${c.verifications || 0} 验证 · CDP ${c.cdp_requests || 0}`);
    onOpenChange(false);
    await onDone();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>清空扫描数据</DialogTitle>
          <DialogDescription>
            选择一个或多个 target_url 清空，或清空全部。<b className="text-red">此操作不可恢复</b>。
          </DialogDescription>
        </DialogHeader>
        <div className="px-6 pb-3">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 target_url..." className="font-mono" />
        </div>
        <div className="min-h-[180px] flex-1 overflow-y-auto border-y border-line py-1">
          {filtered.length ? (
            filtered.map((target) => {
              const duration = target.last_finished_at && target.last_scan_at ? fmtDuration(target.last_finished_at - target.last_scan_at) : "-";
              const when = target.last_scan_at ? `${fmtRelTime(target.last_scan_at)} ago` : "";
              const checked = selected.includes(target.target_url);
              return (
                <label key={target.target_url} className="grid cursor-pointer grid-cols-[22px_minmax(0,1fr)_minmax(120px,220px)] items-center gap-3 px-6 py-2 font-mono text-[12px] hover:bg-ink-3">
                  <Checkbox checked={checked} onCheckedChange={(next) => toggle(target.target_url, next === true)} />
                  <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-text" title={target.target_url}>
                    {target.target_url}
                  </span>
                  <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-[11px] text-text-3" title={`${target.api_count} apis · ${target.replay_count} replays · 耗时 ${duration}${when ? ` · ${when}` : ""}`}>
                    {target.api_count} apis · {target.replay_count} replays · 耗时 {duration}
                    {when ? ` · ${when}` : ""}
                  </span>
                </label>
              );
            })
          ) : (
            <div className="px-6 py-10 text-center text-text-3">没有扫描记录</div>
          )}
        </div>
        <div className="flex justify-end gap-2 px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button variant={armed ? "danger" : "outline"} onClick={purgeAll}>
            {armed ? "再次点击确认清空" : "清空全部..."}
          </Button>
          <Button variant="default" disabled={!selected.length} onClick={purgeSelected}>
            清空所选 ({selected.length})
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
