# File Purpose: Measure merged and closed F-Droid "New App" requests downloaded by collect.py.
# Primary Functions/Classes: description_stats(), recipe_facts(), recipe_changes(),
#   classify_note(), analyze_merged(), analyze_closed(), main()
# Inputs/Outputs: reads $FDROID_STUDY_DATA/merged/*.json and closed/*.json (default
#   ./fdroid-study/data); writes merged.csv, closed.csv, notes.csv and summary.json to
#   $FDROID_STUDY_OUT (default ./fdroid-study/out).
#   Needs PyYAML. Every count in the evidence document comes from summary.json.

import csv
import glob
import json
import os
import re
import statistics
import sys
from datetime import datetime

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("FDROID_STUDY_DATA", os.path.join(os.getcwd(), "fdroid-study", "data"))
OUT = os.environ.get("FDROID_STUDY_OUT", os.path.join(os.getcwd(), "fdroid-study", "out"))

TEMPLATE_LINES = {
    "## abstract for new app inclusion",
    "### please introduce the functions and usage of your app in summary, and also attach some screenshots.",
    "### please elaborate why you wrote this app. please highlight the unique functions it provides over other similar apps in f-droid.",
}

DISCLOSURE = {
    "network": r"\b(internet|network|offline|online|server|api|connect\w*|traffic|fetch\w*|download\w*)\b",
    "permissions": r"\bpermissions?\b",
    "no_tracking": r"\b(no (ads|tracking|analytics|telemetry)|analytics|telemetry|tracker|tracking)\b",
    "anti_feature": r"anti-?features?|\bnonfree\b|non-free",
    "reproducible": r"reproducib",
    "r8": r"\bR8\b|minif|proguard",
    "license_note": r"\blicen[cs]e",
    "quality6": r"quality point 6|three months|3 months|three-month",
    "compares_fdroid_app": r"(similar|alternative|unlike|compared|other) [^.\n]{0,60}(apps?|f-droid)|\bf-droid\b[^.\n]{0,40}(similar|alternative|other)",
    "ai_tools": r"\b(LLM|AI|Claude|ChatGPT|Copilot|Codex|Gemini|vibe[- ]cod\w*)\b",
}

NOTE_KINDS = [
    ("pipeline_or_build_failure", r"fix (the )?pipeline|pipeline (fail|is fail|still fail)|job (fail|is fail)|build (fail|error)|fails? to build|failed"),
    ("template_not_followed", r"template is not followed|follow the (mr |merge request )?template|no (app )?inclusion template|choose the app inclusion template|half app inclusion template"),
    ("code_suggestion", r"```suggestion"),
    ("similar_apps_unique_value", r"many simil|unique (functions|value|features)|already have|diff(erence)? over other apps|minor rebrand"),
    ("jdk_version", r"\bjdk\b|java ?\d\d"),
    ("command_list_style", r"connect the commands|list of strings"),
    ("subdir_output", r"\bsubdir\b|remove the output|\boutput\b"),
    ("auto_update", r"auto ?-?update|updatecheckmode|autoupdatemode|checkupdates|updatecheckdata"),
    ("tags_releases", r"\btags?\b|\btagged\b|github release"),
    ("r8_minify", r"\bR8\b|minify|proguard|shrink"),
    ("dependencies_info", r"dependenciesinfo|dependency ?info|dependencyinfoblock|signing block|vcsinfo"),
    ("reproducible_signing", r"reproducib|allowedapksigningkeys|\bbinaries\b|signature|signing key|\bsigned\b|diffoscope|apksigcopier"),
    ("node_or_debian_packages", r"\bnode(js)?\b|\bnpm\b"),
    ("install_from_debian", r"from debian|debian package"),
    ("prebuild_or_scripts", r"prebuild|\bscripts?\b|what (are )?you trying|what you trying|\bsed\b"),
    ("listing_fastlane", r"fastlane|triple-?t|screenshots?|description|summary|\bicon\b|changelogs?|en-us"),
    ("categories", r"categor"),
    ("license", r"licen[cs]e|\bgpl|\bmit\b|apache"),
    ("antifeature_nonfree", r"anti-?feature|non-?free|proprietary|firebase|\bgms\b|play services|google play|crashlytics|tracking|analytics|admob"),
    ("network_disclosure", r"\bnetwork|\binternet\b|\bserver\b|connections?\b|connects to"),
    ("age_quality6", r"quality point 6|three months|3 months|too new|active(ly)? develop|months of|maintained for more than"),
    ("rebase_conflict", r"rebase|conflict|squash"),
    ("versions_commit", r"full hash|commit hash|versioncode|versionname|only the latest|latest version|old versions?|disabled"),
    ("abi_split", r"\babi\b|split"),
    ("format_lint", r"rewritemeta|\blint\b|format|indent"),
    ("blobs_scanner", r"gradle-wrapper|\.jar\b|\bblob|binary file|scanner|scandelete|scanignore|prebuilt"),
    ("app_id_or_name", r"application ?id|package name|applicationid"),
    ("metadata_fields", r"authorname|website|sourcecode|issuetracker|\bfields?\b|donate|liberapay"),
    ("srclibs_submodules", r"srclib|submodule"),
    ("flutter", r"flutter"),
    ("gradle_flavor_or_tasks", r"flavou?r|gradle|\btask\b|assemble"),
    ("ai_generated", r"\b(LLM|AI|vibe[- ]?cod\w*|slop|chatgpt|claude|copilot)\b|ai[- ]generated"),
    ("twa_wrapper", r"\btwa\b|trusted web|wrapper|webview"),
]
ACK = re.compile(r"^\s*(thanks?( you)?|thx|ty|done|lgtm|merged|nice|great|ok(ay)?|👍)[.!\s]*$", re.I)
MOSTLY_READY = re.compile(r"^This MR is mostly ready", re.I)
PIPELINE_TRIGGERED = re.compile(r"^Trigger+ed a pipeline", re.I)
TEST_REPORT = re.compile(r"\btested\b|works as described|test(ed)? (on|with)", re.I)


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def quartiles(values):
    values = sorted(values)
    if not values:
        return None
    if len(values) < 4:
        return {"n": len(values), "min": values[0], "median": statistics.median(values), "max": values[-1]}
    q = statistics.quantiles(values, n=4, method="inclusive")
    return {"n": len(values), "min": values[0], "q1": round(q[0], 1), "median": round(q[1], 1),
            "q3": round(q[2], 1), "max": values[-1]}


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def author_text(description):
    """Return the author's own prose above the checklist, template headings removed."""
    text = description or ""
    used_template = "## Checklist" in text or "### Policy" in text
    cut = len(text)
    for marker in ("## Checklist", "### Policy"):
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut]
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    lines = [ln for ln in text.splitlines()
             if ln.strip().lower() not in TEMPLATE_LINES and not re.match(r"\s*[*-] \[[ xX]\]", ln)]
    return "\n".join(lines).strip(), used_template


def description_stats(description):
    prose, used_template = author_text(description)
    images = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", prose)) + len(re.findall(r"<img\b", prose, re.I))
    image_links = len(re.findall(r"\.(png|jpe?g|webp|gif)\b", prose, re.I))
    stripped = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", " ", prose)
    stripped = re.sub(r"<img\b[^>]*>", " ", stripped, flags=re.I)
    stripped = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", stripped)
    stripped = re.sub(r"https?://\S+", " ", stripped)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.-]*", stripped)
    bullets = len(re.findall(r"^\s*[*-] (?!\[)", prose, re.M))
    headings = len(re.findall(r"^\s*#{1,6} ", prose, re.M))
    full = description or ""
    boxes_checked = len(re.findall(r"\[[xX]\]", full))
    boxes_open = len(re.findall(r"\[ \]", full))
    found = {k: bool(re.search(p, prose, re.I)) for k, p in DISCLOSURE.items()}
    return {
        "words": len(words), "used_template": used_template, "embedded_images": images,
        "image_refs": image_links, "bullets": bullets, "extra_headings": headings,
        "boxes_checked": boxes_checked, "boxes_open": boxes_open, **{f"says_{k}": v for k, v in found.items()},
    }


def load_recipe(text):
    if not text:
        return None
    try:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def build_kind(recipe, text):
    """Rough build family from the recipe text."""
    t = (text or "").lower()
    if "flutter" in t:
        return "flutter"
    if "capacitor" in t or "cap sync" in t or "cap copy" in t:
        return "capacitor"
    if re.search(r"\b(npm|pnpm|yarn|bun)\b", t) or "nodejs" in t:
        return "node_other"
    if "cargo" in t or "rustup" in t:
        return "rust"
    if "react-native" in t or "expo" in t:
        return "react_native"
    if "go build" in t or "gomobile" in t or "golang" in t:
        return "go"
    if "ndk:" in t:
        return "gradle_ndk"
    return "gradle_plain"


def recipe_facts(recipe, text):
    if not recipe:
        return {}
    builds = recipe.get("Builds") or []
    last = builds[-1] if builds else {}
    def has(key):
        return key in last and last[key] not in (None, [], "")
    sudo = " ".join(map(str, last.get("sudo") or [])) if isinstance(last.get("sudo"), list) else str(last.get("sudo") or "")
    return {
        "auto_update": str(recipe.get("AutoUpdateMode")),
        "update_check": str(recipe.get("UpdateCheckMode", "")).split(" ")[0],
        "update_check_data": "UpdateCheckData" in recipe,
        "binaries": "Binaries" in recipe,
        "allowed_keys": "AllowedAPKSigningKeys" in recipe,
        "n_builds": len(builds),
        "sudo": has("sudo"),
        "node_from_debian": bool(re.search(r"apt(-get)? install[^\n]*\bnodejs\b", sudo)),
        "node_from_tarball": "nodejs.org" in sudo,
        "prebuild": has("prebuild"),
        "init": has("init"),
        "build_step": has("build"),
        "srclibs": has("srclibs"),
        "scandelete": has("scandelete"),
        "scanignore": has("scanignore"),
        "ndk": has("ndk"),
        "output": has("output"),
        "gradle_flavor": (last.get("gradle") or [None])[0] not in (True, "yes", None) if isinstance(last.get("gradle"), list) else False,
        "subdir": has("subdir"),
        "build_kind": build_kind(recipe, text),
        "anti_features": "AntiFeatures" in recipe,
        "categories": tuple(recipe.get("Categories") or []),
        "license": recipe.get("License"),
    }


IGNORED_TOP = {"Builds", "CurrentVersion", "CurrentVersionCode"}
IGNORED_BUILD = {"versionName", "versionCode", "commit"}


def recipe_changes(first, last):
    """Name the fields reviewers or authors changed between first and last version."""
    if not first or not last:
        return None
    changes = []
    for key in sorted(set(first) | set(last)):
        if key in IGNORED_TOP:
            continue
        if first.get(key) != last.get(key):
            if key not in first:
                changes.append(f"+{key}")
            elif key not in last:
                changes.append(f"-{key}")
            else:
                changes.append(f"~{key}")
    fb = (first.get("Builds") or [{}])[-1] or {}
    lb = (last.get("Builds") or [{}])[-1] or {}
    for key in sorted(set(fb) | set(lb)):
        if key in IGNORED_BUILD:
            continue
        if fb.get(key) != lb.get(key):
            sign = "+" if key not in fb else "-" if key not in lb else "~"
            changes.append(f"{sign}build.{key}")
    if fb.get("versionCode") != lb.get("versionCode"):
        changes.append("version_bumped")
    return changes


def clean_note(text):
    """Drop quoted lines, fenced code, inline code spans' URLs and bare URLs before matching."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def classify_note(text):
    kinds = ["code_suggestion"] if "```suggestion" in text else []
    cleaned = clean_note(text)
    kinds += [name for name, pattern in NOTE_KINDS
              if name != "code_suggestion" and re.search(pattern, cleaned, re.I)]
    return kinds


def human_notes(record):
    author = record["mr"]["author"]["username"]
    notes = []
    discussions = record.get("discussions")
    if not isinstance(discussions, list):
        return author, notes
    for disc in discussions:
        for n in disc.get("notes", []):
            if n.get("system"):
                continue
            user = n["author"]["username"]
            if user.endswith("-bot") or user in ("fdroid-bot", "ghost"):
                continue
            notes.append({"user": user, "at": n["created_at"], "text": n.get("note") or "",
                          "diff_note": bool(disc.get("diff_discussion"))})
    notes.sort(key=lambda n: n["at"])
    return author, notes


def maintainers_from_lists():
    users = set()
    for path in glob.glob(os.path.join(DATA, "lists", "*.json")):
        for mr in json.load(open(path)):
            if mr.get("merge_user"):
                users.add(mr["merge_user"]["username"])
            if mr.get("closed_by") and mr["closed_by"]["username"] != mr["author"]["username"]:
                users.add(mr["closed_by"]["username"])
    return users


def analyze_merged(maintainers):
    rows, note_rows = [], []
    for path in sorted(glob.glob(os.path.join(DATA, "merged", "*.json"))):
        rec = json.load(open(path))
        mr = rec["mr"]
        author, notes = human_notes(rec)
        desc = description_stats(mr.get("description"))
        first = load_recipe(rec.get("recipe_first"))
        last = load_recipe(rec.get("recipe_last"))
        facts_first = recipe_facts(first, rec.get("recipe_first"))
        facts_last = recipe_facts(last, rec.get("recipe_last"))
        changes = recipe_changes(first, last)
        maint_notes = [n for n in notes if n["user"] in maintainers and n["user"] != author]
        other_notes = [n for n in notes if n["user"] not in maintainers and n["user"] != author]
        mostly_ready = [n for n in maint_notes if MOSTLY_READY.match(n["text"].strip())]
        triggered = [n for n in maint_notes if PIPELINE_TRIGGERED.match(n["text"].strip())]
        requests = [n for n in maint_notes if not ACK.match(n["text"].strip())
                    and not MOSTLY_READY.match(n["text"].strip())
                    and not PIPELINE_TRIGGERED.match(n["text"].strip())]
        system = [n for d in (rec.get("discussions") or []) for n in d.get("notes", []) if n.get("system")]
        sys_text = [n.get("note") or "" for n in system]
        kinds = set()
        for n in requests:
            k = classify_note(n["text"])
            kinds.update(k)
            note_rows.append({"iid": mr["iid"], "state": "merged", "user": n["user"], "role": "maintainer",
                              "at": n["at"], "kinds": ";".join(k), "text": n["text"][:500].replace("\n", " ")})
        for n in other_notes:
            note_rows.append({"iid": mr["iid"], "state": "merged", "user": n["user"],
                              "role": "community_test" if TEST_REPORT.search(n["text"]) else "community",
                              "at": n["at"], "kinds": ";".join(classify_note(n["text"])),
                              "text": n["text"][:500].replace("\n", " ")})
        created, merged = ts(mr["created_at"]), ts(mr["merged_at"])
        first_maint = ts(maint_notes[0]["at"]) if maint_notes else None
        request_days = sorted({n["at"][:10] for n in requests})
        rows.append({
            "iid": mr["iid"], "title": mr["title"], "author": author,
            "created": mr["created_at"][:10], "merged": mr["merged_at"][:10],
            "days_to_merge": round((merged - created).total_seconds() / 86400, 2),
            "hours_to_first_maintainer_note": round((first_maint - created).total_seconds() / 3600, 1) if first_maint else None,
            "versions": len(rec.get("versions") or []),
            "maintainer_notes": len(maint_notes), "maintainer_requests": len(requests),
            "request_days": len(request_days),
            "community_notes": len(other_notes),
            "community_tests": sum(1 for n in other_notes if TEST_REPORT.search(n["text"])),
            "request_kinds": ";".join(sorted(kinds)),
            "got_mostly_ready": bool(mostly_ready),
            "days_mostly_ready_to_merge": round((merged - ts(mostly_ready[0]["at"])).total_seconds() / 86400, 2) if mostly_ready else None,
            "days_to_mostly_ready": round((ts(mostly_ready[0]["at"]) - created).total_seconds() / 86400, 2) if mostly_ready else None,
            "pipelines_triggered_by_maintainer": len(triggered),
            "closed_then_reopened": any(t.strip() == "closed" for t in sys_text) and any(t.strip() == "reopened" for t in sys_text),
            "description_edited": any(t.startswith("changed the description") for t in sys_text),
            "title_changed": any("changed title" in t for t in sys_text),
            "labels": ";".join(mr.get("labels") or []),
            "label_reproducible": "reproducible-builds" in (mr.get("labels") or []),
            "files_changed": len(rec.get("files") or []),
            "recipe_changes": ";".join(changes) if changes is not None else "",
            "recipe_available": bool(first and last),
            **desc,
            **{f"first_{k}": v for k, v in facts_first.items() if k not in ("categories",)},
            **{f"last_{k}": v for k, v in facts_last.items() if k not in ("categories",)},
        })
    return rows, note_rows


CLOSE_REASONS = [
    ("template_not_followed", r"template is not followed|template was not used|no (proper )?(\(full\) )?(app )?inclusion template|follow the (mr |merge request )?template|check the app inclusion template"),
    ("similar_apps_unique_value", r"many simil|unique (functions|value|features?)|minor rebrand|diff(erence)? over|what diff|anything unique|already so many|many file managers|why a user needs|extra feature|no reason to provide"),
    ("age_quality6", r"quality point 6|three months|3 months?|maintained for|too new"),
    ("no_response_or_stale", r"no activity for a long time|no response|abandon"),
    ("twa_or_wrapper", r"\btwa\b|trusted web|website wrappers?|webview app"),
    ("nonfree_or_antifeature", r"non-?free|proprietary|firebase|\bgms\b|play services"),
    ("no_recipe_or_not_ready", r"no metadata recipe|where is yaml|not ready yet|this is not ready"),
    ("book_or_content_not_app", r"provide your book|pdf file|no need to add an app"),
]


def analyze_closed(maintainers):
    rows, note_rows = [], []
    for path in sorted(glob.glob(os.path.join(DATA, "closed", "*.json"))):
        rec = json.load(open(path))
        mr = rec["mr"]
        author, notes = human_notes(rec)
        closer = (mr.get("closed_by") or {}).get("username")
        maint_notes = [n for n in notes if n["user"] in maintainers and n["user"] != author]
        reasons = set()
        tail = maint_notes[-2:]
        for n in tail:
            for name, pattern in CLOSE_REASONS:
                if re.search(pattern, clean_note(n["text"]), re.I):
                    reasons.add(name)
        all_reasons = set()
        for n in maint_notes:
            for name, pattern in CLOSE_REASONS:
                if re.search(pattern, clean_note(n["text"]), re.I):
                    all_reasons.add(name)
            note_rows.append({"iid": mr["iid"], "state": "closed", "user": n["user"], "role": "maintainer",
                              "at": n["at"], "kinds": ";".join(classify_note(n["text"])),
                              "text": n["text"][:500].replace("\n", " ")})
        last_author_at = max((n["at"] for n in notes if n["user"] == author), default=None)
        last_maint_at = maint_notes[-1]["at"] if maint_notes else None
        desc = description_stats(mr.get("description"))
        last = load_recipe(rec.get("recipe_last"))
        rows.append({
            "iid": mr["iid"], "title": mr["title"], "author": author,
            "created": mr["created_at"][:10], "closed": (mr.get("closed_at") or "")[:10],
            "closed_by": closer, "closed_by_author": closer == author,
            "days_open": round((ts(mr["closed_at"]) - ts(mr["created_at"])).total_seconds() / 86400, 1) if mr.get("closed_at") else None,
            "maintainer_notes": len(maint_notes),
            "author_spoke_last": bool(last_author_at and (not last_maint_at or last_author_at > last_maint_at)),
            "reasons_closing": ";".join(sorted(reasons)), "reasons_any": ";".join(sorted(all_reasons)),
            "last_maintainer_note": (maint_notes[-1]["text"][:400].replace("\n", " ") if maint_notes else ""),
            "words": desc["words"], "labels": ";".join(mr.get("labels") or []),
            "build_kind": recipe_facts(last, rec.get("recipe_last")).get("build_kind") if last else "",
        })
    return rows, note_rows


def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def count(rows, pred):
    return sum(1 for r in rows if pred(r))


def summarize(merged, closed, maintainers):
    s = {"maintainers": sorted(maintainers), "n_merged": len(merged), "n_closed": len(closed)}
    if merged:
        s["merged_window"] = [min(r["created"] for r in merged), max(r["merged"] for r in merged)]
    templated = [r for r in merged if r["used_template"]]
    s["used_template"] = len(templated)
    s["words_all"] = quartiles([r["words"] for r in merged])
    s["words_templated"] = quartiles([r["words"] for r in templated])
    s["embedded_images"] = {"any": count(merged, lambda r: r["embedded_images"] > 0),
                            "image_refs_any": count(merged, lambda r: r["image_refs"] > 0),
                            "count_when_present": quartiles([r["embedded_images"] for r in merged if r["embedded_images"]])}
    s["structure"] = {"bullets_any": count(merged, lambda r: r["bullets"] > 0),
                      "extra_headings_any": count(merged, lambda r: r["extra_headings"] > 0),
                      "open_checkboxes_any": count(merged, lambda r: r["boxes_open"] > 0)}
    s["disclosures"] = {k[5:]: count(merged, lambda r, k=k: r[k]) for k in merged[0] if k.startswith("says_")}
    s["days_to_merge"] = quartiles([r["days_to_merge"] for r in merged])
    s["hours_to_first_maintainer_note"] = quartiles([r["hours_to_first_maintainer_note"] for r in merged
                                                     if r["hours_to_first_maintainer_note"] is not None])
    s["maintainer_requests"] = quartiles([r["maintainer_requests"] for r in merged])
    s["merged_without_maintainer_request"] = count(merged, lambda r: r["maintainer_requests"] == 0)
    s["request_days"] = {str(k): count(merged, lambda r, k=k: r["request_days"] == k) for k in range(0, 6)}
    s["request_days"]["6+"] = count(merged, lambda r: r["request_days"] >= 6)
    s["multi_round"] = count(merged, lambda r: r["request_days"] >= 3)
    s["versions"] = quartiles([r["versions"] for r in merged])
    s["community_tests"] = count(merged, lambda r: r["community_tests"] > 0)
    s["got_mostly_ready"] = count(merged, lambda r: r["got_mostly_ready"])
    s["days_to_mostly_ready"] = quartiles([r["days_to_mostly_ready"] for r in merged if r["days_to_mostly_ready"] is not None])
    s["days_mostly_ready_to_merge"] = quartiles([r["days_mostly_ready_to_merge"] for r in merged if r["days_mostly_ready_to_merge"] is not None])
    s["maintainer_triggered_pipeline"] = count(merged, lambda r: r["pipelines_triggered_by_maintainer"] > 0)
    s["closed_then_reopened"] = count(merged, lambda r: r["closed_then_reopened"])
    s["description_edited"] = count(merged, lambda r: r["description_edited"])
    s["title_changed"] = count(merged, lambda r: r["title_changed"])
    kinds = {}
    for r in merged:
        for k in filter(None, r["request_kinds"].split(";")):
            kinds[k] = kinds.get(k, 0) + 1
    s["request_kinds_mrs"] = dict(sorted(kinds.items(), key=lambda kv: -kv[1]))
    with_recipe = [r for r in merged if r["recipe_available"]]
    s["recipes_compared"] = len(with_recipe)
    changes = {}
    for r in with_recipe:
        for c in filter(None, r["recipe_changes"].split(";")):
            changes[c] = changes.get(c, 0) + 1
    s["recipe_changes_mrs"] = dict(sorted(changes.items(), key=lambda kv: -kv[1]))
    s["recipe_unchanged_except_version"] = count(with_recipe, lambda r: not [c for c in r["recipe_changes"].split(";") if c and c != "version_bumped"])
    def tally(field, rows=with_recipe):
        out = {}
        for r in rows:
            v = str(r.get(field))
            out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
    for f in ("auto_update", "update_check", "build_kind"):
        s[f"first_{f}"] = tally(f"first_{f}")
        s[f"last_{f}"] = tally(f"last_{f}")
    for f in ("update_check_data", "binaries", "allowed_keys", "sudo", "node_from_debian", "node_from_tarball",
              "prebuild", "init", "build_step", "srclibs", "scandelete", "scanignore", "ndk", "output",
              "gradle_flavor", "anti_features"):
        s[f"first_{f}"] = count(with_recipe, lambda r, f=f: r.get(f"first_{f}") is True)
        s[f"last_{f}"] = count(with_recipe, lambda r, f=f: r.get(f"last_{f}") is True)
    s["reproducible_label"] = count(merged, lambda r: r["label_reproducible"])
    s["reproducible_recipe_last"] = count(with_recipe, lambda r: r.get("last_allowed_keys") is True)
    s["auto_none_to_version"] = count(with_recipe, lambda r: r.get("first_auto_update") == "None" and r.get("last_auto_update") not in ("None", None))
    s["auto_none_kept"] = count(with_recipe, lambda r: r.get("last_auto_update") == "None")
    s["node_tarball_to_debian"] = count(with_recipe, lambda r: r.get("first_node_from_tarball") and r.get("last_node_from_debian"))
    s["prebuild_removed"] = count(with_recipe, lambda r: r.get("first_prebuild") and not r.get("last_prebuild"))
    s["repro_added"] = count(with_recipe, lambda r: not r.get("first_allowed_keys") and r.get("last_allowed_keys"))
    s["repro_dropped"] = count(with_recipe, lambda r: r.get("first_allowed_keys") and not r.get("last_allowed_keys"))
    # length against review load
    s["spearman_words_vs_requests"] = spearman([r["words"] for r in templated], [r["maintainer_requests"] for r in templated])
    s["spearman_words_vs_days"] = spearman([r["words"] for r in templated], [r["days_to_merge"] for r in templated])
    by_len = sorted(templated, key=lambda r: r["words"])
    third = len(by_len) // 3
    if third:
        s["requests_by_length_third"] = {
            "short": quartiles([r["maintainer_requests"] for r in by_len[:third]]),
            "middle": quartiles([r["maintainer_requests"] for r in by_len[third:-third]]),
            "long": quartiles([r["maintainer_requests"] for r in by_len[-third:]]),
        }
        s["days_by_length_third"] = {
            "short": quartiles([r["days_to_merge"] for r in by_len[:third]]),
            "long": quartiles([r["days_to_merge"] for r in by_len[-third:]]),
        }
    s["days_by_build_kind"] = {k: quartiles([r["days_to_merge"] for r in with_recipe if r.get("last_build_kind") == k])
                               for k in s["last_build_kind"]}
    s["requests_by_build_kind"] = {k: quartiles([r["maintainer_requests"] for r in with_recipe if r.get("last_build_kind") == k])
                                   for k in s["last_build_kind"]}
    # closed
    if closed:
        s["closed_window"] = [min(r["created"] for r in closed), max(r["closed"] for r in closed)]
        s["closed_by_author"] = count(closed, lambda r: r["closed_by_author"])
        s["closed_by_maintainer"] = count(closed, lambda r: not r["closed_by_author"])
        reasons = {}
        for r in closed:
            if r["closed_by_author"]:
                continue
            for k in filter(None, r["reasons_closing"].split(";")) or []:
                reasons[k] = reasons.get(k, 0) + 1
        s["closed_reasons_by_maintainer"] = dict(sorted(reasons.items(), key=lambda kv: -kv[1]))
        s["closed_by_maintainer_no_reason_matched"] = count(closed, lambda r: not r["closed_by_author"] and not r["reasons_closing"])
        s["closed_by_maintainer_no_note"] = count(closed, lambda r: not r["closed_by_author"] and r["maintainer_notes"] == 0)
        s["closed_days_open"] = quartiles([r["days_open"] for r in closed if r["days_open"] is not None])
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    maintainers = maintainers_from_lists()
    merged, notes_m = analyze_merged(maintainers)
    closed, notes_c = analyze_closed(maintainers)
    write_csv(os.path.join(OUT, "merged.csv"), merged)
    write_csv(os.path.join(OUT, "closed.csv"), closed)
    write_csv(os.path.join(OUT, "notes.csv"), notes_m + notes_c)
    summary = summarize(merged, closed, maintainers)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1, default=str)
    json.dump(summary, sys.stdout, indent=1, default=str)


if __name__ == "__main__":
    main()
