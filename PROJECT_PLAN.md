# Project Plan

Maintainer: Luke Steuber  
Current suite version: 0.2.0

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

## Architecture

```text
suite.toml
    |
    +-- tools/generate_manifests.py --> client manifests + lock
    +-- tools/check_drift.py --> installed projection drift
    +-- src/platforms/ --> CLI + adapters + kdp pipeline
    +-- skills/ --> canonical skill prose
    +-- agents/ --> read-only agent definitions
```

## Outstanding

- Deeper device packaging (real `.pbw`/APK/ipk builds) once toolchains are present.
- Tizen/Vega packaging beyond preflight when SDKs and disk space allow.
- Public GitHub publish of `actually-useful-ai/platforms` after explicit approval.
- Cross-client installation verification on live Claude/Cursor/Codex roots.

## Out of scope

- Automated KDP or store login/submit
- Credentials, signing secrets, or vendor SDK copies in-repo
- Modifying Ambient Time uncommitted work
- Reuse of no-license third-party skill prose
