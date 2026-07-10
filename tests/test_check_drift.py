# File Purpose: Verify read-only detection of drift in installed skill projections.
# Primary Functions/Classes: DriftDetectionTests and temporary projection helpers.
# Inputs/Outputs: Builds temporary skill roots and asserts JSON reports and exit status.

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools import check_drift


class DriftDetectionTests(unittest.TestCase):
    """Exercise missing, changed, extra, clean, and ignored projection behavior."""

    def make_directory(self, name: str) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix=f"{name}-")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    @staticmethod
    def write_skill(root: Path, name: str, prose: str) -> None:
        skill = root / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(prose, encoding="utf-8")

    def test_matching_projection_has_no_drift(self) -> None:
        canonical = self.make_directory("canonical")
        installed = self.make_directory("installed")
        self.write_skill(canonical, "platforms", "canonical\n")
        self.write_skill(installed, "platforms", "canonical\n")

        report = check_drift.compare_roots(canonical, [installed], ["platforms"])

        self.assertFalse(report["drift"])
        self.assertEqual(report["roots"][0]["missing"], [])
        self.assertEqual(report["roots"][0]["changed"], [])
        self.assertEqual(report["roots"][0]["extra"], [])

    def test_missing_changed_and_extra_managed_projections_are_reported(self) -> None:
        canonical = self.make_directory("canonical")
        installed = self.make_directory("installed")
        self.write_skill(canonical, "platforms", "canonical\n")
        self.write_skill(canonical, "platforms-intake", "intake\n")
        self.write_skill(installed, "platforms", "changed\n")
        self.write_skill(installed, "platforms-android", "unexpected\n")

        report = check_drift.compare_roots(
            canonical,
            [installed],
            ["platforms", "platforms-intake", "platforms-android"],
        )

        self.assertTrue(report["drift"])
        root_report = report["roots"][0]
        self.assertEqual(root_report["missing"], ["platforms-intake"])
        self.assertEqual(root_report["changed"], ["platforms/SKILL.md"])
        self.assertEqual(root_report["extra"], ["platforms-android"])

    def test_cli_emits_sorted_json_and_does_not_modify_installed_root(self) -> None:
        canonical = self.make_directory("canonical")
        installed = self.make_directory("installed")
        self.write_skill(canonical, "platforms", "canonical\n")
        self.write_skill(installed, "platforms", "changed\n")
        before = (installed / "platforms/SKILL.md").read_bytes()
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = check_drift.main(
                [
                    "--canonical-root",
                    str(canonical),
                    "--managed-skill",
                    "platforms",
                    str(installed),
                ]
            )

        self.assertEqual(exit_code, 1)
        parsed = json.loads(stdout.getvalue())
        self.assertTrue(parsed["drift"])
        self.assertEqual(
            stdout.getvalue(),
            json.dumps(parsed, indent=2, sort_keys=True) + "\n",
        )
        self.assertEqual((installed / "platforms/SKILL.md").read_bytes(), before)

    def test_agent_caches_and_cursor_managed_root_are_ignored(self) -> None:
        canonical = self.make_directory("canonical")
        cache_root = self.make_directory("cache-parent") / "cache" / "skills"
        cursor_root = Path.home() / ".cursor" / "skills-cursor"

        self.assertTrue(check_drift.is_ignored_root(cache_root))
        self.assertTrue(check_drift.is_ignored_root(cursor_root))
        self.assertTrue(check_drift.is_ignored_root(cursor_root / "nested"))
        report = check_drift.compare_roots(
            canonical,
            [cache_root, cursor_root],
            ["platforms"],
        )
        self.assertFalse(report["drift"])
        self.assertEqual(len(report["ignored_roots"]), 2)


if __name__ == "__main__":
    unittest.main()
