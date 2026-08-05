#!/usr/bin/env bash
# File Purpose: Install repository git hooks that guard installed projection drift.
# Primary Functions/Classes: Thin installer; copies scripts/hooks/* into .git/hooks.
# Inputs/Outputs: Reads scripts/hooks/; writes executable hooks; --uninstall removes them.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/scripts/hooks"
TARGET="$(git -C "$ROOT" rev-parse --git-path hooks)"
TARGET="$(cd "$ROOT" && cd "$TARGET" && pwd)"

mkdir -p "$TARGET"

for hook in "$SOURCE"/*; do
    name="$(basename "$hook")"
    destination="$TARGET/$name"

    if [ "${1:-}" = "--uninstall" ]; then
        if [ -f "$destination" ] && grep -q "^# File Purpose:" "$destination" 2>/dev/null; then
            rm -f "$destination"
            echo "removed $name"
        else
            echo "skipped $name (not installed by this script)"
        fi
        continue
    fi

    # Never clobber a hook this script did not write. A global core.hooksPath
    # (git-lfs sets one) points here, so overwriting would affect every repo.
    if [ -e "$destination" ] && ! grep -q "^# File Purpose:" "$destination" 2>/dev/null; then
        echo "skipped $name: $destination already exists and was not written here." >&2
        if [ -n "$(git -C "$ROOT" config --get core.hooksPath || true)" ]; then
            echo "  core.hooksPath sends hooks to a shared directory, so installing" >&2
            echo "  would change every repository. Run the check directly instead:" >&2
            echo "    python3 tools/check_drift.py" >&2
        fi
        continue
    fi

    cp "$hook" "$destination"
    chmod +x "$destination"
    echo "installed $name"
done
