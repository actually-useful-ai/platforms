# File Purpose: Generate all client manifests and the integrity lock from suite.toml.
# Primary Functions/Classes: SuiteValidationError, load_suite, build_outputs, generate, and main.
# Inputs/Outputs: Reads canonical TOML metadata; writes stable JSON or reports drift in check mode.

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse


GENERATED_MANIFESTS = (
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/marketplace.json",
    ".cursor-plugin/plugin.json",
)
LOCK_PATH = "dist/manifest.lock.json"
SUPPORTED_CLIENTS = ("agents", "claude", "codex", "cursor")
_COMPONENT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class SuiteValidationError(ValueError):
    """Raised when suite.toml does not satisfy the canonical suite model."""


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
        "skills": _component_ids(raw.get("skills"), "skills"),
        "agents": _component_ids(raw.get("agents"), "agents", require_read_only=True),
    }


def _plugin_manifest(suite_data: dict[str, Any], client: str) -> dict[str, Any]:
    suite = suite_data["suite"]
    return {
        "agents": [
            {"name": agent["id"], "read_only": agent["read_only"]}
            for agent in suite_data["agents"]
        ],
        "author": {"name": suite["author"]},
        "client": client,
        "description": suite["description"],
        "license": suite["license"],
        "name": suite["id"],
        "repository": suite["repository"],
        "skills": [
            {"name": skill["id"], "path": f"skills/{skill['id']}"}
            for skill in suite_data["skills"]
        ],
        "version": suite["version"],
    }


def _marketplace_manifest(suite_data: dict[str, Any], client: str) -> dict[str, Any]:
    suite = suite_data["suite"]
    return {
        "client": client,
        "name": f"{suite['id']}-marketplace",
        "owner": {"name": suite["author"]},
        "plugins": [
            {
                "agents": [agent["id"] for agent in suite_data["agents"]],
                "description": suite["description"],
                "license": suite["license"],
                "name": suite["id"],
                "repository": suite["repository"],
                "skills": [skill["id"] for skill in suite_data["skills"]],
                "source": "./",
                "version": suite["version"],
            }
        ],
    }


def build_outputs(root: Path) -> dict[str, bytes]:
    """Build expected generated bytes entirely in memory."""

    suite_path = root / "suite.toml"
    suite_data = load_suite(suite_path)
    outputs = {
        ".agents/plugins/marketplace.json": _stable_json(
            _marketplace_manifest(suite_data, "agents")
        ),
        ".claude-plugin/marketplace.json": _stable_json(
            _marketplace_manifest(suite_data, "claude")
        ),
        ".claude-plugin/plugin.json": _stable_json(
            _plugin_manifest(suite_data, "claude")
        ),
        ".codex-plugin/plugin.json": _stable_json(_plugin_manifest(suite_data, "codex")),
        ".cursor-plugin/marketplace.json": _stable_json(
            _marketplace_manifest(suite_data, "cursor")
        ),
        ".cursor-plugin/plugin.json": _stable_json(
            _plugin_manifest(suite_data, "cursor")
        ),
    }
    lock_entries = [
        {
            "executable": False,
            "mode": "0644",
            "path": "suite.toml",
            "sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        }
    ]
    lock_entries.extend(
        {
            "executable": False,
            "mode": "0644",
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for path, payload in sorted(outputs.items())
    )
    outputs[LOCK_PATH] = _stable_json(
        {
            "files": sorted(lock_entries, key=lambda entry: entry["path"]),
            "suite_version": suite_data["suite"]["version"],
        }
    )
    return outputs


def find_drift(root: Path, outputs: dict[str, bytes]) -> list[str]:
    """Return normalized output paths whose committed bytes differ or are missing."""

    drift: list[str] = []
    for relative_path, expected in sorted(outputs.items()):
        target = root / relative_path
        try:
            actual = target.read_bytes()
        except OSError:
            drift.append(relative_path)
            continue
        if actual != expected:
            drift.append(relative_path)
    return drift


def generate(root: Path, *, check: bool = False) -> list[str]:
    """Generate files, or return drift without writes when check is true."""

    root = root.resolve()
    outputs = build_outputs(root)
    drift = find_drift(root, outputs)
    if check:
        return drift
    for relative_path, payload in sorted(outputs.items()):
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(0o644)
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
    except SuiteValidationError as error:
        print(f"invalid suite metadata: {error}", file=sys.stderr)
        return 2
    if args.check and drift:
        print("generated manifest drift:")
        for path in drift:
            print(path)
        return 1
    if args.check:
        print("generated manifests are current")
    else:
        print(f"generated {len(GENERATED_MANIFESTS) + 1} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
