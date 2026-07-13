# File Purpose: Verify deterministic suite manifest generation and metadata validation.
# Primary Functions/Classes: ManifestGenerationTests and temporary suite fixtures.
# Inputs/Outputs: Creates temporary suite roots; asserts generated JSON, hashes, and exit codes.

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tools import generate_manifests


VALID_SUITE = """\
schema_version = 1

[suite]
id = "platforms"
name = "Platforms"
description = "Portable platform publishing workflows."
version = "0.1.0"
author = "Luke Steuber"
repository = "https://github.com/actually-useful-ai/platforms"
license = "MIT"

[clients]
supported = ["claude", "cursor", "codex", "agents"]

[[skills]]
id = "platforms"

[[skills]]
id = "platforms-intake"

[[aliases]]
id = "platforms-old"
target = "platforms"

[[agents]]
id = "platform-recon"
read_only = true
"""


class ManifestGenerationTests(unittest.TestCase):
    """Exercise generation through its public Python and CLI-style interfaces."""

    def make_root(self, suite_text: str = VALID_SUITE) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "suite.toml").write_text(suite_text, encoding="utf-8")
        return root

    def test_generation_is_deterministic_and_json_is_stable(self) -> None:
        root = self.make_root()

        self.assertEqual(generate_manifests.generate(root), [])
        first = {
            path: (root / path).read_bytes()
            for path in (*generate_manifests.GENERATED_MANIFESTS, generate_manifests.LOCK_PATH)
        }
        self.assertEqual(generate_manifests.generate(root), [])
        second = {
            path: (root / path).read_bytes()
            for path in (*generate_manifests.GENERATED_MANIFESTS, generate_manifests.LOCK_PATH)
        }

        self.assertEqual(first, second)
        for path, payload in second.items():
            self.assertTrue(payload.endswith(b"\n"), path)
            parsed = json.loads(payload)
            self.assertEqual(
                payload.decode("utf-8"),
                json.dumps(parsed, indent=2, sort_keys=True) + "\n",
                path,
            )

        lock = json.loads(second[generate_manifests.LOCK_PATH])
        self.assertEqual(lock["suite_version"], "0.1.0")
        self.assertNotIn("timestamp", lock)
        self.assertEqual(
            [entry["path"] for entry in lock["files"]],
            sorted(entry["path"] for entry in lock["files"]),
        )
        suite_entry = next(entry for entry in lock["files"] if entry["path"] == "suite.toml")
        self.assertEqual(
            suite_entry["sha256"],
            hashlib.sha256((root / "suite.toml").read_bytes()).hexdigest(),
        )
        self.assertEqual(suite_entry["mode"], "0644")
        self.assertFalse(suite_entry["executable"])

    def test_check_reports_drift_without_writing(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)
        manifest = root / ".cursor-plugin/plugin.json"
        manifest.write_text('{"drift": true}\n', encoding="utf-8")
        before = manifest.read_bytes()
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = generate_manifests.main(["--root", str(root), "--check"])

        self.assertEqual(exit_code, 1)
        self.assertIn(".cursor-plugin/plugin.json", stdout.getvalue())
        self.assertEqual(manifest.read_bytes(), before)

    def test_check_reports_mode_drift_without_writing(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)
        manifest = root / ".cursor-plugin/plugin.json"
        manifest.chmod(0o755)
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = generate_manifests.main(["--root", str(root), "--check"])

        self.assertEqual(exit_code, 1)
        self.assertIn(".cursor-plugin/plugin.json", stdout.getvalue())
        self.assertEqual(manifest.stat().st_mode & 0o777, 0o755)

    def test_invalid_suite_metadata_is_rejected_before_writes(self) -> None:
        root = self.make_root(VALID_SUITE.replace('version = "0.1.0"', 'version = "release"'))

        with self.assertRaises(generate_manifests.SuiteValidationError):
            generate_manifests.generate(root)

        self.assertFalse((root / ".claude-plugin/plugin.json").exists())

    def test_generated_component_shapes_follow_local_exemplars(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)

        claude = json.loads(
            (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
        )
        cursor = json.loads(
            (root / ".cursor-plugin/plugin.json").read_text(encoding="utf-8")
        )
        codex = json.loads(
            (root / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        agents_marketplace = json.loads(
            (root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        lock = json.loads((root / generate_manifests.LOCK_PATH).read_text(encoding="utf-8"))

        self.assertNotIn("skills", claude)
        self.assertNotIn("agents", claude)
        self.assertNotIn("client", claude)
        self.assertEqual(cursor["skills"], "./skills/")
        self.assertNotIn("agents", cursor)
        self.assertNotIn("client", cursor)
        self.assertEqual(codex["skills"], "./skills/")
        self.assertNotIn("agents", codex)
        self.assertNotIn("client", codex)
        self.assertEqual(
            agents_marketplace["plugins"][0]["source"],
            {"source": "url", "url": "./"},
        )
        for marketplace_path in (
            ".agents/plugins/marketplace.json",
            ".claude-plugin/marketplace.json",
            ".cursor-plugin/marketplace.json",
        ):
            record = json.loads(
                (root / marketplace_path).read_text(encoding="utf-8")
            )["plugins"][0]
            self.assertNotIsInstance(record.get("skills"), list, marketplace_path)
            self.assertNotIsInstance(record.get("agents"), list, marketplace_path)
        self.assertEqual(
            lock["inventory"],
            {
                "agents": ["platform-recon"],
                "aliases": [{"id": "platforms-old", "target": "platforms"}],
                "skills": ["platforms", "platforms-intake"],
            },
        )

    def test_alias_inventory_is_sorted_in_lock(self) -> None:
        suite = VALID_SUITE.replace(
            '[[aliases]]\nid = "platforms-old"\ntarget = "platforms"',
            '[[aliases]]\nid = "platforms-zed"\ntarget = "platforms"\n\n'
            '[[aliases]]\nid = "platforms-old"\ntarget = "platforms-intake"',
        )
        root = self.make_root(suite)

        generate_manifests.generate(root)

        lock = json.loads((root / generate_manifests.LOCK_PATH).read_text(encoding="utf-8"))
        self.assertEqual(
            lock["inventory"]["aliases"],
            [
                {"id": "platforms-old", "target": "platforms-intake"},
                {"id": "platforms-zed", "target": "platforms"},
            ],
        )

    def test_supported_client_subset_controls_outputs_and_lock(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)
        cursor_only = VALID_SUITE.replace(
            'supported = ["claude", "cursor", "codex", "agents"]',
            'supported = ["cursor"]',
        )
        (root / "suite.toml").write_text(cursor_only, encoding="utf-8")

        check_drift = generate_manifests.generate(root, check=True)
        generate_manifests.generate(root)

        self.assertIn(".claude-plugin/plugin.json", check_drift)
        self.assertIn(".codex-plugin/plugin.json", check_drift)
        self.assertIn(".agents/plugins/marketplace.json", check_drift)
        self.assertTrue((root / ".cursor-plugin/plugin.json").is_file())
        self.assertTrue((root / ".cursor-plugin/marketplace.json").is_file())
        self.assertFalse((root / ".claude-plugin/plugin.json").exists())
        self.assertFalse((root / ".codex-plugin/plugin.json").exists())
        self.assertFalse((root / ".agents/plugins/marketplace.json").exists())
        lock = json.loads((root / generate_manifests.LOCK_PATH).read_text(encoding="utf-8"))
        self.assertEqual(
            [entry["path"] for entry in lock["files"]],
            [
                ".cursor-plugin/marketplace.json",
                ".cursor-plugin/plugin.json",
                "suite.toml",
            ],
        )
        self.assertEqual(lock["supported_clients"], ["cursor"])

    def test_generation_refuses_symlinked_output_file(self) -> None:
        root = self.make_root()
        outside = self.make_root()
        sentinel = outside / "sentinel.json"
        sentinel.write_text("outside\n", encoding="utf-8")
        target = root / ".claude-plugin/plugin.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(sentinel)

        with self.assertRaisesRegex(RuntimeError, "symlink"):
            generate_manifests.generate(root)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside\n")

    def test_generation_refuses_symlinked_output_parent(self) -> None:
        root = self.make_root()
        outside = self.make_root()
        (root / ".cursor-plugin").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(RuntimeError, "symlink"):
            generate_manifests.generate(root)

        self.assertFalse((outside / "plugin.json").exists())

    def test_injected_commit_failure_rolls_back_all_generated_outputs(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)
        managed_paths = (*generate_manifests.GENERATED_MANIFESTS, generate_manifests.LOCK_PATH)
        before = {path: (root / path).read_bytes() for path in managed_paths}
        (root / "suite.toml").write_text(
            VALID_SUITE.replace('version = "0.1.0"', 'version = "0.1.1"'),
            encoding="utf-8",
        )
        real_replace = generate_manifests.os.replace
        calls = 0

        def fail_once(source: Path | str, destination: Path | str) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("injected manifest commit failure")
            real_replace(source, destination)

        with mock.patch.object(generate_manifests.os, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "injected"):
                generate_manifests.generate(root)

        self.assertEqual(
            {path: (root / path).read_bytes() for path in managed_paths},
            before,
        )
        self.assertEqual(list(root.glob(".manifest-stage-*")), [])


if __name__ == "__main__":
    unittest.main()
