# Recipe patterns for fdroiddata

Contents: rules for every recipe, plain Gradle, Capacitor with a committed web payload,
Capacitor or Vite built at build time, reproducible builds, auto-update, what reviewers push back on.

Field reference: <https://f-droid.org/docs/Build_Metadata_Reference/>. Templates:
`templates/` in fdroiddata. Copy a recently merged recipe of the same build family before writing
one from scratch.

## Rules for every recipe

- File: `metadata/<applicationId>.yml`, LF line endings, one app per merge request.
- `commit:` is the full 40-character hash of the tagged release, never a tag or branch name.
- Exactly one build entry before merge: the newest. When you move to a new version, replace the
  entry; do not add a second one or a disabled one.
- No `Summary`, `Description`, screenshots or changelogs in the recipe. They come from the app's
  Fastlane folder.
- `AuthorName`, `SourceCode`, `IssueTracker` and `License` (SPDX id) are expected. Add
  `AuthorWebSite`, `WebSite` and `Changelog` when they exist.
- Categories must come from `config/categories.yml` in fdroiddata.
- Lines with a trailing space are significant: `Binaries: ` and `UpdateCheckData: ` with the value
  on the next line are how fdroiddata's formatter writes long values. Keep them.
- Format with `fdroid rewritemeta` using the library version CI uses (see
  [local-checks.md](local-checks.md)); a different ruamel.yaml version folds long lines differently.

## Plain Gradle with an F-Droid flavor

```yaml
Categories:
  - Clock
License: MIT
AuthorName: Example Author
AuthorWebSite: https://example.org/
SourceCode: https://github.com/example/app
IssueTracker: https://github.com/example/app/issues

AutoName: Example

RepoType: git
Repo: https://github.com/example/app.git
Binaries: https://github.com/example/app/releases/download/fdroid-v%v/example-fdroid-%v.apk

Builds:
  - versionName: 1.3.13
    versionCode: 10320
    commit: b39341f6dbcb9f963fa10f4b1f36c4fb22e3a1dc
    subdir: android/app
    gradle:
      - fdroid

AllowedAPKSigningKeys: <sha256 of the signing certificate>

AutoUpdateMode: Version
UpdateCheckMode: Tags ^fdroid-v[0-9]+\.[0-9]+\.[0-9]+$
UpdateCheckData: android/app/build.gradle.kts|create\("fdroid"\)[^}]*versionCode\s=\s(\d+)||fdroid-v([\d.]+)
CurrentVersion: 1.3.13
CurrentVersionCode: 10320
```

- `gradle: [yes]` builds `assembleRelease`; name the flavor when there is one.
- `subdir` is the folder that holds `src/main` (usually `app`).
- If a flavor drops Play-only dependencies, the scanner reads only the flavor being built. A
  prebuild that deletes the other flavors' sources is unnecessary and draws questions.

## Capacitor with a committed web payload

Use when the built web assets are committed and the Android project only needs `cap sync`.

```yaml
Builds:
  - versionName: 1.0.17
    versionCode: 42
    commit: <full hash>
    subdir: app/android/app
    sudo:
      - echo "deb https://deb.debian.org/debian forky main" > /etc/apt/sources.list.d/forky.list
      - apt-get update
      - apt-get install -y -t forky npm
      - npm install -g pnpm@10.18.0
    gradle:
      - yes
    prebuild:
      - cd ../..
      - pnpm install --frozen-lockfile
      - pnpm exec cap sync android
    scandelete:
      - app/node_modules/.pnpm/@capacitor+cli@8.3.1/node_modules/@capacitor/cli/assets
```

- Install Node and npm from Debian (`apt-get install`, from a newer suite if the buildserver's is
  too old). A reviewer asked to replace a `nodejs.org` tarball with this on the first round.
- `scandelete` the Capacitor CLI's bundled `assets` folder (it holds prebuilt archives the scanner
  flags) and `node_modules` when the build does not need them after sync.
- A committed payload must be the build of the tagged source. Reviewers can ask how it was made;
  building it in the recipe (next pattern) removes the question.

## Capacitor or Vite built at build time

```yaml
Builds:
  - versionName: 1.3.0
    versionCode: 786
    commit: <full hash>
    subdir: android/app
    sudo:
      - echo "deb https://deb.debian.org/debian forky main" > /etc/apt/sources.list.d/forky.list
      - apt-get update
      - apt-get install -y -t forky nodejs npm
      - npm install -g pnpm@12.9.1
    init:
      - cd ../..
      - pnpm install --frozen-lockfile
      - SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) pnpm build:android
      - pnpm exec cap sync android
    gradle:
      - yes
    scandelete:
      - node_modules
```

- Anything the web build stamps (build time, version string, hash) must come from the commit,
  for example `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)`, or the APK will not match the
  reference.
- Pin the package manager version and use the lockfile (`--frozen-lockfile`, `npm ci`).
- The build must not fetch from the network beyond package registries the policy allows.

## Reproducible builds (your signature)

- `Binaries:` points at the signed release APK on the source host, with `%v` (version name) and
  `%c` (version code) placeholders. `AllowedAPKSigningKeys:` is the lowercase SHA-256 of the
  signing certificate (`apksigner verify --print-certs`).
- F-Droid builds the recipe, copies your signature onto its unsigned APK and publishes yours only if
  it verifies. If you skip this, F-Droid signs with its own key and you cannot switch later.
- Sign the reference APK with `apksigner` from build-tools 34 (35+ produces APKs apksigcopier cannot
  verify), v2 and v3 schemes, v1 off. Build it from a clean checkout of the tagged commit.

## Auto-update

- Default: `AutoUpdateMode: Version` with `UpdateCheckMode: Tags`, plus a tag regex when the repo
  has other tags. `checkupdates --auto` must produce a correct build entry from the next tag.
- Add `UpdateCheckData` when Gradle does not hold literal version values (computed names, values in
  another file, several flavors). Form: `file|regex for code|file or empty|regex for name`; an empty
  third field takes the name from the tag.
- With auto-update on, F-Droid builds the newest tag it finds. The signed APK must be on the release
  before the tag is pushed, and the tag name must match the version name.

## What reviewers push back on

Counts are in [evidence.md](evidence.md).

- `AutoUpdateMode: None` without a reason: they ask for auto-update.
- Opaque prebuild steps (scripts that rewrite or delete source, `sed` on build files) without an
  explanation in the recipe: they ask what it does. Remove what the build does not need.
- R8 off: they ask to enable it (`isMinifyEnabled = true` with resource shrinking as needed).
- Node from a tarball or curl-pipe installer: they ask for Debian packages.
- Signing blocks in the APK: the dependency-info block (`dependenciesInfo`) must be off.
- Extra build entries, disabled entries, or a tag in `commit:`.
