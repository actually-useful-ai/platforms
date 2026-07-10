# File Purpose: Full-wrap KDP cover geometry and SVG layout generation.
# Primary Functions/Classes: build_cover_assets.
# Inputs/Outputs: BookMeta + output dir in; cover asset paths and notes out.

from __future__ import annotations

import json
from pathlib import Path

from platforms.kdp.book import BookMeta
from platforms.kdp.print_pdf import cover_width_inches, spine_width_inches


def build_cover_assets(meta: BookMeta, output_dir: Path) -> tuple[list[Path], list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    trim_w, trim_h = meta.trim_inches
    spine = spine_width_inches(meta.page_count_estimate, meta.paper)
    full_w, full_h = cover_width_inches(
        trim_w, trim_h, meta.page_count_estimate, meta.paper, meta.bleed_inches
    )
    spec = {
        "title": meta.title,
        "trim_inches": [trim_w, trim_h],
        "bleed_inches": meta.bleed_inches,
        "spine_inches": round(spine, 4),
        "full_wrap_inches": [round(full_w, 4), round(full_h, 4)],
        "dpi": 300,
        "barcode_reserve_inches": {"width": 2.0, "height": 1.2, "from_right": 0.25, "from_bottom": 0.25},
        "safe_zone_inches": 0.125,
        "paper": meta.paper,
        "page_count_estimate": meta.page_count_estimate,
    }
    spec_path = output_dir / f"{meta.slug}-cover-spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    svg_path = output_dir / f"{meta.slug}-cover.svg"
    svg_path.write_text(_cover_svg(meta, full_w, full_h, spine), encoding="utf-8")
    notes.append("wrote cover geometry spec and SVG layout (no automated KDP upload)")
    return [spec_path, svg_path], notes


def _cover_svg(meta: BookMeta, full_w: float, full_h: float, spine: float) -> str:
    # 72 pt per inch for SVG viewBox convenience.
    scale = 72
    width = full_w * scale
    height = full_h * scale
    bleed = meta.bleed_inches * scale
    trim_w = meta.trim_inches[0] * scale
    spine_w = spine * scale
    back_x = bleed
    spine_x = bleed + trim_w
    front_x = spine_x + spine_w
    title = meta.title.replace("&", "&amp;")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{height:.2f}" viewBox="0 0 {width:.2f} {height:.2f}">
  <rect x="0" y="0" width="{width:.2f}" height="{height:.2f}" fill="#1b1b1b"/>
  <rect x="{back_x:.2f}" y="{bleed:.2f}" width="{trim_w:.2f}" height="{meta.trim_inches[1] * scale:.2f}" fill="#2c2c2c" stroke="#888" />
  <rect x="{spine_x:.2f}" y="{bleed:.2f}" width="{spine_w:.2f}" height="{meta.trim_inches[1] * scale:.2f}" fill="#444" stroke="#aaa" />
  <rect x="{front_x:.2f}" y="{bleed:.2f}" width="{trim_w:.2f}" height="{meta.trim_inches[1] * scale:.2f}" fill="#f7f3ea" stroke="#333" />
  <text x="{front_x + trim_w / 2:.2f}" y="{height / 2:.2f}" text-anchor="middle" font-size="28" fill="#111">{title}</text>
  <text x="{front_x + trim_w / 2:.2f}" y="{height / 2 + 36:.2f}" text-anchor="middle" font-size="14" fill="#333">{", ".join(meta.contributors)}</text>
  <rect x="{width - bleed - 2 * scale:.2f}" y="{height - bleed - 1.2 * scale:.2f}" width="{2 * scale:.2f}" height="{1.2 * scale:.2f}" fill="none" stroke="#c00" stroke-dasharray="4 2" />
</svg>
"""
