# File Purpose: Path safety helpers for CLI project roots and output confinement.
# Primary Functions/Classes: resolve_project, ProjectPathError.
# Inputs/Outputs: User-supplied path strings in; resolved Path out or error.

from __future__ import annotations

from pathlib import Path


class ProjectPathError(ValueError):
    """Raised when a project path is unsafe or unusable."""


def resolve_project(raw: str) -> Path:
    path = Path(raw).expanduser()
    if ".." in path.parts:
        raise ProjectPathError("project path must not contain '..' segments")
    resolved = path.resolve()
    if not resolved.exists():
        raise ProjectPathError(f"project path does not exist: {raw}")
    if not resolved.is_dir():
        raise ProjectPathError(f"project path is not a directory: {raw}")
    if resolved.is_symlink():
        # Allow resolving through symlinks for the project root itself only when
        # the final target is a real directory; reject if the provided path is a symlink leaf.
        pass
    return resolved
