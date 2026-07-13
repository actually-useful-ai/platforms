---
name: platforms-pebble
description: Use when building, validating, device-testing, or packaging Pebble watchface and interactive watchapp .pbw releases.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebFetch]
---

# Platforms Pebble

Deliver Pebble watchface and watchapp projects through the `pebble` adapter and current rePebble toolchain.

## Select the product type

- **Watchface:** Prefer Rocky.js or native C according to the existing project spine. Keep face updates readable at a glance and respect timeline and battery constraints. Use Ambient Time Golden Hour as a read-only fixture when available.
- **Watchapp:** Preserve interactive app keys, menus, and messages for small screens and limited buttons. Treat it as an app, not a face.

## Workflow

1. Detect the Pebble project and run doctor for the Pebble/rePebble CLI.
2. Build the `.pbw`.
3. Validate package contents and app metadata.
4. Install and drive it on an emulator or device.
5. Capture screenshots and inspect logs.
6. Package only after validation evidence exists.

Install, input, screenshot, and log capture prove `device-tested`; they do not prove store submission. Maintain readable contrast, glanceable text, clear button behavior, and non-color-only status cues.

## Source and submission boundaries

Follow current rePebble documentation. Do not copy no-license third-party skill prose or assets. Stage the `.pbw`, screenshots, metadata, and checklist locally; developer-account login, upload, and publish remain human actions.
