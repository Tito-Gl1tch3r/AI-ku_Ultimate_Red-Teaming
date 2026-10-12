
import type { ReactNode } from "react";
import { prettyJson } from "@/lib/format";

type BodyBlockProps = {
  value?: unknown;
  empty?: string;
};

export function BodyBlock({ value, empty = "无响应正文" }: BodyBlockProps) {
  if (!value) return <div className="body-empty">{empty}</div>;
  const formatted = prettyJson(value);
  const highlight = isJsonLike(value, formatted);
  return <pre className="body-block">{highlight ? highlightJson(formatted) : formatted}</pre>;
}

function isJsonLike(value: unknown, formatted: string) {
  if (typeof value === "object") return true;
  const text = String(value || "").trimStart();
  if (text[0] !== "{" && text[0] !== "[") return false;
  try {
    JSON.parse(formatted);
    return true;
  } catch {
    return false;
  }
}

function highlightJson(text: string) {
  const nodes: ReactNode[] = [];
  let index = 0;
  const token = /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\btrue\b|\bfalse\b|\bnull\b)/g;
  let match: RegExpExecArray | null;
  while ((match = token.exec(text)) !== null) {
    if (match.index > index) nodes.push(text.slice(index, match.index));
    const raw = match[0];
    let className = "";
    if (raw.startsWith('"')) className = match[2] ? "json-key" : "json-string";
    else if (raw === "true" || raw === "false") className = "json-boolean";
    else if (raw === "null") className = "json-null";
    else className = "json-number";
    nodes.push(
      <span className={className} key={`${match.index}-${raw}`}>
        {raw}
      </span>,
    );
    index = match.index + raw.length;
  }
  if (index < text.length) nodes.push(text.slice(index));
  return nodes;
}
