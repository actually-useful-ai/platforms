# File Purpose: Show which folders F-Droid reads listing text from in an app's source checkout, in read order.
# Primary Functions/Classes: scan(), fdroidserver_scan(), main()
# Inputs/Outputs: takes a source checkout path, the recipe's last build `subdir`, and optionally the
#   application ID; prints JSON with the folders fdroidserver walks (the last one read wins) and flags
#   any root `metadata/<locale>` folder. With --fdroidserver and an importable fdroidserver, also runs
#   its own insert_localized_app_metadata() and prints the summary and description it would publish.

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from pathlib import Path

# Same globs, same order (sorted, last read wins) as fdroidserver.update.insert_localized_app_metadata
# at fdroidserver master fc2c8647 (checked 2026-11-24). Re-check if fdroidserver changes that function.
PATTERNS = (
    ("src", "[A-Za-z]*", "fastlane", "metadata", "android", "[a-z][a-z]*"),
    ("**", "fastlane", "metadata", "android", "[a-z][a-z]*"),
    ("metadata", "[a-z][a-z]*"),
)


def scan(checkout: Path, subdir: str | None = None, app_id: str = "app.id") -> dict:
    """List listing-text folders the way fdroidserver orders them, without fdroidserver installed."""
    checkout = Path(checkout).resolve()
    with tempfile.TemporaryDirectory() as temporary:
        build = Path(temporary) / "build"
        build.mkdir()
        (build / app_id).symlink_to(checkout, target_is_directory=True)
        cwd = os.getcwd()
        os.chdir(temporary)
        try:
            found: list[str] = []
            for parts in PATTERNS:
                found += glob.glob(os.path.join("build", app_id, *parts), recursive=True)
        finally:
            os.chdir(cwd)
    prefix = os.path.join("build", app_id) + os.sep
    entries = []
    for path in sorted(set(found)):
        relative = path[len(prefix):]
        if not (checkout / relative).is_dir():
            continue
        kind = "root_metadata" if relative.split(os.sep)[0] == "metadata" else "fastlane"
        entries.append({"relative": relative.replace(os.sep, "/"), "kind": kind})
    root = [e["relative"] for e in entries if e["kind"] == "root_metadata"]
    fastlane = [e["relative"] for e in entries if e["kind"] == "fastlane"]
    expected = f"{subdir}/fastlane/metadata/android" if subdir else None
    return {
        "checkout": str(checkout),
        "read_order": entries,
        "last_read_wins": True,
        "root_metadata": root,
        "fastlane": fastlane,
        "subdir_fastlane_present": bool(expected and any(f.startswith(expected) for f in fastlane)),
        "conflict": bool(root and fastlane),
    }


def fdroidserver_scan(checkout: Path, app_id: str, subdir: str | None, current_code: int = 0) -> dict:
    """Run fdroidserver's own scan on a temporary workspace and return what it would publish."""
    from fdroidserver import common, metadata, update  # imported late: optional dependency

    checkout = Path(checkout).resolve()
    with tempfile.TemporaryDirectory() as temporary:
        (Path(temporary) / "build").mkdir()
        (Path(temporary) / "build" / app_id).symlink_to(checkout, target_is_directory=True)
        cwd = os.getcwd()
        os.chdir(temporary)
        try:
            update.config = common.read_config()
            app = metadata.App()
            app.id = app_id
            app["CurrentVersionCode"] = current_code
            build = metadata.Build()
            build.subdir = subdir
            build.versionCode = current_code
            app["Builds"] = [build]
            update.insert_localized_app_metadata({app_id: app})
        finally:
            os.chdir(cwd)
    localized = app.get("localized", {})
    out = {}
    for locale, fields in sorted(localized.items()):
        out[locale] = {key: (str(value)[:160] + ("…" if len(str(value)) > 160 else ""))
                       for key, value in fields.items() if key in ("name", "summary", "description", "whatsNew")}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="source checkout at the commit the recipe builds")
    parser.add_argument("--subdir", help="the last build's subdir from the recipe, e.g. android/app")
    parser.add_argument("--app-id", default="app.id", help="application ID (needed with --fdroidserver)")
    parser.add_argument("--version-code", type=int, default=0, help="current version code (picks the changelog)")
    parser.add_argument("--fdroidserver", action="store_true", help="also run fdroidserver's own scan")
    args = parser.parse_args(argv)
    report = scan(args.checkout, args.subdir, args.app_id)
    if args.fdroidserver:
        try:
            report["fdroidserver_result"] = fdroidserver_scan(args.checkout, args.app_id, args.subdir, args.version_code)
        except ImportError:
            report["fdroidserver_result"] = "fdroidserver is not importable; run inside its virtualenv"
    json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 1 if report["conflict"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
