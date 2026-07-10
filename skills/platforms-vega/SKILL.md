---
name: platforms-vega
description: Vega OS delivery
---

# Platforms Vega

Amazon Vega targets are isolated from Fire OS.

## Rules
- Require explicit `platforms.yml` selection; do not auto-detect aggressively.
- Wrap offline web bundles in Vega WebView only when that is the chosen architecture.
- Doctor must report missing Kepler/Vega CLI and disk-space blockers (~20 GB).
- Preflight-only until the SDK is installed; never invent a successful device-tested state.
