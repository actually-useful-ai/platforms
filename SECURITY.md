# Security Policy

Luke Steuber maintains the security policy for the Platforms and Publishing Suite.

## Supported versions

The latest tagged minor release receives security updates. Version 0.2.x is the currently supported line.

## Reporting a vulnerability

Send a private report to <luke@lukesteuber.com> with:

- the affected file, version, or commit;
- reproduction steps;
- the expected and observed behavior;
- potential impact; and
- any suggested mitigation.

Do not open a public issue for an undisclosed vulnerability or include credentials, tokens, signing assets, or personal data in a report.

Luke will acknowledge a complete report as soon as practical, assess impact, coordinate a fix, and publish credit when requested and appropriate.

## Scope notes

- `tools/check_drift.py` is read-only against installed projections.
- `tools/generate_manifests.py` writes only documented generated files under the repository root and refuses symlink escapes.
- The `platforms` CLI rejects project paths containing `..`, confines adapter writes under project `dist/`, and runs external tools through allowlisted argv arrays with `shell=False`.
- KDP and store workflows stop at upload-ready artifacts and human checklists. The suite does not store store credentials, automate login, or submit packages.
- Network access is not required for core validation; optional external validators run only when installed locally.
