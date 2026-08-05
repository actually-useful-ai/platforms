# File Purpose: Compare canonical skills with installed projections without editing them.
# Primary Functions/Classes: is_ignored_root, default_client_roots, compare_roots, and main.
# Inputs/Outputs: Reads skill trees and suite metadata; emits stable JSON and drift exit status.

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

try:
    from .generate_manifests import SuiteValidationError, load_suite
except ImportError:
    from generate_manifests import SuiteValidationError, load_suite


_CACHE_COMPONENTS = {
    ".agent-cache",
    ".cache",
    "agent-cache",
    "agent_caches",
    "cache",
    "caches",
}
_IGNORED_PROJECTION_DIRECTORIES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
_IGNORED_PROJECTION_FILES = {
    ".coverage",
    ".DS_Store",
}
_IGNORED_PROJECTION_SUFFIXES = {
    ".pyc",
    ".pyo",
}
_STATE_FILE = ".platforms-projections.json"
SUPPORTED_CLIENTS = ("claude", "codex", "cursor", "agents")


def default_client_roots(home: Path | None = None) -> list[Path]:
    """Return the conventional skill root for every supported client."""

    base = (home or Path.home()).expanduser()
    return [base / f".{client}" / "skills" for client in SUPPORTED_CLIENTS]


def is_ignored_root(root: Path) -> bool:
    """Return whether a root is managed externally and must not be inspected."""

    resolved = root.expanduser().resolve(strict=False)
    cursor_managed = (Path.home() / ".cursor" / "skills-cursor").resolve(strict=False)
    if resolved == cursor_managed or cursor_managed in resolved.parents:
        return True
    return any(part.lower() in _CACHE_COMPONENTS for part in resolved.parts)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _projection_files(skill_root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    if not skill_root.is_dir():
        return files
    for path in sorted(skill_root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(skill_root).as_posix()
            relative_parts = Path(relative).parts
            if any(
                part in _IGNORED_PROJECTION_DIRECTORIES
                for part in relative_parts[:-1]
            ):
                continue
            if (
                path.name in _IGNORED_PROJECTION_FILES
                or path.suffix in _IGNORED_PROJECTION_SUFFIXES
            ):
                continue
            files[relative] = _hash_file(path)
    return files


def _recorded_managed_names(root: Path) -> set[str]:
    """Read valid managed names from installer state without modifying it."""

    state_path = root / _STATE_FILE
    if not state_path.is_file() or state_path.is_symlink():
        return set()
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    managed = value.get("managed", [])
    if not isinstance(managed, list):
        return set()
    return {name for name in managed if isinstance(name, str)}


def compare_roots(
    canonical_root: Path,
    installed_roots: Sequence[Path],
    managed_skills: Sequence[str],
    *,
    aliases: dict[str, str] | None = None,
    stale_managed_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Compare canonical content, aliases, and stale managed names separately."""

    canonical_root = canonical_root.expanduser().resolve(strict=False)
    aliases = aliases or {}
    canonical = {
        name: _projection_files(canonical_root / name)
        for name in sorted(set(managed_skills))
        if (canonical_root / name / "SKILL.md").is_file()
    }
    ignored_roots: list[str] = []
    root_reports: list[dict[str, Any]] = []

    for installed_root in installed_roots:
        resolved = installed_root.expanduser().resolve(strict=False)
        if is_ignored_root(resolved):
            ignored_roots.append(str(resolved))
            continue

        installed = {
            name: _projection_files(resolved / name)
            for name in sorted(set(managed_skills))
            if (resolved / name / "SKILL.md").is_file()
        }
        missing = sorted(set(canonical) - set(installed))
        extra = sorted(set(installed) - set(canonical))
        changed: list[str] = []
        for name in sorted(set(canonical) & set(installed)):
            canonical_files = canonical[name]
            installed_files = installed[name]
            for relative in sorted(set(canonical_files) | set(installed_files)):
                if canonical_files.get(relative) != installed_files.get(relative):
                    changed.append(f"{name}/{relative}")
        missing_aliases: list[str] = []
        changed_aliases: list[str] = []
        for alias, target in sorted(aliases.items()):
            alias_path = resolved / alias
            target_path = resolved / target
            if not alias_path.exists() and not alias_path.is_symlink():
                missing_aliases.append(alias)
                continue
            if (
                not alias_path.is_symlink()
                or not target_path.exists()
                or alias_path.resolve(strict=False) != target_path.resolve(strict=False)
            ):
                changed_aliases.append(alias)
        recorded_stale = _recorded_managed_names(resolved) - set(canonical) - set(aliases)
        stale = sorted(
            name
            for name in set(stale_managed_names) | recorded_stale
            if (resolved / name).exists() or (resolved / name).is_symlink()
        )
        root_reports.append(
            {
                "changed": changed,
                "changed_aliases": changed_aliases,
                "extra": extra,
                "missing": missing,
                "missing_aliases": missing_aliases,
                "root": str(resolved),
                "stale": stale,
            }
        )

    drift = any(
        report["missing"]
        or report["changed"]
        or report["extra"]
        or report["missing_aliases"]
        or report["changed_aliases"]
        or report["stale"]
        for report in root_reports
    )
    return {
        "canonical_root": str(canonical_root),
        "drift": drift,
        "ignored_roots": sorted(ignored_roots),
        "roots": root_reports,
    }


def _parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Report drift in optional installed skill projections as JSON."
    )
    parser.add_argument(
        "installed_roots",
        metavar="ROOT",
        nargs="*",
        type=Path,
        help="installed skill roots to compare; omitted roots fall back to discovery",
    )
    parser.add_argument(
        "--client-home",
        type=Path,
        default=None,
        help="home directory searched for supported-client skill roots",
    )
    parser.add_argument(
        "--allow-no-roots",
        action="store_true",
        help="report clean when no installed root is given or discovered",
    )
    parser.add_argument(
        "--canonical-root",
        type=Path,
        default=repository_root / "skills",
        help="canonical skill root (defaults to repository skills/)",
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=repository_root / "suite.toml",
        help="suite metadata used to identify managed skill names",
    )
    parser.add_argument(
        "--managed-skill",
        action="append",
        default=[],
        help="override suite inventory with a managed skill name; repeat as needed",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Emit a drift report and return nonzero only for managed projection drift."""

    args = _parser().parse_args(argv)
    if args.managed_skill:
        managed_skills = sorted(set(args.managed_skill))
    else:
        try:
            suite_data = load_suite(args.suite)
        except SuiteValidationError as error:
            report = {
                "error": f"invalid suite metadata: {error}",
                "ignored_roots": [],
                "roots": [],
                "status": "error",
            }
            print(json.dumps(report, indent=2, sort_keys=True))
            return 2
        managed_skills = [skill["id"] for skill in suite_data["skills"]]
    aliases = (
        {}
        if args.managed_skill
        else {item["id"]: item["target"] for item in suite_data["aliases"]}
    )

    installed_roots = list(args.installed_roots)
    discovered_roots: list[str] = []
    if not installed_roots:
        for candidate in default_client_roots(args.client_home):
            if candidate.is_dir():
                installed_roots.append(candidate)
                discovered_roots.append(str(candidate.resolve(strict=False)))
    if not installed_roots and not args.allow_no_roots:
        report = {
            "error": (
                "no installed skill root was given or discovered; pass roots "
                "explicitly or use --allow-no-roots to assert none are installed"
            ),
            "ignored_roots": [],
            "roots": [],
            "status": "error",
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    report = compare_roots(
        args.canonical_root,
        installed_roots,
        managed_skills,
        aliases=aliases,
    )
    report["discovered_roots"] = sorted(discovered_roots)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["drift"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
