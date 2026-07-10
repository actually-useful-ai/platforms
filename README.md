# Platforms and Publishing Suite

`platforms` is the canonical cross-client home for portable platform-delivery and publishing workflows maintained by Luke Steuber. Version 0.1.0 establishes the control plane: canonical metadata, deterministic manifests, source provenance, and read-only drift reporting.

Skill prose and agent instructions are intentionally deferred. The inventories in `suite.toml` describe planned components; they do not imply that those components are implemented yet.

## Canonical metadata

`suite.toml` is the sole authority for:

- suite identity, version, author, repository, and license;
- supported clients;
- the 20 planned portable skills; and
- the four planned read-only agents.

`schemas/suite.schema.json` documents that model. Runtime validation uses only the Python standard library so the tools work without installing dependencies.

## Requirements and setup

- Python 3.11 or newer (`tomllib` is required)
- Git

Clone the repository and run the standard-library test suite:

```sh
git clone https://github.com/actually-useful-ai/platforms.git
cd platforms
python3 -m unittest discover -s tests -v
```

No package installation is required for the bootstrap tools.

## Generated files

Run:

```sh
python3 tools/generate_manifests.py
```

The generator writes:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.cursor-plugin/plugin.json`
- `.cursor-plugin/marketplace.json`
- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `dist/manifest.lock.json`

Do not edit these files by hand. Edit `suite.toml`, regenerate, review the diff, and commit the canonical metadata and generated outputs together. The generator never creates or changes `SKILL.md` prose.

Only clients listed in `clients.supported` receive manifests and lock entries. Removing client support removes its known generated manifests on the next generation run. Claude uses component auto-discovery, while Cursor and Codex use official relative directory-path fields. Planned component names stay in `suite.toml` and the lock inventory rather than client-reserved fields.

Check for generated drift without writing:

```sh
python3 tools/generate_manifests.py --check
```

The check detects byte, file-type, symlink, stale-client, and permission-mode drift. Generation refuses symlinked output files or parents and uses atomic replacement inside the repository.

The lock records normalized POSIX paths, SHA-256 hashes, suite version, supported clients, planned inventory, and file modes. It contains no timestamps, so identical inputs produce identical bytes.

## Installed-skill drift

Compare canonical skills with any optional installed roots:

```sh
python3 tools/check_drift.py ~/.claude/skills ~/.codex/skills
```

The command emits sorted JSON and never edits installed files. Missing, changed, or extra managed projections produce exit code 1. Invalid or unreadable canonical metadata fails closed with exit code 2 and a distinct error result. Unmanaged files do not affect the exit code. Agent-managed cache paths, generated cache content inside skills, and `~/.cursor/skills-cursor` are intentionally ignored.

Calling the command with no installed roots returns a clean report:

```sh
python3 tools/check_drift.py
```

## Accessibility

Accessibility is a first-order suite requirement, including dedicated TV and EPUB accessibility components. Future skill prose must account for keyboard and remote navigation, focus visibility, screen-reader semantics, captions, reduced motion, readable contrast, reflow, and platform-specific assistive technology behavior.

## Source provenance

`sources.lock.toml` pins every evaluated source used in planning. `ATTRIBUTIONS.md` records licenses and usage boundaries. Sources without a published license are research-only, and this release copies no third-party code or prose.

## Documentation

- [Project plan](PROJECT_PLAN.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Attributions](ATTRIBUTIONS.md)

## License

This project ships under the [MIT License](LICENSE). In plain English: have fun, do not sue, keep the copyright header intact, and give credit where it is due.

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

All code, documentation, diagrams, haikus, and rogue ASCII art in this repository are released under the MIT License by Luke Steuber. Forks and remixes must preserve required copyright and license notices.
