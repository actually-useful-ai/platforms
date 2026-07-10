# File Purpose: Common platform adapter protocol and shared helper utilities.
# Primary Functions/Classes: PlatformAdapter, BaseAdapter, read_platforms_yml, sha256_file.
# Inputs/Outputs: Project Path in; Detection/Plan/Doctor/Artifact/Evidence models out.

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from platforms.models import (
    ArtifactBundle,
    Detection,
    DoctorReport,
    EvidenceReport,
    Finding,
    Plan,
    TrackState,
)

_PLATFORM_LINE = re.compile(r"^\s*platforms\s*:\s*\[([^\]]*)\]\s*$", re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_platforms_yml(project: Path) -> dict[str, Any]:
    """Parse a minimal platforms.yml without requiring PyYAML."""
    path = project / "platforms.yml"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    result: dict[str, Any] = {"raw": text}
    for line in text.splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "platforms" and value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            result["platforms"] = [
                item.strip().strip("'\"") for item in inner.split(",") if item.strip()
            ]
        elif key and value:
            result[key] = value.strip("'\"")
    match = _PLATFORM_LINE.search(text)
    if match and "platforms" not in result:
        inner = match.group(1).strip()
        result["platforms"] = [
            item.strip().strip("'\"") for item in inner.split(",") if item.strip()
        ]
    return result


def ensure_output_root(project: Path, platform_id: str) -> Path:
    root = (project / "dist" / "platforms" / platform_id).resolve()
    try:
        root.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"output root escapes project: {root}") from exc
    root.mkdir(parents=True, exist_ok=True)
    return root


class PlatformAdapter(ABC):
    """Contract every platform adapter must implement."""

    id: str
    display_name: str

    @abstractmethod
    def detect(self, project: Path) -> Detection:
        raise NotImplementedError

    @abstractmethod
    def plan(self, project: Path, detection: Detection) -> Plan:
        raise NotImplementedError

    @abstractmethod
    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        raise NotImplementedError

    @abstractmethod
    def build(self, project: Path, plan: Plan) -> ArtifactBundle:
        raise NotImplementedError

    @abstractmethod
    def validate(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        raise NotImplementedError

    @abstractmethod
    def package(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        raise NotImplementedError

    @abstractmethod
    def report(self, project: Path, bundle: Plan | ArtifactBundle) -> EvidenceReport:
        raise NotImplementedError


class BaseAdapter(PlatformAdapter):
    """Default adapter behavior for scaffolded platforms."""

    id = "base"
    display_name = "Base"
    markers: tuple[str, ...] = ()
    config_keys: tuple[str, ...] = ()
    required_tools: tuple[tuple[str, str], ...] = ()

    def detect(self, project: Path) -> Detection:
        config = read_platforms_yml(project)
        configured = self.id in set(config.get("platforms", []))
        reasons: list[str] = []
        score = 0.0
        if configured:
            reasons.append(f"listed in platforms.yml as {self.id}")
            score += 0.6
        for marker in self.markers:
            if (project / marker).exists():
                reasons.append(f"found marker {marker}")
                score += 0.2
        for key in self.config_keys:
            if key in config:
                reasons.append(f"found config key {key}")
                score += 0.1
        marker_hit = any(reason.startswith("found marker ") for reason in reasons)
        matched = configured or marker_hit or score >= 0.4
        return Detection(
            platform_id=self.id,
            matched=matched,
            confidence=min(score, 1.0),
            reasons=tuple(reasons),
            metadata={"project": config.get("project", project.name)},
        )

    def plan(self, project: Path, detection: Detection) -> Plan:
        output_root = ensure_output_root(project, self.id)
        steps = (
            "doctor toolchain",
            "build artifacts into dist/platforms/<id>",
            "validate package constraints",
            "stage store package",
            "emit evidence report for human upload/submission",
        )
        notes = detection.reasons
        if self.id == "vega":
            notes = notes + ("vega requires explicit selection until detection is reliable",)
        return Plan(
            platform_id=self.id,
            track_state=TrackState.SCAFFOLDED,
            steps=steps,
            output_root=output_root,
            notes=notes,
        )

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        findings: list[Finding] = []
        for tool, hint in self.required_tools:
            if not _which(tool):
                findings.append(
                    Finding(
                        code=f"missing-{tool}",
                        severity="error",
                        message=f"Required tool not found on PATH: {tool}",
                        remediation=hint,
                    )
                )
        if not (project / "platforms.yml").is_file():
            findings.append(
                Finding(
                    code="missing-platforms-yml",
                    severity="warning",
                    message="platforms.yml is missing; detection confidence will be low",
                    remediation="Add platforms.yml listing target platform ids",
                )
            )
        ready = not any(finding.severity == "error" for finding in findings)
        return DoctorReport(
            platform_id=self.id,
            ready=ready,
            findings=tuple(findings),
        )

    def build(self, project: Path, plan: Plan) -> ArtifactBundle:
        output_root = ensure_output_root(project, self.id)
        marker = output_root / "BUILD_STUB.txt"
        marker.write_text(
            f"Platform {self.id} build stub for {project.name}\n"
            "Replace with deterministic platform packaging in later milestones.\n",
            encoding="utf-8",
        )
        return ArtifactBundle(
            platform_id=self.id,
            track_state=TrackState.BUILT,
            artifacts=(marker,),
            checksums={str(marker): sha256_file(marker)},
            notes=("stub build; platform-specific packaging pending",),
        )

    def validate(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        missing = [path for path in bundle.artifacts if not path.exists()]
        notes = list(bundle.notes)
        if missing:
            notes.append(f"missing artifacts: {', '.join(str(path) for path in missing)}")
            state = TrackState.BUILT
        else:
            notes.append("stub validation passed for existing artifacts")
            state = TrackState.VALIDATED
        return ArtifactBundle(
            platform_id=bundle.platform_id,
            track_state=state,
            artifacts=bundle.artifacts,
            checksums=dict(bundle.checksums),
            notes=tuple(notes),
        )

    def package(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        output_root = ensure_output_root(project, self.id)
        checklist = output_root / "UPLOAD_CHECKLIST.md"
        checklist.write_text(
            f"# {self.display_name} upload checklist\n\n"
            "- Review artifacts under dist/platforms/\n"
            "- Confirm signing and store metadata manually\n"
            "- Do not treat this suite as an automated submitter\n",
            encoding="utf-8",
        )
        artifacts = tuple(dict.fromkeys([*bundle.artifacts, checklist]))
        checksums = dict(bundle.checksums)
        checksums[str(checklist)] = sha256_file(checklist)
        return ArtifactBundle(
            platform_id=bundle.platform_id,
            track_state=TrackState.STORE_STAGED,
            artifacts=artifacts,
            checksums=checksums,
            notes=bundle.notes + ("store staging checklist written; submission remains manual",),
        )

    def report(self, project: Path, bundle: Plan | ArtifactBundle) -> EvidenceReport:
        if isinstance(bundle, Plan):
            state = bundle.track_state
            details = bundle.to_dict()
        else:
            state = bundle.track_state
            details = bundle.to_dict()
        return EvidenceReport(
            platform_id=self.id,
            track_state=state,
            summary=f"{self.display_name} track is {state.value}",
            inferred_states=(state,),
            details=details,
        )


def _which(tool: str) -> bool:
    for directory in os_path_dirs():
        candidate = Path(directory) / tool
        if candidate.is_file() and os_access_executable(candidate):
            return True
    return False


def os_path_dirs() -> list[str]:
    import os

    return [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]


def os_access_executable(path: Path) -> bool:
    import os

    return os.access(path, os.X_OK)
