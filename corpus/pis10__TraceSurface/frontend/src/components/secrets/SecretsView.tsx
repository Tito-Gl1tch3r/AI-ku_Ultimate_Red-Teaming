
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { DetailPanel } from "@/components/shared/DetailPanel";
import { EmptyState } from "@/components/shared/EmptyState";
import { Pager } from "@/components/shared/Pager";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { shortSourceLabel } from "@/lib/format";
import type { FilterState } from "@/lib/filters";
import { cn } from "@/lib/utils";
import type { PageResult, SecretDetail, SecretFacets, SecretListItem, SecretSource } from "@/types/api";

function groupColor(group: string): string {
  let hash = 0;
  for (let i = 0; i < group.length; i++) hash = (hash * 31 + group.charCodeAt(i)) | 0;
  const hue = ((hash % 360) + 360) % 360;
  return `hsl(${hue} 60% 42%)`;
}

type SecretsViewProps = {
  filters: FilterState;
  onResultLabel: (label: string) => void;
  toast: (message: string) => void;
};

export function SecretsView({ filters, onResultLabel, toast }: SecretsViewProps) {
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [facets, setFacets] = useState<SecretFacets>({ groups: {}, sensitive: {} });
  const [data, setData] = useState<PageResult<SecretListItem>>({ total: 0, items: [] });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<SecretDetail | null>(null);

  const groupKey = useMemo(
    () => Array.from(selectedGroups).sort().join(","),
    [selectedGroups],
  );

  const listParams = useMemo(() => {
    const params: Record<string, string | number> = {
      offset: (page - 1) * pageSize,
      limit: pageSize,
    };
    if (filters.target) params.target = filters.target;
    if (groupKey) params.groups = groupKey;
    if (query) params.q = query;
    return params;
  }, [filters.target, groupKey, query, page, pageSize]);

  useEffect(() => {
    setPage(1);
    setSelectedId(null);
    setSelected(null);
  }, [filters.target, groupKey, query]);

  // 标签计数只随站点变化（不随勾选收窄，保持全集可选）
  useEffect(() => {
    let cancelled = false;
    const targetParams = filters.target ? { target: filters.target } : undefined;
    api
      .secretFacets(targetParams)
      .then((next) => {
        if (cancelled) return;
        setFacets({ groups: next.groups || {}, sensitive: next.sensitive || {} });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [filters.target]);

  useEffect(() => {
    let cancelled = false;
    api
      .secrets(listParams)
      .then((next) => {
        if (cancelled) return;
        setData(next);
        onResultLabel(next.total ? `${next.total} 条` : "-");
      })
      .catch(() => {
        if (!cancelled) onResultLabel("-");
      });
    return () => {
      cancelled = true;
    };
  }, [listParams, onResultLabel]);

  const select = async (id: number) => {
    setSelectedId(id);
    setSelected(null);
    try {
      setSelected(await api.secret(id));
    } catch {
      toast("加载详情失败");
    }
  };

  const toggleGroup = (group: string) => {
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  const groups = Object.entries(facets.groups).sort((a, b) => b[1] - a[1]);
  const totalAll = Object.values(facets.groups).reduce((sum, value) => sum + value, 0);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-surface-content">
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-line bg-surface-chrome px-4 py-2.5">
        <div className="flex flex-wrap gap-1.5">
          <button className={secretChipClass(selectedGroups.size === 0)} onClick={() => setSelectedGroups(new Set())}>
            全部 <span>{totalAll}</span>
          </button>
          {groups.map(([key, count]) => (
            <button
              key={key}
              className={secretChipClass(selectedGroups.has(key))}
              onClick={() => toggleGroup(key)}
              title={key}
            >
              <span className="mr-1 inline-block h-2 w-2 rounded-full align-middle" style={{ background: groupColor(key) }} />
              {key} <span>{count}</span>
            </button>
          ))}
        </div>
        <Input value={query} onChange={(event) => setQuery(event.target.value.trim())} placeholder="搜索命中值" className="ml-auto h-8 min-w-[180px] max-w-[280px] bg-ink-0 font-mono" />
        <div className="min-w-[64px] text-right font-mono text-[11px] text-text-4">{data.total ? `${data.total} 条` : ""}</div>
      </header>
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="secret-row-grid sticky top-0 z-10 border-b border-line bg-surface-chrome px-4 py-2.5 font-mono text-[10.5px] uppercase text-text-4">
            <span>Group</span>
            <span>Rule</span>
            <span>Value</span>
            <span>Count</span>
            <span>Source</span>
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            {data.items.length ? (
              data.items.map((item) => <SecretRow key={item.id} item={item} selected={item.id === selectedId} onClick={() => select(item.id)} />)
            ) : (
              <EmptyState title="无命中" />
            )}
          </div>
          <Pager total={data.total} page={page} pageSize={pageSize} onChange={({ page: p, pageSize: ps }) => { setPage(p); setPageSize(ps); }} />
        </div>
        {selectedId ? <SecretDetailPanel id={selectedId} detail={selected} onClose={() => { setSelectedId(null); setSelected(null); }} /> : null}
      </div>
    </div>
  );
}

function secretChipClass(active: boolean) {
  return cn(
    "rounded-md border border-line-2 px-3 py-1 font-mono text-[11.5px] text-text-3 transition-colors hover:border-text-3 hover:text-text",
    active && "border-brand bg-[var(--brand-soft)] text-brand",
  );
}

// sensitive 角标：HaE 标记为敏感的规则更值得优先看
function SensitiveBadge({ sensitive }: { sensitive: number }) {
  if (!sensitive) return null;
  return (
    <span className="rounded bg-[var(--brand-soft)] px-1 py-px text-[9.5px] font-semibold uppercase text-brand">敏感</span>
  );
}

// 单行密钥记录：group + sensitive、规则名、命中值、出现次数、来源文件
function SecretRow({ item, selected, onClick }: { item: SecretListItem; selected: boolean; onClick: () => void }) {
  const sourceText = (item.source_count || 0) > 1 ? `${item.source_count} sources` : `L${item.line}:c${item.col_start}`;
  return (
    <button
      className={cn("secret-row-grid w-full border-b border-line px-4 py-2 text-left font-mono text-[12px] transition-colors hover:bg-[color-mix(in_srgb,var(--surface-content)_88%,var(--ink-2))]", selected && "border-l-[3px] border-l-brand bg-[var(--accent-soft)]")}
      onClick={onClick}
    >
      <span className="flex min-w-0 flex-col gap-1 pt-0.5">
        <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-[10.5px] uppercase" style={{ color: groupColor(item.rule_group) }} title={item.rule_group}>{item.rule_group}</span>
        <span><SensitiveBadge sensitive={item.sensitive} /></span>
      </span>
      <span className="min-w-0 break-all font-medium text-text-2">{item.rule_id}</span>
      <span className="max-h-[5.6em] overflow-auto whitespace-pre-wrap break-all leading-5 text-brand">{item.value}</span>
      <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-[11px] font-semibold text-text-2">{item.occurrence_count || 1}</span>
      <span className="flex min-w-0 flex-col gap-0.5 break-all text-[11px] text-text-3" title={item.source_js}>
        <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">{shortSourceLabel(item.source_js)}</span>
        <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-[10.5px] text-text-4">{sourceText}</span>
      </span>
    </button>
  );
}

// 密钥详情面板：展示命中值、来源、上下文行、元数据
function SecretDetailPanel({ id, detail, onClose }: { id: number; detail: SecretDetail | null; onClose: () => void }) {
  if (!detail) {
    return (
      <DetailPanel>
        <div className="flex h-full flex-col items-center justify-center gap-2 p-6 font-mono text-text-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-line-2 border-t-brand" />
          <span className="text-[11px] uppercase text-text-4">SECRET #{id}</span>
        </div>
      </DetailPanel>
    );
  }
  const meta = detail.metadata || {};
  const context = renderContext(detail);
  const lineCol = `line ${detail.line} · col ${detail.col_start}`;
  const ctxLabel = (detail.context_line || "").length > 240 ? "Context (压缩窗口)" : "Context (±5 行)";

  return (
    <DetailPanel className="overflow-y-auto px-6 py-5">
      <button type="button" className="absolute right-4 top-4 z-10 inline-flex h-7 w-7 items-center justify-center rounded-full border border-line-2 bg-surface-chrome text-text-3 transition-colors hover:bg-ink-2 hover:text-text" onClick={onClose} title="关闭">
        <X className="h-4 w-4" />
      </button>
      <div className="mb-1 break-all font-mono text-[13px] font-semibold text-text">{detail.rule_id}</div>
      <div className="mb-4 flex items-center gap-2 text-[11px] uppercase text-text-3">
        <span style={{ color: groupColor(detail.rule_group) }}>{detail.rule_group}</span>
        <SensitiveBadge sensitive={detail.sensitive} />
      </div>
      <SecretSection title="Value"><div className="rounded-md border border-line-2 bg-surface-content px-3 py-2 font-mono text-[12px] leading-6 text-brand">{detail.value}</div></SecretSection>
      <SecretSection title="Source">
        <div className="break-all font-mono text-[11.5px] text-text-2">{detail.source_js}<br /><span className="text-[11px] text-text-4">{lineCol}</span></div>
      </SecretSection>
      {detail.sources && detail.sources.length > 1 ? <SecretSources sources={detail.sources} /> : null}
      <SecretSection title={ctxLabel}>{context}</SecretSection>
      {Object.keys(meta).length ? (
        <SecretSection title="Metadata">
          <div className="break-all font-mono text-[11px] text-text-3">
            {Object.entries(meta).map(([key, value]) => <span key={key}>{key}=<b className="text-brand">{String(value)}</b> </span>)}
          </div>
        </SecretSection>
      ) : null}
    </DetailPanel>
  );
}

function SecretSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="my-4">
      <div className="mb-1.5 text-[10.5px] uppercase text-text-4">{title}</div>
      {children}
    </section>
  );
}

const SOURCE_CAP = 50;

// 出现位置：按文件去重，默认收起，展开后封顶可滚动——避免几十上百文件时撑爆面板
function SecretSources({ sources }: { sources: SecretSource[] }) {
  const [open, setOpen] = useState(false);
  const shown = sources.slice(0, SOURCE_CAP);
  return (
    <section className="my-4">
      <button type="button" onClick={() => setOpen((v) => !v)} className="flex items-center gap-1.5 text-[10.5px] uppercase text-text-4 transition-colors hover:text-text-2">
        <span className="inline-block w-2">{open ? "▾" : "▸"}</span>
        出现位置 · {sources.length} 个文件
      </button>
      {open ? (
        <div className="mt-1.5 max-h-48 space-y-2 overflow-auto rounded-md border border-line-2 bg-surface-content px-3 py-2">
          {shown.map((s, i) => (
            <div key={`${s.source_js}-${i}`} className="font-mono text-[11px]">
              <div className="break-all text-text-2">{s.source_js}</div>
              <div className="text-[10.5px] text-text-4">L{s.line}:c{s.col_start}{s.count > 1 ? ` ·×${s.count}` : ""}</div>
            </div>
          ))}
          {sources.length > SOURCE_CAP ? (
            <div className="pt-1 text-[10.5px] text-text-4">… 还有 {sources.length - SOURCE_CAP} 个文件</div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

const MINIFIED_LINE_THRESHOLD = 240;
const MINIFIED_WINDOW = 200;

// 上下文展示：正常行号 + 命中高亮；压缩源码则用窗口展示
function renderContext(secret: SecretDetail) {
  const hit = secret.context_line || "";
  if (hit.length > MINIFIED_LINE_THRESHOLD) return renderMinifiedHit(secret);
  const before = secret.context_before ? secret.context_before.split("\n") : [];
  const after = secret.context_after ? secret.context_after.split("\n") : [];
  const startBefore = secret.line - before.length;
  return (
    <pre className="overflow-x-auto rounded-md border border-line-2 bg-surface-content py-2 font-mono text-[11.5px] leading-6 text-text-2">
      {before.map((line, index) => <ContextLine key={`b-${index}`} num={startBefore + index} line={line} />)}
      <ContextLine num={secret.line} line={hit} hit />
      {after.map((line, index) => <ContextLine key={`a-${index}`} num={secret.line + index + 1} line={line} />)}
    </pre>
  );
}

function ContextLine({ num, line, hit }: { num: number; line: string; hit?: boolean }) {
  return (
    <span className={cn("block pr-3", hit && "bg-[var(--brand-soft)]")}>
      <span className={cn("mr-3 inline-block w-12 select-none text-right text-text-4", hit && "font-semibold text-brand")}>{num}</span>
      {line}
    </span>
  );
}

// 压缩源码命中展示：在命中位置 ±200 字符的窗口中高亮显示
function renderMinifiedHit(secret: SecretDetail) {
  const line = secret.context_line || "";
  const value = secret.value || "";
  const meta = secret.metadata || {};
  const offset = Number.isFinite(meta.context_line_offset) ? Number(meta.context_line_offset) : 0;
  const fullSize = Number.isFinite(meta.context_line_full_size) ? Number(meta.context_line_full_size) : line.length;
  const colInLine = Number.isFinite(secret.col_start) ? secret.col_start : 0;
  let hitStart = Math.max(0, colInLine - offset);
  let hitEnd = hitStart + value.length;
  if (line.slice(hitStart, hitEnd) !== value) {
    const idx = line.indexOf(value);
    if (idx >= 0) {
      hitStart = idx;
      hitEnd = idx + value.length;
    }
  }
  const winStart = Math.max(0, hitStart - MINIFIED_WINDOW);
  const winEnd = Math.min(line.length, hitEnd + MINIFIED_WINDOW);
  const showLead = offset + winStart > 0;
  const showTrail = offset + winEnd < fullSize;
  const fmtLen = fullSize > 1024 ? `${(fullSize / 1024).toFixed(1)} KB` : `${fullSize} 字符`;
  return (
    <>
      <div className="mb-1.5 rounded-md border border-dashed border-line-2 bg-surface-chrome px-3 py-1.5 font-mono text-[11px] text-text-3">
        压缩源码 · 命中位于 line {secret.line} col {colInLine} · 原行 {fmtLen} · 仅展示命中位置 ±{MINIFIED_WINDOW} 字符窗口
      </div>
      <pre className="whitespace-pre-wrap break-all rounded-md border border-line-2 bg-surface-content px-3 py-2 font-mono text-[11.5px] leading-6 text-text-2">
        {showLead ? "... " : ""}
        {line.slice(winStart, hitStart)}
        <mark className="rounded bg-[var(--brand-soft)] px-0.5 font-semibold text-brand">{line.slice(hitStart, hitEnd)}</mark>
        {line.slice(hitEnd, winEnd)}
        {showTrail ? " ..." : ""}
      </pre>
    </>
  );
}
