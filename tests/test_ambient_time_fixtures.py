# File Purpose: Read-only Ambient Time fixture detection for device adapters.
# Primary Functions/Classes: AmbientTimeFixtureTests.
# Inputs/Outputs: Uses /Users/luke/workspace/ambient-time when present; skips otherwise.

from __future__ import annotations

import unittest
from pathlib import Path

from platforms.adapters.registry import get_adapter
from platforms.fixtures.ambient_time import (
    TEST_PACK_FACE_IDS,
    load_listed_platforms,
    manifest_face_ids,
    www_manifest_path,
)

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

    def test_platforms_yml_lists_expected_targets(self) -> None:
        listed = set(load_listed_platforms(AMBIENT))
        self.assertTrue(
            {
                "web-kiosk",
                "android",
                "fire-tv",
                "webos",
                "tizen",
                "pebble",
            }.issubset(listed)
        )
        self.assertNotIn("vega", listed)

    def test_full_www_contains_test_pack_faces(self) -> None:
        manifest = www_manifest_path(AMBIENT, test_pack=False)
        if not manifest.is_file():
            self.skipTest("appstores/dist/www/manifest.json not built yet")
        ids = manifest_face_ids(manifest)
        missing = [face_id for face_id in TEST_PACK_FACE_IDS if face_id not in ids]
        self.assertEqual(missing, [], f"test pack faces missing from full www: {missing}")
