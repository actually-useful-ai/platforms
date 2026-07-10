# File Purpose: Assemble KDP upload-ready bundles with checksums and human checklist.
# Primary Functions/Classes: build_upload_bundle.
# Inputs/Outputs: Project path in; ArtifactBundle-compatible paths and notes out.

from __future__ import annotations

import json
from pathlib import Path

from platforms.adapters.base import sha256_file
from platforms.kdp.book import load_book_yml, validate_book_meta
from platforms.kdp.cover import build_cover_assets
from platforms.kdp.epub import build_epub
from platforms.kdp.print_pdf import build_print_interior
from platforms.kdp.validate import validate_bundle
from platforms.models import ArtifactBundle, TrackState


def build_upload_bundle(project: Path) -> ArtifactBundle:
    book_path = project / "book.yml"
    meta = load_book_yml(book_path)
    problems = validate_book_meta(meta)
    output_dir = (project / "dist" / meta.slug / meta.version).resolve()
    output_dir.relative_to(project.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)

    notes: list[str] = []
    if problems:
        notes.extend(problems)

    epub_path, epub_notes = build_epub(meta, output_dir)
    notes.extend(epub_notes)
    interior_path, interior_notes = build_print_interior(meta, output_dir)
    notes.extend(interior_notes)
    cover_paths, cover_notes = build_cover_assets(meta, output_dir)
    notes.extend(cover_notes)

    metadata = {
        "title": meta.title,
        "slug": meta.slug,
        "version": meta.version,
        "language": meta.language,
        "contributors": list(meta.contributors),
        "keywords": list(meta.keywords),
        "categories": list(meta.categories),
        "description": meta.description,
        "identifiers": meta.identifiers,
        "accessibility": meta.accessibility,
        "trim_inches": list(meta.trim_inches),
        "paper": meta.paper,
        "bleed_inches": meta.bleed_inches,
        "page_count_estimate": meta.page_count_estimate,
        "submission": "manual-only",
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    artifacts = [epub_path, interior_path, *cover_paths, metadata_path]
    report = validate_bundle(meta, artifacts, output_dir)
    artifacts.extend(report.report_paths)
    notes.extend(f"{finding.severity}:{finding.code}:{finding.message}" for finding in report.findings)

    provenance = output_dir / "PROVENANCE.md"
    provenance.write_text(
        f"# Provenance\n\n"
        f"- Title: {meta.title}\n"
        f"- Version: {meta.version}\n"
        f"- Built by platforms KDP pipeline\n"
        f"- Maintainer: Luke Steuber\n"
        f"- Submission: human upload only (no automated KDP login or publish)\n",
        encoding="utf-8",
    )
    checklist = output_dir / "UPLOAD_CHECKLIST.md"
    checklist.write_text(
        f"# KDP upload checklist — {meta.title}\n\n"
        "## Included artifacts\n"
        f"- EPUB: `{epub_path.name}`\n"
        f"- Interior: `{interior_path.name}`\n"
        f"- Cover assets: {', '.join(path.name for path in cover_paths)}\n"
        f"- Metadata: `{metadata_path.name}`\n"
        f"- Validation: validation-report.json\n\n"
        "## Human steps (required)\n"
        "1. Review EPUBCheck/Ace findings and fix errors.\n"
        "2. Confirm print PDF page size, margins, gutter, fonts, and image DPI.\n"
        "3. Confirm cover wrap size against the current KDP calculator.\n"
        "4. Upload files manually in KDP.\n"
        "5. Set pricing, territories, and disclosures yourself.\n"
        "6. Mark track state `submitted` only after you personally publish.\n\n"
        "This suite never logs into KDP and never submits for you.\n",
        encoding="utf-8",
    )
    artifacts.extend([provenance, checklist])

    checksums = {str(path): sha256_file(path) for path in artifacts if path.is_file()}
    checksums_path = output_dir / "checksums.json"
    checksums_path.write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append(checksums_path)
    checksums[str(checksums_path)] = sha256_file(checksums_path)

    state = TrackState.VALIDATED if report.ok and not problems else TrackState.BUILT
    return ArtifactBundle(
        platform_id="kdp",
        track_state=state,
        artifacts=tuple(artifacts),
        checksums=checksums,
        notes=tuple(notes),
    )


def package_upload_bundle(project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
    """Promote a validated KDP bundle to store-staged without submitting."""
    notes = bundle.notes + (
        "store-staged: upload checklist ready for human KDP console use",
        "submitted state must be set manually after human publish",
    )
    return ArtifactBundle(
        platform_id="kdp",
        track_state=TrackState.STORE_STAGED,
        artifacts=bundle.artifacts,
        checksums=dict(bundle.checksums),
        notes=notes,
    )
