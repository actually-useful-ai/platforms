# File Purpose: Check, before an fdroiddata request is filed or a build is added, that the Android
#   module the recipe builds turns on R8 for release and keeps the dependency-metadata block out of
#   the APK.
# Primary Functions/Classes: check(), read_build_file(), parse_blocks(), signing_block_ids(), main()
# Inputs/Outputs: takes a source checkout, the recipe's `subdir`, optionally the Gradle flavor the
#   recipe builds, a commit to read the build file from, and the signed reference APK. Prints one
#   PASS, FAIL or UNKNOWN line per check (or JSON with --json). Exit 0 when every check passes, 1
#   when any fails, 3 when none fails but at least one cannot be decided from the file.

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

DEPENDENCY_METADATA_BLOCK = 0x504B4453  # Google's encrypted dependency report, written by AGP
VERITY_PADDING_BLOCK = 0x42726577
APK_SIG_MAGIC = b"APK Sig Block 42"

WILDCARD = "*"
TRANSPARENT = re.compile(r"^(?:if\s*\(.*\)|else(?:\s+if\s*\(.*\))?|try|finally|run|with\s*\(.*\)|also|let)$", re.S)
NAMED_CALL = re.compile(r"""^(?:getByName|named|maybeCreate|create|register|getAt)\s*\(\s*["'](\w+)["']\s*\)(?:\.(?:apply|configure|run|also))?$""")
ALL_CALL = re.compile(r"^(?:all|configureEach|each|forEach|matching\s*\(.*\)|withType\s*\(.*\))$", re.S)


# --------------------------------------------------------------------------- reading the file

def read_build_file(checkout: Path, subdir: str, commit: str | None) -> tuple[str | None, str | None, str]:
    """Return (path relative to checkout, text, note). Text is None when the file cannot be read."""
    candidates = [f"{subdir.strip('/')}/build.gradle.kts", f"{subdir.strip('/')}/build.gradle"]
    found: list[tuple[str, str]] = []
    for relative in candidates:
        if commit:
            shown = subprocess.run(["git", "-C", str(checkout), "show", f"{commit}:{relative}"],
                                   capture_output=True, text=True)
            if shown.returncode == 0:
                found.append((relative, shown.stdout))
        elif (checkout / relative).is_file():
            found.append((relative, (checkout / relative).read_text(encoding="utf-8")))
    where = f"commit {commit}" if commit else "the working tree"
    if not found:
        return None, None, f"no build.gradle or build.gradle.kts in {subdir} at {where}"
    if len(found) > 1:
        return found[0][0], None, f"both build.gradle and build.gradle.kts are in {subdir}; check by hand which one Gradle uses"
    return found[0][0], found[0][1], ""


def _strip(text: str) -> tuple[str, str]:
    """Return (code, skeleton): comments blanked in both, string contents also blanked in skeleton.

    Both keep the original length and newlines, so offsets and line numbers line up with the file.
    """
    code, skeleton = list(text), list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end == -1 else end
            for j in range(i, end):
                code[j] = skeleton[j] = " "
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            for j in range(i, end):
                if text[j] != "\n":
                    code[j] = skeleton[j] = " "
            i = end
        elif text.startswith('"""', i) or text.startswith("'''", i):
            quote = text[i:i + 3]
            end = text.find(quote, i + 3)
            end = n if end == -1 else end + 3
            for j in range(i + 3, max(i + 3, end - 3)):
                if text[j] != "\n":
                    skeleton[j] = "x"
            i = end
        elif text[i] == "/" and text[:i].rstrip().endswith("~"):
            # Groovy slashy regex after =~ or ==~; braces inside it are not blocks
            j = i + 1
            while j < n and text[j] != "/" and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                skeleton[k] = "x"
            i = j + 1
        elif text[i] in "\"'":
            quote, j = text[i], i + 1
            while j < n and text[j] != quote and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                skeleton[k] = "x"
            i = j + 1
        else:
            i += 1
    return "".join(code), "".join(skeleton)


# --------------------------------------------------------------------------- block structure

def _segments(header: str) -> list[str] | None:
    """Turn a block header or dotted prefix into path segments; None means transparent."""
    header = " ".join(header.split())
    if not header or TRANSPARENT.match(header):
        return None
    parts: list[str] = []
    for piece in re.findall(r"""(?:\w+\s*\([^()]*\)|\w+)""", header):
        named = NAMED_CALL.match(piece)
        if named:
            parts.append(named.group(1))
        elif ALL_CALL.match(piece):
            parts.append(WILDCARD)
        elif piece in ("apply", "configure", "run", "also", "project"):
            continue
        elif "(" not in piece:
            parts.append(piece)
        else:
            parts.append(piece.split("(", 1)[0].strip())
    return parts


def parse_blocks(code: str, skeleton: str) -> list[dict]:
    """Return every brace block as {start, end, path}, path being the segments from the file root."""
    blocks: list[dict] = []
    stack: list[dict] = []
    for i, char in enumerate(skeleton):
        if char == "{":
            cut = max(skeleton.rfind(c, 0, i) for c in "\n{};")
            header = code[cut + 1:i].strip()
            if header.startswith(("->", "=")) or header.endswith(("->", "=")):
                header = ""
            if not header:  # a header on the previous line: `release\n{`
                prev_cut = max(skeleton.rfind(c, 0, max(cut, 0)) for c in "\n{};")
                if cut >= 0 and skeleton[cut] == "\n":
                    header = code[prev_cut + 1:cut].strip()
            own = _segments(header)
            parent = stack[-1]["path"] if stack else []
            block = {"start": i, "end": len(code), "path": parent + (own or []), "header": header}
            blocks.append(block)
            stack.append(block)
        elif char == "}" and stack:
            stack.pop()["end"] = i
    return blocks


def _path_at(blocks: list[dict], offset: int) -> list[str]:
    inner: dict | None = None
    for block in blocks:
        if block["start"] < offset < block["end"] and (inner is None or block["start"] > inner["start"]):
            inner = block
    return inner["path"] if inner else []


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _assignments(code: str, blocks: list[dict], names: tuple[str, ...]) -> list[dict]:
    """Find `name value`, `name = value` and `setName(value)` with the block path they sit in."""
    alternatives = "|".join(names)
    setter = "|".join("set" + name[2:] if name.startswith("is") else "set" + name[0].upper() + name[1:]
                      for name in names)
    pattern = re.compile(
        rf"""(?P<prefix>(?:(?:\w+\s*\([^()\n]*\)|\w+)\s*\.\s*)*)"""
        rf"""(?:\b(?P<name>{alternatives})\b[ \t]*(?:=[ \t]*)?(?P<value>[^\n;}})]*)"""
        rf"""|\b(?P<setter>{setter})\s*\(\s*(?P<arg>[^)\n]*)\))""")
    found = []
    for match in pattern.finditer(code):
        raw = (match.group("value") if match.group("name") else match.group("arg")) or ""
        raw = raw.strip()
        if not raw or raw.startswith(("=", "!=", "&&", "||", "?", ")")):
            continue  # a read, not an assignment
        prefix = match.group("prefix").rstrip(". \t")
        path = _path_at(blocks, match.start()) + (_segments(prefix) or [] if prefix else [])
        literal = {"true": True, "false": False}.get(raw)
        found.append({"path": path, "raw": raw, "value": literal, "line": _line(code, match.start()),
                      "name": match.group("name") or match.group("setter")})
    return found


def _after(path: list[str], key: str) -> str | None:
    """The segment that follows `key` in a path ('' when key ends it, None when absent)."""
    if key not in path:
        return None
    index = len(path) - 1 - path[::-1].index(key)
    return path[index + 1] if index + 1 < len(path) else ""


# --------------------------------------------------------------------------- the checks

def _result(check: str, status: str, reason: str) -> dict:
    return {"check": check, "status": status, "reason": reason}


def _check_r8(code: str, blocks: list[dict], flavor: str | None) -> dict:
    release, flavors, elsewhere = [], {}, []
    for item in _assignments(code, blocks, ("isMinifyEnabled", "minifyEnabled")):
        build_type = _after(item["path"], "buildTypes")
        product = _after(item["path"], "productFlavors")
        if product is not None:
            flavors.setdefault(product or "?", []).append(item)
        elif build_type in ("release", WILDCARD):
            release.append(item)
        elif build_type is None or build_type == "":
            elsewhere.append(item)
        # other named build types (debug, benchmark) do not affect release
    if elsewhere:
        lines = ", ".join(str(item["line"]) for item in elsewhere)
        return _result("r8", "unknown", f"minify is also set outside buildTypes.release (line {lines}); "
                                        "check by hand what the release build ends up with")
    chosen = None
    overriding = sorted(name for name in flavors if name != WILDCARD)
    if flavor:
        chosen = (flavors.get(flavor) or flavors.get(WILDCARD) or [None])[-1]
    elif overriding:
        return _result("r8", "unknown", f"flavor {', '.join(overriding)} sets minify; pass --flavor with "
                                        "the flavor the recipe builds")
    effective = chosen or (release[-1] if release else None)
    where = f"flavor {flavor}" if chosen else "buildTypes.release"
    if effective is None:
        return _result("r8", "fail", "the release build type never turns on minify, and it is off by default; "
                                     "set isMinifyEnabled = true (minifyEnabled true in Groovy)")
    shown = f"{effective['name']} {effective['raw']}" if effective["name"] == "minifyEnabled" else \
        f"{effective['name']} = {effective['raw']}"
    if effective["value"] is True:
        return _result("r8", "pass", f"{where} sets {shown} (line {effective['line']})")
    if effective["value"] is False:
        return _result("r8", "fail", f"{where} sets {shown} (line {effective['line']}); "
                                     "F-Droid reviewers ask for R8 on")
    return _result("r8", "unknown", f"{where} sets minify from `{effective['raw']}` (line {effective['line']}); "
                                    "can't tell its value from the file")


def _check_dependencies_info(code: str, blocks: list[dict]) -> tuple[dict, dict]:
    apk_items, bundle_items = [], []
    for item in _assignments(code, blocks, ("includeInApk", "includeInBundle")):
        if "dependenciesInfo" not in item["path"]:
            continue
        (apk_items if item["name"].endswith("Apk") else bundle_items).append(item)
    bundle = bundle_items[-1]["raw"] if bundle_items else None
    info = {"includeInApk": apk_items[-1]["raw"] if apk_items else None, "includeInBundle": bundle}
    if not apk_items:
        return _result("dependencies_info", "fail",
                       "no dependenciesInfo { includeInApk = false }, so an APK Gradle signs carries the "
                       "dependency-metadata block; add it, or pass --apk with the signed reference APK "
                       "if it is signed outside Gradle"), info
    last = apk_items[-1]
    if last["value"] is False:
        return _result("dependencies_info", "pass", f"dependenciesInfo sets includeInApk = false (line {last['line']})"), info
    if last["value"] is True:
        return _result("dependencies_info", "fail", f"dependenciesInfo sets includeInApk = true (line {last['line']}); "
                                                    "set it to false"), info
    return _result("dependencies_info", "unknown", f"includeInApk is set from `{last['raw']}` (line {last['line']}); "
                                                   "can't tell its value from the file"), info


def signing_block_ids(apk: Path) -> list[int] | None:
    """Return the IDs in the APK Signing Block, [] when there is none, None when unreadable."""
    try:
        data = Path(apk).read_bytes()
        zipfile.ZipFile(apk).close()
    except (OSError, zipfile.BadZipFile):
        return None
    eocd = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if eocd < 0:
        return None
    cd_offset = struct.unpack_from("<I", data, eocd + 16)[0]
    if cd_offset < 24 or data[cd_offset - 16:cd_offset] != APK_SIG_MAGIC:
        return []
    size = struct.unpack_from("<Q", data, cd_offset - 24)[0]
    start = cd_offset - size - 8
    if start < 0 or struct.unpack_from("<Q", data, start)[0] != size:
        return None
    ids, position, end = [], start + 8, cd_offset - 24
    while position + 12 <= end:
        length, ident = struct.unpack_from("<QI", data, position)
        ids.append(ident)
        position += 8 + length
    return ids


def _check_apk(apk: Path) -> dict:
    ids = signing_block_ids(apk)
    if ids is None:
        return _result("dependencies_info", "unknown", f"{apk} is not a readable APK")
    if DEPENDENCY_METADATA_BLOCK in ids:
        return _result("dependencies_info", "fail", f"{Path(apk).name} carries the dependency-metadata block "
                                                    "(0x504b4453) in its signing block; set "
                                                    "dependenciesInfo { includeInApk = false } and re-sign")
    if not ids:
        return _result("dependencies_info", "pass", f"{Path(apk).name} has no APK Signing Block, so no "
                                                    "dependency-metadata block")
    return _result("dependencies_info", "pass", f"{Path(apk).name} has no dependency-metadata block in its signing block")


def check(checkout: Path, subdir: str, flavor: str | None = None, commit: str | None = None,
          apk: Path | None = None) -> dict:
    """Run every check and return {result, checks, build_file, commit, ...}."""
    checkout = Path(checkout)
    relative, text, note = read_build_file(checkout, subdir, commit)
    report: dict = {"checkout": str(checkout), "build_file": relative, "flavor": flavor,
                    "commit": commit or _head(checkout), "read_from": "commit" if commit else "working tree"}
    if not commit:
        report["uncommitted_changes"] = _dirty(checkout, relative)
    if text is None:
        report["checks"] = [_result("r8", "unknown", note), _result("dependencies_info", "unknown", note)]
    else:
        code, skeleton = _strip(text)
        blocks = parse_blocks(code, skeleton)
        source_dependencies, info = _check_dependencies_info(code, blocks)
        report["dependencies_info"] = info
        dependencies = source_dependencies
        if apk is not None:
            dependencies = _check_apk(apk)
            if source_dependencies["status"] != "pass" and dependencies["status"] == "pass":
                dependencies["reason"] += ("; the build file does not turn it off, so keep signing "
                                           "this module outside Gradle")
        report["checks"] = [_check_r8(code, blocks, flavor), dependencies]
    statuses = {item["status"] for item in report["checks"]}
    report["result"] = "fail" if "fail" in statuses else "unknown" if "unknown" in statuses else "pass"
    return report


def _git(checkout: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, text=True)
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _head(checkout: Path) -> str | None:
    return _git(checkout, "rev-parse", "HEAD")


def _dirty(checkout: Path, relative: str | None) -> bool | None:
    if relative is None or _head(checkout) is None:
        return None
    return bool(_git(checkout, "status", "--porcelain", "--", relative))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="source checkout of the app")
    parser.add_argument("--subdir", required=True, help="the recipe's subdir, e.g. android/app")
    parser.add_argument("--flavor", help="the Gradle flavor the recipe builds (its gradle: line)")
    parser.add_argument("--commit", help="read the build file at this commit (the recipe's commit:) "
                                         "instead of the working tree")
    parser.add_argument("--apk", type=Path, help="the signed reference APK; decides the dependency-block check")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args(argv)
    report = check(args.checkout, args.subdir, args.flavor, args.commit, args.apk)
    if args.json:
        json.dump(report, sys.stdout, indent=1)
        print()
    else:
        where = f"{report['build_file'] or args.subdir} at {report['commit'] or 'an unversioned tree'}"
        if report.get("uncommitted_changes"):
            where += " (with uncommitted changes; pass --commit to check the tagged file)"
        print(f"release_check: {where}")
        for item in report["checks"]:
            print(f"{item['status'].upper():<7} {item['check']}: {item['reason']}")
    return {"pass": 0, "fail": 1}.get(report["result"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
