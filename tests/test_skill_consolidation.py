# File Purpose: Verify the nine-skill consolidation, aliases, and merged skill contracts.
# Primary Functions/Classes: SkillConsolidationTests.
# Inputs/Outputs: Reads suite.toml and canonical SKILL.md files; asserts inventory and content.

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from tools import generate_manifests


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CANONICAL = {
    "platforms",
    "platforms-intake",
    "platforms-release-plan",
    "platforms-store-assets",
    "platforms-tv",
    "platforms-mobile",
    "platforms-kdp",
    "platforms-pebble",
    "platforms-web-kiosk",
}
EXPECTED_ALIASES = {
    "platforms-android": "platforms-mobile",
    "platforms-fire-tablet": "platforms-mobile",
    "platforms-android-tv": "platforms-tv",
    "platforms-fire-tv": "platforms-tv",
    "platforms-vega": "platforms-tv",
    "platforms-webos": "platforms-tv",
    "platforms-tizen": "platforms-tv",
    "platforms-roku": "platforms-tv",
    "platforms-tv-accessibility": "platforms-tv",
    "platforms-kdp-book": "platforms-kdp",
    "platforms-kdp-cover": "platforms-kdp",
    "platforms-kdp-metadata": "platforms-kdp",
    "platforms-epub-accessibility": "platforms-kdp",
    "platforms-pebble-watchface": "platforms-pebble",
    "platforms-pebble-watchapp": "platforms-pebble",
}
EXPECTED_TOOLS = {
    "platforms": {"Read", "Glob", "Grep", "Bash", "AskUserQuestion"},
    "platforms-intake": {"Read", "Write", "Glob", "Grep", "Bash", "AskUserQuestion"},
    "platforms-release-plan": {
        "Read",
        "Write",
        "Glob",
        "Grep",
        "AskUserQuestion",
    },
    "platforms-store-assets": {
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Bash",
        "WebFetch",
        "WebSearch",
    },
    "platforms-tv": {"Read", "Write", "Edit", "Glob", "Grep", "Bash"},
    "platforms-mobile": {"Read", "Write", "Edit", "Glob", "Grep", "Bash"},
    "platforms-kdp": {
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Bash",
        "WebFetch",
    },
    "platforms-pebble": {
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Bash",
        "WebFetch",
    },
    "platforms-web-kiosk": {"Read", "Write", "Edit", "Glob", "Grep", "Bash"},
}
MAXIMAL_TOOLS = {
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "WebFetch",
    "WebSearch",
    "AskUserQuestion",
}


class SkillConsolidationTests(unittest.TestCase):
    def test_suite_has_nine_canonical_skills_and_fifteen_aliases(self) -> None:
        suite = generate_manifests.load_suite(ROOT / "suite.toml")

        self.assertEqual(suite["suite"]["version"], "0.3.0")
        self.assertEqual({item["id"] for item in suite["skills"]}, EXPECTED_CANONICAL)
        self.assertEqual(
            {item["id"]: item["target"] for item in suite["aliases"]},
            EXPECTED_ALIASES,
        )
        self.assertEqual(
            {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()},
            EXPECTED_CANONICAL,
        )

    def test_alias_validation_rejects_collisions_unknown_targets_and_chains(self) -> None:
        base = (ROOT / "suite.toml").read_text(encoding="utf-8")
        cases = {
            "collision": base + '\n[[aliases]]\nid = "platforms"\ntarget = "platforms-tv"\n',
            "unknown": base
            + '\n[[aliases]]\nid = "platforms-old"\ntarget = "platforms-unknown"\n',
            "chain": base
            + '\n[[aliases]]\nid = "platforms-old"\ntarget = "platforms-android"\n',
        }
        for label, suite_text in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                suite_path = Path(temporary) / "suite.toml"
                suite_path.write_text(suite_text, encoding="utf-8")
                with self.assertRaises(generate_manifests.SuiteValidationError):
                    generate_manifests.load_suite(suite_path)

    def test_all_canonical_skills_have_precise_frontmatter(self) -> None:
        for skill_id in sorted(EXPECTED_CANONICAL):
            with self.subTest(skill=skill_id):
                text = (ROOT / "skills" / skill_id / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                opening, frontmatter_text, body = text.split("---", maxsplit=2)
                self.assertEqual(opening, "")
                frontmatter = yaml.safe_load(frontmatter_text)
                self.assertIsInstance(frontmatter, dict)
                self.assertEqual(
                    set(frontmatter),
                    {"name", "description", "allowed-tools"},
                )
                self.assertEqual(frontmatter["name"], skill_id)
                self.assertEqual(set(frontmatter["allowed-tools"]), EXPECTED_TOOLS[skill_id])
                self.assertNotEqual(set(frontmatter["allowed-tools"]), MAXIMAL_TOOLS)
                description = frontmatter["description"]
                self.assertIsInstance(description, str)
                self.assertGreater(len(description), 30)
                self.assertIn("Use when", description)
                self.assertTrue(body.strip())

    def test_merged_skills_preserve_platform_specific_contracts(self) -> None:
        required_phrases = {
            "platforms-tv": (
                "android-tv",
                "fire-tv",
                "vega",
                "webos",
                "tizen",
                "roku",
                "LEANBACK_LAUNCHER",
                "ares-package",
                "SceneGraph",
                "explicit `platforms.yml` selection",
                "human",
                "captions",
                "audio descriptions",
                "explicit architecture",
                "icons and version",
            ),
            "platforms-web-kiosk": (
                "visible focus",
                "screen-reader semantics",
                "text zoom",
                "human",
                "publish",
            ),
            "platforms-mobile": (
                "android",
                "fire-tablet",
                "JDK",
                "TalkBack",
                "touch targets",
                "`adb`",
                "human",
            ),
            "platforms-kdp": (
                "kdp",
                "book.yml",
                "EPUB3",
                "Typst",
                "spine width",
                "barcode reserve",
                "EPUBCheck",
                "Ace by DAISY",
                "alt text",
                "human",
                "Never automate KDP login",
            ),
            "platforms-pebble": (
                "pebble",
                "watchface",
                "watchapp",
                "Rocky.js",
                "native C",
                ".pbw",
                "app keys",
                "no-license",
                "human",
            ),
        }
        for skill_id, phrases in required_phrases.items():
            text = (ROOT / "skills" / skill_id / "SKILL.md").read_text(
                encoding="utf-8"
            )
            for phrase in phrases:
                with self.subTest(skill=skill_id, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_store_requirements_have_an_authoritative_source_contract(self) -> None:
        store_assets = (ROOT / "skills/platforms-store-assets/SKILL.md").read_text(
            encoding="utf-8"
        )
        release_plan = (ROOT / "skills/platforms-release-plan/SKILL.md").read_text(
            encoding="utf-8"
        )

        for phrase in ("official vendor", "source URL", "retrieved date", "fail closed"):
            self.assertIn(phrase, store_assets)
        self.assertIn("recorded store specification source", release_plan)
        self.assertNotIn("come from adapters", release_plan)


if __name__ == "__main__":
    unittest.main()
