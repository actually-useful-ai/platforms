# Changelog

All notable changes to the Platforms and Publishing Suite are documented here.

## [0.2.0] - 2026-07-10

### Added

- Typed `src/platforms` package with `detect`, `plan`, `doctor`, `build`, `validate`, `package`, `report`, and `drift` commands.
- Secure allowlisted process runner (`shell=False`, argv safety, optional root confinement).
- Platform adapters for KDP, Pebble, Android family, Vega, webOS, Tizen, Roku, and web kiosk.
- KDP upload-bundle pipeline from `book.yml` (EPUB3, cover geometry, metadata, checksums, checklist).
- Canonical prose for all 20 skills and four read-only agents.
- Example KDP sample, book schema, platform matrix, accessibility, and adding-a-platform docs.
- Ambient Time read-only fixture detection tests.

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

[0.2.0]: https://github.com/actually-useful-ai/platforms/releases/tag/v0.2.0
[0.1.0]: https://github.com/actually-useful-ai/platforms/releases/tag/v0.1.0
