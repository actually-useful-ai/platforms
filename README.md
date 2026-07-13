# Platforms and Publishing Suite

`platforms` is the canonical cross-client home for portable platform-delivery and publishing workflows maintained by Luke Steuber. Version 0.3.0 consolidates the suite into nine canonical skills while preserving 15 legacy names as explicit aliases.

## What it does

- Detects likely targets for a project
- Plans and diagnoses toolchains per platform
- Builds and validates artifacts into confined output roots
- Stages store packages and human upload checklists
- Stops before automated store login or publish (especially KDP)

## Requirements

- Python 3.11 or newer
- Git
- Optional tools depending on target: `pandoc`, `typst`, `epubcheck`, `ace`, `pebble`, `adb`, `ares-package`, `tizen`, Vega/Kepler CLI

## Setup

```sh
git clone https://github.com/actually-useful-ai/platforms.git
cd platforms
PYTHONPATH=src:tools:. python3 -m unittest discover -s tests -v
```

Optional editable install with test validators:

```sh
pip install -e '.[test]'
```

## CLI

```sh
PYTHONPATH=src:tools:. python3 -m platforms detect --project /path/to/project --json
PYTHONPATH=src:tools:. python3 -m platforms plan --project . --platform web-kiosk --json
PYTHONPATH=src:tools:. python3 -m platforms doctor --project . --platform kdp --json
PYTHONPATH=src:tools:. python3 -m platforms build --project examples/kdp-sample --platform kdp --json
PYTHONPATH=src:tools:. python3 -m platforms validate --project examples/kdp-sample --platform kdp --json
PYTHONPATH=src:tools:. python3 -m platforms package --project examples/kdp-sample --platform kdp --json
PYTHONPATH=src:tools:. python3 -m platforms report --project examples/kdp-sample --platform kdp --json
PYTHONPATH=src:tools:. python3 -m platforms drift
```

Commands refuse project paths containing `..` segments. Adapters run allowlisted
argv arrays with `shell=False`. Generic adapters without a concrete builder
remain `scaffolded`; placeholders never count as build evidence. Validation
requires non-empty artifacts and checksum agreement, and packaging advances to
`store-staged` only from validated evidence.

## KDP pipeline

Source of truth: `book.yml` plus a Markdown manuscript.

```sh
PYTHONPATH=src:tools:. python3 -m platforms build --project examples/kdp-sample --platform kdp --json
```

Output lands in `dist/<slug>/<version>/` with EPUB, print PDF or pending marker, cover SVG/spec, metadata, checksums, validation report, provenance, and `UPLOAD_CHECKLIST.md`. This suite never logs into KDP and never submits.

## Canonical metadata

`suite.toml` is the sole authority for identity, version, supported clients, nine canonical skills, 15 aliases, and four read-only agents. Run:

```sh
python3 tools/generate_manifests.py
python3 tools/generate_manifests.py --check
python3 tools/check_drift.py
python3 tools/install_projections.py --dry-run
python3 -m unittest tests.test_suite_schema -v
```

The installer copies canonical skills into Claude and creates valid sibling-relative
legacy aliases. Codex receives direct absolute links to those Claude projections.
Cursor and Agents receive canonical copies plus sibling-relative aliases.
Installation is state-tracked, idempotent, stale-managed cleanup-aware, rejects
ancestor symlinks, hostile state names, and overlapping roots, and preserves an
existing entry if its staged replacement fails.
Initial adoption recognizes only the exact legacy Codex alias link to the
same-named Claude alias, plus exact non-Codex same-name links to real directories
under another configured supported-client root.
See [Client installation](docs/install.md) for temporary-root review commands.

Store dimensions, limits, slot counts, formats, and safe zones are never assumed
from adapter prose. Asset work records the current official vendor source URL,
retrieval date, store, and applicable platform/version, and fails closed when a
requirement cannot be confirmed.

## Ambient Time fixture

See [Ambient Time fixture](docs/ambient-time-fixture.md) for the read-only acceptance
project, test-pack face ids, and smoke commands.

## Skills and agents

Canonical prose lives under `skills/*/SKILL.md` and `agents/*.md`. See:

- [Platform matrix](docs/platform-matrix.md)
- [Adding a platform](docs/adding-a-platform.md)
- [Accessibility guide](docs/accessibility.md)
- [Client installation](docs/install.md)

## Accessibility

Accessibility is a first-order requirement: keyboard/remote navigation, focus visibility, screen-reader semantics, captions, reduced motion, contrast, reflow, and platform-specific assistive behavior.

## Source provenance

`sources.lock.toml` pins evaluated sources. `ATTRIBUTIONS.md` records licenses and reuse boundaries. No-license material is research-only.

## Documentation

- [Project plan](PROJECT_PLAN.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Attributions](ATTRIBUTIONS.md)

## License

This project ships under the [MIT License](LICENSE).

## Author and maintainer

**Luke “Luke” Steuber**  
Speech-language pathologist · Linguist · Product nerd · Occasional code gremlin

| Where to find Luke | Link |
|---|---|
| Website | <https://lukesteuber.com> |
| Playground | <https://assisted.site> |
| Email | <luke@lukesteuber.com> |
| Bluesky | <https://bsky.app/profile/lukesteuber.com> |
| LinkedIn | <https://www.linkedin.com/in/lukesteuber/> |
| GitHub | <https://github.com/lukeslp> |
| Ollama models | <https://ollama.com/coolhand> |
| Newsletter | <https://lukesteuber.substack.com/> |
| Tip jar | <https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af> |

All code, documentation, diagrams, haikus, and rogue ASCII art in this repository are released under the MIT License by Luke Steuber.
