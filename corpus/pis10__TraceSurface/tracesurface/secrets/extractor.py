from __future__ import annotations

from tracesurface.htmlast import extract_inline_scripts
from tracesurface.models import SecretMatch
from tracesurface.secrets.rules import RULES

MAX_SECRET_SCAN_BYTES = 50 * 1024 * 1024
CONTEXT_LINES = 5
CONTEXT_LINE_MAX_BYTES = 4 * 1024


class SecretScanner:
    def __init__(self) -> None:
        self.results: list[SecretMatch] = []
        self.seen: set[tuple[str, str, str]] = set()
        self.total_bytes = 0

    def scan_js(self, url: str, text: str) -> list[SecretMatch]:
        return self.scan_source(url, text, 0)

    def scan_html(self, html_url: str, html: str) -> list[SecretMatch]:
        matches: list[SecretMatch] = []
        if not html:
            return matches

        for idx, (start_line_0, body) in enumerate(extract_inline_scripts(html)):
            matches.extend(
                self.scan_source(f"{html_url}#script[{idx}]", body, start_line_0)
            )
        return matches

    def scan_source(
        self,
        source_label: str,
        text: str,
        line_offset: int = 0,
    ) -> list[SecretMatch]:
        if not text or self.total_bytes >= MAX_SECRET_SCAN_BYTES:
            return []

        self.total_bytes += len(text)

        line_starts = _line_starts(text)
        matches: list[SecretMatch] = []

        for rule in RULES:
            for m in rule.pattern.finditer(text):
                if rule.s_pattern is not None and not rule.s_pattern.search(m.group()):
                    continue
                value = m.group()
                line_in_text, col_start = _pos_to_line_col(line_starts, m.start())

                line = line_in_text + line_offset

                key = (rule.rule_id, value, source_label)
                if key in self.seen:
                    continue
                self.seen.add(key)

                (
                    ctx_before,
                    ctx_line,
                    ctx_after,
                    ctx_line_offset,
                    ctx_line_full_size,
                ) = _slice_context(text, line_in_text, col_start)
                full_meta: dict[str, object] = {}

                if ctx_line_offset > 0 or ctx_line_full_size != len(ctx_line):
                    full_meta["context_line_offset"] = ctx_line_offset
                    full_meta["context_line_full_size"] = ctx_line_full_size

                match = SecretMatch(
                    rule_id=rule.rule_id,
                    rule_group=rule.rule_group,
                    sensitive=rule.sensitive,
                    value=value,
                    source_js=source_label,
                    line=line,
                    col_start=col_start,
                    context_before=ctx_before,
                    context_line=ctx_line,
                    context_after=ctx_after,
                    metadata=full_meta,
                )
                matches.append(match)
                self.results.append(match)
        return matches


def _line_starts(text: str) -> list[int]:
    starts = [0]
    offset = 0

    for line in text.splitlines(keepends=True):
        offset += len(line)
        if offset < len(text):
            starts.append(offset)
    return starts


def _pos_to_line_col(line_starts: list[int], pos: int) -> tuple[int, int]:
    if pos <= 0:
        return 1, 0

    lo, hi = 0, len(line_starts)
    while lo < hi:
        mid = (lo + hi) // 2
        if line_starts[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    line_idx = lo - 1

    return line_idx + 1, pos - line_starts[line_idx]


def _slice_context(
    text: str,
    hit_line_1based: int,
    hit_col: int,
) -> tuple[str, str, str, int, int]:
    lines = text.splitlines()
    idx = hit_line_1based - 1

    if idx < 0 or idx >= len(lines):
        return "", "", "", 0, 0

    before_start = max(0, idx - CONTEXT_LINES)
    after_end = min(len(lines), idx + 1 + CONTEXT_LINES)
    before = "\n".join(lines[before_start:idx])
    hit = lines[idx]
    after = "\n".join(lines[idx + 1 : after_end])

    full_size = len(hit)
    hit_offset = 0

    if full_size > CONTEXT_LINE_MAX_BYTES:
        half = CONTEXT_LINE_MAX_BYTES // 2

        win_start = max(0, hit_col - half)
        win_end = min(full_size, win_start + CONTEXT_LINE_MAX_BYTES)
        win_start = max(0, win_end - CONTEXT_LINE_MAX_BYTES)
        hit = hit[win_start:win_end]
        hit_offset = win_start

    if len(before) > CONTEXT_LINE_MAX_BYTES:
        before = before[-CONTEXT_LINE_MAX_BYTES:]
    if len(after) > CONTEXT_LINE_MAX_BYTES:
        after = after[:CONTEXT_LINE_MAX_BYTES]

    return before, hit, after, hit_offset, full_size
