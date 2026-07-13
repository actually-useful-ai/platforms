---
name: platforms
description: Use when routing cross-platform delivery, packaging, publishing, accessibility, or store-staging work to the correct suite skill.
allowed-tools: [Read, Glob, Grep, Bash, AskUserQuestion]
---

# Platforms

Route platform-delivery and publishing work to the correct specialized skill.

## When to use
- A project needs packaging, validation, or store staging for non-Apple targets or KDP.
- The user asks which platform skill applies.

## Workflow
1. Run intake (`platforms-intake`) to identify targets and constraints.
2. Build a release plan (`platforms-release-plan`) with explicit track states.
3. Route TV targets to `platforms-tv`, Android/Fire tablet to `platforms-mobile`, books to `platforms-kdp`, Pebble to `platforms-pebble`, and kiosks to `platforms-web-kiosk`.
4. Use `platforms-store-assets` for local asset staging. Never collapse strategy, generation, preflight, staging, and submission into one step.
5. Use the `platforms` CLI (`detect`, `plan`, `doctor`, `build`, `validate`, `package`, `report`) for deterministic work.
6. Stop at human upload/submission gates.

## Track states
Use only: scaffolded → built → validated → device-tested → store-staged → submitted.
Never infer a later state from an earlier one.

## Hard limits
- No credentials in reports.
- No automated store login or publish for KDP or device stores in v1.
- Accessibility is mandatory for every target.
