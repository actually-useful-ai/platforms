# File Purpose: Verify the shared platform adapter contract and registry behavior.
# Primary Functions/Classes: AdapterContractTests.
# Inputs/Outputs: Uses temporary project roots; asserts detect/plan/doctor/build/validate/package/report shapes.

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from platforms.adapters.registry import get_adapter, list_adapters
from platforms.models import ArtifactBundle, TrackState


class AdapterContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [web-kiosk]\n",
            encoding="utf-8",
        )
        (root / "www").mkdir()
        (root / "www/index.html").write_text(
            "<!doctype html><html lang=\"en\"><head><title>Fixture</title></head>"
            "<body><a href=\"#main\">Skip</a><main id=\"main\" tabindex=\"-1\">"
            "<h1>Fixture</h1></main></body></html>\n",
            encoding="utf-8",
        )
        return root

    def test_registry_exposes_expected_adapters(self) -> None:
        ids = {adapter.id for adapter in list_adapters()}
        expected = {
            "kdp",
            "pebble",
            "android",
            "fire-tablet",
            "fire-tv",
            "android-tv",
            "vega",
            "webos",
            "tizen",
            "roku",
            "web-kiosk",
        }
        self.assertTrue(expected.issubset(ids))

    def test_unknown_adapter_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_adapter("not-a-platform")

    def test_web_kiosk_adapter_round_trip(self) -> None:
        root = self.make_project()
        adapter = get_adapter("web-kiosk")
        detection = adapter.detect(root)
        self.assertTrue(detection.matched or detection.confidence >= 0.0)
        plan = adapter.plan(root, detection)
        self.assertEqual(plan.platform_id, "web-kiosk")
        self.assertEqual(plan.track_state, TrackState.SCAFFOLDED)
        doctor = adapter.doctor(root, plan)
        self.assertIsInstance(doctor.findings, (list, tuple))
        built = adapter.build(root, plan)
        self.assertEqual(built.track_state, TrackState.BUILT)
        self.assertFalse(any(path.name == "BUILD_STUB.txt" for path in built.artifacts))
        archive = next(path for path in built.artifacts if path.suffix == ".zip")
        with zipfile.ZipFile(archive) as package:
            self.assertIn("index.html", package.namelist())
        validated = adapter.validate(root, built)
        self.assertEqual(validated.track_state, TrackState.VALIDATED)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.STORE_STAGED)
        report = adapter.report(root, packaged)
        self.assertIn("Web Kiosk", report.summary)
        self.assertNotIn(TrackState.SUBMITTED, report.inferred_states)

    def test_stub_or_missing_evidence_cannot_advance_track_state(self) -> None:
        root = self.make_project()
        adapter = get_adapter("android")
        plan = adapter.plan(root, adapter.detect(root))

        built = adapter.build(root, plan)
        self.assertEqual(built.track_state, TrackState.SCAFFOLDED)
        self.assertFalse(any(path.name == "BUILD_STUB.txt" for path in built.artifacts))

        fake_stub = root / "BUILD_STUB.txt"
        fake_stub.write_text("not a package\n", encoding="utf-8")
        untrusted = ArtifactBundle(
            platform_id="android",
            track_state=TrackState.BUILT,
            artifacts=(fake_stub,),
        )
        validated = adapter.validate(root, untrusted)
        self.assertEqual(validated.track_state, TrackState.BUILT)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.BUILT)
        self.assertFalse(any(path.name == "UPLOAD_CHECKLIST.md" for path in packaged.artifacts))

    def test_vega_requires_explicit_architecture_and_webos_metadata(self) -> None:
        root = self.make_project()
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [vega, webos]\n",
            encoding="utf-8",
        )
        vega = get_adapter("vega")
        vega_plan = vega.plan(root, vega.detect(root))
        vega_codes = {finding.code for finding in vega.doctor(root, vega_plan).findings}
        self.assertIn("missing-vega-architecture", vega_codes)

        (root / "appinfo.json").write_text('{"id": "com.example.fixture"}\n', encoding="utf-8")
        webos = get_adapter("webos")
        webos_plan = webos.plan(root, webos.detect(root))
        webos_codes = {finding.code for finding in webos.doctor(root, webos_plan).findings}
        self.assertIn("missing-webos-version", webos_codes)
        self.assertIn("missing-webos-icon", webos_codes)

    def test_track_states_are_not_inferred_forward(self) -> None:
        root = self.make_project()
        adapter = get_adapter("web-kiosk")
        detection = adapter.detect(root)
        plan = adapter.plan(root, detection)
        report = adapter.report(root, plan)
        self.assertEqual(report.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(list(report.inferred_states), [TrackState.SCAFFOLDED])
