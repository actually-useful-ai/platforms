# Evidence behind this skill

Contents: sample, request text, what maintainers asked for, recipe changes, review timing,
closed requests, which rules rest on a single case.

Source: the 180 most recent merged and 300 most recent closed "New App" merge requests in
fdroiddata (project 36528), read on 24 November 2026 through GitLab's public endpoints. Full method,
tables and caveats: `docs/fdroid-new-app-evidence-2026-11.md` in the platforms repository; scripts
in `docs/research/fdroid-new-apps/`. Counts are of requests, not comments. Kinds of request come
from keyword rules checked by reading samples, so treat small counts as approximate.

## Request text (merged requests)

| Measure | Value |
| --- | --- |
| Words above the checklist | median 188, middle half 130 to 287, 9 of 179 over 500 |
| Embedded screenshots | 116 of 180; 3 or 4 when present (median 3.5) |
| Mention network use or offline operation | 143 of 180 (keyword match) |
| Say there are no ads, tracking or analytics | 90 of 180 |
| Compare with another app | 56 of 180 |
| Leave some checklist boxes unticked | 99 of 180 |
| Description edited after filing | 80 of 180 |

Length against review load (179 requests using the template): rank correlation 0.12 with the number
of maintainer requests and 0.07 with days to merge. The shortest and longest thirds both had a
median of 1 to 2 requests. No relationship worth acting on.

## What maintainers asked for (merged requests, n = 180)

| Kind | Requests |
| --- | --- |
| Enable R8 | 30 |
| Add `Binaries` / `AllowedAPKSigningKeys` (reproducible build) | 28 |
| Choose a better category | 27 |
| A GitLab suggestion editing the recipe directly | 24 |
| Follow the merge request template | 24 |
| Flutter: pin the SDK, ABI split with version codes | 14 Flutter requests; 12 asked for ABI split |
| Fastlane listing (icon in every locale, summary length, images folder) | 11 |
| Unique value over similar apps | 9 |
| Declare anti-features | 8 |
| Install Node or rustup from Debian | 8 |
| Quality point 6 (closed for it, later reopened and merged) | 8 |
| JDK version | 7 |
| `subdir` / `output` | 7 |
| Enable auto-update | 4 |
| Network connections (asking testers to check) | 4 |
| Prebuild steps or scripts | 2 |

39 of 180 merged with no maintainer request at all; 83 needed one day of requests, 42 two, 16
three or more.

Problems the CI's `check apk` job raised and authors fixed: the dependency-metadata signing block
came up in 11 requests, `version-control-info.textproto` (vcsInfo) in 3, `baseline.prof` in 1. No
maintainer asked about them directly; the pipeline did.

## Recipe as filed against as merged (171 with both versions readable)

| Change | Requests |
| --- | --- |
| Version moved to a newer release | 116 |
| Categories changed | 50 |
| `AllowedAPKSigningKeys` added | 35 (none removed) |
| `Binaries` added | 31 |
| `prebuild` changed | 23 |
| `sudo` changed or removed | 31 |
| `AntiFeatures` added | 11 |
| `AutoUpdateMode: None` → `Version` | 7 of 7 (none merged with `None`) |
| Node from a `nodejs.org` tarball → none from tarballs | 6 → 0 (5 moved to Debian) |
| Nothing changed but the version | 53 |

As merged: 126 of 171 recipes use `AllowedAPKSigningKeys` (the owner's signature); 169 use
`UpdateCheckMode: Tags`, 2 `HTTP`; every one has auto-update on.

## Review timing (merged)

| Measure | Value |
| --- | --- |
| First maintainer comment | median 4.2 hours; within a day for 161 of 176 |
| "This MR is mostly ready" (queued for community testing) | 119 of 180, median 0.7 days after filing |
| From "mostly ready" to merge | median 2.9 days |
| Filing to merge | median 5.5 days, middle half 2.1 to 11.4, longest 42 |
| By rounds of requests: 0 / 1 / 2 / 3+ | median 2.1 / 4.7 / 9.5 / 11.1 days |
| Community test reports | 86 requests; 76 of 97 reports mention network or the INTERNET permission |
| Closed and reopened on the way | 30 (18 for the template, 7 for Quality point 6) |

## Closed without merging

300 closed requests from the same window; maintainers closed 275, authors 25. Reasons in the
maintainer's closing comments (one request can have several):

| Reason | Requests (of 275) |
| --- | --- |
| Not developed for three months (Quality point 6) | 211 |
| Template not followed | 60 |
| No unique value over catalog apps | 31 |
| No activity after a request | 25 |
| Website wrapper | 1 |
| No reason matched | 12 |

Median 1.9 days open; three-month closures took a median 1.5 days, and 186 of 211 had no other
maintainer comment. No closure in the sample cited a non-free dependency.

## Which rules rest on what

Measured in the sample above: R8, reproducible-build fields, categories, template, auto-update on,
Node from Debian, Quality point 6 closures, description length, screenshots, network disclosure
being checked by testers, review timing, the dependency-metadata block.

Policy text only (F-Droid's Inclusion Policy and Reproducible Builds pages, read 24 November
2026): website wrappers needing native features, proprietary dependencies, apksigner build-tools
34 for reference APKs, vcsInfo guidance, `UpdateCheckData` syntax.

Single cases, not measured: "We don't accept TWA" and "we don't accept website wrapper" (maintainer
lines; this sample has one website-wrapper refusal, !52244, and no TWA refusal); "what you trying to
do over here" on an opaque prebuild script and "enable autoupdate not none" (Mandaza, !55922);
"Install node from debian." and "Please enable R8." on Hexsweeper (!57772) are also instances of
measured kinds; a private repository's history not counting toward three months (Mandaza, closed
9 November 2026); a root `metadata/` folder replacing the Fastlane description (Mandaza 1.3.12,
checked with fdroidserver's own scan); ruamel.yaml 0.18.10 formatting (fdroiddata's CI image,
checked once); creating the fork branch in GitLab's web editor.
