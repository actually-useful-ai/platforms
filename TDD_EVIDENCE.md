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

Final verification evidence belongs in the task handoff and must come from a fresh run immediately before commit.
