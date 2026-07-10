# File Purpose: Concrete platform adapters for device and publishing targets.
# Primary Functions/Classes: KdpAdapter and device-family BaseAdapter subclasses.
# Inputs/Outputs: Project paths in; Detection/Plan/Doctor/Artifact/Evidence models out.

from __future__ import annotations

from pathlib import Path

from platforms.adapters.base import BaseAdapter, read_platforms_yml
from platforms.models import (
    ArtifactBundle,
    Detection,
    DoctorReport,
    Finding,
    Plan,
)


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
