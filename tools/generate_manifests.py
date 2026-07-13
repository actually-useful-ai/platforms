# File Purpose: Generate all client manifests and the integrity lock from suite.toml.
# Primary Functions/Classes: SuiteValidationError, load_suite, build_outputs, generate, and main.
# Inputs/Outputs: Reads canonical TOML metadata; writes stable JSON or reports drift in check mode.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any, Sequence
from urllib.parse import urlparse


CLIENT_MANIFESTS = {
    "agents": (".agents/plugins/marketplace.json",),
    "claude": (
        ".claude-plugin/marketplace.json",
        ".claude-plugin/plugin.json",
    ),
    "codex": (".codex-plugin/plugin.json",),
    "cursor": (
        ".cursor-plugin/marketplace.json",
        ".cursor-plugin/plugin.json",
    ),
}
GENERATED_MANIFESTS = tuple(
    sorted(path for paths in CLIENT_MANIFESTS.values() for path in paths)
)
LOCK_PATH = "dist/manifest.lock.json"
SUPPORTED_CLIENTS = ("agents", "claude", "codex", "cursor")
GENERATED_MODE = 0o644
_COMPONENT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class SuiteValidationError(ValueError):
    """Raised when suite.toml does not satisfy the canonical suite model."""


class GenerationSafetyError(RuntimeError):
    """Raised when an output path could escape or traverse a symlink."""


def _stable_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _require_text(table: dict[str, Any], key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SuiteValidationError(f"suite.{key} must be a non-empty string")
    return value


def _component_ids(
    raw_components: Any,
    component_type: str,
    *,
    require_read_only: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(raw_components, list) or not raw_components:
        raise SuiteValidationError(f"{component_type} must contain at least one component")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, component in enumerate(raw_components):
        if not isinstance(component, dict):
            raise SuiteValidationError(f"{component_type}[{index}] must be a table")
        component_id = component.get("id")
        if not isinstance(component_id, str) or not _COMPONENT_ID.fullmatch(component_id):
            raise SuiteValidationError(
                f"{component_type}[{index}].id must be a lowercase kebab-case identifier"
            )
        if component_id in seen:
            raise SuiteValidationError(f"duplicate {component_type} id: {component_id}")
        if require_read_only and component.get("read_only") is not True:
            raise SuiteValidationError(f"agent {component_id} must set read_only = true")
        seen.add(component_id)
        normalized_component: dict[str, Any] = {"id": component_id}
        if require_read_only:
            normalized_component["read_only"] = True
        normalized.append(normalized_component)
    return normalized


def _aliases(
    raw_aliases: Any,
    canonical_ids: set[str],
) -> list[dict[str, str]]:
    """Validate aliases as direct, unique links to canonical skill ids."""

    if raw_aliases is None:
        return []
    if not isinstance(raw_aliases, list):
        raise SuiteValidationError("aliases must be an array of tables")

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, alias in enumerate(raw_aliases):
        if not isinstance(alias, dict):
            raise SuiteValidationError(f"aliases[{index}] must be a table")
        alias_id = alias.get("id")
        target = alias.get("target")
        if not isinstance(alias_id, str) or not _COMPONENT_ID.fullmatch(alias_id):
            raise SuiteValidationError(
                f"aliases[{index}].id must be a lowercase kebab-case identifier"
            )
        if alias_id in seen:
            raise SuiteValidationError(f"duplicate alias id: {alias_id}")
        if alias_id in canonical_ids:
            raise SuiteValidationError(f"alias collides with canonical skill: {alias_id}")
        if not isinstance(target, str) or not _COMPONENT_ID.fullmatch(target):
            raise SuiteValidationError(
                f"aliases[{index}].target must be a lowercase kebab-case identifier"
            )
        if target not in canonical_ids:
            raise SuiteValidationError(
                f"alias {alias_id} target must be canonical: {target}"
            )
        seen.add(alias_id)
        normalized.append({"id": alias_id, "target": target})
    return sorted(normalized, key=lambda item: item["id"])


def load_suite(path: Path) -> dict[str, Any]:
    """Load and validate canonical suite metadata without changing the filesystem."""

    try:
        with path.open("rb") as suite_file:
            raw = tomllib.load(suite_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SuiteValidationError(f"cannot read {path}: {error}") from error

    if raw.get("schema_version") != 1:
        raise SuiteValidationError("schema_version must be 1")
    suite = raw.get("suite")
    clients = raw.get("clients")
    if not isinstance(suite, dict):
        raise SuiteValidationError("[suite] is required")
    if not isinstance(clients, dict):
        raise SuiteValidationError("[clients] is required")

    suite_id = _require_text(suite, "id")
    if not _COMPONENT_ID.fullmatch(suite_id):
        raise SuiteValidationError("suite.id must be a lowercase kebab-case identifier")
    version = _require_text(suite, "version")
    if not _SEMVER.fullmatch(version):
        raise SuiteValidationError("suite.version must use MAJOR.MINOR.PATCH")
    repository = _require_text(suite, "repository")
    parsed_repository = urlparse(repository)
    if parsed_repository.scheme != "https" or not parsed_repository.netloc:
        raise SuiteValidationError("suite.repository must be an absolute HTTPS URL")
    license_name = _require_text(suite, "license")
    if license_name != "MIT":
        raise SuiteValidationError("suite.license must be MIT")

    supported = clients.get("supported")
    if not isinstance(supported, list) or not supported:
        raise SuiteValidationError("clients.supported must be a non-empty array")
    if any(not isinstance(client, str) for client in supported):
        raise SuiteValidationError("clients.supported entries must be strings")
    if len(supported) != len(set(supported)):
        raise SuiteValidationError("clients.supported entries must be unique")
    unknown_clients = sorted(set(supported) - set(SUPPORTED_CLIENTS))
    if unknown_clients:
        raise SuiteValidationError(f"unsupported clients: {', '.join(unknown_clients)}")

    skills = _component_ids(raw.get("skills"), "skills")
    aliases = _aliases(raw.get("aliases"), {skill["id"] for skill in skills})
    return {
        "schema_version": 1,
        "suite": {
            "id": suite_id,
            "name": _require_text(suite, "name"),
            "description": _require_text(suite, "description"),
            "version": version,
            "author": _require_text(suite, "author"),
            "repository": repository,
            "license": license_name,
        },
        "clients": {"supported": sorted(supported)},
        "skills": skills,
        "aliases": aliases,
        "agents": _component_ids(raw.get("agents"), "agents", require_read_only=True),
    }


def _base_plugin_manifest(suite_data: dict[str, Any]) -> dict[str, Any]:
    suite = suite_data["suite"]
    return {
        "author": {"name": suite["author"]},
        "description": suite["description"],
        "homepage": suite["repository"],
        "license": suite["license"],
        "name": suite["id"],
        "repository": suite["repository"],
        "version": suite["version"],
    }


def _plugin_manifest(suite_data: dict[str, Any], client: str) -> dict[str, Any]:
    manifest = _base_plugin_manifest(suite_data)
    if client == "cursor":
        manifest["displayName"] = suite_data["suite"]["name"]
        manifest["skills"] = "./skills/"
    elif client == "codex":
        manifest["skills"] = "./skills/"
    return manifest


def _standard_marketplace_manifest(suite_data: dict[str, Any]) -> dict[str, Any]:
    suite = suite_data["suite"]
    return {
        "description": suite["description"],
        "name": suite["id"],
        "owner": {"name": suite["author"]},
        "plugins": [
            {
                "author": {"name": suite["author"]},
                "description": suite["description"],
                "name": suite["id"],
                "source": "./",
                "version": suite["version"],
            }
        ],
    }


def _agents_marketplace_manifest(suite_data: dict[str, Any]) -> dict[str, Any]:
    suite = suite_data["suite"]
    return {
        "interface": {"displayName": suite["name"]},
        "name": suite["id"],
        "plugins": [
            {
                "category": "Developer Tools",
                "name": suite["id"],
                "policy": {
                    "authentication": "ON_INSTALL",
                    "installation": "AVAILABLE",
                },
                "source": {"source": "url", "url": "./"},
            }
        ],
    }


def build_outputs(root: Path) -> dict[str, bytes]:
    """Build expected generated bytes entirely in memory."""

    suite_path = root / "suite.toml"
    suite_data = load_suite(suite_path)
    supported = set(suite_data["clients"]["supported"])
    outputs: dict[str, bytes] = {}
    if "agents" in supported:
        outputs[".agents/plugins/marketplace.json"] = _stable_json(
            _agents_marketplace_manifest(suite_data)
        )
    if "claude" in supported:
        outputs[".claude-plugin/marketplace.json"] = _stable_json(
            _standard_marketplace_manifest(suite_data)
        )
        outputs[".claude-plugin/plugin.json"] = _stable_json(
            _plugin_manifest(suite_data, "claude")
        )
    if "codex" in supported:
        outputs[".codex-plugin/plugin.json"] = _stable_json(
            _plugin_manifest(suite_data, "codex")
        )
    if "cursor" in supported:
        outputs[".cursor-plugin/marketplace.json"] = _stable_json(
            _standard_marketplace_manifest(suite_data)
        )
        outputs[".cursor-plugin/plugin.json"] = _stable_json(
            _plugin_manifest(suite_data, "cursor")
        )
    lock_entries = [
        {
            "executable": False,
            "mode": f"{GENERATED_MODE:04o}",
            "path": "suite.toml",
            "sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        }
    ]
    lock_entries.extend(
        {
            "executable": False,
            "mode": f"{GENERATED_MODE:04o}",
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for path, payload in sorted(outputs.items())
    )
    outputs[LOCK_PATH] = _stable_json(
        {
            "files": sorted(lock_entries, key=lambda entry: entry["path"]),
            "inventory": {
                "agents": [agent["id"] for agent in suite_data["agents"]],
                "aliases": suite_data["aliases"],
                "skills": [skill["id"] for skill in suite_data["skills"]],
            },
            "supported_clients": suite_data["clients"]["supported"],
            "suite_version": suite_data["suite"]["version"],
        }
    )
    return outputs


def find_drift(root: Path, outputs: dict[str, bytes]) -> list[str]:
    """Return output paths whose bytes, type, symlink status, or mode drift."""

    drift: list[str] = []
    for relative_path, expected in sorted(outputs.items()):
        target = root / relative_path
        try:
            metadata = target.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                drift.append(relative_path)
                continue
            actual = target.read_bytes()
        except OSError:
            drift.append(relative_path)
            continue
        if actual != expected or stat.S_IMODE(metadata.st_mode) != GENERATED_MODE:
            drift.append(relative_path)
    for relative_path in sorted(set(GENERATED_MANIFESTS) - set(outputs)):
        try:
            (root / relative_path).lstat()
        except OSError:
            continue
        drift.append(relative_path)
    return drift


def _safe_target(root: Path, relative_path: str) -> Path:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise GenerationSafetyError(f"generated path escapes repository: {relative_path}")
    target = root.joinpath(*path.parts)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise GenerationSafetyError(
            f"generated path escapes repository: {relative_path}"
        ) from error

    current = root
    for part in path.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise GenerationSafetyError(
                f"generated parent is a symlink: {current.relative_to(root).as_posix()}"
            )
        if current.exists() and not current.is_dir():
            raise GenerationSafetyError(
                f"generated parent is not a directory: "
                f"{current.relative_to(root).as_posix()}"
            )
    if target.is_symlink():
        raise GenerationSafetyError(f"generated output is a symlink: {relative_path}")
    if target.exists() and not target.is_file():
        raise GenerationSafetyError(
            f"generated output is not a regular file: {relative_path}"
        )
    return target


def _create_safe_parents(root: Path, target: Path) -> None:
    current = root
    for part in target.relative_to(root).parts[:-1]:
        current /= part
        if current.is_symlink():
            raise GenerationSafetyError(
                f"generated parent is a symlink: {current.relative_to(root).as_posix()}"
            )
        current.mkdir(exist_ok=True)
        if current.is_symlink() or not current.is_dir():
            raise GenerationSafetyError(
                f"generated parent is unsafe: {current.relative_to(root).as_posix()}"
            )


def _atomic_write(root: Path, relative_path: str, payload: bytes) -> None:
    target = _safe_target(root, relative_path)
    _create_safe_parents(root, target)
    target = _safe_target(root, relative_path)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, GENERATED_MODE, follow_symlinks=False)
        _safe_target(root, relative_path)
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _transactional_write(
    root: Path,
    outputs: dict[str, bytes],
    stale_outputs: Sequence[str],
) -> None:
    """Stage the complete set and roll back file replacements on commit failure.

    File contents are transactionally restored within one filesystem. Directory
    creation and durability across power loss remain filesystem-level limits.
    """

    stage_root = Path(tempfile.mkdtemp(prefix=".manifest-stage-", dir=root))
    staged_root = stage_root / "new"
    backup_root = stage_root / "backup"
    operations = sorted(set(outputs) | set(stale_outputs))
    processed: list[dict[str, Any]] = []
    try:
        for relative_path, payload in sorted(outputs.items()):
            staged = staged_root / relative_path
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(payload)
            staged.chmod(GENERATED_MODE)

        for relative_path in operations:
            target = _safe_target(root, relative_path)
            _create_safe_parents(root, target)
            backup = backup_root / relative_path
            record = {
                "backed_up": False,
                "installed": False,
                "path": relative_path,
            }
            processed.append(record)
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
                record["backed_up"] = True
            if relative_path in outputs:
                staged = staged_root / relative_path
                os.replace(staged, target)
                record["installed"] = True
    except Exception:
        for record in reversed(processed):
            relative_path = str(record["path"])
            target = root / relative_path
            backup = backup_root / relative_path
            if record["installed"] and target.exists() and not target.is_symlink():
                target.unlink()
            if record["backed_up"] and backup.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def generate(root: Path, *, check: bool = False) -> list[str]:
    """Generate files, or return drift without writes when check is true."""

    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise GenerationSafetyError(f"suite root is not a directory: {root}")
    outputs = build_outputs(root)
    drift = find_drift(root, outputs)
    if check:
        return drift
    stale_outputs = sorted(set(GENERATED_MANIFESTS) - set(outputs))
    for relative_path in sorted((*outputs, *stale_outputs)):
        _safe_target(root, relative_path)
    _transactional_write(root, outputs, stale_outputs)
    return find_drift(root, outputs)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic client manifests from suite.toml."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="suite repository root (defaults to this checkout)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing and exit nonzero when drift exists",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run manifest generation and return a process-compatible exit code."""

    args = _parser().parse_args(argv)
    try:
        drift = generate(args.root, check=args.check)
    except (GenerationSafetyError, SuiteValidationError) as error:
        print(f"cannot generate manifests: {error}", file=sys.stderr)
        return 2
    if args.check and drift:
        print("generated manifest drift:")
        for path in drift:
            print(path)
        return 1
    if args.check:
        print("generated manifests are current")
    else:
        print(f"generated {len(build_outputs(args.root))} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
