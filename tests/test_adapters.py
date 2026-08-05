# File Purpose: Verify the shared platform adapter contract and registry behavior.
# Primary Functions/Classes: AdapterContractTests.
# Inputs/Outputs: Uses temporary project roots; asserts detect/plan/doctor/build/validate/package/report shapes.

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from platforms.adapters.registry import get_adapter, list_adapters
from platforms.models import ArtifactBundle, TrackState
from platforms.process import ProcessResult


class AdapterContractTests(unittest.TestCase):
    def make_project(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [web-kiosk]\n",
            encoding="utf-8",
        )
        (root / "www").mkdir()
        (root / "www/index.html").write_text(
            "<!doctype html><html lang=\"en\"><head><title>Fixture</title></head>"
            "<body><a href=\"#main\">Skip</a><main id=\"main\" tabindex=\"-1\">"
            "<h1>Fixture</h1></main></body></html>\n",
            encoding="utf-8",
        )
        return root

    def test_registry_exposes_expected_adapters(self) -> None:
        ids = {adapter.id for adapter in list_adapters()}
        expected = {
            "kdp",
            "pebble",
            "android",
            "fire-tablet",
            "fire-tv",
            "android-tv",
            "vega",
            "webos",
            "tizen",
            "roku",
            "web-kiosk",
        }
        self.assertTrue(expected.issubset(ids))

    def test_unknown_adapter_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_adapter("not-a-platform")

    def test_web_kiosk_adapter_round_trip(self) -> None:
        root = self.make_project()
        adapter = get_adapter("web-kiosk")
        detection = adapter.detect(root)
        self.assertTrue(detection.matched or detection.confidence >= 0.0)
        plan = adapter.plan(root, detection)
        self.assertEqual(plan.platform_id, "web-kiosk")
        self.assertEqual(plan.track_state, TrackState.SCAFFOLDED)
        doctor = adapter.doctor(root, plan)
        self.assertIsInstance(doctor.findings, (list, tuple))
        built = adapter.build(root, plan)
        self.assertEqual(built.track_state, TrackState.BUILT)
        self.assertFalse(any(path.name == "BUILD_STUB.txt" for path in built.artifacts))
        archive = next(path for path in built.artifacts if path.suffix == ".zip")
        with zipfile.ZipFile(archive) as package:
            self.assertIn("index.html", package.namelist())
        validated = adapter.validate(root, built)
        self.assertEqual(validated.track_state, TrackState.VALIDATED)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.STORE_STAGED)
        report = adapter.report(root, packaged)
        self.assertIn("Web Kiosk", report.summary)
        self.assertNotIn(TrackState.SUBMITTED, report.inferred_states)

    def test_stub_or_missing_evidence_cannot_advance_track_state(self) -> None:
        root = self.make_project()
        adapter = get_adapter("android")
        plan = adapter.plan(root, adapter.detect(root))

        built = adapter.build(root, plan)
        self.assertEqual(built.track_state, TrackState.SCAFFOLDED)
        self.assertFalse(any(path.name == "BUILD_STUB.txt" for path in built.artifacts))

        fake_stub = root / "BUILD_STUB.txt"
        fake_stub.write_text("not a package\n", encoding="utf-8")
        untrusted = ArtifactBundle(
            platform_id="android",
            track_state=TrackState.BUILT,
            artifacts=(fake_stub,),
        )
        validated = adapter.validate(root, untrusted)
        self.assertEqual(validated.track_state, TrackState.BUILT)
        packaged = adapter.package(root, validated)
        self.assertEqual(packaged.track_state, TrackState.BUILT)
        self.assertFalse(any(path.name == "UPLOAD_CHECKLIST.md" for path in packaged.artifacts))

    def test_vega_requires_explicit_architecture_and_webos_metadata(self) -> None:
        root = self.make_project()
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [vega, webos]\n",
            encoding="utf-8",
        )
        vega = get_adapter("vega")
        vega_plan = vega.plan(root, vega.detect(root))
        vega_codes = {finding.code for finding in vega.doctor(root, vega_plan).findings}
        self.assertIn("missing-vega-architecture", vega_codes)

        (root / "appinfo.json").write_text('{"id": "com.example.fixture"}\n', encoding="utf-8")
        webos = get_adapter("webos")
        webos_plan = webos.plan(root, webos.detect(root))
        webos_codes = {finding.code for finding in webos.doctor(root, webos_plan).findings}
        self.assertIn("missing-webos-version", webos_codes)
        self.assertIn("missing-webos-icon", webos_codes)

    def make_tizen_project(self) -> Path:
        root = self.make_project()
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [tizen]\n",
            encoding="utf-8",
        )
        (root / "config.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<widget xmlns="http://www.w3.org/ns/widgets" '
            'id="http://example.com/fixture" version="1.0.0">\n'
            "  <name>Fixture</name>\n"
            '  <content src="index.html"/>\n'
            "</widget>\n",
            encoding="utf-8",
        )
        (root / "index.html").write_text(
            '<!doctype html><html lang="en"><head><title>Fixture</title></head>'
            '<body><main id="main"><h1>Fixture</h1></main></body></html>\n',
            encoding="utf-8",
        )
        return root

    def test_tizen_build_without_config_xml_stays_scaffolded(self) -> None:
        root = self.make_project()
        adapter = get_adapter("tizen")
        built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(built.artifacts, ())
        self.assertTrue(any("config.xml" in note for note in built.notes))

    def test_tizen_build_without_cli_reports_missing_toolchain(self) -> None:
        root = self.make_tizen_project()
        adapter = get_adapter("tizen")
        with mock.patch("platforms.adapters.base._which", return_value=False):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(built.artifacts, ())
        self.assertTrue(any("tizen" in note for note in built.notes))

    @staticmethod
    def _packaging_runner(calls: list[tuple[str, ...]]):
        def fake_run(argv, *, cwd, allowed_roots=None, env=None, timeout=None):
            calls.append(tuple(argv))
            destination = Path(argv[argv.index("-o") + 1])
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "Fixture.wgt").write_bytes(b"PK\x03\x04fixture-widget")
            return ProcessResult(argv=tuple(argv), returncode=0, stdout="", stderr="")

        return fake_run

    def test_tizen_build_produces_a_signed_wgt_package(self) -> None:
        root = self.make_tizen_project()
        adapter = get_adapter("tizen")
        calls: list[tuple[str, ...]] = []

        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted",
            side_effect=self._packaging_runner(calls),
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.BUILT)
        wgt = next(path for path in built.artifacts if path.suffix == ".wgt")
        self.assertTrue(wgt.is_file())
        self.assertIn(str(wgt), built.checksums)
        # A staged widget is packaged as-is; build-web is a source-tree step and
        # must not be required, since it needs the Web CLI package.
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ("tizen", "package"))
        self.assertNotIn("build-web", [part for call in calls for part in call])

    def test_tizen_build_finds_the_staged_appstores_widget_root(self) -> None:
        root = self.make_project()
        staged = root / "appstores/dist/tizen"
        staged.mkdir(parents=True)
        (staged / "config.xml").write_text("<widget/>\n", encoding="utf-8")
        (staged / "index.html").write_text(
            '<!doctype html><html lang="en"><title>x</title><main></main></html>\n',
            encoding="utf-8",
        )
        adapter = get_adapter("tizen")

        self.assertEqual(adapter.app_root(root), staged)

        calls: list[tuple[str, ...]] = []
        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted",
            side_effect=self._packaging_runner(calls),
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.BUILT)

    def test_tizen_build_leaves_the_widget_source_untouched(self) -> None:
        root = self.make_tizen_project()
        staged = root / "appstores/dist/tizen"
        staged.mkdir(parents=True)
        (staged / "config.xml").write_text("<widget/>\n", encoding="utf-8")
        (staged / "index.html").write_text("<html lang=\"en\"></html>\n", encoding="utf-8")
        before = sorted(path.name for path in staged.iterdir())
        adapter = get_adapter("tizen")
        packaged_from: list[Path] = []

        def fake_run(argv, *, cwd, allowed_roots=None, env=None, timeout=None):
            packaged_from.append(Path(cwd))
            # The real CLI signs in place, dropping these into its working copy.
            for litter in ("author-signature.xml", "signature1.xml", ".manifest.tmp"):
                (Path(cwd) / litter).write_text("x\n", encoding="utf-8")
            destination = Path(argv[argv.index("-o") + 1])
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "Fixture.wgt").write_bytes(b"PK\x03\x04fixture")
            return ProcessResult(argv=tuple(argv), returncode=0, stdout="", stderr="")

        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted", side_effect=fake_run
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.BUILT)
        # Signing byproducts must never land in the project's own widget source.
        self.assertEqual(sorted(path.name for path in staged.iterdir()), before)
        self.assertNotEqual(packaged_from[0].resolve(), staged.resolve())
        self.assertIn("dist", packaged_from[0].parts)

    def test_tizen_default_signature_is_reported_as_test_only(self) -> None:
        root = self.make_tizen_project()
        adapter = get_adapter("tizen")
        calls: list[tuple[str, ...]] = []

        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted",
            side_effect=self._packaging_runner(calls),
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertNotIn("--sign", calls[0])
        self.assertTrue(any("emulator" in note or "sideload" in note for note in built.notes))
        self.assertFalse(any("store" in note.lower() for note in built.notes))

    def test_tizen_configured_profile_is_passed_to_the_signer(self) -> None:
        root = self.make_tizen_project()
        (root / "platforms.yml").write_text(
            "project: fixture\nplatforms: [tizen]\ntizen_profile: AmbientTV\n",
            encoding="utf-8",
        )
        adapter = get_adapter("tizen")
        calls: list[tuple[str, ...]] = []

        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted",
            side_effect=self._packaging_runner(calls),
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertIn("--sign", calls[0])
        self.assertEqual(calls[0][calls[0].index("--sign") + 1], "AmbientTV")
        self.assertEqual(built.track_state, TrackState.BUILT)

    def test_tizen_packaging_failure_does_not_advance_track_state(self) -> None:
        root = self.make_tizen_project()
        adapter = get_adapter("tizen")

        def fake_run(argv, *, cwd, allowed_roots=None, env=None, timeout=None):
            if argv[1] == "package":
                return ProcessResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout="",
                    stderr="error: No security profile.",
                )
            return ProcessResult(argv=tuple(argv), returncode=0, stdout="", stderr="")

        with mock.patch("platforms.adapters.base._which", return_value=True), mock.patch(
            "platforms.adapters.platforms.run_allowlisted", side_effect=fake_run
        ):
            built = adapter.build(root, adapter.plan(root, adapter.detect(root)))

        self.assertEqual(built.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(built.artifacts, ())
        self.assertTrue(any("security profile" in note for note in built.notes))

    def test_track_states_are_not_inferred_forward(self) -> None:
        root = self.make_project()
        adapter = get_adapter("web-kiosk")
        detection = adapter.detect(root)
        plan = adapter.plan(root, detection)
        report = adapter.report(root, plan)
        self.assertEqual(report.track_state, TrackState.SCAFFOLDED)
        self.assertEqual(list(report.inferred_states), [TrackState.SCAFFOLDED])
