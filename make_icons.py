#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rasteriserar klubbloggan (Alingsas_HK_logo.svg) till app-/favicon-PNG:er.

Körs lokalt vid behov (ikoner är statiska – CI behöver inte rendera dem).
Kräver: cairosvg, Pillow.

Genererar:
  icon-180.png            apple-touch-icon (iPhone, ogenomskinlig)
  icon-192.png            Android (any)
  icon-512.png            Android (any) + og:image
  icon-512-maskable.png   Android maskable (logo inom säker zon)
  favicon-32.png          favicon-fallback (genomskinlig)
Favikon i övrigt: SVG:n används direkt i <link rel=icon>.
"""

import io
import os
import sys

import cairosvg
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Alingsas_HK_logo.svg")
NAVY = (0x13, 0x29, 0x3d, 255)
SS = 4  # supersampling för mjuka kanter


def render_logo(height_px):
    png = cairosvg.svg2png(url=SRC, output_height=height_px)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def icon(size, frac, bg):
    S = size * SS
    canvas = Image.new("RGBA", (S, S), bg)
    logo = render_logo(int(S * frac))
    canvas.alpha_composite(logo, ((S - logo.width) // 2, (S - logo.height) // 2))
    out = canvas.resize((size, size), Image.LANCZOS)
    return out if bg[3] == 0 else out.convert("RGB")


def main():
    if not os.path.exists(SRC):
        sys.exit("Saknar " + SRC)
    jobs = [
        ("icon-180.png", 180, 0.84, NAVY),
        ("icon-192.png", 192, 0.84, NAVY),
        ("icon-512.png", 512, 0.84, NAVY),
        ("icon-512-maskable.png", 512, 0.70, NAVY),
        ("favicon-32.png", 32, 0.92, (0, 0, 0, 0)),
    ]
    for fn, size, frac, bg in jobs:
        icon(size, frac, bg).save(os.path.join(ROOT, fn))
        print("skrev", fn, f"({size}px)")


if __name__ == "__main__":
    main()
