#!/usr/bin/env python3
"""Render the favicon raster fallbacks from the same geometry as src/favicon.svg.

Browsers rasterise SVG favicons unevenly, and some browsers/OS shells only look
for a PNG or an .ico. So we ship all three: SVG (vector), PNG 16/32 (tab +
bookmark) and apple-touch-icon 180 (iOS home screen), plus a multi-size .ico
for the Windows/legacy path. Drawn at 4x and downsampled so the letters stay
crisp at 16px.

Run from the repo root:  python src/make_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent

INK = (20, 21, 17, 255)      # #141511
CREAM = (242, 239, 229, 255)  # #f2efe5
ACCENT = (233, 73, 27, 255)   # #e9491b

SS = 8  # supersample factor


def render(size: int) -> Image.Image:
    n = size * SS
    img = Image.new("RGBA", (n, n), INK)
    d = ImageDraw.Draw(img)
    k = n / 64.0  # SVG user units -> device px
    w = max(1, round(5.2 * k))

    def pt(x: float, y: float) -> tuple[float, float]:
        return (x * k, y * k)

    # "A": two diagonals + crossbar
    d.line([pt(9, 46), pt(18, 18)], fill=CREAM, width=w, joint="curve")
    d.line([pt(18, 18), pt(27, 46)], fill=CREAM, width=w, joint="curve")
    d.line([pt(13, 36.5), pt(23, 36.5)], fill=CREAM, width=w)
    # round the stroke ends like stroke-linecap="round"
    r = w / 2
    for cx, cy in [(9, 46), (18, 18), (27, 46), (13, 36.5), (23, 36.5)]:
        x, y = pt(cx, cy)
        d.ellipse([x - r, y - r, x + r, y + r], fill=CREAM)

    # "C": a ring with the right side erased by the tile colour
    cx, cy, rr = 44, 32, 11.5
    box = [pt(cx - rr, cy - rr), pt(cx + rr, cy + rr)]
    d.arc([box[0][0], box[0][1], box[1][0], box[1][1]], start=45, end=315, fill=CREAM, width=w)
    d.rectangle([pt(43, 24), pt(59, 40)], fill=INK)

    # the signal bar, bottom-right
    d.rectangle([pt(43, 53), pt(57, 56.5)], fill=ACCENT)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    (ROOT / "favicon.svg").write_text(
        (SRC / "favicon.svg").read_text(encoding="utf-8"), encoding="utf-8"
    )
    for size, name in [(16, "favicon-16.png"), (32, "favicon-32.png"),
                       (180, "apple-touch-icon.png")]:
        render(size).save(ROOT / name)
        print(f"wrote {name}")
    big = render(64)
    big.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("wrote favicon.ico (16/32/48/64)")


if __name__ == "__main__":
    main()
