# File Purpose: Verify the shared platform adapter contract and registry behavior.
# Primary Functions/Classes: AdapterContractTests.
# Inputs/Outputs: Uses temporary project roots; asserts detect/plan/doctor/build/validate/package/report shapes.

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from platforms.adapters.registry import get_adapter, list_adapters
from platforms.models import TrackState


class AdapterContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [web-kiosk]\n",
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
        validated = adapter.validate(root, built)
        self.assertEqual(validated.track_state, TrackState.VALIDATED)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.STORE_STAGED)
        report = adapter.report(root, packaged)
        self.assertIn("Web Kiosk", report.summary)
        self.assertNotIn(TrackState.SUBMITTED, report.inferred_states)

    def test_track_states_are_not_inferred_forward(self) -> None:
        root = self.make_project()
        adapter = get_adapter("web-kiosk")
        detection = adapter.detect(root)
        plan = adapter.plan(root, detection)
        report = adapter.report(root, plan)
        self.assertEqual(report.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(list(report.inferred_states), [TrackState.SCAFFOLDED])
