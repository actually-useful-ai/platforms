# File Purpose: Verify KDP book parsing, EPUB packaging, and upload-bundle assembly.
# Primary Functions/Classes: KdpPipelineTests.
# Inputs/Outputs: Temporary book projects in; asserts artifacts and no-submit guarantees.

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from platforms.adapters.registry import get_adapter
from platforms.kdp.book import load_book_yml
from platforms.kdp.bundle import build_upload_bundle
from platforms.kdp.print_pdf import spine_width_inches
from platforms.models import ArtifactBundle, TrackState


SAMPLE_BOOK = """\
title: "Ambient Notes"
slug: ambient-notes
version: "0.1.0"
language: en
contributors: ["Luke Steuber"]
manuscript: manuscript.md
trim_inches: [6.0, 9.0]
page_count_estimate: 120
paper: white
bleed_inches: 0.125
keywords: ["accessibility", "publishing"]
categories: ["Computers"]
description: "A short sample manuscript."
identifiers:
  isbn: "9798000000000"
accessibility:
  summary: "Semantic headings and image alternatives required."
  hazards: []
"""

SAMPLE_MD = """\
# Ambient Notes

## Why this exists

A short chapter for offline EPUB packaging.

![Cover sketch](cover.png)

### Details

More text with a proper heading ladder.
"""


class KdpPipelineTests(unittest.TestCase):
    def make_book_project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "book.yml").write_text(SAMPLE_BOOK, encoding="utf-8")
        (root / "manuscript.md").write_text(SAMPLE_MD, encoding="utf-8")
        return root

    def test_load_book_yml(self) -> None:
        root = self.make_book_project()
        meta = load_book_yml(root / "book.yml")
        self.assertEqual(meta.title, "Ambient Notes")
        self.assertEqual(meta.slug, "ambient-notes")
        self.assertEqual(meta.trim_inches, (6.0, 9.0))

    def test_spine_width_increases_with_pages(self) -> None:
        self.assertGreater(spine_width_inches(300), spine_width_inches(100))

    def test_build_upload_bundle_without_external_tools(self) -> None:
        root = self.make_book_project()
        bundle = build_upload_bundle(root)
        names = {Path(path).name for path in bundle.artifacts}
        self.assertIn("ambient-notes.epub", names)
        self.assertIn("UPLOAD_CHECKLIST.md", names)
        self.assertIn("metadata.json", names)
        self.assertIn("checksums.json", names)
        self.assertTrue(any("cover" in name for name in names))
        checklist = next(path for path in bundle.artifacts if path.name == "UPLOAD_CHECKLIST.md")
        text = checklist.read_text(encoding="utf-8")
        self.assertIn("never logs into KDP", text)
        self.assertNotIn(TrackState.SUBMITTED, (bundle.track_state,))
        epub = next(path for path in bundle.artifacts if path.suffix == ".epub")
        with zipfile.ZipFile(epub) as archive:
            self.assertEqual(archive.read("mimetype"), b"application/epub+zip")
        metadata = json.loads((root / "dist/ambient-notes/0.1.0/metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["submission"], "manual-only")

    def test_adapter_package_is_store_staged_not_submitted(self) -> None:
        root = self.make_book_project()
        adapter = get_adapter("kdp")
        detection = adapter.detect(root)
        self.assertTrue(detection.matched)
        plan = adapter.plan(root, detection)
        built = adapter.build(root, plan)
        validated = adapter.validate(root, built)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.STORE_STAGED)
        self.assertTrue(any("manual" in note.lower() or "human" in note.lower() for note in packaged.notes))

    def test_unvalidated_kdp_bundle_cannot_be_store_staged(self) -> None:
        root = self.make_book_project()
        adapter = get_adapter("kdp")
        unvalidated = ArtifactBundle(
            platform_id="kdp",
            track_state=TrackState.BUILT,
            artifacts=(),
        )

        packaged = adapter.package(root, unvalidated)

        self.assertEqual(packaged.track_state, TrackState.BUILT)
