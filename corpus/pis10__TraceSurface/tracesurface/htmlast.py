from __future__ import annotations

import re

_SCRIPT_TAG = re.compile(
    r"<script\b([^>]*)>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_HAS_SRC = re.compile(r"\bsrc\s*=", re.IGNORECASE)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

MIN_SCRIPT_LENGTH = 100


def extract_inline_scripts(html: str) -> list[tuple[int, str]]:
    def blank_comment(match: re.Match[str]) -> str:
        return "".join("\n" if ch == "\n" else " " for ch in match.group(0))

    cleaned = _HTML_COMMENT.sub(blank_comment, html)
    results: list[tuple[int, str]] = []
    for match in _SCRIPT_TAG.finditer(cleaned):
        attrs, raw = match.group(1), match.group(2)

        if _HAS_SRC.search(attrs):
            continue
        content = raw.strip()

        if len(content) < MIN_SCRIPT_LENGTH:
            continue

        leading = len(raw) - len(raw.lstrip())

        start_line = cleaned[: match.start(2) + leading].count("\n")
        results.append((start_line, content))
    return results
