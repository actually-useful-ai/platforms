---
name: platforms-roku
description: Roku channel delivery
---

# Platforms Roku

Roku is a native BrightScript/SceneGraph redesign, not a web wrapper.

## Rules
- Do not ship a WebView shell as the Roku strategy.
- Port selected faces/features into SceneGraph components.
- Validate `manifest`, focusable nodes, and remote key handling.
- Package zip/channel artifacts locally; developer account publish is manual.
