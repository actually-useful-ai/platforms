#!/usr/bin/env bash
# File Purpose: Project canonical platforms skills into local client skill roots.
# Primary Functions/Classes: sync_root helper; CLI entry.
# Inputs/Outputs: Reads skills/*; writes/updates matching directories under client roots.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANONICAL="$ROOT/skills"

usage() {
  cat <<'EOF'
Usage: scripts/install-projections.sh [--dry-run] [root ...]

Default roots:
  ~/.claude/skills
  ~/.cursor/skills
  ~/.codex/skills
  ~/.agents/skills

Only managed platforms skill directories are created or updated.
EOF
}

DRY_RUN=0
ROOTS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      ROOTS+=("$1")
      shift
      ;;
  esac
done

if [[ ${#ROOTS[@]} -eq 0 ]]; then
  ROOTS=(
    "$HOME/.claude/skills"
    "$HOME/.cursor/skills"
    "$HOME/.codex/skills"
    "$HOME/.agents/skills"
  )
fi

sync_root() {
  local dest="$1"
  mkdir -p "$dest"
  local skill
  for skill in "$CANONICAL"/*/SKILL.md; do
    local name
    name="$(basename "$(dirname "$skill")")"
    local target="$dest/$name"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "would sync $name -> $target"
      continue
    fi
    mkdir -p "$target"
    # Replace managed projection contents with canonical copy.
    rm -rf "$target"
    mkdir -p "$target"
    cp -R "$CANONICAL/$name/." "$target/"
    echo "synced $name -> $target"
  done
}

for root in "${ROOTS[@]}"; do
  echo "## $root"
  sync_root "$root"
done

if [[ "$DRY_RUN" -eq 0 ]]; then
  PYTHONPATH="$ROOT/tools:$ROOT" python3 "$ROOT/tools/check_drift.py" "${ROOTS[@]}"
fi
