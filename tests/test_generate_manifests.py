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

    def test_invalid_suite_metadata_is_rejected_before_writes(self) -> None:
        root = self.make_root(VALID_SUITE.replace('version = "0.1.0"', 'version = "release"'))

        with self.assertRaises(generate_manifests.SuiteValidationError):
            generate_manifests.generate(root)

        self.assertFalse((root / ".claude-plugin/plugin.json").exists())

    def test_manifest_inventory_comes_from_suite_metadata(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)

        plugin = json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [skill["name"] for skill in plugin["skills"]],
            ["platforms", "platforms-intake"],
        )
        self.assertEqual(plugin["agents"], [{"name": "platform-recon", "read_only": True}])

    def test_marketplace_record_carries_component_inventory(self) -> None:
        root = self.make_root()
        generate_manifests.generate(root)

        marketplace = json.loads(
            (root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        record = marketplace["plugins"][0]

        self.assertEqual(record["skills"], ["platforms", "platforms-intake"])
        self.assertEqual(record["agents"], ["platform-recon"])


if __name__ == "__main__":
    unittest.main()
