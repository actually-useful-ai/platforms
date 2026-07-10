# File Purpose: Read-only Ambient Time fixture detection for device adapters.
# Primary Functions/Classes: AmbientTimeFixtureTests.
# Inputs/Outputs: Uses /Users/luke/workspace/ambient-time when present; skips otherwise.

from __future__ import annotations

import unittest
from pathlib import Path

from platforms.adapters.registry import get_adapter

AMBIENT = Path("/Users/luke/workspace/ambient-time")


@unittest.skipUnless(AMBIENT.is_dir(), "Ambient Time fixture not present")
class AmbientTimeFixtureTests(unittest.TestCase):
    def test_detects_pebble_golden_hour(self) -> None:
        detection = get_adapter("pebble").detect(AMBIENT)
        self.assertTrue(detection.matched)
        self.assertIn("Golden Hour", " ".join(detection.reasons))

    def test_detects_android_family_markers(self) -> None:
        self.assertTrue(get_adapter("android").detect(AMBIENT).matched)
        self.assertGreaterEqual(get_adapter("fire-tv").detect(AMBIENT).confidence, 0.2)

    def test_detects_webos_and_tizen_and_web_kiosk(self) -> None:
        self.assertTrue(get_adapter("webos").detect(AMBIENT).matched)
        self.assertTrue(get_adapter("tizen").detect(AMBIENT).matched)
        self.assertTrue(get_adapter("web-kiosk").detect(AMBIENT).matched)

    def test_vega_stays_explicit_only(self) -> None:
        detection = get_adapter("vega").detect(AMBIENT)
        self.assertFalse(detection.matched)
