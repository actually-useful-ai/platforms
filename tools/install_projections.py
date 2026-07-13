# File Purpose: Safely project canonical suite skills and legacy aliases into client roots.
# Primary Functions/Classes: InstallSafetyError, InstallValidationError, install, and main.
# Inputs/Outputs: Reads suite metadata and skills; copies or links managed projections and emits JSON.

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .check_drift import compare_roots
    from .generate_manifests import SuiteValidationError, load_suite
except ImportError:
    from check_drift import compare_roots
    from generate_manifests import SuiteValidationError, load_suite


STATE_FILE = ".platforms-projections.json"
_MANAGED_NAME = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SUPPORTED_CLIENTS = ("claude", "codex", "cursor", "agents")
DEFAULT_ROOTS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "cursor": Path.home() / ".cursor" / "skills",
    "agents": Path.home() / ".agents" / "skills",
}


class InstallSafetyError(RuntimeError):
    """Raised before an installation could follow or overwrite an unsafe path."""


class InstallValidationError(ValueError):
    """Raised when canonical source content cannot be safely projected."""


def _read_state(root: Path) -> set[str]:
    state_path = root / STATE_FILE
    if not state_path.exists():
        return set()
    if state_path.is_symlink() or not state_path.is_file():
        raise InstallSafetyError(f"managed state is not a regular file: {state_path}")
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallValidationError(f"cannot read managed state {state_path}: {error}") from error
    managed = value.get("managed", [])
    if not isinstance(managed, list) or any(not isinstance(name, str) for name in managed):
        raise InstallValidationError(f"invalid managed state: {state_path}")
    invalid = sorted(name for name in managed if not _MANAGED_NAME.fullmatch(name))
    if invalid:
        raise InstallValidationError(
            f"invalid managed name in {state_path}: {invalid[0]!r}"
        )
    return set(managed)


def _assert_safe_root(root: Path) -> None:
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current /= part
        if current.is_symlink():
            raise InstallSafetyError(f"projection root ancestor is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise InstallSafetyError(
                f"projection root ancestor is not a directory: {current}"
            )
    if root.exists() and not root.is_dir():
        raise InstallSafetyError(f"projection root is not a directory: {root}")


def _assert_safe_entry(
    path: Path,
    expected_link: Path | None = None,
    legacy_link: Path | None = None,
    shared_roots: Sequence[Path] = (),
) -> None:
    if not path.is_symlink():
        if path.exists() and not path.is_dir():
            raise InstallSafetyError(f"managed destination is not a directory: {path}")
        return
    try:
        actual = path.readlink()
    except OSError as error:
        raise InstallSafetyError(f"cannot inspect managed symlink {path}: {error}") from error
    if expected_link is not None and actual == expected_link:
        return
    if legacy_link is not None and actual == legacy_link:
        try:
            resolved_legacy = legacy_link.resolve(strict=True)
        except OSError:
            resolved_legacy = None
        legacy_root = legacy_link.parent
        if (
            legacy_link.is_absolute()
            and legacy_link.name == path.name
            and resolved_legacy is not None
            and resolved_legacy.is_dir()
            and (resolved_legacy == legacy_root or legacy_root in resolved_legacy.parents)
        ):
            return
    try:
        resolved_actual = (path.parent / actual).resolve(strict=True)
    except OSError:
        resolved_actual = None
    if resolved_actual is not None:
        for shared_root in shared_roots:
            candidate = shared_root / path.name
            if candidate.is_symlink() or not candidate.is_dir():
                continue
            try:
                resolved_candidate = candidate.resolve(strict=True)
            except OSError:
                continue
            if (
                resolved_candidate == candidate
                and shared_root in resolved_candidate.parents
                and resolved_actual == resolved_candidate
            ):
                return
    if expected_link is None:
        raise InstallSafetyError(f"managed destination is an unsafe symlink: {path}")
    raise InstallSafetyError(f"managed destination has unexpected symlink target: {path}")


def _validate_sources(
    suite_root: Path,
    canonical_names: Sequence[str],
) -> None:
    skills_root = suite_root / "skills"
    if skills_root.is_symlink() or not skills_root.is_dir():
        raise InstallValidationError(f"canonical skills root is unsafe or missing: {skills_root}")
    for name in canonical_names:
        source = skills_root / name
        skill_file = source / "SKILL.md"
        if source.is_symlink() or not source.is_dir() or not skill_file.is_file():
            raise InstallValidationError(f"missing canonical skill: {name}")
        if skill_file.is_symlink():
            raise InstallValidationError(f"canonical SKILL.md must not be a symlink: {name}")
        if any(path.is_symlink() for path in source.rglob("*")):
            raise InstallValidationError(f"canonical skill contains a symlink: {name}")
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n") or f"\nname: {name}\n" not in f"\n{text}":
            raise InstallValidationError(f"invalid canonical skill frontmatter: {name}")


def _copy_payload(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, symlinks=False)
    for path in sorted(destination.rglob("*")):
        if path.is_symlink():
            raise InstallValidationError(f"canonical skill contains a symlink: {source.name}")
        if path.is_file():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        elif path.is_dir():
            path.chmod(
                stat.S_IRUSR
                | stat.S_IWUSR
                | stat.S_IXUSR
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
            )


def _same_tree(left: Path, right: Path) -> bool:
    if left.is_symlink() or not left.is_dir():
        return False
    if any(
        path.is_symlink()
        or (path.is_file() and stat.S_IMODE(path.stat().st_mode) & 0o222 != 0)
        for path in left.rglob("*")
    ):
        return False
    left_files = {
        path.relative_to(left): path.read_bytes()
        for path in left.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    right_files = {
        path.relative_to(right): path.read_bytes()
        for path in right.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    return left_files == right_files


def _remove_managed(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _replace_with_backup(staged: Path, destination: Path) -> None:
    """Replace one managed entry and restore the original if commit fails."""

    backup = destination.parent / f".platforms-stage-backup-{destination.name}"
    if backup.exists() or backup.is_symlink():
        raise InstallSafetyError(f"stale replacement backup exists: {backup}")
    had_original = destination.exists() or destination.is_symlink()
    if had_original:
        os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except Exception:
        if had_original and (backup.exists() or backup.is_symlink()):
            os.replace(backup, destination)
        raise
    if backup.exists() or backup.is_symlink():
        _remove_managed(backup)


def _commit_copy(source: Path, destination: Path) -> None:
    stage_root = Path(
        tempfile.mkdtemp(prefix=".platforms-stage-", dir=destination.parent)
    )
    try:
        staged = stage_root / destination.name
        _copy_payload(source, staged)
        _replace_with_backup(staged, destination)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def _commit_link(target: Path, destination: Path) -> None:
    stage_root = Path(
        tempfile.mkdtemp(prefix=".platforms-stage-", dir=destination.parent)
    )
    try:
        staged = stage_root / destination.name
        staged.symlink_to(target, target_is_directory=True)
        _replace_with_backup(staged, destination)
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def _write_state(root: Path, managed: Sequence[str]) -> bool:
    payload = (
        json.dumps({"managed": sorted(set(managed)), "schema_version": 1}, indent=2, sort_keys=True)
        + "\n"
    )
    state_path = root / STATE_FILE
    if state_path.exists() and state_path.read_text(encoding="utf-8") == payload:
        return False
    descriptor, temporary_name = tempfile.mkstemp(
        dir=root, prefix=f".{STATE_FILE}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, state_path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _apply_changes(
    normalized_roots: Mapping[str, Path],
    prior_managed: Mapping[str, set[str]],
    expected_names: Mapping[str, set[str]],
    canonical_names: Sequence[str],
    aliases: Mapping[str, str],
    claude_root: Path | None,
    staged_skills: Path,
) -> int:
    """Commit validated staged entries, one rollback-safe destination at a time."""

    changed = 0
    for root in normalized_roots.values():
        root.mkdir(parents=True, exist_ok=True)
    for client, root in sorted(normalized_roots.items()):
        for name in canonical_names:
            destination = root / name
            if client == "codex":
                assert claude_root is not None
                target = (claude_root / name).absolute()
                if not destination.is_symlink() or destination.readlink() != target:
                    _commit_link(target, destination)
                    changed += 1
            elif not _same_tree(destination, staged_skills / name):
                _commit_copy(staged_skills / name, destination)
                changed += 1
        for alias, target_name in sorted(aliases.items()):
            destination = root / alias
            target = (
                (claude_root / target_name).absolute()  # type: ignore[operator]
                if client == "codex"
                else Path(target_name)
            )
            if not destination.is_symlink() or destination.readlink() != target:
                _commit_link(target, destination)
                changed += 1
        for name in sorted(prior_managed[client] - expected_names[client]):
            path = root / name
            if path.exists() or path.is_symlink():
                _remove_managed(path)
                changed += 1
        if _write_state(root, expected_names[client]):
            changed += 1
    return changed


def install(
    suite_root: Path,
    roots: Mapping[str, Path],
    *,
    dry_run: bool = False,
    include_portable: bool = True,
) -> dict[str, Any]:
    """Install deterministic client projections after validating every destination."""

    del include_portable  # Retained for API compatibility; portable clients are enabled by default.
    suite_root = suite_root.expanduser().resolve(strict=True)
    try:
        suite = load_suite(suite_root / "suite.toml")
    except SuiteValidationError as error:
        raise InstallValidationError(str(error)) from error
    canonical_names = [item["id"] for item in suite["skills"]]
    aliases = {item["id"]: item["target"] for item in suite["aliases"]}
    _validate_sources(suite_root, canonical_names)

    normalized_roots: dict[str, Path] = {}
    for client, root in roots.items():
        if client not in SUPPORTED_CLIENTS:
            raise InstallValidationError(f"unsupported projection client: {client}")
        requested = root.expanduser().absolute()
        _assert_safe_root(requested)
        normalized_roots[client] = requested
    root_items = sorted(normalized_roots.items())
    for index, (left_client, left) in enumerate(root_items):
        for right_client, right in root_items[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise InstallSafetyError(
                    f"projection roots overlap: {left_client}={left} and "
                    f"{right_client}={right}"
                )

    claude_root = normalized_roots.get("claude")
    if "codex" in normalized_roots and claude_root is None:
        raise InstallValidationError("codex projection requires a claude destination root")

    prior_managed: dict[str, set[str]] = {}
    expected_names: dict[str, set[str]] = {}
    for client, root in normalized_roots.items():
        prior_managed[client] = _read_state(root) if root.exists() else set()
        names = set(canonical_names)
        names.update(aliases)
        expected_names[client] = names
        for name in sorted(names | prior_managed[client]):
            expected_link: Path | None = None
            legacy_link: Path | None = None
            shared_roots: tuple[Path, ...] = ()
            if client != "codex" and name in aliases:
                expected_link = Path(aliases[name])
            elif client == "codex":
                assert claude_root is not None
                target_name = aliases.get(name, name)
                expected_link = (claude_root / target_name).absolute()
                if name in aliases:
                    legacy_link = (claude_root / name).absolute()
            if client != "codex":
                shared_roots = tuple(
                    other_root
                    for other_client, other_root in normalized_roots.items()
                    if other_client != client
                )
            _assert_safe_entry(
                root / name,
                expected_link,
                legacy_link,
                shared_roots,
            )
        state_path = root / STATE_FILE
        if state_path.is_symlink():
            raise InstallSafetyError(f"managed state is a symlink: {state_path}")

    staged_skills = Path(tempfile.mkdtemp(prefix="platforms-projections-"))
    try:
        for name in canonical_names:
            _copy_payload(suite_root / "skills" / name, staged_skills / name)
    except Exception:
        shutil.rmtree(staged_skills, ignore_errors=True)
        raise

    actions: list[str] = []
    removed: list[str] = []
    changed = 0
    for client, root in sorted(normalized_roots.items()):
        stale = sorted(prior_managed[client] - expected_names[client])
        for name in stale:
            path = root / name
            if path.exists() or path.is_symlink():
                actions.append(f"remove {path}")
                removed.append(str(path))
        for name in canonical_names:
            destination = root / name
            if client == "codex":
                assert claude_root is not None
                target = (claude_root / name).absolute()
                if not destination.is_symlink() or destination.readlink() != target:
                    actions.append(f"link {destination} -> {target}")
            elif not _same_tree(destination, staged_skills / name):
                actions.append(f"copy {name} -> {destination}")
        for alias, target_name in sorted(aliases.items()):
            destination = root / alias
            target = (
                (claude_root / target_name).absolute()  # type: ignore[operator]
                if client == "codex"
                else Path(target_name)
            )
            if not destination.is_symlink() or destination.readlink() != target:
                actions.append(f"link {destination} -> {target}")

    if not dry_run:
        try:
            changed = _apply_changes(
                normalized_roots,
                prior_managed,
                expected_names,
                canonical_names,
                aliases,
                claude_root,
                staged_skills,
            )
        finally:
            shutil.rmtree(staged_skills, ignore_errors=True)
    else:
        shutil.rmtree(staged_skills, ignore_errors=True)

    drift_roots: list[dict[str, Any]] = []
    if not dry_run:
        for client, root in sorted(normalized_roots.items()):
            report = compare_roots(
                suite_root / "skills",
                [root],
                canonical_names,
                aliases=aliases,
                stale_managed_names=sorted(
                    prior_managed[client] - expected_names[client]
                ),
            )
            drift_roots.extend(report["roots"])
    drift = {
        "canonical_root": str(suite_root / "skills"),
        "drift": any(
            any(
                item.get(key)
                for key in (
                    "missing",
                    "changed",
                    "extra",
                    "missing_aliases",
                    "changed_aliases",
                    "stale",
                )
            )
            for item in drift_roots
        ),
        "ignored_roots": [],
        "roots": drift_roots,
    }
    result = {
        "actions": actions,
        "alias_count": len(aliases),
        "canonical_count": len(canonical_names),
        "changed": changed,
        "dry_run": dry_run,
        "drift": drift,
        "removed": removed,
    }
    return result


def _parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Safely install canonical platform skills and legacy aliases."
    )
    parser.add_argument("--root", type=Path, default=repository_root)
    parser.add_argument("--dry-run", action="store_true")
    for client in SUPPORTED_CLIENTS:
        parser.add_argument(
            f"--{client}-root",
            type=Path,
            default=DEFAULT_ROOTS[client],
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run projection installation and emit a deterministic JSON report."""

    args = _parser().parse_args(argv)
    roots = {client: getattr(args, f"{client}_root") for client in SUPPORTED_CLIENTS}
    try:
        report = install(args.root, roots, dry_run=args.dry_run)
    except (InstallSafetyError, InstallValidationError, OSError) as error:
        print(json.dumps({"error": str(error), "status": "error"}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["drift"]["drift"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
