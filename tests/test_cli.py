# File Purpose: Verify platforms CLI commands for detect/plan/doctor/build/validate/package/report/drift.
# Primary Functions/Classes: CliCommandTests.
# Inputs/Outputs: Invokes platforms.cli.main with temporary projects; asserts exit codes and JSON shape.

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from platforms import cli


class CliCommandTests(unittest.TestCase):
    def make_project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [web-kiosk]\n",
            encoding="utf-8",
        )
        (root / "www").mkdir()
        (root / "www" / "index.html").write_text(
            "<!doctype html><html lang=\"en\"><head><title>Fixture</title></head>"
            "<body><a href=\"#main\">Skip</a><main id=\"main\" tabindex=\"-1\">"
            "<h1>Fixture</h1></main></body></html>\n",
            encoding="utf-8",
        )
        return root

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_detect_emits_json(self) -> None:
        root = self.make_project()
        code, out, err = self.run_cli("detect", "--project", str(root), "--json")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertIn("detections", payload)
        self.assertTrue(any(item["platform_id"] == "web-kiosk" for item in payload["detections"]))

    def test_plan_doctor_build_validate_package_report(self) -> None:
        root = self.make_project()
        for command in ("plan", "doctor", "build", "validate", "package", "report"):
            code, out, err = self.run_cli(
                command,
                "--project",
                str(root),
                "--platform",
                "web-kiosk",
                "--json",
            )
            self.assertEqual(code, 0, f"{command}: {err}\n{out}")
            payload = json.loads(out)
            self.assertEqual(payload["platform_id"], "web-kiosk")
            if command == "build":
                self.assertEqual(payload["track_state"], "built")
                self.assertFalse(
                    any(path.endswith("BUILD_STUB.txt") for path in payload["artifacts"])
                )
            if command == "validate":
                self.assertEqual(payload["track_state"], "validated")
            if command == "package":
                self.assertEqual(payload["track_state"], "store-staged")
            if command == "build":
                self.assertEqual(payload["track_state"], "built")
                self.assertFalse(
                    any(path.endswith("BUILD_STUB.txt") for path in payload["artifacts"])
                )
            if command == "validate":
                self.assertEqual(payload["track_state"], "validated")
            if command == "package":
                self.assertEqual(payload["track_state"], "store-staged")

    def test_rejects_path_traversal_project(self) -> None:
        code, _out, err = self.run_cli("detect", "--project", "/tmp/../etc", "--json")
        self.assertEqual(code, 2)
        self.assertIn("project", err.lower())

    def test_drift_command_delegates(self) -> None:
        code, out, err = self.run_cli("drift", "--help")
        self.assertEqual(code, 0, err)
        self.assertIn("drift", out.lower() + err.lower())
