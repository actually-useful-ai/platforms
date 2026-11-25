# File Purpose: Verify the platforms-fdroid skill's routing contract, stop gates, references and scripts.
# Primary Functions/Classes: FdroidRoutingTests, FdroidGateTests, ReferenceLinkTests,
#   ListingSourcesTests, RequestWordsTests.
# Inputs/Outputs: Reads canonical SKILL.md files and evals/ cases; runs the skill's scripts
#   against temporary trees; asserts routing text, gates, link targets and script output.

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "platforms-fdroid"


def _frontmatter(skill_id: str) -> tuple[dict, str]:
    text = (ROOT / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
    _, front, body = text.split("---", maxsplit=2)
    return yaml.safe_load(front), body


def _load_script(name: str):
    path = SKILL / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"fdroid_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FdroidRoutingTests(unittest.TestCase):
    def test_description_names_the_catalog_and_its_exclusions(self) -> None:
        front, _ = _frontmatter("platforms-fdroid")
        description = front["description"]
        for phrase in ("Use when", "F-Droid", "fdroiddata", "Not for"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, description)
        self.assertLessEqual(len(description), 1024)

    def test_router_sends_fdroid_work_to_the_fdroid_skill(self) -> None:
        _, body = _frontmatter("platforms")
        self.assertRegex(body, r"F-Droid[^\n]*`platforms-fdroid`")

    def test_mobile_skill_hands_fdroid_catalog_work_over(self) -> None:
        front, body = _frontmatter("platforms-mobile")
        self.assertIn("platforms-fdroid", body)
        self.assertIn("F-Droid", front["description"])

    def test_routing_eval_cases_cover_positive_negative_and_explicit(self) -> None:
        cases = sorted((ROOT / "evals").glob("fdroid-*/prompt.md"))
        self.assertGreaterEqual(len(cases), 5)
        kinds = set()
        for case in cases:
            text = case.read_text(encoding="utf-8")
            front = yaml.safe_load(text.split("---", maxsplit=2)[1])
            kinds.update(front.get("tags", []))
            graders = list((case.parent / "graders").glob("*.md"))
            self.assertTrue(graders, f"{case.parent.name} has no graders")
        for kind in ("positive", "negative", "explicit", "composition"):
            with self.subTest(kind=kind):
                self.assertIn(kind, kinds)


class FdroidGateTests(unittest.TestCase):
    def test_every_outward_step_stops_for_the_owner(self) -> None:
        _, raw = _frontmatter("platforms-fdroid")
        gates = re.findall(r"^\*\*Stop[^*]*\*\*", raw, flags=re.M)
        self.assertGreaterEqual(len(gates), 4)
        body = " ".join(raw.split())
        for phrase in (
            "before opening the merge request",
            "before posting",
            "signs and tags",
            "Never merge",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_fit_check_refuses_wrappers_before_any_work(self) -> None:
        _, body = _frontmatter("platforms-fdroid")
        fit = body.split("## 1.", 1)[1].split("## 2.", 1)[0]
        for phrase in ("Trusted Web Activit", "website wrapper", "three months", "Play Services"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, fit)


class ReferenceLinkTests(unittest.TestCase):
    def test_relative_links_in_every_skill_resolve(self) -> None:
        for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
            folder = skill_md.parent
            files = [skill_md, *sorted((folder / "references").glob("*.md"))]
            for path in files:
                text = re.sub(r"```.*?```", " ", path.read_text(encoding="utf-8"), flags=re.S)
                for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                    if "://" in target or target.startswith("mailto:"):
                        continue
                    with self.subTest(file=str(path.relative_to(ROOT)), target=target):
                        self.assertTrue((path.parent / target).exists())

    def test_fdroid_references_are_linked_from_skill_md(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for ref in sorted((SKILL / "references").glob("*.md")):
            with self.subTest(reference=ref.name):
                self.assertIn(f"references/{ref.name}", text)


class ListingSourcesTests(unittest.TestCase):
    def test_root_metadata_folder_is_read_after_fastlane_and_wins(self) -> None:
        module = _load_script("listing_sources")
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "fastlane/metadata/android/en-US").mkdir(parents=True)
            (repo / "fastlane/metadata/android/en-US/full_description.txt").write_text("Android", encoding="utf-8")
            (repo / "metadata/tvOS/en-US").mkdir(parents=True)
            (repo / "metadata/tvOS/en-US/description.txt").write_text("Apple TV", encoding="utf-8")
            report = module.scan(repo, subdir="android/app")
        self.assertEqual(
            [entry["relative"] for entry in report["read_order"]],
            ["fastlane/metadata/android/en-US", "metadata/tvOS"],
        )
        self.assertEqual(report["root_metadata"], ["metadata/tvOS"])
        self.assertTrue(report["conflict"])

    def test_clean_fastlane_tree_reports_no_conflict(self) -> None:
        module = _load_script("listing_sources")
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "fastlane/metadata/android/en-US/images").mkdir(parents=True)
            (repo / "apple/metadata/en-US").mkdir(parents=True)
            report = module.scan(repo, subdir="app")
        self.assertEqual(report["root_metadata"], [])
        self.assertFalse(report["conflict"])


class RequestWordsTests(unittest.TestCase):
    def test_counts_author_prose_above_the_checklist_only(self) -> None:
        module = _load_script("request_words")
        text = (
            "## Abstract for new app inclusion\n\n"
            "### Please introduce the functions and usage of your app in summary, "
            "and also attach some screenshots.\n\n"
            "A small offline clock.\n\n"
            "![Main screen](https://example.org/1.png){width=240}\n\n"
            "## Checklist\n\n* [x] The app complies with the inclusion policy.\n"
        )
        result = module.count(text)
        self.assertEqual(result["words"], 4)
        self.assertEqual(result["images"], 1)
        self.assertTrue(result["has_checklist"])


if __name__ == "__main__":
    unittest.main()
