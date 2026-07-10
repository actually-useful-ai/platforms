# File Purpose: Registry of platform adapters keyed by stable platform id.
# Primary Functions/Classes: list_adapters, get_adapter.
# Inputs/Outputs: Platform id string in; PlatformAdapter instance out.

from __future__ import annotations

from platforms.adapters.base import PlatformAdapter
from platforms.adapters.platforms import (
    AndroidAdapter,
    AndroidTvAdapter,
    FireTabletAdapter,
    FireTvAdapter,
    KdpAdapter,
    PebbleAdapter,
    RokuAdapter,
    TizenAdapter,
    VegaAdapter,
    WebKioskAdapter,
    WebOsAdapter,
)

_ADAPTERS: tuple[PlatformAdapter, ...] = (
    KdpAdapter(),
    PebbleAdapter(),
    AndroidAdapter(),
    FireTabletAdapter(),
    FireTvAdapter(),
    AndroidTvAdapter(),
    VegaAdapter(),
    WebOsAdapter(),
    TizenAdapter(),
    RokuAdapter(),
    WebKioskAdapter(),
)

_BY_ID = {adapter.id: adapter for adapter in _ADAPTERS}


def list_adapters() -> tuple[PlatformAdapter, ...]:
    return _ADAPTERS


def get_adapter(platform_id: str) -> PlatformAdapter:
    try:
        return _BY_ID[platform_id]
    except KeyError as exc:
        raise KeyError(f"unknown platform adapter: {platform_id}") from exc
