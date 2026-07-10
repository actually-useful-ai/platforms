# Repository Working Agreement

This repository is maintained by Luke Steuber.

## Required workflow

1. Read complete files before editing them.
2. Use strict test-first development for behavioral changes.
3. Run the focused RED test before implementation and record the expected failure.
4. Run the focused test and full suite after implementation.
5. Update `README.md`, `PROJECT_PLAN.md`, and `CHANGELOG.md` when project behavior or goals change.
6. Add a top-of-file banner to every Python file with File Purpose, Primary Functions/Classes, and Inputs/Outputs.

## Sources of truth

- `suite.toml` alone defines suite identity, version, author, repository, license, supported clients, and component inventory.
- `sources.lock.toml` pins evaluated upstream revisions and reuse boundaries.
- `skills/` will contain canonical skill prose after the bootstrap milestone.
- Installed skill directories are read-only projections.

## Generated-file policy

Never hand-edit:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.cursor-plugin/plugin.json`
- `.cursor-plugin/marketplace.json`
- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `dist/manifest.lock.json`

Change `suite.toml` and run `python3 tools/generate_manifests.py`. Generation must never create or edit `SKILL.md`.

## Verification

```sh
python3 -m unittest discover -s tests -v
python3 tools/generate_manifests.py --check
python3 tools/check_drift.py --help
```

Do not commit credentials, vendor SDKs, caches, installed projections, or content copied from no-license sources. Do not push unless Luke explicitly requests it.
