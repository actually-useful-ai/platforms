# Test-Driven Development Evidence

Maintainer: Luke Steuber  
Bootstrap date: 2026-07-10

## Cycle 1: control-plane tools

Tests were written before `tools/generate_manifests.py` and `tools/check_drift.py`.

RED command:

```sh
python3 -m unittest discover -s tests -v
```

Expected RED result:

- exit code 1;
- two import errors; and
- missing `tools.generate_manifests` and `tools.check_drift` implementations.

GREEN command:

```sh
python3 -m unittest discover -s tests -v
```

GREEN result after minimal implementation:

- exit code 0;
- eight tests passed; and
- zero failures or errors.

## Cycle 2: marketplace inventory regression

Inspection showed that the standalone agents marketplace record lacked explicit component inventory.

RED command:

```sh
python3 -m unittest tests.test_generate_manifests.ManifestGenerationTests.test_marketplace_record_carries_component_inventory -v
```

Expected RED result:

- exit code 1; and
- `KeyError: 'skills'`.

GREEN command:

```sh
python3 -m unittest discover -s tests -v
```

GREEN result after adding inventory fields:

- exit code 0;
- nine tests passed; and
- zero failures or errors.

This implementation was later superseded after enabled local plugin exemplars showed that component-name arrays and objects were invalid in reserved client fields. Cycle 4 records the correction.

## Cycle 3: nested managed-root exclusion

A focused edge-case test required descendants of `~/.cursor/skills-cursor` to remain excluded.

RED command:

```sh
python3 -m unittest tests.test_check_drift.DriftDetectionTests.test_agent_caches_and_cursor_managed_root_are_ignored -v
```

Expected RED result:

- exit code 1; and
- an assertion failure because a nested managed path was not ignored.

GREEN result after broadening the path boundary:

- exit code 0;
- one focused test passed; and
- zero failures or errors.

## Cycle 4: official client component shapes

RED showed Claude still contained `skills`, `agents`, and `client` fields with inventory objects. Cursor and Codex also used inventory objects instead of relative paths, and the agents marketplace used name arrays instead of its structured source shape.

GREEN removed reserved-field inventories, retained Claude auto-discovery, added `./skills/` for Cursor and Codex, adopted the local agents marketplace source convention, and moved planned names into lock inventory metadata.

## Cycle 5: supported-client subsets

The initial RED showed a cursor-only suite still generated every client manifest. A second focused RED after the first fix showed stale unsupported manifests were ignored by check mode and left on disk.

GREEN made `clients.supported` control expected outputs, lock entries, stale checks, and safe stale-file cleanup.

## Cycle 6: permission-mode drift

RED command:

```sh
python3 -m unittest tests.test_generate_manifests.ManifestGenerationTests.test_check_reports_mode_drift_without_writing -v
```

RED returned exit code 0 after a generated manifest changed from mode `0644` to `0755`. GREEN returned exit code 1, reported the path, and preserved mode `0755` in check mode.

## Cycle 7: fail-closed canonical metadata

RED returned exit code 0 with `drift: false` for invalid suite metadata. GREEN returns exit code 2 with `status: error` and no misleading drift result.

## Cycle 8: generated cache exclusions

RED treated `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and `.pyc` content inside an installed managed skill as drift. GREEN excludes those generated files while continuing to compare managed source content.

## Cycle 9: contained atomic generation

Two focused RED tests showed that symlinked output files and parent directories allowed writes outside the repository. GREEN rejects both before any generated file write and uses same-directory temporary files with atomic replacement.

## Cycle 10: excluded source provenance

The first RED raised `StopIteration` because `jordangarrison/ash-kindle` was absent from `sources.lock.toml`. A follow-up RED raised `KeyError: 'excluded'` to require explicit status flags. GREEN pins revision `d425946fe9585f43af2eedf20721f3fdf3779026` as excluded, unrelated, research-only, and unavailable for reuse.

## Review-fix regression command

```sh
python3 -m unittest \
  tests.test_generate_manifests.ManifestGenerationTests.test_generated_component_shapes_follow_local_exemplars \
  tests.test_generate_manifests.ManifestGenerationTests.test_supported_client_subset_controls_outputs_and_lock \
  tests.test_generate_manifests.ManifestGenerationTests.test_check_reports_mode_drift_without_writing \
  tests.test_generate_manifests.ManifestGenerationTests.test_generation_refuses_symlinked_output_file \
  tests.test_generate_manifests.ManifestGenerationTests.test_generation_refuses_symlinked_output_parent \
  tests.test_check_drift.DriftDetectionTests.test_invalid_suite_metadata_fails_closed_with_error_result \
  tests.test_check_drift.DriftDetectionTests.test_generated_cache_files_inside_skills_are_ignored \
  tests.test_sources_lock.SourceLockTests.test_ash_kindle_is_pinned_as_excluded_without_reuse -v
```

Combined RED evidence: seven assertion failures and one missing-source error. Combined GREEN evidence: eight tests passed with zero failures or errors.

## Full-suite evidence

```sh
python3 -m unittest discover -s tests -v
```

Result after implementation: 15 tests passed with zero failures or errors.

Required command checks:

```sh
python3 tools/generate_manifests.py --check
python3 tools/check_drift.py --help
```

Both commands completed with exit code 0; manifest check reported that generated files were current.

## Cycle 4: shared CLI and adapters

RED tests added first for process runner, adapter contract, and CLI commands (`tests/test_process.py`, `tests/test_adapters.py`, `tests/test_cli.py`).

GREEN after implementing `src/platforms/` with secure `run_allowlisted`, adapter registry, and CLI handlers.

## Cycle 5: KDP pipeline and inventory

RED/GREEN for `tests/test_kdp_pipeline.py`, Ambient Time fixture detection, and inventory presence.

Full-suite evidence after 0.2.0:

```sh
PYTHONPATH=src:tools:. python3 -m unittest discover -s tests -v
```

Result: 37 tests passed with zero failures or errors.
