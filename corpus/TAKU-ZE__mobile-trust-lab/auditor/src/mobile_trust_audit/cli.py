from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import render_html, render_json, render_markdown
from .scanner import scan_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mobile-trust-audit",
        description="Scan an Android source or decoded project for client trust-boundary weaknesses.",
    )
    parser.add_argument("target", help="Directory containing an AndroidManifest.xml")
    parser.add_argument(
        "--format",
        choices=("json", "markdown", "html"),
        default="json",
        help="Report format (default: json)",
    )
    parser.add_argument("--output", type=Path, help="Write the report to this path")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Return exit code 2 when findings are present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        findings = scan_project(args.target)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    renderers = {
        "json": render_json,
        "markdown": render_markdown,
        "html": render_html,
    }
    report = renderers[args.format](findings)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"wrote {args.output} ({len(findings)} findings)")
    else:
        print(report, end="")
    if findings and args.fail_on_findings:
        return 2
    return 0

