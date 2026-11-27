# Changelog

All notable changes to the Platforms and Publishing Suite are documented here.

## [Unreleased]

### Changed

- Color-vision checks require simulated deuteranopia only. Protanopia,
  tritanopia and grayscale are optional, except the KDP grayscale check,
  since many e-readers show grayscale only.
- Python files no longer need a top-of-file purpose banner.

### Added

- `platforms-fdroid` ships `scripts/release_check.py`, which reads the Android
  module's `build.gradle` or `build.gradle.kts` at the commit a recipe names
  and fails when the release build has R8 off or `dependenciesInfo` leaves
  `includeInApk` on. It handles both Gradle DSLs, `release { }` and
  `getByName("release")` blocks, flavor overrides (`--flavor`), and the signed
  reference APK's signing block (`--apk`) for apps signed outside Gradle. When
  a value comes from a variable or the variant API it reports UNKNOWN instead
  of passing. Tests use excerpts of Solar Orrery, Mandaza and Hexsweeper
  before and after R8.
- An eval case, `fdroid-r8-off-blocks-filing`, where the expected answer to a
  filing request with R8 off is to stop and turn it on in a new release.

### Changed

- R8 and `dependenciesInfo` are now a blocker in `platforms-fdroid`: run
  `release_check.py` at the recipe's commit before filing or adding a build,
  and do not file while it fails. Turning R8 on belongs in the release that
  gets filed, and that build is tested minified on an emulator before signing. The request text no
  longer lists "R8 off" as something to explain. Maintainers asked for R8 on
  Hexsweeper (!57772) and again on Solar Orrery (!58981).

## [0.4.0] - 2026-11-24

### Added

- `platforms-fdroid`, a tenth canonical skill for taking an Android app into
  F-Droid's main catalog: fit check (license, proprietary dependencies, website
  wrappers, Quality point 6), app preparation (R8, `dependenciesInfo`,
  `vcsInfo`, deterministic stamps, Fastlane, root `metadata/` conflicts),
  recipe patterns, local checks with the fdroidserver and ruamel.yaml versions
  fdroiddata's CI uses, request text and review, with a stop for the owner
  before every outward step. Two scripts ship with it: `listing_sources.py`
  (which folders fdroidserver takes listing text from, optionally through
  fdroidserver itself) and `request_words.py` (words above the checklist).
- `docs/fdroid-new-app-evidence-2026-11.md`, the study of 180 merged and 300
  closed "New App" requests the skill's rules are drawn from, with the
  collection and analysis scripts under `docs/research/fdroid-new-apps/`.
- Routing evals for the new skill under `evals/` (`claude plugin eval`), and
  unit tests for its routing contract, stop gates, reference links and scripts
  (`tests/test_fdroid_skill.py`). The reference-link test covers every skill.
- Color-vision checks in every visual skill: status, focus, figures, icons,
  and screenshots must read without hue under simulated deuteranopia and
  grayscale, pinned by `test_visual_targets_require_color_vision_checks`.
- Store assets stage the store's accessibility declarations with the bundle
  (Apple's Accessibility Nutrition Labels), claim a feature only when every
  common task works with it, and keep the device evidence beside the claim.
  Apple screenshot and preview sizes live in one dated record that is
  re-checked against the live page. Pinned by
  `test_store_assets_stage_accessibility_declarations_with_evidence`.
- `--client-home` to point root discovery at a temporary home for review runs.
- `default_client_roots` in `tools/check_drift.py` as the single definition of
  per-client skill roots, now also consumed by `tools/install_projections.py`.
- A concrete `tizen` builder. `TizenAdapter` runs `build-web` and
  `package -t wgt` through the allowlisted argv runner and returns the signed
  widget with its checksum. Missing `config.xml`, a `tizen` CLI absent from
  PATH, a non-zero CLI exit, and packaging that yields no widget all stay at
  `scaffolded` and report the real reason.
- `examples/tizen-sample`, a minimal offline widget fixture with a declared
  language, title, main landmark, and reduced-motion handling.
- An optional `post-commit` hook, installed by `scripts/install-hooks.sh`, that
  warns when a commit changes `skills/` or `suite.toml` while installed
  projections are stale.

### Changed

- The `platforms` router sends F-Droid main-catalog work to
  `platforms-fdroid`, and `platforms-mobile` hands it over explicitly.
- An invocation without positional roots now discovers the conventional skill
  root for every supported client and compares the ones that exist, reporting
  them under `discovered_roots`.
- Discovering no root at all fails closed with exit `2` instead of reporting
  clean; `--allow-no-roots` restores the old behavior as an explicit assertion.

### Fixed

- `tools/check_drift.py` no longer reports a clean result when it is given no
  installed roots. The bare command documented in `README.md` and `AGENTS.md`
  previously returned `drift: false` and exit `0` unconditionally, so it could
  not fail and masked real drift in installed projections.

### Notes

- The corrected check found real drift that the previous one could not: the
  Claude and Agents roots still held pre-consolidation prose, and Codex held no
  platform skills. Reprojecting brought all four supported clients to the 0.3.0
  canonical content, including the least-privilege `allowed-tools` frontmatter.

## [0.3.0] - 2026-07-12

### Changed

- Consolidated the canonical skill inventory from 20 directories to nine skills:
  routing, intake, release planning, store assets, TV, mobile, KDP, Pebble, and
  web kiosk.
- Preserved all 15 superseded names as validated direct aliases in `suite.toml`
  and the generated deterministic lock.
- Merged target-specific adapter, accessibility, artifact, toolchain, and
  human-only submission requirements into the TV, mobile, KDP, and Pebble skills.

### Added

- Safe projection installer with dry-run support, deterministic managed state,
  idempotent updates, stale-managed cleanup, and symlink refusal.
- Client-specific projection layouts: Claude copies plus relative aliases,
  Codex direct absolute links, and canonical copies plus relative aliases for
  Cursor and Agents.
- Separate drift fields for missing/changed aliases and stale managed names.

### Fixed

- Added aliases to the published suite schema and standards-based schema tests.
- Replaced maximal skill permissions with parsed, least-privilege frontmatter.
- Defined official vendor documentation, source URL, retrieval date, and
  fail-closed handling as the store-specification contract.
- Prevented placeholders, missing artifacts, failed validation, and unvalidated
  KDP bundles from advancing release states.
- Restored web-kiosk accessibility/human publication gates, Vega architecture
  selection, and webOS icon/version checks.
- Rejected ancestor symlinks, hostile managed names, and overlapping projection
  roots; staged replacements now restore originals on failure.
- Allowed initial adoption to migrate only exact Codex links from a legacy alias
  to the matching Claude legacy alias, while rejecting missing or mismatched targets.
- Allowed non-Codex clients to adopt exact same-name links to real directories
  under another configured supported-client root.
- Staged complete generated-manifest sets and added rollback on injected commit
  failure.

## [0.2.0] - 2026-07-10

### Added

- Typed `src/platforms` package with `detect`, `plan`, `doctor`, `build`, `validate`, `package`, `report`, and `drift` commands.
- Secure allowlisted process runner (`shell=False`, argv safety, optional root confinement).
- Platform adapters for KDP, Pebble, Android family, Vega, webOS, Tizen, Roku, and web kiosk.
- KDP upload-bundle pipeline from `book.yml` (EPUB3, cover geometry, metadata, checksums, checklist).
- Canonical prose for all 20 skills and four read-only agents.
- Example KDP sample, book schema, platform matrix, accessibility, and adding-a-platform docs.
- Ambient Time read-only fixture detection tests.
- Ambient Time fixture helpers and docs for the cross-platform test-pack contract (`tv-dial`, `tv-cosmic`, `tv-word-grid`, `clk-binary`).

### Security

- Project paths reject `..` segments.
- KDP and store flows stop at human upload/submission checklists.

## [0.1.0] - 2026-07-10

### Added

- Canonical `suite.toml` metadata for suite identity, client support, 20 planned skills, and four planned read-only agents.
- Standard-library manifest generation with deterministic JSON and `--check` drift detection.
- Timestamp-free integrity lock with SHA-256 hashes, normalized paths, and file modes.
- Read-only installed-skill drift reporting for optional roots.
- JSON Schema documentation for the suite model.
- Pinned source provenance, license boundaries, and attributions.
- Test-first coverage for generation, validation, check mode, and projection drift.
- Project, contribution, security, and maintenance documentation.

### Fixed

- Replaced invalid reserved-field inventories with official client component shapes.
- Made supported-client subsets control generation, stale-file checks, cleanup, and lock entries.
- Added generated-file mode drift detection and atomic symlink-safe writes.
- Made canonical metadata failures return a distinct nonzero error result.
- Excluded nested generated caches from managed-skill comparisons.
- Pinned the excluded `jordangarrison/ash-kindle` revision with an explicit no-reuse boundary.

[0.3.0]: https://github.com/actually-useful-ai/platforms/releases/tag/v0.3.0
[0.2.0]: https://github.com/actually-useful-ai/platforms/releases/tag/v0.2.0
[0.1.0]: https://github.com/actually-useful-ai/platforms/releases/tag/v0.1.0
