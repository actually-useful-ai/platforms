# Client installation

Canonical skills live in this repository under `skills/`. Installed copies are projections.

## Claude

Point the plugin/marketplace at this repository or copy `skills/*` into a managed Claude skills root, then run:

```sh
python3 tools/check_drift.py ~/.claude/skills
```

## Cursor

Install or sync skills into `~/.cursor/skills` (not `~/.cursor/skills-cursor`, which is managed separately and ignored by drift checks).

## Codex / agents

Use the generated `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` manifests. Compare projections with:

```sh
python3 tools/check_drift.py ~/.codex/skills
```

## Rule

Never edit installed projections and copy changes back. Edit canonical `skills/` here, regenerate manifests when `suite.toml` changes, then re-project.
