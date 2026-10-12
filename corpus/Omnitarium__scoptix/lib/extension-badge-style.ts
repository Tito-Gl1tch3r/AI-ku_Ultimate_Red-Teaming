const EXT_BADGE_PALETTE = [
  {
    bg: "bg-slate-500/10",
    text: "text-slate-600 dark:text-slate-400",
    border: "border-slate-500/25",
  },
  {
    bg: "bg-stone-500/10",
    text: "text-stone-600 dark:text-stone-400",
    border: "border-stone-500/25",
  },
  {
    bg: "bg-zinc-500/10",
    text: "text-zinc-600 dark:text-zinc-400",
    border: "border-zinc-500/25",
  },
  {
    bg: "bg-teal-500/10",
    text: "text-teal-700 dark:text-teal-500/90",
    border: "border-teal-500/20",
  },
  {
    bg: "bg-cyan-500/10",
    text: "text-cyan-800 dark:text-cyan-500/90",
    border: "border-cyan-500/20",
  },
  {
    bg: "bg-sky-500/10",
    text: "text-sky-700 dark:text-sky-400/90",
    border: "border-sky-500/20",
  },
  {
    bg: "bg-blue-500/10",
    text: "text-blue-700 dark:text-blue-400/90",
    border: "border-blue-500/20",
  },
  {
    bg: "bg-indigo-500/10",
    text: "text-indigo-700 dark:text-indigo-400/90",
    border: "border-indigo-500/20",
  },
  {
    bg: "bg-violet-500/10",
    text: "text-violet-700 dark:text-violet-400/90",
    border: "border-violet-500/20",
  },
  {
    bg: "bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-400/90",
    border: "border-emerald-500/20",
  },
] as const;

function hashExtension(ext: string): number {
  const normalized = ext.trim().toLowerCase();
  let hash = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = (hash * 31 + normalized.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function extensionBadgeClassName(ext: string | null | undefined): string {
  if (!ext) {
    return "border-line bg-black/15 text-cream/70 dark:bg-white/5";
  }

  const palette = EXT_BADGE_PALETTE[hashExtension(ext) % EXT_BADGE_PALETTE.length]!;
  return [palette.bg, palette.text, palette.border].join(" ");
}
