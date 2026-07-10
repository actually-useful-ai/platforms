# File Purpose: Package marker for Ambient Time and other acceptance fixtures.
# Primary Functions/Classes: re-exports ambient_time helpers.
# Inputs/Outputs: Import surface for tests and adapters.

from platforms.fixtures.ambient_time import (
    TEST_PACK_FACE_IDS,
    ambient_root,
    load_listed_platforms,
    manifest_face_ids,
    www_manifest_path,
)

__all__ = [
    "TEST_PACK_FACE_IDS",
    "ambient_root",
    "load_listed_platforms",
    "manifest_face_ids",
    "www_manifest_path",
]
