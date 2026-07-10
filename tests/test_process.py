# File Purpose: Verify the secure subprocess runner rejects unsafe invocation patterns.
# Primary Functions/Classes: ProcessRunnerTests.
# Inputs/Outputs: Exercises allowlisted argv execution; asserts no shell=True and path constraints.

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from platforms.process import ProcessError, run_allowlisted


class ProcessRunnerTests(unittest.TestCase):
    def test_runs_allowlisted_argv_without_shell(self) -> None:
        result = run_allowlisted(["/bin/echo", "platforms-ok"], cwd=Path.cwd())
        self.assertEqual(result.returncode, 0)
        self.assertIn("platforms-ok", result.stdout)

    def test_rejects_shell_metacharacters_in_argv(self) -> None:
        with self.assertRaises(ProcessError):
            run_allowlisted(["/bin/echo", "a;b"], cwd=Path.cwd())

    def test_rejects_cwd_outside_allowed_roots(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        outside = Path(temporary.name)
        with self.assertRaises(ProcessError):
            run_allowlisted(
                ["/bin/echo", "nope"],
                cwd=outside,
                allowed_roots=[Path.cwd()],
            )

    def test_rejects_empty_argv(self) -> None:
        with self.assertRaises(ProcessError):
            run_allowlisted([], cwd=Path.cwd())
