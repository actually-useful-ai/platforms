# File Purpose: Module entrypoint for `python -m platforms`.
# Primary Functions/Classes: module-level main delegation.
# Inputs/Outputs: Process argv in; exit code out.

from __future__ import annotations

import sys

from platforms.cli import main

if __name__ == "__main__":
    sys.exit(main())
