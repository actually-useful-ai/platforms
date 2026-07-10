# Contributing

Luke Steuber maintains this suite and reviews contributions for portability, accessibility, provenance, and deterministic behavior.

## Development requirements

- Python 3.11 or newer
- Git
- No runtime dependencies for repository tools

Create a focused feature branch and use strict test-driven development:

1. Write the smallest test that describes the required behavior.
2. Run it and confirm the expected failure.
3. Implement the smallest production change.
4. Run the focused test and full suite.
5. Refactor only while the suite remains green.

Run the required checks:

```sh
python3 -m unittest discover -s tests -v
python3 tools/generate_manifests.py --check
python3 tools/check_drift.py --help
```

## Python file banners

Every new Python file must begin with comments documenting:

- File Purpose
- Primary Functions/Classes
- Inputs/Outputs

## Canonical metadata and generated files

Edit `suite.toml` for suite identity, version, author, repository, supported clients, or component inventory. Then run:

```sh
python3 tools/generate_manifests.py
```

Never hand-edit generated manifests or `dist/manifest.lock.json`. Commit the canonical edit and regenerated files together. The generator must never write `SKILL.md` prose.

Client component fields must follow enabled local exemplar conventions: use auto-discovery where supported or relative directory paths such as `./skills/`. Do not place component-name inventories in reserved client fields. Keep inventory in `suite.toml` and the generated lock.

Generated destinations must remain inside the repository. Do not weaken symlink rejection, atomic replacement, file-mode checks, or stale unsupported-client cleanup.

## Source and license policy

Pin evaluated sources in `sources.lock.toml` and explain attribution in `ATTRIBUTIONS.md`. Do not copy code, prose, media, or other protected content from a source without a compatible published license. No-license sources are research-only.

Do not commit credentials, signing material, vendor SDKs, caches, or installed projections.

## Accessibility

Contributions that affect user workflows must document keyboard, remote, switch, screen-reader, focus, contrast, motion, caption, and reflow implications where relevant. Tests and examples should use clear labels and avoid interaction patterns that depend on one input method.

## Documentation

Update `README.md`, `PROJECT_PLAN.md`, and `CHANGELOG.md` when behavior, setup, usage, architecture, or project status changes.
