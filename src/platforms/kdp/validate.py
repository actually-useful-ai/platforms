# File Purpose: KDP/EPUB structural and accessibility validation with optional external tools.
# Primary Functions/Classes: validate_bundle, ValidationReport.
# Inputs/Outputs: Artifact paths + BookMeta in; findings and report paths out.

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from platforms.adapters.base import _which
from platforms.kdp.book import BookMeta
from platforms.models import Finding
from platforms.process import ProcessError, run_allowlisted


@dataclass(frozen=True)
class ValidationReport:
    findings: tuple[Finding, ...]
    report_paths: tuple[Path, ...]
    ok: bool


def validate_bundle(meta: BookMeta, artifacts: list[Path], output_dir: Path) -> ValidationReport:
    findings: list[Finding] = []
    report_paths: list[Path] = []
    epubs = [path for path in artifacts if path.suffix.lower() == ".epub"]
    for epub in epubs:
        findings.extend(_structural_epub_checks(epub, meta))
        findings.extend(_run_optional_tool("epubcheck", ["epubcheck", str(epub)], epub.parent, findings_code="epubcheck"))
        findings.extend(_run_optional_tool("ace", ["ace", "--outdir", str(output_dir / "ace"), str(epub)], epub.parent, findings_code="ace"))
    manuscript_text = meta.manuscript.read_text(encoding="utf-8") if meta.manuscript.is_file() else ""
    findings.extend(_markdown_a11y_checks(manuscript_text))
    if not meta.accessibility:
        findings.append(
            Finding(
                code="missing-accessibility-metadata",
                severity="warning",
                message="book.yml accessibility map is empty",
                remediation="Declare accessibility summary, hazards, and modes in book.yml",
            )
        )
    report = output_dir / "validation-report.json"
    payload = {
        "ok": not any(item.severity == "error" for item in findings),
        "findings": [item.to_dict() for item in findings],
    }
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_paths.append(report)
    return ValidationReport(
        findings=tuple(findings),
        report_paths=tuple(report_paths),
        ok=payload["ok"],
    )


def _structural_epub_checks(epub: Path, meta: BookMeta) -> list[Finding]:
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(epub) as archive:
            names = set(archive.namelist())
            if "mimetype" not in names:
                findings.append(
                    Finding("epub-mimetype", "error", "EPUB missing mimetype entry", "Rebuild EPUB with stored mimetype")
                )
            if "META-INF/container.xml" not in names:
                findings.append(
                    Finding("epub-container", "error", "EPUB missing META-INF/container.xml", "Rebuild package container")
                )
            has_nav = any(name.endswith("nav.xhtml") or name.endswith("nav.xhtml") for name in names)
            if not has_nav and not any("nav" in name.lower() for name in names):
                findings.append(
                    Finding("epub-nav", "warning", "No obvious navigation document found", "Include EPUB3 nav landmark document")
                )
            opf_candidates = [name for name in names if name.endswith(".opf")]
            if opf_candidates:
                opf = archive.read(opf_candidates[0]).decode("utf-8", errors="replace")
                if f"<dc:language>{meta.language}" not in opf and meta.language not in opf:
                    findings.append(
                        Finding("epub-language", "warning", "Package language may not match book.yml", "Align dc:language with book.yml")
                    )
    except zipfile.BadZipFile:
        findings.append(Finding("epub-corrupt", "error", f"EPUB is not a valid zip: {epub}", "Rebuild EPUB"))
    return findings


def _markdown_a11y_checks(text: str) -> list[Finding]:
    findings: list[Finding] = []
    headings = re.findall(r"^(#{1,6})\s+", text, flags=re.MULTILINE)
    levels = [len(item) for item in headings]
    if levels and levels[0] != 1:
        findings.append(
            Finding("heading-start", "warning", "Manuscript does not start with an h1", "Begin with a single top-level title heading")
        )
    for previous, current in zip(levels, levels[1:]):
        if current > previous + 1:
            findings.append(
                Finding("heading-skip", "warning", f"Heading level skips from h{previous} to h{current}", "Avoid skipped heading levels")
            )
            break
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
        if match.group(1).strip() == "":
            findings.append(
                Finding("image-alt", "error", f"Image missing alt text: {match.group(2)}", "Provide meaningful alt text for every image")
            )
    return findings


def _run_optional_tool(tool: str, argv: list[str], cwd: Path, findings_code: str) -> list[Finding]:
    if not _which(tool):
        return [
            Finding(
                code=f"missing-{tool}",
                severity="warning",
                message=f"{tool} not installed; skipped external validation",
                remediation=f"Install {tool} for stronger validation",
            )
        ]
    try:
        result = run_allowlisted(argv, cwd=cwd, allowed_roots=[cwd.resolve()])
        if result.returncode != 0:
            return [
                Finding(
                    code=f"{findings_code}-failed",
                    severity="error",
                    message=f"{tool} exited {result.returncode}",
                    remediation=result.stderr.strip() or f"Inspect {tool} output",
                )
            ]
    except ProcessError as exc:
        return [
            Finding(
                code=f"{findings_code}-blocked",
                severity="warning",
                message=f"{tool} invocation blocked: {exc}",
                remediation="Adjust allowlisted argv or install tooling locally",
            )
        ]
    return []
