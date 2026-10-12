from __future__ import annotations

import html
import json
from collections import Counter

from .models import Finding


def render_json(findings: list[Finding]) -> str:
    payload = {
        "schema": "mobile-trust-audit/v1",
        "summary": dict(Counter(f.severity for f in findings)),
        "findings": [finding.to_dict() for finding in findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_markdown(findings: list[Finding]) -> str:
    lines = ["# Mobile Trust Audit Report", "", f"Total findings: **{len(findings)}**", ""]
    if not findings:
        lines.append("No findings were detected by the current rule set.")
        return "\n".join(lines) + "\n"
    for finding in findings:
        lines.extend(
            [
                f"## {finding.rule_id}: {finding.title}",
                "",
                f"- Severity: **{finding.severity}**",
                f"- File: `{finding.file}`",
                f"- Evidence: {finding.evidence}",
                f"- Remediation: {finding.remediation}",
                "",
            ]
        )
    return "\n".join(lines)


def render_html(findings: list[Finding]) -> str:
    counts = Counter(f.severity for f in findings)
    cards = []
    for finding in findings:
        cards.append(
            f"""
            <article class="finding {html.escape(finding.severity.lower())}">
              <div class="heading"><span>{html.escape(finding.rule_id)}</span>
              <strong>{html.escape(finding.severity)}</strong></div>
              <h2>{html.escape(finding.title)}</h2>
              <p><b>File:</b> <code>{html.escape(finding.file)}</code></p>
              <p><b>Evidence:</b> {html.escape(finding.evidence)}</p>
              <p><b>Remediation:</b> {html.escape(finding.remediation)}</p>
            </article>"""
        )
    body = "\n".join(cards) or "<p class='clean'>No findings were detected.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mobile Trust Audit Report</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
    body {{ max-width: 960px; margin: 0 auto; padding: 40px 24px; background:#0b1020; color:#e8eefc; }}
    header {{ border-bottom:1px solid #29334f; margin-bottom:24px; }}
    .summary {{ display:flex; gap:12px; flex-wrap:wrap; margin:20px 0; }}
    .pill {{ background:#17213b; border:1px solid #344263; border-radius:999px; padding:8px 14px; }}
    .finding {{ background:#121a2e; border:1px solid #2b3859; border-left:5px solid #ef4444; border-radius:12px; padding:20px; margin:16px 0; }}
    .finding.medium {{ border-left-color:#f59e0b; }}
    .heading {{ display:flex; justify-content:space-between; color:#9fb0d8; }}
    code {{ color:#9ee7ff; }}
    .clean {{ color:#86efac; font-size:1.1rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Mobile Trust Audit Report</h1>
    <p>Deterministic checks for Android client trust-boundary weaknesses.</p>
    <div class="summary">
      <span class="pill">Total: {len(findings)}</span>
      <span class="pill">High: {counts.get('HIGH', 0)}</span>
      <span class="pill">Medium: {counts.get('MEDIUM', 0)}</span>
    </div>
  </header>
  <main>{body}</main>
</body>
</html>
"""

