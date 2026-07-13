# File Purpose: Verify safe, staged installation of canonical skills and legacy aliases.
# Primary Functions/Classes: ProjectionInstallerTests.
# Inputs/Outputs: Creates temporary suite/client roots; asserts copies, symlinks, cleanup, and safety.

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import install_projections


ROOT = Path(__file__).resolve().parents[1]


class ProjectionInstallerTests(unittest.TestCase):
    def make_directory(self, name: str) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix=f"{name}-")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve()

    def roots(self) -> dict[str, Path]:
        base = self.make_directory("clients")
        return {
            "claude": base / "claude",
            "codex": base / "codex",
            "cursor": base / "cursor",
            "agents": base / "agents",
        }

    def test_dry_run_stages_and_reports_without_mutation(self) -> None:
        roots = self.roots()

        report = install_projections.install(
            ROOT,
            roots,
            dry_run=True,
            include_portable=True,
        )

        self.assertTrue(report["dry_run"])
        self.assertEqual(report["canonical_count"], 9)
        self.assertEqual(report["alias_count"], 15)
        self.assertTrue(report["actions"])
        self.assertTrue(all(not root.exists() for root in roots.values()))

    def test_install_layout_is_idempotent_and_uses_direct_links(self) -> None:
        roots = self.roots()

        first = install_projections.install(
            ROOT,
            roots,
            include_portable=True,
        )
        second = install_projections.install(
            ROOT,
            roots,
            include_portable=True,
        )

        claude_canonical = roots["claude"] / "platforms-mobile"
        claude_alias = roots["claude"] / "platforms-android"
        codex_canonical = roots["codex"] / "platforms-mobile"
        codex_alias = roots["codex"] / "platforms-android"
        self.assertTrue((claude_canonical / "SKILL.md").is_file())
        self.assertFalse(claude_canonical.is_symlink())
        self.assertEqual((claude_canonical / "SKILL.md").stat().st_mode & 0o222, 0)
        self.assertEqual(claude_alias.readlink(), Path("platforms-mobile"))
        self.assertEqual(codex_canonical.readlink(), claude_canonical.absolute())
        self.assertEqual(codex_alias.readlink(), claude_canonical.absolute())
        self.assertTrue((roots["cursor"] / "platforms-mobile/SKILL.md").is_file())
        self.assertEqual(
            (roots["cursor"] / "platforms-android").readlink(),
            Path("platforms-mobile"),
        )
        self.assertTrue((roots["agents"] / "platforms-mobile/SKILL.md").is_file())
        self.assertEqual(
            (roots["agents"] / "platforms-android").readlink(),
            Path("platforms-mobile"),
        )
        self.assertEqual(first["drift"]["drift"], False)
        self.assertEqual(second["changed"], 0)

    def test_initial_adoption_migrates_exact_legacy_codex_alias_link(self) -> None:
        roots = self.roots()
        alias = "platforms-android"
        canonical = "platforms-mobile"
        for client in ("claude", "cursor", "agents"):
            legacy_directory = roots[client] / alias
            legacy_directory.mkdir(parents=True)
            (legacy_directory / "SKILL.md").write_text(
                "pre-consolidation projection\n",
                encoding="utf-8",
            )
        roots["codex"].mkdir(parents=True)
        (roots["codex"] / alias).symlink_to(
            roots["claude"] / alias,
            target_is_directory=True,
        )

        dry_run = install_projections.install(ROOT, roots, dry_run=True)
        expected_target = (roots["claude"] / canonical).absolute()

        self.assertFalse(
            any((root / install_projections.STATE_FILE).exists() for root in roots.values())
        )
        self.assertIn(
            f"link {roots['codex'] / alias} -> {expected_target}",
            dry_run["actions"],
        )

        install_projections.install(ROOT, roots)

        for client in ("claude", "cursor", "agents"):
            self.assertEqual((roots[client] / alias).readlink(), Path(canonical))
        self.assertEqual((roots["codex"] / alias).readlink(), expected_target)

    def test_legacy_codex_alias_adoption_rejects_nonexact_or_missing_targets(self) -> None:
        alias = "platforms-android"
        cases = {
            "arbitrary-outside": lambda roots, outside: outside / alias,
            "relative-escape": lambda roots, outside: Path(
                f"../claude/{alias}"
            ),
            "missing-exact-alias": lambda roots, outside: roots["claude"] / alias,
            "canonical-name-mismatch": lambda roots, outside: (
                roots["claude"] / "platforms-tv"
            ),
        }
        for label, target_factory in cases.items():
            with self.subTest(label=label):
                roots = self.roots()
                outside = self.make_directory("legacy-target-outside")
                roots["claude"].mkdir(parents=True)
                if label != "missing-exact-alias":
                    (roots["claude"] / alias).mkdir()
                if label == "arbitrary-outside":
                    (outside / alias).mkdir()
                elif label == "canonical-name-mismatch":
                    (roots["claude"] / "platforms-tv").mkdir()
                roots["codex"].mkdir(parents=True)
                destination = roots["codex"] / alias
                destination.symlink_to(
                    target_factory(roots, outside),
                    target_is_directory=True,
                )

                with self.assertRaisesRegex(
                    install_projections.InstallSafetyError,
                    "unexpected symlink target",
                ):
                    install_projections.install(ROOT, roots, dry_run=True)

                self.assertTrue(destination.is_symlink())
                self.assertFalse(
                    any(
                        (root / install_projections.STATE_FILE).exists()
                        for root in roots.values()
                    )
                )

    def test_initial_adoption_migrates_exact_shared_client_links(self) -> None:
        base = self.make_directory("shared-clients")
        roots = {
            client: base / f".{client}" / "skills"
            for client in install_projections.SUPPORTED_CLIENTS
        }
        canonical = "platforms"
        alias = "platforms-android"
        roots["claude"].mkdir(parents=True)
        for name in (canonical, alias):
            legacy_directory = roots["agents"] / name
            legacy_directory.mkdir(parents=True)
            (legacy_directory / "SKILL.md").write_text(
                "legacy shared projection\n",
                encoding="utf-8",
            )
            (roots["claude"] / name).symlink_to(
                Path(f"../../.agents/skills/{name}"),
                target_is_directory=True,
            )

        dry_run = install_projections.install(ROOT, roots, dry_run=True)

        self.assertFalse(
            any((root / install_projections.STATE_FILE).exists() for root in roots.values())
        )
        self.assertIn(
            f"copy {canonical} -> {roots['claude'] / canonical}",
            dry_run["actions"],
        )
        self.assertIn(
            f"link {roots['claude'] / alias} -> platforms-mobile",
            dry_run["actions"],
        )

        install_projections.install(ROOT, roots)

        self.assertFalse((roots["claude"] / canonical).is_symlink())
        self.assertTrue((roots["claude"] / canonical / "SKILL.md").is_file())
        self.assertEqual(
            (roots["claude"] / alias).readlink(),
            Path("platforms-mobile"),
        )

    def test_shared_client_adoption_rejects_unsafe_targets(self) -> None:
        name = "platforms"
        for label in (
            "wrong-name",
            "missing",
            "symlink-target",
            "outside-root",
            "nested-entry",
            "file-target",
        ):
            with self.subTest(label=label):
                roots = self.roots()
                roots["claude"].mkdir(parents=True)
                roots["agents"].mkdir(parents=True)
                if label == "wrong-name":
                    (roots["agents"] / "platforms-mobile").mkdir()
                    target = Path("../agents/platforms-mobile")
                elif label == "missing":
                    target = Path(f"../agents/{name}")
                elif label == "symlink-target":
                    (roots["agents"] / "backing").mkdir()
                    (roots["agents"] / name).symlink_to(
                        "backing",
                        target_is_directory=True,
                    )
                    target = Path(f"../agents/{name}")
                elif label == "outside-root":
                    outside = roots["claude"].parent / "outside" / name
                    outside.mkdir(parents=True)
                    target = Path(f"../outside/{name}")
                elif label == "nested-entry":
                    (roots["agents"] / name / "nested").mkdir(parents=True)
                    target = Path(f"../agents/{name}/nested")
                else:
                    (roots["agents"] / name).write_text("not a directory\n", encoding="utf-8")
                    target = Path(f"../agents/{name}")
                destination = roots["claude"] / name
                destination.symlink_to(target, target_is_directory=True)

                with self.assertRaisesRegex(
                    install_projections.InstallSafetyError,
                    "symlink",
                ):
                    install_projections.install(ROOT, roots, dry_run=True)

                self.assertTrue(destination.is_symlink())
                self.assertFalse(
                    any(
                        (root / install_projections.STATE_FILE).exists()
                        for root in roots.values()
                    )
                )

    def test_stale_recorded_managed_name_is_removed(self) -> None:
        roots = self.roots()
        claude = roots["claude"]
        stale = claude / "platforms-retired"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("retired\n", encoding="utf-8")
        (claude / install_projections.STATE_FILE).write_text(
            json.dumps({"managed": ["platforms-retired"]}) + "\n",
            encoding="utf-8",
        )

        report = install_projections.install(ROOT, roots)

        self.assertFalse(stale.exists())
        self.assertIn(str(stale), report["removed"])

    def test_symlink_unsafe_target_is_rejected_without_touching_outside(self) -> None:
        roots = self.roots()
        outside = self.make_directory("outside")
        sentinel = outside / "SKILL.md"
        sentinel.write_text("outside\n", encoding="utf-8")
        roots["claude"].mkdir(parents=True)
        (roots["claude"] / "platforms-mobile").symlink_to(
            outside,
            target_is_directory=True,
        )

        with self.assertRaisesRegex(install_projections.InstallSafetyError, "symlink"):
            install_projections.install(ROOT, roots)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside\n")
        self.assertFalse(roots["codex"].exists())

    def test_invalid_stage_fails_before_destination_mutation(self) -> None:
        suite_root = self.make_directory("invalid-suite")
        (suite_root / "suite.toml").write_text(
            (ROOT / "suite.toml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (suite_root / "skills").mkdir()
        roots = self.roots()

        with self.assertRaises(install_projections.InstallValidationError):
            install_projections.install(suite_root, roots)

        self.assertTrue(all(not root.exists() for root in roots.values()))

    def test_ancestor_symlink_and_overlapping_roots_are_rejected(self) -> None:
        base = self.make_directory("unsafe-roots")
        outside = self.make_directory("outside-root")
        linked_parent = base / "linked"
        linked_parent.symlink_to(outside, target_is_directory=True)
        roots = self.roots()
        roots["claude"] = linked_parent / "claude"

        with self.assertRaisesRegex(install_projections.InstallSafetyError, "ancestor"):
            install_projections.install(ROOT, roots)
        self.assertFalse((outside / "claude").exists())

        overlapping = self.roots()
        overlapping["cursor"] = overlapping["claude"] / "nested"
        with self.assertRaisesRegex(install_projections.InstallSafetyError, "overlap"):
            install_projections.install(ROOT, overlapping)
        self.assertTrue(all(not root.exists() for root in overlapping.values()))

    def test_hostile_managed_state_names_are_rejected_without_deletion(self) -> None:
        for hostile in ("../sentinel", "/tmp/platforms-sentinel", "platforms/../../sentinel"):
            with self.subTest(hostile=hostile):
                roots = self.roots()
                claude = roots["claude"]
                claude.mkdir(parents=True)
                sentinel = claude.parent / "sentinel"
                sentinel.write_text("keep\n", encoding="utf-8")
                (claude / install_projections.STATE_FILE).write_text(
                    json.dumps({"managed": [hostile]}) + "\n",
                    encoding="utf-8",
                )

                with self.assertRaises(install_projections.InstallValidationError):
                    install_projections.install(ROOT, roots)

                self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
                self.assertFalse(roots["codex"].exists())

    def test_failed_replacement_preserves_original_and_cleans_staging(self) -> None:
        roots = self.roots()
        install_projections.install(ROOT, roots)
        installed = roots["claude"] / "platforms-mobile/SKILL.md"
        installed.chmod(0o644)
        installed.write_text("original projection\n", encoding="utf-8")

        with mock.patch.object(
            install_projections,
            "_replace_with_backup",
            side_effect=OSError("injected replacement failure"),
        ):
            with self.assertRaisesRegex(OSError, "injected"):
                install_projections.install(ROOT, roots)

        self.assertEqual(installed.read_text(encoding="utf-8"), "original projection\n")
        for root in roots.values():
            self.assertEqual(list(root.glob(".platforms-stage-*")), [])


if __name__ == "__main__":
    unittest.main()
