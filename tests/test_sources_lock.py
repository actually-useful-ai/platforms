# File Purpose: Verify excluded source provenance and no-reuse boundaries remain pinned.
# Primary Functions/Classes: SourceLockTests.
# Inputs/Outputs: Reads sources.lock.toml and asserts required repository metadata.

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


class SourceLockTests(unittest.TestCase):
    """Protect explicit exclusions from disappearing from source provenance."""

    def test_ash_kindle_is_pinned_as_excluded_without_reuse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with (root / "sources.lock.toml").open("rb") as lock_file:
            sources = tomllib.load(lock_file)["sources"]

        source = next(
            item
            for item in sources
            if item["repository"] == "https://github.com/jordangarrison/ash-kindle"
        )
        self.assertEqual(
            source["revision"],
            "d425946fe9585f43af2eedf20721f3fdf3779026",
        )
        self.assertEqual(source["license"], "NOASSERTION")
        self.assertEqual(source["use"], "excluded-unrelated")
        self.assertTrue(source["excluded"])
        self.assertEqual(source["exclusion_reason"], "unrelated")
        self.assertTrue(source["research_only"])
        self.assertFalse(source["code_copy_allowed"])


if __name__ == "__main__":
    unittest.main()
