# Security Policy

Luke Steuber maintains the security policy for the Platforms and Publishing Suite.

## Supported versions

The latest tagged minor release receives security updates. Version 0.1.x is the currently supported line.

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

The bootstrap tools read local metadata and optional installed skill roots. `tools/check_drift.py` is intentionally read-only. `tools/generate_manifests.py` writes only the documented generated files under the selected repository root. Neither tool requires network access, credentials, or third-party Python packages.
