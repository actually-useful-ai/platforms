---
name: platforms-pebble-watchface
description: Pebble watchface delivery
---

# Platforms Pebble Watchface

Build and package Pebble watchfaces with the rePebble toolchain.

## Guidance
- Prefer Rocky.js or native C based on the project spine.
- Keep face updates readable at a glance; respect timeline and battery constraints.
- Use Ambient Time Golden Hour as a read-only fixture when available.
- Commands: detect → doctor → build `.pbw` → validate → package.
- Install/screenshot/log capture are device-test evidence, not store submission.
