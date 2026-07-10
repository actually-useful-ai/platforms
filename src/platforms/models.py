# File Purpose: Shared typed models for platform detection, planning, and track state.
# Primary Functions/Classes: TrackState, Detection, Plan, DoctorReport, ArtifactBundle, EvidenceReport.
# Inputs/Outputs: Immutable dataclasses serialized to JSON-friendly dictionaries.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TrackState(str, Enum):
    """Explicit delivery states. Later states are never inferred from earlier ones."""

    SCAFFOLDED = "scaffolded"
    BUILT = "built"
    VALIDATED = "validated"
    DEVICE_TESTED = "device-tested"
    STORE_STAGED = "store-staged"
    SUBMITTED = "submitted"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Detection:
    platform_id: str
    matched: bool
    confidence: float
    reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "matched": self.matched,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Plan:
    platform_id: str
    track_state: TrackState
    steps: tuple[str, ...]
    output_root: Path
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "track_state": self.track_state.value,
            "steps": list(self.steps),
            "output_root": str(self.output_root),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DoctorReport:
    platform_id: str
    ready: bool
    findings: tuple[Finding, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "ready": self.ready,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class ArtifactBundle:
    platform_id: str
    track_state: TrackState
    artifacts: tuple[Path, ...]
    checksums: dict[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "track_state": self.track_state.value,
            "artifacts": [str(path) for path in self.artifacts],
            "checksums": dict(self.checksums),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class EvidenceReport:
    platform_id: str
    track_state: TrackState
    summary: str
    inferred_states: tuple[TrackState, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "track_state": self.track_state.value,
            "summary": self.summary,
            "inferred_states": [state.value for state in self.inferred_states],
            "details": dict(self.details),
        }
