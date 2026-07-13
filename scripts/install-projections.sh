#!/usr/bin/env bash
# File Purpose: Delegate projection installation to the validated Python installer.
# Primary Functions/Classes: Thin command-line wrapper only.
# Inputs/Outputs: Forwards all arguments to tools/install_projections.py.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tools/install_projections.py" --root "$ROOT" "$@"
