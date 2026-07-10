# File Purpose: Build semantic EPUB3 packages from Markdown manuscripts.
# Primary Functions/Classes: build_epub.
# Inputs/Outputs: BookMeta + output directory in; EPUB path and notes out.

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

from platforms.adapters.base import _which
from platforms.kdp.book import BookMeta
from platforms.process import ProcessError, run_allowlisted


def build_epub(meta: BookMeta, output_dir: Path) -> tuple[Path, list[str]]:
    """Create an EPUB3 file using Pandoc when available, else a minimal offline EPUB."""
    output_dir.mkdir(parents=True, exist_ok=True)
    epub_path = output_dir / f"{meta.slug}.epub"
    notes: list[str] = []
    if _which("pandoc"):
        try:
            result = run_allowlisted(
                [
                    "pandoc",
                    str(meta.manuscript),
                    "-o",
                    str(epub_path),
                    "--to=epub3",
                    f"--metadata=title:{meta.title}",
                    f"--metadata=lang:{meta.language}",
                ],
                cwd=meta.manuscript.parent,
                allowed_roots=[meta.manuscript.parent.resolve(), output_dir.resolve()],
            )
            if result.returncode == 0 and epub_path.is_file():
                notes.append("built EPUB3 with pandoc")
                return epub_path, notes
            notes.append(f"pandoc failed ({result.returncode}); falling back to minimal EPUB")
        except ProcessError as exc:
            notes.append(f"pandoc invocation blocked ({exc}); falling back to minimal EPUB")
    path = _write_minimal_epub(meta, epub_path)
    notes.append("built minimal deterministic EPUB3 without pandoc")
    return path, notes


def _write_minimal_epub(meta: BookMeta, epub_path: Path) -> Path:
    markdown = meta.manuscript.read_text(encoding="utf-8")
    body = _markdown_to_simple_html(markdown)
    title = html.escape(meta.title)
    lang = html.escape(meta.language)
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{lang}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{html.escape(meta.identifiers.get("isbn", meta.slug))}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>{lang}</dc:language>
    <dc:creator>{html.escape(", ".join(meta.contributors))}</dc:creator>
    <meta property="dcterms:modified">2026-07-10T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
"""
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}">
<head><title>Navigation</title></head>
<body>
<nav epub:type="toc" role="doc-toc" aria-label="Table of contents">
  <ol><li><a href="chapter1.xhtml">{title}</a></li></ol>
</nav>
</body></html>
"""
    chapter = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head><title>{title}</title></head>
<body>
<main>
{body}
</main>
</body></html>
"""
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("EPUB/content.opf", content_opf)
        archive.writestr("EPUB/nav.xhtml", nav)
        archive.writestr("EPUB/chapter1.xhtml", chapter)
    return epub_path


def _markdown_to_simple_html(markdown: str) -> str:
    lines = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line):
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            assert match is not None
            alt = html.escape(match.group(1))
            src = html.escape(match.group(2))
            lines.append(f'<img src="{src}" alt="{alt}" />')
        elif line.strip() == "":
            continue
        else:
            lines.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(lines) if lines else "<p></p>"
