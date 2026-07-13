# Client installation

Canonical skills live in this repository under `skills/`. Installed copies are projections.

## Local projection sync

From the repository root:

```sh
./scripts/install-projections.sh --dry-run
./scripts/install-projections.sh
```

Default destinations:

- `~/.claude/skills`
- `~/.cursor/skills`
- `~/.codex/skills`
- `~/.agents/skills`

The shell script is a thin wrapper around `tools/install_projections.py`. The
installer validates and stages all canonical input before destination mutation,
tracks only names it manages, and removes a stale name only when a prior state
file recorded it.

Client layouts are intentionally different:

- Claude: canonical read-only copies and sibling-relative legacy aliases.
- Codex: direct absolute canonical and legacy links to Claude canonical copies.
- Cursor and Agents: canonical read-only copies and sibling-relative legacy aliases.

The operation is idempotent and refuses ancestor symlinks, unexpected managed
symlinks, path-like managed-state names, overlapping client roots, or
non-directory managed destinations. Every replacement is prepared beside its
destination; if commit fails, the prior entry is restored and staging is
removed. During initial adoption without managed state, the installer recognizes
an exact Codex legacy alias link to the matching Claude legacy alias. For other
clients, it also recognizes a same-name link to a real directory directly under
another configured supported-client root. These entries migrate through the
normal backup-safe copy or alias replacement path; missing, nested, escaped,
symlinked, or mismatched targets remain errors. `--dry-run` reports actions
without creating any root.

Safety is per managed entry, not a cross-filesystem transaction. A process or
machine failure after one entry commits can leave later entries pending; rerun
the installer safely to converge. Roots on separate filesystems cannot be
committed atomically as one operation.

To review against temporary roots without touching client configuration:

```sh
tmp="$(mktemp -d)"
python3 tools/install_projections.py --dry-run \
  --claude-root "$tmp/claude" --codex-root "$tmp/codex" \
  --cursor-root "$tmp/cursor" --agents-root "$tmp/agents"
rm -rf "$tmp"
```

## Claude

Point the plugin/marketplace at this repository or sync with the installer above, then run:

```sh
python3 tools/check_drift.py ~/.claude/skills
```

## Cursor

Install or sync skills into `~/.cursor/skills` (not `~/.cursor/skills-cursor`, which is managed separately and ignored by drift checks).

## Codex / agents

Use the generated `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` manifests. Codex aliases resolve to Claude canonical projections; Agents receives canonical copies and aliases. Compare projections with:

```sh
python3 tools/check_drift.py ~/.codex/skills
```

## Rule

Never edit installed projections and copy changes back. Edit canonical `skills/` here, regenerate manifests when `suite.toml` changes, then re-project.
