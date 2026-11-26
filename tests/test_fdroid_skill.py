# File Purpose: Verify the platforms-fdroid skill's routing contract, stop gates, references and scripts.
# Primary Functions/Classes: FdroidRoutingTests, FdroidGateTests, ReferenceLinkTests,
#   ListingSourcesTests, RequestWordsTests, ReleaseCheckTests, ReleaseCheckGateTests.
# Inputs/Outputs: Reads canonical SKILL.md files and evals/ cases; runs the skill's scripts
#   against temporary trees and the excerpts in tests/fixtures/fdroid_release_check/; asserts
#   routing text, gates, link targets and script output.

from __future__ import annotations

import importlib.util
import io
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from contextlib import redirect_stdout
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "platforms-fdroid"
FIXTURES = ROOT / "tests" / "fixtures" / "fdroid_release_check"


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


def _apk(path: Path, block_ids: list[int] | None) -> Path:
    """Write a small zip; with block_ids, insert an APK Signing Block holding those IDs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"\0" * 16)
        archive.writestr("classes.dex", b"dex\n035\0")
    data = buffer.getvalue()
    if block_ids is not None:
        eocd = data.rfind(b"PK\x05\x06")
        cd_offset = struct.unpack_from("<I", data, eocd + 16)[0]
        pairs = b"".join(struct.pack("<QI", 4 + 8, ident) + b"\x01" * 8 for ident in block_ids)
        size = len(pairs) + 8 + 16
        block = struct.pack("<Q", size) + pairs + struct.pack("<Q", size) + b"APK Sig Block 42"
        data = data[:cd_offset] + block + data[cd_offset:]
        eocd += len(block)
        data = data[: eocd + 16] + struct.pack("<I", cd_offset + len(block)) + data[eocd + 20:]
    path.write_bytes(data)
    return path


V2_SIGNATURE = 0x7109871A
DEPENDENCY_METADATA = 0x504B4453


class ReleaseCheckTests(unittest.TestCase):
    """release_check.py against excerpts of real build files and small synthetic ones."""

    def setUp(self) -> None:
        self.module = _load_script("release_check")

    def _check(self, name: str, subdir: str, **options) -> dict:
        return self.module.check(FIXTURES / name, subdir, **options)

    def _status(self, report: dict) -> dict:
        return {item["check"]: item["status"] for item in report["checks"]}

    def _write(self, folder: Path, text: str, kts: bool = True) -> Path:
        name = "build.gradle.kts" if kts else "build.gradle"
        (folder / "app").mkdir(parents=True, exist_ok=True)
        (folder / "app" / name).write_text(text, encoding="utf-8")
        return folder

    def test_solar_orrery_filed_with_r8_off_fails(self) -> None:
        report = self._check("orrery", "android/app")
        self.assertEqual(report["result"], "fail")
        self.assertEqual(self._status(report), {"r8": "fail", "dependencies_info": "pass"})
        reason = next(item["reason"] for item in report["checks"] if item["check"] == "r8")
        self.assertIn("minifyEnabled false", reason)
        self.assertNotIn("\n", reason)

    def test_hexsweeper_before_and_after_r8(self) -> None:
        before = self._check("hexsweeper-before", "app/android/app")
        after = self._check("hexsweeper-after", "app/android/app")
        self.assertEqual(self._status(before)["r8"], "fail")
        self.assertEqual(after["result"], "pass")

    def test_mandaza_kotlin_dsl_fdroid_flavor_passes_r8(self) -> None:
        report = self._check("mandaza", "android/app", flavor="fdroid")
        self.assertEqual(self._status(report)["r8"], "pass")
        self.assertTrue(report["build_file"].endswith("build.gradle.kts"))

    def test_mandaza_without_dependencies_info_needs_the_signed_apk(self) -> None:
        report = self._check("mandaza", "android/app", flavor="fdroid")
        self.assertEqual(self._status(report)["dependencies_info"], "fail")
        self.assertIn("--apk", next(i["reason"] for i in report["checks"] if i["check"] == "dependencies_info"))
        with tempfile.TemporaryDirectory() as temporary:
            apk = _apk(Path(temporary) / "mandaza.apk", [V2_SIGNATURE])
            confirmed = self._check("mandaza", "android/app", flavor="fdroid", apk=apk)
        self.assertEqual(confirmed["result"], "pass")

    def test_apk_with_the_dependency_block_fails_whatever_gradle_says(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            apk = _apk(Path(temporary) / "hex.apk", [V2_SIGNATURE, DEPENDENCY_METADATA])
            report = self._check("hexsweeper-after", "app/android/app", apk=apk)
            unsigned = self._check("hexsweeper-after", "app/android/app",
                                   apk=_apk(Path(temporary) / "unsigned.apk", None))
        self.assertEqual(self._status(report)["dependencies_info"], "fail")
        self.assertEqual(unsigned["result"], "pass")

    def test_get_by_name_release_and_flavor_override(self) -> None:
        text = (
            "android {\n"
            "  productFlavors {\n"
            "    create(\"fdroid\") { isMinifyEnabled = false }\n"
            "    create(\"play\") { }\n"
            "  }\n"
            "  buildTypes {\n"
            "    getByName(\"release\") {\n"
            "      isMinifyEnabled = true // shrink\n"
            "    }\n"
            "  }\n"
            "  dependenciesInfo { includeInApk = false; includeInBundle = false }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            repo = self._write(Path(temporary), text)
            fdroid = self.module.check(repo, "app", flavor="fdroid")
            play = self.module.check(repo, "app", flavor="play")
            unnamed = self.module.check(repo, "app")
        self.assertEqual(self._status(fdroid)["r8"], "fail")
        self.assertEqual(play["result"], "pass")
        self.assertEqual(self._status(unnamed)["r8"], "unknown")

    def test_value_from_a_variable_is_reported_not_passed(self) -> None:
        text = (
            "android {\n"
            "  buildTypes { release { minifyEnabled enableR8 } }\n"
            "  dependenciesInfo { includeInApk false }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            report = self.module.check(self._write(Path(temporary), text, kts=False), "app")
        self.assertEqual(report["result"], "unknown")
        reason = next(item["reason"] for item in report["checks"] if item["check"] == "r8")
        self.assertIn("enableR8", reason)

    def test_missing_release_block_and_commented_out_settings_fail(self) -> None:
        text = (
            "android {\n"
            "  buildTypes {\n"
            "    debug { isMinifyEnabled = true }\n"
            "    // release { isMinifyEnabled = true }\n"
            "  }\n"
            "  /* dependenciesInfo { includeInApk = false } */\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            report = self.module.check(self._write(Path(temporary), text), "app")
        self.assertEqual(self._status(report), {"r8": "fail", "dependencies_info": "fail"})

    def test_minify_set_outside_build_types_cannot_be_decided(self) -> None:
        text = (
            "android {\n"
            "  buildTypes { release { isMinifyEnabled = true } }\n"
            "  dependenciesInfo { includeInApk = false }\n"
            "}\n"
            "androidComponents { beforeVariants { it.isMinifyEnabled = false } }\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            report = self.module.check(self._write(Path(temporary), text), "app")
        self.assertEqual(self._status(report)["r8"], "unknown")

    def test_missing_build_file_cannot_be_decided(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.module.check(Path(temporary), "android/app")
        self.assertEqual(report["result"], "unknown")

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_commit_option_reads_the_tagged_commit_not_the_working_tree(self) -> None:
        on = "android {\n buildTypes { release { isMinifyEnabled = true } }\n dependenciesInfo { includeInApk = false }\n}\n"
        with tempfile.TemporaryDirectory() as temporary:
            repo = self._write(Path(temporary), on)
            git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org"]
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "add", "."], check=True)
            subprocess.run([*git, "commit", "-q", "-m", "on"], check=True)
            commit = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True,
                                    text=True).stdout.strip()
            (repo / "app" / "build.gradle.kts").write_text(on.replace("true", "false"), encoding="utf-8")
            working = self.module.check(repo, "app")
            tagged = self.module.check(repo, "app", commit=commit)
        self.assertEqual(working["result"], "fail")
        self.assertEqual(tagged["result"], "pass")
        self.assertEqual(tagged["commit"], commit)

    def test_cli_prints_one_line_per_check_and_exit_codes(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            failing = self.module.main([str(FIXTURES / "orrery"), "--subdir", "android/app"])
        lines = [line for line in out.getvalue().splitlines() if line.startswith(("PASS", "FAIL", "UNKNOWN"))]
        self.assertEqual(failing, 1)
        self.assertEqual(len(lines), 2)
        with redirect_stdout(io.StringIO()):
            passing = self.module.main([str(FIXTURES / "hexsweeper-after"), "--subdir", "app/android/app"])
        self.assertEqual(passing, 0)


class ReleaseCheckGateTests(unittest.TestCase):
    def test_skill_blocks_filing_until_release_check_passes(self) -> None:
        _, raw = _frontmatter("platforms-fdroid")
        body = " ".join(raw.split())
        prepare = body.split("## 2.", 1)[1].split("## 3.", 1)[0]
        for phrase in ("scripts/release_check.py", "exact commit", "Do not file", "emulator"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, prepare)

    def test_review_and_recipes_point_at_the_check(self) -> None:
        for name in ("review.md", "recipes.md"):
            with self.subTest(reference=name):
                self.assertIn("release_check.py", (SKILL / "references" / name).read_text(encoding="utf-8"))

    def test_an_eval_case_expects_a_stop_when_r8_is_off(self) -> None:
        case = ROOT / "evals" / "fdroid-r8-off-blocks-filing"
        self.assertTrue((case / "prompt.md").is_file())
        graders = " ".join(path.read_text(encoding="utf-8") for path in (case / "graders").glob("*.md"))
        self.assertIn("type: llm", graders)
        self.assertIn("R8", graders)


if __name__ == "__main__":
    unittest.main()
