"use client";

import { Block, type BlockProps } from "streamdown";
import { DefaultCodeBlock } from "./code-block";

function parseFencedCodeBlock(
  content: string,
  isIncomplete: boolean
): { code: string; language: string } | null {
  const trimmed = content.trim();

  if (!trimmed.startsWith("```")) {
    return null;
  }

  const firstNewline = trimmed.indexOf("\n");
  if (firstNewline === -1) {
    return null;
  }

  const fenceLine = trimmed.slice(0, firstNewline);
  const language = fenceLine.slice(3).trim().split(/\s+/)[0] || "text";

  let code = trimmed.slice(firstNewline + 1);
  const hasClosingFence = /\n```[\t ]*$/.test(code) || code === "```";

  if (hasClosingFence) {
    code = code.replace(/\n```[\t ]*$/, "");
    if (code === "```") {
      code = "";
    }
  } else if (!isIncomplete) {
    return null;
  }

  return { code, language };
}

export function StreamdownBlock(props: BlockProps) {
  const parsed = parseFencedCodeBlock(props.content, props.isIncomplete);

  if (!parsed) {
    return <Block {...props} />;
  }

  return (
    <DefaultCodeBlock
      code={parsed.code}
      language={parsed.language}
      className="rounded-none"
    />
  );
}
