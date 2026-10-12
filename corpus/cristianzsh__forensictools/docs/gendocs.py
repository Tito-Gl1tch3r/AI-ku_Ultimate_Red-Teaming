#!/usr/bin/env python3
"""
gendocs.py: build help.html from the section files.
"""

import argparse
import collections
import glob
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from descriptions import DESCRIPTIONS, PYTHON_EXTRAS  # noqa: E402

# Categories with no SectionGroup of their own.
STANDALONE = {"onlinesearch": "Online search"}

CSS = """
            body {
                background-color: #2E3440;
                color: #E5E9F0;
                font-family: Arial;
                padding: 30px;
            }

            h1 {
                padding-bottom: 20px;
            }

            details {
                padding-bottom: 20px;
            }

            summary {
                font-size: 20px;
                cursor: pointer;
            }

            code {
                font-family: Courier;
            }

            pre {
                padding-left: 30px;
            }

            a {
                color: #E5E9F0;
            }

            .description {
                padding: 25px;
            }

            #logo {
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 50%;
            }

            #index {
                text-align: center;
                line-height: 2;
                padding-bottom: 20px;
            }

            .count {
                font-size: 14px;
                font-weight: normal;
                opacity: 0.6;
            }
"""

REVIEW_CSS = """
            .todo {
                font-size: 12px;
                background-color: #BF616A;
                color: #ECEFF4;
                border-radius: 3px;
                padding: 2px 6px;
                vertical-align: middle;
            }
"""


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def collect(src):
    """Return [(display, slug, [(name, url), ...]), ...] in sections.nsh order."""
    inc = read(os.path.join(src, "include", "sections.nsh"))
    order = [
        (d, g.lower())
        for d, g in re.findall(r'SectionGroup /e "([^"]+)" SECGRP_(\w+)', inc)
    ]

    tools = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(src, "sections", "*", "*.nsh"))):
        cat = os.path.basename(os.path.dirname(path))
        text = read(path)
        m = re.search(
            r'FT_TOOL_(?:BEGIN|FILES)\s+"([^"]+)"', text
        ) or re.search(r'^Section\s+"([^"]+)"', text, re.M)
        if not m:
            continue
        name = m.group(1).replace("$$", "$") # undo NSIS escaping
        header = re.match(r";\s*(.*)", text)
        url = ""
        if header:
            u = re.search(r"\((https?://[^)]+)\)", header.group(1))
            if u:
                url = u.group(1)
        tools[cat].append((name, url))

    grouped = {slug for _, slug in order}
    extra = [
        (STANDALONE.get(c, c.capitalize()), c)
        for c in sorted(tools)
        if c not in grouped
    ]
    return [
        (disp, slug, sorted(tools.get(slug, []), key=lambda x: x[0].lower()))
        for disp, slug in order + extra
    ]


def entry(name, url, review, missing):
    d = DESCRIPTIONS.get(name)
    badge = ""
    css = ""
    if d is None:
        missing.append(name)
        link = (
            f'<a href="{html.escape(url)}" target="_blank">{html.escape(name)}</a>'
            if url
            else f"<strong>{html.escape(name)}</strong>"
        )
        body = f"<p>{link} - no description yet.</p>"
        examples = None
        if review:
            badge = ' <span class="todo">no description</span>'
            css = ' class="todo-entry"'
    else:
        body = d["html"]
        examples = d.get("examples")

    out = [
        f"            <details{css}>",
        f"                <summary>{html.escape(name)}{badge}</summary>",
        '                <div class="description">',
        "                    " + body,
    ]
    if examples:
        out += [
            "",
            "                    <p><strong>Examples:</strong></p>",
            "",
            "                    <pre><code>"
            + "\n".join(html.escape(x) for x in examples)
            + "</code></pre>",
        ]
    out += ["                </div>", "            </details>", ""]
    return "\n".join(out)


def build(src, review):
    sections = collect(src)
    missing = []

    nav = " &middot; ".join(
        f'<a href="#{slug}">{html.escape(disp)}</a>' for disp, slug, _ in sections
    )

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "    <head>",
        "        <title>forensictools</title>",
        '        <meta charset="UTF-8">',
        "        <style>" + CSS + (REVIEW_CSS if review else "") + " </style>",
        "    </head>",
        "",
        "    <body>",
        '        <img id="logo" src="forensictools_full.png"/>',
        "",
        f'        <p id="index">{nav}</p>',
        "",
        "        <hr/>",
    ]

    for disp, slug, items in sections:
        parts.append(f'\n        <section id="{slug}">')
        parts.append(
            f'            <h1>{html.escape(disp)} '
            f'<span class="count">({len(items)})</span></h1>'
        )
        for name, url in items:
            parts.append(entry(name, url, review, missing))
        parts.append("        </section>\n")
        parts.append("        <hr/>\n")

    # Python scripts have no section file of their own.
    parts.append('\n        <section id="pythonextras">')
    parts.append(
        f'            <h1>Python scripts '
        f'<span class="count">({len(PYTHON_EXTRAS)})</span></h1>'
    )
    parts.append(
        '            <p class="description">Extra scripts under '
        "<code>utilities\\python\\extras_forensictools</code>. Each one is on the "
        "PATH and can be run by name, without <code>python.exe</code> or a full "
        "path.</p>\n"
    )
    for name, body, examples in PYTHON_EXTRAS:
        parts.append("            <details>")
        parts.append(f"                <summary>{html.escape(name)}</summary>")
        parts.append('                <div class="description">')
        parts.append("                    " + body)
        if examples:
            parts += [
                "",
                "                    <p><strong>Examples:</strong></p>",
                "",
                "                    <pre><code>"
                + "\n".join(html.escape(x) for x in examples)
                + "</code></pre>",
            ]
        parts += ["                </div>", "            </details>", ""]
    parts.append("        </section>")
    parts.append("    </body>")
    parts.append("</html>")

    return "\n".join(parts), sections, missing


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(os.path.dirname(here), "src"))
    ap.add_argument("--out", default=os.path.join(here, "help.html"))
    ap.add_argument(
        "--review",
        action="store_true",
        help="mark entries that have no description in descriptions.py",
    )
    args = ap.parse_args()

    page, sections, missing = build(args.src, args.review)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)

    total = sum(len(i) for _, _, i in sections)
    print(f"{args.out}: {len(sections)} sections, {total} tools")
    if missing:
        print("\nno description in descriptions.py:")
        for m in sorted(missing):
            print("   ", m)
        return 1
    print("every tool has a description")
    return 0


if __name__ == "__main__":
    sys.exit(main())
