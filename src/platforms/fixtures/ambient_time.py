# File Purpose: Ambient Time fixture constants and test-pack contract helpers.
# Primary Functions/Classes: ambient_root, load_listed_platforms, TEST_PACK_FACE_IDS.
# Inputs/Outputs: Optional Ambient Time path in; ids/targets out for tests and CLI docs.

from __future__ import annotations

from pathlib import Path

from platforms.adapters.base import read_platforms_yml

DEFAULT_AMBIENT = Path("/Users/luke/workspace/ambient-time")

# Keep in sync with ambient-time/appstores/build/catalog.mjs TEST_PACK_FACE_IDS.
TEST_PACK_FACE_IDS = (
    "tv-dial",
    "tv-cosmic",
    "tv-word-grid",
    "clk-binary",
)


def ambient_root(path: Path | None = None) -> Path:
    return (path or DEFAULT_AMBIENT).expanduser().resolve()


def load_listed_platforms(project: Path) -> list[str]:
    config = read_platforms_yml(project)
    platforms = config.get("platforms", [])
    return list(platforms) if isinstance(platforms, list) else []


def www_manifest_path(project: Path, *, test_pack: bool = False) -> Path:
    name = "www-test-pack" if test_pack else "www"
    return project / "appstores" / "dist" / name / "manifest.json"


def manifest_face_ids(manifest_path: Path) -> set[str]:
    import json

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {str(item["id"]) for item in payload.get("faces", []) if "id" in item}
