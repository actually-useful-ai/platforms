---
name: platforms-fdroid
description: Use when getting an Android app into F-Droid's main catalog through fdroiddata, from the fit check against the inclusion policy through preparing a reproducible build, writing and checking the build recipe, opening the "New app" merge request and answering review. Not for Google Play or Amazon staging, IzzyOnDroid, or running a self-hosted F-Droid repository.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebFetch, AskUserQuestion]
---

# Platforms F-Droid

Take one Android app from "could this go in F-Droid?" to a merged `New app: <name>` request in
`gitlab.com/fdroid/fdroiddata`. Work in order; each stage ends in evidence, and the stop gates are
where the human owner of the app acts or approves.

Track states (the suite's states, mapped): fit-checked → built (release tagged) → validated (local
checks pass) → store-staged (fork pipeline green) → submitted (request open). Merged is the
maintainers' act, never yours. Never infer a later state from an earlier one.

**Stop: the owner approves or edits every outward text.** Show the exact text before opening the
merge request, before posting any comment, and before any commit to the request branch once it is
open. One approval covers one post or one commit.

## 1. Fit check, before any work

Answer each with evidence (a file, a command's output, a link). Any "no" ends the job here: report
it with the policy line and stop.

- **Source and license.** Public repository, a FLOSS license file (SPDX id for `License`), and
  redistributable assets. Media or data files with no stated license are named in the request.
- **Proprietary dependencies.** The flavor F-Droid will build has no Google Play Services, Firebase,
  Crashlytics, ML Kit or proprietary ad, analytics or tracking SDK. Check the resolved runtime
  classpath (`./gradlew :app:dependencies --configuration <flavor>ReleaseRuntimeClasspath`), not the
  build files alone. Prebuilt binaries only from trusted Maven repositories or Debian.
- **Anti-features.** List what applies (network services that are non-free, tracking, ads,
  non-free assets). An anti-feature is declared, not hidden; it does not by itself block inclusion.
- **Wrappers.** Trusted Web Activities are refused, and so is a website wrapper: an app that loads
  a live site without native features. A web app whose content ships inside the APK and works
  offline is not a wrapper; say so in one sentence in the request.
- **Age (Quality point 6).** At least three months of active development in the public
  repository's history. This is the most common reason new apps are closed (211 of 275
  maintainer closures in the study), usually within two days and without other review. A private repository's history does not count. Exceptions: the app has
  proven users, the author already maintains an app in the catalog (link its merged request), or
  the app is for an event. Name the exception in the request if you rely on one.
- **Not already there.** `curl -s -o /dev/null -w "%{http_code}\n"
  https://f-droid.org/api/v1/packages/<applicationId>` returns 404, and no open fdroiddata request
  or RFP issue covers it. The application ID is unique and, ideally, under a domain the author owns.

## 2. Prepare the app (in the app's own repository)

- **R8 on** for the release build (`isMinifyEnabled = true`, `minifyEnabled true` in Groovy;
  resource shrinking only if it helps). It is the change maintainers ask for most (30 of 180
  merged requests).
- **Signing blocks off:** `dependenciesInfo { includeInApk = false; includeInBundle = false }`.
- **Blocker: run the release check at the exact commit the recipe names.**
  `scripts/release_check.py <checkout> --subdir <subdir> --commit <commit> [--flavor <flavor>]`
  reads the module's build file at that commit and fails when the release build has R8 off or
  `dependenciesInfo` leaves `includeInApk` on. Pass `--apk <signed reference APK>` when the app is
  signed outside Gradle; the APK then decides the dependency-block check. Do not file the request, and do not
  add a build to an open one, while it reports FAIL or UNKNOWN. UNKNOWN means the value comes from
  somewhere the script can't read; settle it by hand and tell the owner how.
- **R8 goes in the release that gets filed.** Turning it on changes the APK, so it needs a new
  version and a new signed release. Build the minified release and run it on an emulator first
  (launch, the main screens, anything that uses reflection, such as plugins or serialization) before
  the owner signs it.
- **vcsInfo:** build the reference APK from a clean checkout of the tagged commit, so the bundled
  `version-control-info.textproto` names that commit. Set `vcsInfo.include false` only if that is
  impossible.
- **Deterministic output:** no build time or machine path in the APK or web bundle; take any
  stamp from the commit (`SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)`); pin the JDK, Gradle,
  Node and package-manager versions; use lockfiles. Two clean builds must give the same unsigned
  APK hash.
- **Listing:** `fastlane/metadata/android/en-US/` with `title.txt`, `short_description.txt`,
  `full_description.txt`, `changelogs/<versionCode>.txt`, `images/icon.png` and
  `images/phoneScreenshots/`. The description says what the app connects to and when.
  Screenshots must read without hue: check each under simulated deuteranopia and
  pair color with text or shape.
- **No root `metadata/` folder holding another store's text.** fdroidserver reads
  `metadata/<locale>/` at the repository root after Fastlane, and the last one read wins. Run
  `scripts/listing_sources.py <checkout> --subdir <subdir>`; move the folder and re-tag if it
  reports a conflict.
- **Tags and release:** one tag per release, named to match the version name, with a pattern
  `UpdateCheckMode` can filter. The reference APK is signed with `apksigner` (v2 and v3 schemes,
  v1 off) and attached to the release at the address `Binaries` will name.

**Stop: the owner signs and tags the release.** Never sign, create or move tags, or publish a
release yourself. Prepare the commands and the expected hashes; wait for the owner to run them.

## 3. Write the recipe

Read [references/recipes.md](references/recipes.md) and start from the pattern for the build family:
plain Gradle, Capacitor with a committed web payload, or Capacitor or Vite built at build time.
Use `Binaries` and `AllowedAPKSigningKeys` so F-Droid ships the owner's signature, and
`AutoUpdateMode: Version` with `UpdateCheckMode: Tags` (plus `UpdateCheckData` when Gradle does not
hold literal versions). Every prebuild or init line must be one the build needs and a reviewer can
read; delete the rest rather than explaining it.

## 4. Check locally, then the fork branch and pipeline

Follow [references/local-checks.md](references/local-checks.md): fdroidserver from git master with
ruamel.yaml 0.18.10 (what CI uses), then `fdroid lint`, `fdroid rewritemeta` (file unchanged), the
schema check, `fdroid checkupdates` (including an `--auto` run from one version back), `fdroid
scanner` on the tagged commit and `fdroid build` with the reference comparison. Then commit only
`metadata/<applicationId>.yml` to a branch on the owner's fork, compare the raw file's sha256 with
the local file and get a green pipeline. Keep the logs; the request links nothing it cannot back.

## 5. Write the request text

Follow [references/request-text.md](references/request-text.md): the fdroiddata template with its
headings, a short description sized to the app, two to four screenshots, one paragraph on why it
exists and what it adds over a named catalog app, then one plain sentence per fact that could change
the decision (network services and when each is contacted, anti-features, a missing license, a
policy exception). Nothing argued in advance, no offers to remove features. Count with
`scripts/request_words.py`. Copy the checklist from the current template and tick only what is true.

**Stop: show the owner the exact title, text, recipe sha256 and pipeline link before opening the
merge request.** Open it only on an explicit yes for that text.

## 6. Review

Follow [references/review.md](references/review.md). Fix first, get the pipeline green, then reply
under the comment in a sentence or two. A new version while the request is open replaces the single
build entry after the owner has released it and `scripts/release_check.py` passes at its commit.

**Stop: before posting any reply or committing any change to the open request, show the owner the
exact text or diff.** Never merge, close or reopen the request, never push to it without approval,
and never ping maintainers.

## Evidence and limits

[references/evidence.md](references/evidence.md) holds the counts behind these steps (what merged
requests look like, what reviewers asked for, why requests were closed) and marks which rules rest
on a single case. Re-check policy pages and CI versions when they matter; both change.

- No credentials, keystores or tokens in files, logs or reports.
- No GitLab or GitHub login, merge request, comment or tag without the human owner's go for that
  exact action.
