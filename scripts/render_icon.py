#!/usr/bin/env python3
"""
Renders NextCue's launcher icon to PNG at every size the website and the
Play Store listing need.

Why this exists
---------------
The icon's real source of truth is the Android project's adaptive-icon
vector XML, not any PNG. Hand-redrawing it in an image editor is how the
website icon and the actual app icon silently drift apart. This script
reads that XML directly, so every PNG it emits is generated from the same
geometry the app itself ships.

Usage
-----
    # Preferred: read straight from the Android project (no drift possible)
    python3 scripts/render_icon.py --project ../NextCue

    # Or point at the res/ directory explicitly
    python3 scripts/render_icon.py --res ../NextCue/app/src/main/res

    # No Android project to hand? Falls back to the pinned geometry below.
    python3 scripts/render_icon.py

    # Write somewhere other than assets/
    python3 scripts/render_icon.py --project ../NextCue --out /tmp/icons

Requirements
------------
    pip install cairosvg pillow

Output
------
    assets/nextcue_icon.png              512x512  rounded, transparent  (website)
    assets/nextcue_icon_192.png          192x192  rounded, transparent
    assets/nextcue_icon_96.png            96x96   rounded, transparent
    assets/nextcue_playstore_icon_512.png 512x512 FULL SQUARE, NO ALPHA (Play Console)
    assets/nextcue_foreground_512.png    512x512  artwork only, transparent background

The Play Console icon slot rejects images with an alpha channel, which is
why that one is written as flat RGB on a solid background while the others
keep their transparency.

A note on the 18dp crop
-----------------------
Android adaptive icons are authored on a 108x108dp canvas, but the system
reserves the outer 18dp on each side for parallax and masking effects — a
launcher only ever displays the centre 72x72. Rendering viewBox "18 18 72 72"
therefore reproduces exactly what the icon looks like on a real phone.
This was verified by measuring a Redmi Note 12 Pro (HyperOS) screenshot
against this render: every element landed within ~1.5%.

If you ever change the icon
---------------------------
Edit the vector XML in the Android project as usual, re-run this script
with --project, and commit the regenerated PNGs. Nothing here needs editing.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

# ── Pinned fallback ──────────────────────────────────────────────────────
# Mirrors ic_launcher_foreground.xml / ic_launcher_background.xml as of
# v1.22, used only when the Android project isn't available to parse.
# Keep in sync if the icon changes and you can't run with --project.
FALLBACK_BACKGROUND = "#00C4B4"
FALLBACK_SHAPES = [
    # (pathData, fill, stroke, stroke_width, linecap, linejoin)
    ("M32,78 L32,36 L62,78", "none", "#FFFFFF", 12.0, "round", "round"),
    ("M67,28 A7,7 0 1,1 53,28 A7,7 0 1,1 67,28 Z", "#FFB800", "none", 0.0, "butt", "miter"),
    ("M58,49 L70,65 L82,39", "none", "#FFB800", 8.0, "round", "round"),
]

# Corner radius as a fraction of icon width, for the rounded/transparent
# variants. ~0.2237 approximates the squircle most Android launchers use.
CORNER_RADIUS_FRAC = 0.2237

SIZES_ROUNDED = [("nextcue_icon.png", 512), ("nextcue_icon_192.png", 192), ("nextcue_icon_96.png", 96)]
SUPERSAMPLE = 4  # render large, downsample with LANCZOS — keeps curves clean


def load_colors(res_dir: str) -> dict[str, str]:
    """Maps @color/name -> #RRGGBB from res/values/colors.xml."""
    colors: dict[str, str] = {}
    path = os.path.join(res_dir, "values", "colors.xml")
    if not os.path.exists(path):
        return colors
    for node in ET.parse(path).getroot().findall("color"):
        name, value = node.get("name"), (node.text or "").strip()
        if name and value.startswith("#"):
            colors[name] = value
    return colors


def resolve(value: str | None, colors: dict[str, str], default: str = "none") -> str:
    """Turns '@color/brand_cyan' or '#FFB800' into a CSS-usable colour."""
    if not value:
        return default
    value = value.strip()
    if value.startswith("@color/"):
        return colors.get(value[len("@color/"):], default)
    if value.startswith("#"):
        # #00000000 is Android's fully transparent, i.e. SVG's "none".
        if len(value) == 9:
            if value[1:3] == "00":
                return "none"
            return "#" + value[3:]  # drop the leading alpha pair
        return value
    return default


def parse_vector(path: str, colors: dict[str, str]):
    """Extracts drawable shapes from an Android <vector> XML file."""
    shapes = []
    for node in ET.parse(path).getroot().iter():
        if not node.tag.endswith("path"):
            continue
        data = node.get(f"{ANDROID_NS}pathData")
        if not data:
            continue
        shapes.append((
            data,
            resolve(node.get(f"{ANDROID_NS}fillColor"), colors),
            resolve(node.get(f"{ANDROID_NS}strokeColor"), colors),
            float(node.get(f"{ANDROID_NS}strokeWidth") or 0),
            node.get(f"{ANDROID_NS}strokeLineCap") or "butt",
            node.get(f"{ANDROID_NS}strokeLineJoin") or "miter",
        ))
    return shapes


def background_colour(res_dir: str, colors: dict[str, str]) -> str:
    """Reads the flat fill colour out of ic_launcher_background.xml."""
    path = os.path.join(res_dir, "drawable", "ic_launcher_background.xml")
    if not os.path.exists(path):
        return FALLBACK_BACKGROUND
    for shape in parse_vector(path, colors):
        if shape[1] != "none":
            return shape[1]
    return FALLBACK_BACKGROUND


def shapes_to_svg(shapes, background: str | None) -> str:
    """Wraps shapes as an SVG cropped to the launcher-visible 72x72 region."""
    parts = []
    if background:
        parts.append(f'<rect x="18" y="18" width="72" height="72" fill="{background}"/>')
    for data, fill, stroke, width, cap, join in shapes:
        attrs = [f'd="{data}"', f'fill="{fill}"']
        if stroke != "none" and width > 0:
            attrs += [
                f'stroke="{stroke}"',
                f'stroke-width="{width}"',
                f'stroke-linecap="{cap}"',
                f'stroke-linejoin="{join}"',
            ]
        parts.append(f'<path {" ".join(attrs)}/>')
    body = "\n  ".join(parts)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="18 18 72 72">\n  '
        f"{body}\n</svg>"
    )


def render(svg: str, px: int):
    import cairosvg
    from PIL import Image

    png = cairosvg.svg2png(
        bytestring=svg.encode(),
        output_width=px * SUPERSAMPLE,
        output_height=px * SUPERSAMPLE,
    )
    return Image.open(io.BytesIO(png)).convert("RGBA")


def rounded(img, px: int):
    from PIL import Image, ImageDraw

    big = px * SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, big - 1, big - 1], radius=int(big * CORNER_RADIUS_FRAC), fill=255
    )
    img.putalpha(mask)
    return img.resize((px, px), Image.LANCZOS)


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)

    ap = argparse.ArgumentParser(description="Render NextCue icons from the Android vector XML.")
    ap.add_argument("--project", help="Path to the NextCue Android project root")
    ap.add_argument("--res", help="Path to app/src/main/res (overrides --project)")
    ap.add_argument("--out", default=os.path.join(repo, "assets"), help="Output directory")
    args = ap.parse_args()

    try:
        import cairosvg  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Missing dependencies. Run:  pip install cairosvg pillow", file=sys.stderr)
        return 1

    res_dir = args.res
    if not res_dir and args.project:
        res_dir = os.path.join(args.project, "app", "src", "main", "res")

    if res_dir and os.path.isdir(res_dir):
        colors = load_colors(res_dir)
        fg = os.path.join(res_dir, "drawable", "ic_launcher_foreground.xml")
        if not os.path.exists(fg):
            print(f"No ic_launcher_foreground.xml under {res_dir}", file=sys.stderr)
            return 1
        shapes = parse_vector(fg, colors)
        background = background_colour(res_dir, colors)
        print(f"Parsed {len(shapes)} shape(s) from {os.path.relpath(fg)}")
    else:
        if res_dir:
            print(f"Warning: {res_dir} not found — using pinned fallback geometry.", file=sys.stderr)
        else:
            print("No --project/--res given — using pinned fallback geometry.")
        shapes, background = FALLBACK_SHAPES, FALLBACK_BACKGROUND

    os.makedirs(args.out, exist_ok=True)
    svg_full = shapes_to_svg(shapes, background)
    svg_fg = shapes_to_svg(shapes, None)

    from PIL import Image

    for name, px in SIZES_ROUNDED:
        rounded(render(svg_full, px), px).save(os.path.join(args.out, name))
        print(f"  wrote {name}  ({px}x{px}, rounded, transparent)")

    # Play Console rejects alpha, so flatten onto the background colour.
    play = render(svg_full, 512).resize((512, 512), Image.LANCZOS)
    flat = Image.new("RGB", (512, 512), background)
    flat.paste(play, (0, 0), play)
    flat.save(os.path.join(args.out, "nextcue_playstore_icon_512.png"))
    print("  wrote nextcue_playstore_icon_512.png  (512x512, full square, NO alpha)")

    render(svg_fg, 512).resize((512, 512), Image.LANCZOS).save(
        os.path.join(args.out, "nextcue_foreground_512.png")
    )
    print("  wrote nextcue_foreground_512.png  (artwork only, transparent)")

    print(f"\nDone — output in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
