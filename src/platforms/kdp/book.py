# File Purpose: Minimal book.yml parsing and validation for KDP manuscript projects.
# Primary Functions/Classes: BookMeta, load_book_yml, validate_book_meta.
# Inputs/Outputs: Path to book.yml in; BookMeta dataclass or ValueError out.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BookMeta:
    title: str
    slug: str
    version: str
    language: str
    contributors: tuple[str, ...]
    manuscript: Path
    trim_inches: tuple[float, float]
    page_count_estimate: int
    paper: str
    bleed_inches: float
    keywords: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    description: str = ""
    accessibility: dict[str, Any] = field(default_factory=dict)
    identifiers: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def output_dirname(self) -> str:
        return f"{self.slug}/{self.version}"


def load_book_yml(path: Path) -> BookMeta:
    """Parse a constrained book.yml without requiring PyYAML."""
    if not path.is_file():
        raise ValueError(f"book.yml not found: {path}")
    text = path.read_text(encoding="utf-8")
    data = _parse_simple_yaml(text)
    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("book.yml requires title")
    slug = str(data.get("slug") or _slugify(title))
    version = str(data.get("version", "0.1.0"))
    language = str(data.get("language", "en"))
    contributors = _as_str_tuple(data.get("contributors", ["Luke Steuber"]))
    manuscript_rel = str(data.get("manuscript", "manuscript.md"))
    manuscript = (path.parent / manuscript_rel).resolve()
    trim = data.get("trim_inches", [6.0, 9.0])
    if not isinstance(trim, list) or len(trim) != 2:
        raise ValueError("trim_inches must be [width, height]")
    page_count = int(data.get("page_count_estimate", 100))
    paper = str(data.get("paper", "white"))
    bleed = float(data.get("bleed_inches", 0.125))
    return BookMeta(
        title=title,
        slug=slug,
        version=version,
        language=language,
        contributors=contributors,
        manuscript=manuscript,
        trim_inches=(float(trim[0]), float(trim[1])),
        page_count_estimate=page_count,
        paper=paper,
        bleed_inches=bleed,
        keywords=_as_str_tuple(data.get("keywords", [])),
        categories=_as_str_tuple(data.get("categories", [])),
        description=str(data.get("description", "")),
        accessibility=dict(data.get("accessibility", {}) or {}),
        identifiers={str(k): str(v) for k, v in dict(data.get("identifiers", {}) or {}).items()},
        raw=data,
    )


def validate_book_meta(meta: BookMeta) -> list[str]:
    problems: list[str] = []
    if not meta.manuscript.is_file():
        problems.append(f"manuscript missing: {meta.manuscript}")
    if meta.page_count_estimate < 24:
        problems.append("page_count_estimate below typical KDP paperback minimum (24)")
    if meta.language.strip() == "":
        problems.append("language is empty")
    if not meta.contributors:
        problems.append("at least one contributor is required")
    return problems


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "book"


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a narrow YAML subset: scalars, inline lists, and one-level maps."""
    root: dict[str, Any] = {}
    current_map: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent >= 2 and current_map is not None and ":" in line:
            key, _, value = line.partition(":")
            mapping = root.setdefault(current_map, {})
            if not isinstance(mapping, dict):
                mapping = {}
                root[current_map] = mapping
            mapping[key.strip()] = _parse_scalar(value.strip())
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            current_map = key
            root[key] = {}
            continue
        current_map = None
        root[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for part in inner.split(","):
            items.append(_parse_scalar(part.strip()))
        return items
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
