# Project Plan

Maintainer: Luke Steuber  
Current suite version: 0.3.0

## Objective

Build one canonical, portable suite for platform delivery and publishing workflows. The suite projects reviewed skills and read-only agents into supported clients and provides a deterministic CLI for detect → plan → doctor → build → validate → package → report, with human upload/submission gates.

## Completed milestones

### Control-plane bootstrap (0.1.0)

- `suite.toml` authority, schemas, generated manifests, lock, drift checks, provenance.

### Shared CLI and adapters (0.2.0)

- Typed `src/platforms/` package with secure process runner.
- Adapter contract for kdp, pebble, android, fire-tablet, fire-tv, android-tv, vega, webos, tizen, roku, web-kiosk.
- Explicit track states; later states are never inferred from earlier ones.
- KDP upload-bundle pipeline from `book.yml` (EPUB, cover geometry, validation, checklist; no submit).
- Canonical skill and agent prose for the full inventory.
- Ambient Time used read-only as an acceptance fixture for detection.

### Canonical skill consolidation (0.3.0)

- Consolidated 20 skill directories into nine canonical skills without dropping
  platform targets, adapter identities, accessibility gates, artifacts, or
  human-only submission boundaries.
- Preserved 15 legacy skill names as validated direct aliases in `suite.toml`
  and the deterministic manifest lock.
- Added a symlink-safe, dry-runnable, idempotent projection installer with
  per-client layouts, managed-state cleanup, and post-install drift checks.
- Split drift reporting into canonical content, alias destinations, and stale
  managed names.
- Hardened the release gate with schema-validated aliases, least-privilege skill
  tools, evidence-based build/validation/package transitions, and compatibility
  aliases across Claude, Codex, Cursor, and Agents.
- Added hostile-root/state rejection, rollback-safe projection replacement, and
  rollback-tested manifest-set generation.
- Added bounded initial adoption for exact same-name legacy Codex-to-Claude
  alias links, migrating them to canonical Claude targets.
- Added bounded adoption of non-Codex same-name links to real projections under
  another configured supported-client root.

### Drift-check correction and first full projection (unreleased)

- Fixed `check_drift.py` reporting clean whenever it received no installed
  roots, which made the documented verification command unable to fail.
- Projected the 0.3.0 skills into all four supported client roots. Claude and
  Agents had carried pre-consolidation prose since installation, with four
  skills loading under stub descriptions and no `allowed-tools`; Codex had no
  platform skills at all. Cursor, the only installer-managed root, was clean.
- All four roots now verify clean, and the 0.3.0 least-privilege frontmatter is
  in effect for every client.

## Architecture

```text
suite.toml
    |
    +-- tools/generate_manifests.py --> client manifests + lock
    +-- tools/install_projections.py --> safe client copies + links
    +-- tools/check_drift.py --> installed projection drift
    +-- src/platforms/ --> CLI + adapters + kdp pipeline
    +-- skills/ --> canonical skill prose
    +-- agents/ --> read-only agent definitions
```

## Outstanding

- Create and push the public GitHub repository `actually-useful-ai/platforms` once org create permissions are available for the active `gh` token (local `origin` is already configured).
- Deeper device packaging (real `.pbw`/APK/ipk builds) once toolchains are present.
- Tizen/Vega packaging beyond preflight when SDKs and disk space allow.
- Concrete builders for adapters that currently remain honestly `scaffolded`.
- Ongoing cross-client drift checks after canonical skill edits, now that the
  bare `check_drift.py` command detects drift instead of always passing.

## Out of scope

- Automated KDP or store login/submit
- Credentials, signing secrets, or vendor SDK copies in-repo
- Modifying Ambient Time uncommitted work
- Reuse of no-license third-party skill prose
