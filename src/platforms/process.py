# File Purpose: Secure allowlisted subprocess execution without shell interpolation.
# Primary Functions/Classes: ProcessResult, ProcessError, run_allowlisted.
# Inputs/Outputs: Accepts argv + cwd + optional allowed roots; returns captured stdout/stderr/returncode.

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_UNSAFE_ARGV = re.compile(r"[;&|`$<>\n\r]")


class ProcessError(ValueError):
    """Raised when a process invocation violates safety policy."""


@dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _resolve_under_roots(path: Path, allowed_roots: list[Path] | None) -> Path:
    resolved = path.resolve()
    if allowed_roots is None:
        return resolved
    for root in allowed_roots:
        root_resolved = root.resolve()
        try:
            resolved.relative_to(root_resolved)
            return resolved
        except ValueError:
            continue
    raise ProcessError(f"path escapes allowed roots: {path}")


def run_allowlisted(
    argv: list[str] | tuple[str, ...],
    *,
    cwd: Path,
    allowed_roots: list[Path] | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = 120.0,
) -> ProcessResult:
    """Run an exact argv array with shell disabled and optional root confinement."""
    if not argv:
        raise ProcessError("argv must not be empty")
    for part in argv:
        if not isinstance(part, str) or part == "":
            raise ProcessError("argv entries must be non-empty strings")
        if _UNSAFE_ARGV.search(part):
            raise ProcessError(f"argv contains unsafe characters: {part!r}")

    workdir = _resolve_under_roots(cwd, allowed_roots)
    if not workdir.is_dir():
        raise ProcessError(f"cwd is not a directory: {cwd}")

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    completed = subprocess.run(
        list(argv),
        cwd=str(workdir),
        env=merged_env,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return ProcessResult(
        argv=tuple(argv),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
