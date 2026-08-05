# File Purpose: Concrete platform adapters for device and publishing targets.
# Primary Functions/Classes: KdpAdapter and device-family BaseAdapter subclasses.
# Inputs/Outputs: Project paths in; Detection/Plan/Doctor/Artifact/Evidence models out.

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from platforms.adapters.base import (
    BaseAdapter,
    ensure_output_root,
    read_platforms_yml,
    sha256_file,
)
from platforms.models import (
    ArtifactBundle,
    Detection,
    DoctorReport,
    Finding,
    Plan,
    TrackState,
)
from platforms.process import ProcessResult, run_allowlisted

_CLI_TIMEOUT = 600.0


def _cli_detail(result: ProcessResult) -> str:
    """Summarize a failed CLI invocation without leaking a whole log."""

    stream = result.stderr.strip() or result.stdout.strip()
    line = next((entry for entry in stream.splitlines() if entry.strip()), "")
    return line.strip()[:200] if line else f"exit status {result.returncode}"


class KdpAdapter(BaseAdapter):
    id = "kdp"
    display_name = "Kindle Direct Publishing"
    markers = ("book.yml",)
    config_keys = ("book",)
    required_tools = ()

    def detect(self, project: Path) -> Detection:
        base = super().detect(project)
        reasons = list(base.reasons)
        score = base.confidence
        if (project / "book.yml").is_file():
            reasons.append("found book.yml")
            score = min(score + 0.5, 1.0)
        return Detection(
            platform_id=self.id,
            matched=base.matched or (project / "book.yml").is_file(),
            confidence=score,
            reasons=tuple(reasons),
            metadata=base.metadata,
        )

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        report = super().doctor(project, plan)
        findings = list(report.findings)
        from platforms.adapters.base import _which

        for tool, severity, hint in (
            ("pandoc", "warning", "Install Pandoc for higher-fidelity EPUB3 conversion"),
            ("typst", "warning", "Install Typst for print interior PDF generation"),
            ("epubcheck", "warning", "Install EPUBCheck for EPUB structural validation"),
            ("ace", "warning", "Install Ace by DAISY for EPUB accessibility reports"),
        ):
            if not _which(tool):
                findings.append(
                    Finding(
                        code=f"missing-{tool}",
                        severity=severity,
                        message=f"Tool not found on PATH: {tool}",
                        remediation=hint,
                    )
                )
        if not (project / "book.yml").is_file():
            findings.append(
                Finding(
                    code="missing-book-yml",
                    severity="error",
                    message="book.yml is required for KDP builds",
                    remediation="Create book.yml with title, contributors, and accessibility metadata",
                )
            )
        ready = not any(finding.severity == "error" for finding in findings)
        return DoctorReport(platform_id=self.id, ready=ready, findings=tuple(findings))

    def build(self, project: Path, plan: Plan) -> ArtifactBundle:
        if not (project / "book.yml").is_file():
            return super().build(project, plan)
        from platforms.kdp import build_upload_bundle

        return build_upload_bundle(project)

    def validate(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        if bundle.platform_id != "kdp":
            return super().validate(project, bundle)
        # build_upload_bundle already validates; preserve its track state.
        if not bundle.artifacts:
            return super().validate(project, bundle)
        return bundle

    def package(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        if (project / "book.yml").is_file():
            from platforms.kdp import package_upload_bundle

            return package_upload_bundle(project, bundle)
        return super().package(project, bundle)


class PebbleAdapter(BaseAdapter):
    id = "pebble"
    display_name = "Pebble"
    markers = (
        "package.json",
        "src/rocky",
        "wscript",
        "appstores/pebble",
        "appstores/pebble/golden-hour/package.json",
    )
    required_tools = (("pebble", "Install the Pebble/rePebble SDK and CLI"),)

    def detect(self, project: Path) -> Detection:
        detection = super().detect(project)
        golden = project / "appstores/pebble/golden-hour"
        if golden.is_dir():
            reasons = detection.reasons + ("found Ambient Time Golden Hour fixture path",)
            return Detection(
                platform_id=self.id,
                matched=True,
                confidence=min(detection.confidence + 0.3, 1.0),
                reasons=reasons,
                metadata={**detection.metadata, "fixture": str(golden)},
            )
        return detection


class AndroidAdapter(BaseAdapter):
    id = "android"
    display_name = "Android"
    markers = (
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "app/src/main/AndroidManifest.xml",
        "appstores/android/package.json",
        "appstores/android/capacitor.config.json",
    )
    required_tools = (
        ("adb", "Install Android platform-tools"),
        ("java", "Install a supported JDK (17-21 recommended)"),
    )


class FireTabletAdapter(BaseAdapter):
    id = "fire-tablet"
    display_name = "Fire Tablet"
    markers = (
        "app/src/main/AndroidManifest.xml",
        "appstores/android/capacitor.config.json",
    )
    required_tools = (("adb", "Install Android platform-tools for Fire tablet sideload"),)


class FireTvAdapter(BaseAdapter):
    id = "fire-tv"
    display_name = "Fire TV"
    markers = (
        "app/src/main/AndroidManifest.xml",
        "appstores/android/capacitor.config.json",
    )
    required_tools = (("adb", "Install Android platform-tools for Fire TV sideload"),)

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        report = super().doctor(project, plan)
        findings = list(report.findings)
        manifests = list(project.glob("**/AndroidManifest.xml"))
        if manifests:
            text = manifests[0].read_text(encoding="utf-8", errors="replace")
            if "LEANBACK_LAUNCHER" not in text and "leanback" not in text.lower():
                findings.append(
                    Finding(
                        code="missing-leanback",
                        severity="warning",
                        message="AndroidManifest.xml does not mention Leanback launcher intent",
                        remediation="Declare LEANBACK_LAUNCHER for TV launcher visibility",
                    )
                )
        return DoctorReport(
            platform_id=self.id,
            ready=not any(f.severity == "error" for f in findings),
            findings=tuple(findings),
        )


class AndroidTvAdapter(FireTvAdapter):
    id = "android-tv"
    display_name = "Android TV"


class VegaAdapter(BaseAdapter):
    id = "vega"
    display_name = "Vega"
    markers = ("package.json",)
    required_tools = (("kepler", "Install the Vega/Kepler CLI when disk space allows (~20 GB)"),)

    def detect(self, project: Path) -> Detection:
        # Explicit selection only until detection is reliable.
        config = read_platforms_yml(project)
        configured = self.id in set(config.get("platforms", []))
        reasons = ("explicit platforms.yml selection required for vega",)
        return Detection(
            platform_id=self.id,
            matched=configured,
            confidence=0.9 if configured else 0.0,
            reasons=reasons if configured else ("vega not explicitly selected",),
            metadata={"project": config.get("project", project.name)},
        )

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        report = super().doctor(project, plan)
        findings = list(report.findings)
        architecture = read_platforms_yml(project).get("vega_architecture")
        if architecture not in {"native", "webview"}:
            findings.append(
                Finding(
                    code="missing-vega-architecture",
                    severity="error",
                    message="Vega requires an explicit native or webview architecture decision",
                    remediation="Set vega_architecture: native or webview in platforms.yml",
                )
            )
        return DoctorReport(
            platform_id=self.id,
            ready=not any(finding.severity == "error" for finding in findings),
            findings=tuple(findings),
        )


class WebOsAdapter(BaseAdapter):
    id = "webos"
    display_name = "webOS"
    markers = (
        "appinfo.json",
        "www/index.html",
        "appstores/webos/appinfo.json.tmpl",
        "appstores/dist/webos/appinfo.json",
    )
    required_tools = (("ares-package", "Install the webOS CLI / ares-package tooling"),)

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        report = super().doctor(project, plan)
        findings = list(report.findings)
        candidates = (
            project / "appinfo.json",
            project / "appstores/dist/webos/appinfo.json",
        )
        appinfo_path = next((path for path in candidates if path.is_file()), None)
        appinfo: dict[str, object] = {}
        if appinfo_path is not None:
            try:
                parsed = json.loads(appinfo_path.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    appinfo = parsed
            except json.JSONDecodeError:
                findings.append(
                    Finding(
                        code="invalid-webos-appinfo",
                        severity="error",
                        message="webOS appinfo.json is not valid JSON",
                    )
                )
        if not isinstance(appinfo.get("version"), str) or not appinfo["version"]:
            findings.append(
                Finding(
                    code="missing-webos-version",
                    severity="error",
                    message="webOS appinfo.json must declare a non-empty version",
                )
            )
        icon = appinfo.get("icon")
        if (
            appinfo_path is None
            or not isinstance(icon, str)
            or not icon
            or not (appinfo_path.parent / icon).is_file()
        ):
            findings.append(
                Finding(
                    code="missing-webos-icon",
                    severity="error",
                    message="webOS appinfo.json must reference an existing icon",
                )
            )
        return DoctorReport(
            platform_id=self.id,
            ready=not any(finding.severity == "error" for finding in findings),
            findings=tuple(findings),
        )


class TizenAdapter(BaseAdapter):
    id = "tizen"
    display_name = "Tizen"
    markers = (
        "config.xml",
        "www/index.html",
        "appstores/tizen/config.xml.tmpl",
        "appstores/dist/tizen/config.xml",
    )
    required_tools = (("tizen", "Install Tizen Studio and add the tizen CLI to PATH"),)

    def app_root(self, project: Path) -> Path | None:
        """Return the widget root holding config.xml, or None when absent."""

        for candidate in (project, project / "www"):
            if (candidate / "config.xml").is_file():
                return candidate
        return None

    def _blocked(self, *notes: str) -> ArtifactBundle:
        return ArtifactBundle(
            platform_id=self.id,
            track_state=TrackState.SCAFFOLDED,
            artifacts=(),
            checksums={},
            notes=tuple(note for note in notes if note),
        )

    def build(self, project: Path, plan: Plan) -> ArtifactBundle:
        """Build and package a Tizen widget through the tizen CLI."""

        source = self.app_root(project)
        if source is None:
            return self._blocked("tizen build blocked: config.xml is missing")

        from platforms.adapters.base import _which

        if not _which("tizen"):
            return self._blocked(
                "tizen build blocked: the tizen CLI is not on PATH; "
                "no build evidence produced"
            )

        output_root = ensure_output_root(project, self.id)
        allowed_roots = [project.resolve()]

        compiled = run_allowlisted(
            ["tizen", "build-web"],
            cwd=source,
            allowed_roots=allowed_roots,
            timeout=_CLI_TIMEOUT,
        )
        if compiled.returncode != 0:
            return self._blocked("tizen build-web failed", _cli_detail(compiled))

        packaged = run_allowlisted(
            ["tizen", "package", "-t", "wgt", "-o", str(output_root), "--", ".buildResult"],
            cwd=source,
            allowed_roots=allowed_roots,
            timeout=_CLI_TIMEOUT,
        )
        if packaged.returncode != 0:
            return self._blocked(
                "tizen package failed; signing requires an active security profile",
                _cli_detail(packaged),
            )

        widgets = sorted(path for path in output_root.glob("*.wgt") if path.is_file())
        if not widgets:
            return self._blocked(
                "tizen package reported success but produced no .wgt; "
                "no build evidence produced"
            )

        return ArtifactBundle(
            platform_id=self.id,
            track_state=TrackState.BUILT,
            artifacts=tuple(widgets),
            checksums={str(path): sha256_file(path) for path in widgets},
            notes=("tizen widget built and signed through the tizen CLI",),
        )


class RokuAdapter(BaseAdapter):
    id = "roku"
    display_name = "Roku"
    markers = ("manifest", "source/main.brs", "components")
    required_tools = ()

    def doctor(self, project: Path, plan: Plan) -> DoctorReport:
        report = super().doctor(project, plan)
        findings = list(report.findings)
        if not (project / "manifest").is_file() and not (project / "source").is_dir():
            findings.append(
                Finding(
                    code="roku-native-required",
                    severity="warning",
                    message="Roku targets need a BrightScript/SceneGraph project, not a web wrapper",
                    remediation="Scaffold a native Roku channel for selected faces",
                )
            )
        return DoctorReport(
            platform_id=self.id,
            ready=not any(f.severity == "error" for f in findings),
            findings=tuple(findings),
        )


class WebKioskAdapter(BaseAdapter):
    id = "web-kiosk"
    display_name = "Web Kiosk"
    markers = (
        "www/index.html",
        "index.html",
        "appstores/dist/www/index.html",
    )
    required_tools = ()


    def build(self, project: Path, plan: Plan) -> ArtifactBundle:
        source = project / "www" if (project / "www/index.html").is_file() else project
        index = source / "index.html"
        if not index.is_file():
            return ArtifactBundle(
                platform_id=self.id,
                track_state=TrackState.SCAFFOLDED,
                artifacts=(),
                notes=("web kiosk build blocked: index.html is missing",),
            )
        output_root = ensure_output_root(project, self.id)
        archive_path = output_root / "web-kiosk.zip"
        files = [
            path
            for path in sorted(source.rglob("*"))
            if path.is_file()
            and "dist" not in path.relative_to(source).parts
            and not any(part.startswith(".") for part in path.relative_to(source).parts)
        ]
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                relative = path.relative_to(source).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        return ArtifactBundle(
            platform_id=self.id,
            track_state=TrackState.BUILT,
            artifacts=(archive_path,),
            checksums={str(archive_path): sha256_file(archive_path)},
            notes=("deterministic offline web kiosk archive built",),
        )

    def validate(self, project: Path, bundle: ArtifactBundle) -> ArtifactBundle:
        base = super().validate(project, bundle)
        if base.track_state is not TrackState.VALIDATED:
            return base
        archive_path = next(
            (path for path in bundle.artifacts if path.suffix.lower() == ".zip"),
            None,
        )
        problems: list[str] = []
        if archive_path is None:
            problems.append("web kiosk validation requires a zip artifact")
        else:
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    if archive.testzip() is not None:
                        problems.append("web kiosk zip contains a corrupt member")
                    if "index.html" not in archive.namelist():
                        problems.append("web kiosk zip is missing index.html")
                    else:
                        html = archive.read("index.html").decode("utf-8", errors="replace")
                        lowered = html.lower()
                        for requirement, marker in (
                            ("document language", " lang="),
                            ("document title", "<title"),
                            ("main landmark", "<main"),
                        ):
                            if marker not in lowered:
                                problems.append(f"index.html is missing {requirement}")
                        if "http://" in lowered or "https://" in lowered:
                            problems.append("index.html contains a network URL")
            except (OSError, zipfile.BadZipFile):
                problems.append("web kiosk zip cannot be opened")
        if not problems:
            return base
        return ArtifactBundle(
            platform_id=bundle.platform_id,
            track_state=TrackState.BUILT,
            artifacts=bundle.artifacts,
            checksums=dict(bundle.checksums),
            notes=base.notes + tuple(problems),
        )
