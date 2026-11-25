# File Purpose: Count the words an author wrote above the checklist of an fdroiddata "New app" request.
# Primary Functions/Classes: count(), main()
# Inputs/Outputs: reads request text from a file or stdin; prints JSON with the word count (template
#   headings, HTML comments, image markup and bare URLs excluded), embedded image count, and whether
#   the template checklist is present. Same counting rule as the evidence study in docs/.

from __future__ import annotations

import argparse
import json
import re
import sys

TEMPLATE_HEADINGS = {
    "## abstract for new app inclusion",
    "### please introduce the functions and usage of your app in summary, and also attach some screenshots.",
    "### please elaborate why you wrote this app. please highlight the unique functions it provides over other similar apps in f-droid.",
}


def count(text: str) -> dict:
    has_checklist = "## Checklist" in text or "### Policy" in text
    cut = min([i for i in (text.find("## Checklist"), text.find("### Policy")) if i != -1] or [len(text)])
    prose = re.sub(r"<!--.*?-->", " ", text[:cut], flags=re.S)
    prose = "\n".join(line for line in prose.splitlines()
                      if line.strip().lower() not in TEMPLATE_HEADINGS
                      and not re.match(r"\s*[*-] \[[ xX]\]", line))
    images = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", prose)) + len(re.findall(r"<img\b", prose, re.I))
    stripped = re.sub(r"!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?", " ", prose)
    stripped = re.sub(r"<img\b[^>]*>", " ", stripped, flags=re.I)
    stripped = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", stripped)
    stripped = re.sub(r"https?://\S+", " ", stripped)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.-]*", stripped)
    return {"words": len(words), "images": images, "has_checklist": has_checklist}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="request text; stdin when omitted")
    args = parser.parse_args(argv)
    text = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    json.dump(count(text), sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
