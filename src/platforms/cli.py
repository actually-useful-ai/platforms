# File Purpose: Command-line interface for platform detect/plan/doctor/build/validate/package/report/drift.
# Primary Functions/Classes: build_parser, main, command handlers.
# Inputs/Outputs: argv in; JSON or text on stdout; process exit code out.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from platforms.adapters.registry import get_adapter, list_adapters
from platforms.models import ArtifactBundle, Plan
from platforms.paths import ProjectPathError, resolve_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="platforms",
        description="Deterministic platform delivery and publishing workflows.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="Detect likely platform targets for a project")
    _add_project_args(detect)
    detect.add_argument("--json", action="store_true", help="Emit JSON")

    for name, help_text in (
        ("plan", "Create a scaffolded delivery plan"),
        ("doctor", "Diagnose toolchain readiness"),
        ("build", "Build platform artifacts"),
        ("validate", "Validate built artifacts"),
        ("package", "Stage store package and checklist"),
        ("report", "Emit an evidence report"),
    ):
        command = sub.add_parser(name, help=help_text)
        _add_project_args(command)
        command.add_argument("--platform", required=True, help="Platform adapter id")
        command.add_argument("--json", action="store_true", help="Emit JSON")

    drift = sub.add_parser("drift", help="Compare canonical skills with installed projections")
    drift.add_argument("roots", nargs="*", help="Optional installed skill roots")
    drift.add_argument("--help-text", action="store_true", help=argparse.SUPPRESS)

    return parser


def _add_project_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project",
        default=".",
        help="Project root (must exist; '..' segments rejected)",
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["drift", "--help"] or argv == ["drift", "-h"]:
        print("usage: platforms drift [installed-root ...]")
        print("Compare canonical skills/ with optional installed projection roots.")
        print("Delegates to tools/check_drift.py semantics; never edits installed files.")
        return 0

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "detect": _cmd_detect,
        "plan": _cmd_plan,
        "doctor": _cmd_doctor,
        "build": _cmd_build,
        "validate": _cmd_validate,
        "package": _cmd_package,
        "report": _cmd_report,
        "drift": _cmd_drift,
    }
    try:
        return handlers[args.command](args)
    except ProjectPathError as exc:
        print(f"project path error: {exc}", file=sys.stderr)
        return 2
    except KeyError as exc:
        print(f"unknown platform: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected failures
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_detect(args: argparse.Namespace) -> int:
    project = resolve_project(args.project)
    detections = [adapter.detect(project).to_dict() for adapter in list_adapters()]
    payload = {"project": str(project), "detections": detections}
    _emit(payload, as_json=args.json, text=_format_detections(detections))
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    _emit(plan.to_dict(), as_json=args.json, text=json.dumps(plan.to_dict(), indent=2))
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    report = adapter.doctor(project, plan)
    payload = report.to_dict()
    payload["platform_id"] = adapter.id
    _emit(payload, as_json=args.json, text=json.dumps(payload, indent=2))
    return 0 if report.ready else 1


def _cmd_build(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    bundle = adapter.build(project, plan)
    _emit(bundle.to_dict(), as_json=args.json, text=json.dumps(bundle.to_dict(), indent=2))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    built = adapter.build(project, plan)
    validated = adapter.validate(project, built)
    _emit(validated.to_dict(), as_json=args.json, text=json.dumps(validated.to_dict(), indent=2))
    return 0 if validated.track_state.value == "validated" else 1


def _cmd_package(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    built = adapter.build(project, plan)
    validated = adapter.validate(project, built)
    packaged = adapter.package(project, validated)
    _emit(packaged.to_dict(), as_json=args.json, text=json.dumps(packaged.to_dict(), indent=2))
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    project, adapter, detection = _load(args)
    plan = adapter.plan(project, detection)
    built = adapter.build(project, plan)
    validated = adapter.validate(project, built)
    packaged = adapter.package(project, validated)
    report = adapter.report(project, packaged)
    payload = report.to_dict()
    _emit(payload, as_json=args.json, text=json.dumps(payload, indent=2))
    return 0


def _cmd_drift(args: argparse.Namespace) -> int:
    # Import lazily so the CLI package remains usable without tools/ on PYTHONPATH
    # when only adapter commands are needed.
    repo_root = Path(__file__).resolve().parents[2]
    tools_dir = repo_root / "tools"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from tools import check_drift

    return int(check_drift.main([*(args.roots or [])]))


def _load(args: argparse.Namespace):
    project = resolve_project(args.project)
    adapter = get_adapter(args.platform)
    detection = adapter.detect(project)
    return project, adapter, detection


def _emit(payload: dict[str, Any], *, as_json: bool, text: str) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(text)


def _format_detections(detections: list[dict[str, Any]]) -> str:
    lines = []
    for item in detections:
        mark = "yes" if item["matched"] else "no"
        lines.append(
            f"{item['platform_id']}: matched={mark} confidence={item['confidence']:.2f}"
        )
    return "\n".join(lines)


# Silence unused-import lint for type checkers referencing models in annotations.
_ = (ArtifactBundle, Plan)
