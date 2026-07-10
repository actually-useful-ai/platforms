# Project Plan

Maintainer: Luke Steuber  
Current suite version: 0.1.0

## Objective

Build one canonical, portable suite for platform delivery and publishing workflows. The suite will project the same reviewed skills and read-only agents into supported clients without allowing installed copies or generated manifests to become competing sources of truth.

## Current milestone: control-plane bootstrap

Status: complete in version 0.1.0

- Define identity, support, and component inventory in `suite.toml`.
- Document the metadata model in `schemas/suite.schema.json`.
- Generate deterministic client and marketplace manifests.
- Generate a timestamp-free SHA-256 integrity lock.
- Detect installed projection drift without changing user files.
- Validate official client component shapes against enabled local exemplars.
- Fail closed on unsafe generated paths and unreadable canonical metadata.
- Pin evaluated source revisions and license boundaries.
- Establish strict test-first evidence and contributor guidance.

## Architecture

```text
suite.toml
    |
    +-- tools/generate_manifests.py
    |       +-- client manifests
    |       +-- marketplace manifests
    |       +-- dist/manifest.lock.json
    |
    +-- tools/check_drift.py
            +-- canonical skills/
            +-- optional installed roots (read-only)
```

Rules:

1. `suite.toml` is the sole metadata authority.
2. Generated JSON and the lock are committed but never hand-edited.
3. Supported-client subsets determine generated files, stale-file cleanup, and lock entries.
4. Client component fields use official relative directory paths or auto-discovery.
5. Generated writes remain inside the repository, reject symlinks, and replace files atomically.
6. Canonical skill prose will live under `skills/` when implementation begins.
7. Installed roots are projections, never inputs to generation.
8. Source content may be adapted only when its license permits reuse.
9. No-license and excluded material permits no reuse.

## Planned components

The canonical inventory contains 20 skills spanning intake, planning, store assets, accessibility, Pebble, Android and Amazon devices, television platforms, web kiosks, KDP, and EPUB. It also contains four read-only agents for reconnaissance, package auditing, TV accessibility review, and documentation curation.

The exact component identifiers belong in `suite.toml`; this document intentionally avoids duplicating that authority.

## Next milestones

- Write original canonical skill prose with accessibility requirements.
- Add the four read-only agent definitions.
- Validate each client’s installation and discovery behavior.
- Add packaging and release workflows after component content exists.
- Add end-to-end projection fixtures for supported clients.

## Out of scope for the bootstrap

- Vendor SDKs or generated SDK copies
- Credentials, secrets, signing assets, or store accounts
- Third-party code copied from no-license sources
- Functional skill or agent prose
- Publishing or pushing this repository
