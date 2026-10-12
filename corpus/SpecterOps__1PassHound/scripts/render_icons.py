#!/usr/bin/env python3
"""
Render PNG node icons from a BloodHound OpenGraph extension schema.

Reads schema.json and generates a PNG icon for each node kind.
Each icon is a colored circle with a black border and a centered black
Font Awesome icon silhouette.

Dependencies (pure Python — no native C libraries required):
    pip install Pillow svgpathtools numpy requests

Usage:
    python3 scripts/render_icons.py [options]

Options:
    --schema PATH    Path to schema.json (default: schema.json in repo root)
    --output PATH    Output directory for PNGs (default: images/)
    --prefix TEXT    Filename prefix (default: none, e.g. --prefix black_)
    --size N         Output image size in pixels (default: 220)
    --scale F        Icon scale relative to image size (default: 0.55)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── Dependency check ────────────────────────────────────────────────
_missing = []
try:
    from PIL import Image, ImageDraw
except ImportError:
    _missing.append("Pillow")
try:
    from svgpathtools import parse_path
except ImportError:
    _missing.append("svgpathtools")
try:
    import requests
except ImportError:
    _missing.append("requests")

if _missing:
    print(
        "Missing Python dependencies: " + ", ".join(_missing),
        file=sys.stderr,
    )
    print(
        "Install with:  pip3 install Pillow svgpathtools numpy requests",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Constants ───────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

FA_SVG_URL = (
    "https://raw.githubusercontent.com/FortAwesome/Font-Awesome"
    "/refs/heads/7.x/svgs/solid/{name}.svg"
)

# Caches
_svg_cache: dict[str, str] = {}

# Points per unit length when sampling bezier curves
SAMPLES_PER_UNIT = 0.15


def fetch_icon_svg(icon_name: str) -> str:
    """Download a Font Awesome SVG and return its text."""
    if icon_name in _svg_cache:
        return _svg_cache[icon_name]

    url = FA_SVG_URL.format(name=icon_name)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
    _svg_cache[icon_name] = text
    return text


def parse_svg_viewbox(svg_text: str) -> tuple[float, float, float, float]:
    """Extract viewBox from SVG text."""
    m = re.search(r'viewBox="([^"]+)"', svg_text)
    if not m:
        raise ValueError("No viewBox found in SVG")
    parts = m.group(1).split()
    return tuple(float(x) for x in parts)  # type: ignore


def parse_svg_paths(svg_text: str) -> list[str]:
    """Extract all <path d="..."> data strings from SVG text."""
    return re.findall(r'<path[^>]*\bd="([^"]+)"', svg_text)


def path_to_polygons(
    d: str,
    target_size: int,
    vb_x: float,
    vb_y: float,
    vb_w: float,
    vb_h: float,
) -> list[list[tuple[float, float]]]:
    """
    Convert an SVG path 'd' attribute into a list of polygon point lists.

    Each sub-path (separated by M/m commands) becomes a separate polygon.
    Bezier curves are sampled into line segments.
    Coordinates are scaled from viewBox space to target pixel space,
    centered in target_size.
    """
    path = parse_path(d)

    # Compute scale to fit viewBox into target_size, preserving aspect ratio
    scale = target_size / max(vb_w, vb_h)
    # Center offset
    ox = (target_size - vb_w * scale) / 2 - vb_x * scale
    oy = (target_size - vb_h * scale) / 2 - vb_y * scale

    polygons: list[list[tuple[float, float]]] = []
    current_poly: list[tuple[float, float]] = []

    for seg in path:
        # Determine number of sample points based on segment length
        seg_len = seg.length()
        n_points = max(2, int(seg_len * SAMPLES_PER_UNIT))

        start_pt = seg.point(0)
        sx = start_pt.real * scale + ox
        sy = start_pt.imag * scale + oy

        # Check if this is a new sub-path (discontinuity)
        if current_poly and (
            abs(sx - current_poly[-1][0]) > 1 or abs(sy - current_poly[-1][1]) > 1
        ):
            if len(current_poly) >= 3:
                polygons.append(current_poly)
            current_poly = []

        if not current_poly:
            current_poly.append((sx, sy))

        # Sample points along the segment
        for i in range(1, n_points + 1):
            t = i / n_points
            pt = seg.point(t)
            px = pt.real * scale + ox
            py = pt.imag * scale + oy
            current_poly.append((px, py))

    if len(current_poly) >= 3:
        polygons.append(current_poly)

    return polygons


def render_icon(
    icon_name: str,
    fill_color: str,
    image_size: int = 220,
    icon_scale: float = 0.55,
    border_width: int = 0,
) -> Image.Image:
    """
    Render a single node icon as a Pillow RGBA Image.

    1. Draw a filled circle in fill_color with a black border.
    2. Parse the Font Awesome SVG path and render as filled polygons.
    3. Return the composited image.
    """
    if border_width == 0:
        border_width = max(2, int(image_size * 0.054))

    # ── Supersample for antialiasing ────────────────────────────────
    ss = 4
    ss_size = image_size * ss
    ss_border = border_width * ss

    canvas = Image.new("RGBA", (ss_size, ss_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    center = ss_size // 2
    radius = center - ss_border // 2

    # Filled circle with black border
    bbox = [
        center - radius,
        center - radius,
        center + radius,
        center + radius,
    ]
    draw.ellipse(bbox, fill=fill_color, outline="black", width=ss_border)

    # ── Parse and render SVG icon ───────────────────────────────────
    svg_text = fetch_icon_svg(icon_name)
    vb = parse_svg_viewbox(svg_text)
    path_strings = parse_svg_paths(svg_text)

    icon_target = int(ss_size * icon_scale)
    icon_offset = (ss_size - icon_target) // 2

    for d in path_strings:
        polygons = path_to_polygons(d, icon_target, vb[0], vb[1], vb[2], vb[3])
        for poly in polygons:
            # Offset polygons to center on canvas
            shifted = [(x + icon_offset, y + icon_offset) for x, y in poly]
            if len(shifted) >= 3:
                draw.polygon(shifted, fill="black")

    # ── Downsample ──────────────────────────────────────────────────
    final = canvas.resize((image_size, image_size), Image.LANCZOS)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render PNG node icons from an OpenGraph extension schema"
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=REPO_ROOT / "schema.json",
        help="Path to schema.json (default: schema.json in repo root)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "Documentation" / "Icons",
        help="Output directory for PNGs (default: Documentation/Icons/)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Filename prefix (e.g. 'black_' produces 'black_OP_User.png')",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=220,
        help="Output image size in pixels (default: 220)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.55,
        help="Icon scale relative to image size (default: 0.55)",
    )
    args = parser.parse_args()

    schema_path = args.schema.resolve()
    output_dir = args.output.resolve()

    if not schema_path.exists():
        print(f"Error: {schema_path} not found", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(schema_path) as f:
        schema = json.load(f)

    node_kinds = schema.get("node_kinds", [])
    if not node_kinds:
        print("No node_kinds found in schema", file=sys.stderr)
        sys.exit(1)

    # Filter to nodes that have real (non-placeholder) icons and colors
    renderable = [
        nk for nk in node_kinds
        if nk.get("icon", "placeholder") != "placeholder"
        and nk.get("color", "#000000") != "#000000"
    ]

    if not renderable:
        print("No node kinds with assigned icons and colors found", file=sys.stderr)
        print("Run /select-icons-colors first to assign icons and colors", file=sys.stderr)
        sys.exit(1)

    skipped = len(node_kinds) - len(renderable)
    if skipped:
        print(f"[*] Skipping {skipped} node kind(s) with placeholder icons/colors")

    print(f"[*] Rendering {len(renderable)} node icons ({args.size}x{args.size}px)")

    rendered = 0
    errors = 0

    for node in sorted(renderable, key=lambda n: n["name"]):
        node_name = node["name"]
        icon_name = node["icon"]
        icon_color = node["color"]

        try:
            img = render_icon(
                icon_name=icon_name,
                fill_color=icon_color,
                image_size=args.size,
                icon_scale=args.scale,
            )
            filename = f"{args.prefix}{node_name}.png"
            out_path = output_dir / filename
            img.save(out_path, "PNG")
            print(f"  [+] {filename}")
            rendered += 1
        except requests.exceptions.HTTPError as e:
            print(f"  [!] {node_name}: Failed to fetch icon '{icon_name}' — {e}")
            errors += 1
        except Exception as e:
            print(f"  [!] {node_name}: {e}")
            errors += 1

    print(f"[+] Done. Rendered: {rendered}, Errors: {errors}")

    if errors:
        print(
            "\n[!] Some icons failed to render. Check that the icon names in "
            "schema.json match Font Awesome 6 Free Solid icon names.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
