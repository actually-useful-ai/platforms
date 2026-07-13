# Changelog

All notable changes to the Platforms and Publishing Suite are documented here.

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
