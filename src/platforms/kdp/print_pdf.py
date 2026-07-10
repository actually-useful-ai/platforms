# File Purpose: Print-interior PDF generation and KDP geometry helpers.
# Primary Functions/Classes: spine_width_inches, build_print_interior.
# Inputs/Outputs: BookMeta + output dir in; PDF or marker path and notes out.

from __future__ import annotations

from pathlib import Path

from platforms.adapters.base import _which
from platforms.kdp.book import BookMeta
from platforms.process import ProcessError, run_allowlisted

# Approximate PPI for common KDP cream/white papers (inches per page thickness).
_PAPER_THICKNESS = {
    "white": 0.002252,
    "cream": 0.0025,
}


def spine_width_inches(page_count: int, paper: str = "white") -> float:
    thickness = _PAPER_THICKNESS.get(paper.lower(), _PAPER_THICKNESS["white"])
    return max(page_count * thickness, 0.06)


def cover_width_inches(trim_w: float, trim_h: float, page_count: int, paper: str, bleed: float) -> tuple[float, float]:
    spine = spine_width_inches(page_count, paper)
    width = (bleed * 2) + (trim_w * 2) + spine
    height = (bleed * 2) + trim_h
    return width, height


def build_print_interior(meta: BookMeta, output_dir: Path) -> tuple[Path, list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    pdf_path = output_dir / f"{meta.slug}-interior.pdf"
    if _which("typst"):
        typst_src = output_dir / "interior.typ"
        typst_src.write_text(_typst_template(meta), encoding="utf-8")
        try:
            result = run_allowlisted(
                ["typst", "compile", str(typst_src), str(pdf_path)],
                cwd=output_dir,
                allowed_roots=[output_dir.resolve(), meta.manuscript.parent.resolve()],
            )
            if result.returncode == 0 and pdf_path.is_file():
                notes.append("built print interior with typst")
                return pdf_path, notes
            notes.append(f"typst failed ({result.returncode}); writing pending marker")
        except ProcessError as exc:
            notes.append(f"typst invocation blocked ({exc}); writing pending marker")
    marker = output_dir / f"{meta.slug}-interior.PENDING.txt"
    marker.write_text(
        "Print interior PDF pending Typst installation.\n"
        f"trim_inches={meta.trim_inches}\n"
        f"page_count_estimate={meta.page_count_estimate}\n"
        f"paper={meta.paper}\n"
        f"bleed_inches={meta.bleed_inches}\n"
        "Validate margins, gutter, embedded fonts, and image DPI before upload.\n",
        encoding="utf-8",
    )
    notes.append("typst unavailable; wrote interior pending marker")
    return marker, notes


def _typst_template(meta: BookMeta) -> str:
    width, height = meta.trim_inches
    body = meta.manuscript.read_text(encoding="utf-8").replace("\\", "\\\\").replace('"', '\\"')
    return f"""#set page(width: {width}in, height: {height}in, margin: 0.75in)
#set text(font: "Libertinus Serif", size: 11pt)
= {meta.title}

{body}
"""
