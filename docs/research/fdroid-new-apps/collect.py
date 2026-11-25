# File Purpose: Download public merge request data for the F-Droid "New App" study.
# Primary Functions/Classes: get(), collect_list(), collect_mr(), main()
# Inputs/Outputs: reads the public GitLab API for fdroid/fdroiddata (project 36528),
#   unauthenticated; writes one JSON file per request under $FDROID_STUDY_DATA/merged/ and
#   closed/, plus list pages under lists/ (default ./fdroid-study/data). Resumable: existing
#   files are kept. Usage: python3 collect.py <merged pages> <closed pages> (60 per page).

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://gitlab.com/api/v4/projects/36528"
UA = "fdroid-mr-study/1.0"
ROOT = os.environ.get("FDROID_STUDY_DATA", os.path.join(os.getcwd(), "fdroid-study", "data"))


def get(url, tries=8):
    """Fetch JSON, sleeping through HTTP 429 and transient errors."""
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                remaining = resp.headers.get("ratelimit-remaining")
                body = json.loads(resp.read().decode("utf-8"))
                if remaining is not None and int(remaining) < 20:
                    time.sleep(65)
                return body
        except urllib.error.HTTPError as err:
            if err.code == 429:
                wait = int(err.headers.get("retry-after") or 300)
                print(f"429 on {url}; sleeping {wait}s", flush=True)
                time.sleep(min(max(wait, 30), 600))
                continue
            if err.code in (401, 404, 403, 410):
                return {"_error": err.code}
            print(f"HTTP {err.code} on {url}", flush=True)
            time.sleep(20)
        except Exception as err:  # network hiccup
            print(f"{type(err).__name__} on {url}: {err}", flush=True)
            time.sleep(20)
    return {"_error": "gave up"}


def collect_list(state, pages):
    out = []
    os.makedirs(os.path.join(ROOT, "lists"), exist_ok=True)
    for page in range(1, pages + 1):
        path = os.path.join(ROOT, "lists", f"{state}-{page}.json")
        if os.path.exists(path):
            out.extend(json.load(open(path)))
            continue
        query = urllib.parse.urlencode({
            "state": state, "labels": "New App", "per_page": 60,
            "order_by": "created_at", "sort": "desc", "page": page,
        })
        data = get(f"{API}/merge_requests?{query}")
        if not isinstance(data, list):
            print(f"list {state} page {page} failed: {data}", flush=True)
            break
        json.dump(data, open(path, "w"))
        out.extend(data)
    return out


WEB = "https://gitlab.com/fdroid/fdroiddata/-"


def get_text(url, tries=6):
    """Fetch a raw text file from the web endpoint; returns None when missing."""
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            if err.code == 429:
                wait = int(err.headers.get("retry-after") or 300)
                print(f"429 on {url}; sleeping {wait}s", flush=True)
                time.sleep(min(max(wait, 30), 600))
                continue
            if err.code in (401, 403, 404, 410):
                return None
            time.sleep(20)
        except Exception as err:
            print(f"{type(err).__name__} on {url}: {err}", flush=True)
            time.sleep(20)
    return None


def collect_mr(mr, state, with_versions):
    folder = os.path.join(ROOT, state)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{mr['iid']}.json")
    if os.path.exists(path):
        return
    iid = mr["iid"]
    record = {"mr": mr}
    record["discussions"] = get(f"{WEB}/merge_requests/{iid}/discussions.json")
    time.sleep(0.3)
    diffs = get(f"{WEB}/merge_requests/{iid}/diffs.json")
    time.sleep(0.3)
    if isinstance(diffs, dict) and "merge_request_diffs" in diffs:
        versions = []
        for v in diffs["merge_request_diffs"]:
            sha = None
            cp = v.get("compare_path") or ""
            if "start_sha=" in cp:
                sha = cp.split("start_sha=")[1].split("&")[0]
            versions.append({"index": v["version_index"], "created_at": v["created_at"],
                             "commits_count": v["commits_count"], "sha": sha})
        versions.sort(key=lambda v: (v["created_at"] or "", v["index"] or 0))
        files = [{"path": f.get("new_path"), "new_file": f.get("new_file"),
                  "added": f.get("added_lines"), "removed": f.get("removed_lines")}
                 for f in diffs.get("diff_files", [])]
        record["versions"] = versions
        record["files"] = files
        recipes = [f["path"] for f in files
                   if f["path"] and f["path"].startswith("metadata/") and f["path"].endswith(".yml")
                   and f["path"].count("/") == 1]
        record["recipe_path"] = recipes[0] if recipes else None
        if recipes and versions:
            first, last = versions[0], versions[-1]
            if first["sha"]:
                record["recipe_first"] = get_text(f"{WEB}/raw/{first['sha']}/{recipes[0]}")
                time.sleep(0.3)
            if last["sha"] and last["sha"] != first["sha"]:
                record["recipe_last"] = get_text(f"{WEB}/raw/{last['sha']}/{recipes[0]}")
                time.sleep(0.3)
            else:
                record["recipe_last"] = record.get("recipe_first")
    else:
        record["diffs_error"] = diffs if not isinstance(diffs, dict) else list(diffs.keys())[:5]
    json.dump(record, open(path, "w"))
    nd = len(record["discussions"]) if isinstance(record["discussions"], list) else record["discussions"]
    print(f"{state} {iid} discussions={nd} versions={len(record.get('versions', []))} recipe={record.get('recipe_path')}", flush=True)


def main():
    merged_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    closed_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    merged = collect_list("merged", merged_pages)
    closed = collect_list("closed", closed_pages)
    print(f"merged listed {len(merged)}, closed listed {len(closed)}", flush=True)
    for mr in merged:
        collect_mr(mr, "merged", True)
    for mr in closed:
        collect_mr(mr, "closed", True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
