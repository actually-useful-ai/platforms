---
name: platforms
description: Platforms suite router
---

# Platforms

Route platform-delivery and publishing work to the correct specialized skill.

## When to use
- A project needs packaging, validation, or store staging for non-Apple targets or KDP.
- The user asks which platform skill applies.

## Workflow
1. Run intake (`platforms-intake`) to identify targets and constraints.
2. Build a release plan (`platforms-release-plan`) with explicit track states.
3. Dispatch device or publishing skills. Never collapse strategy, generation, preflight, staging, and submission into one step.
4. Use the `platforms` CLI (`detect`, `plan`, `doctor`, `build`, `validate`, `package`, `report`) for deterministic work.
5. Stop at human upload/submission gates.

## Track states
Use only: scaffolded → built → validated → device-tested → store-staged → submitted.
Never infer a later state from an earlier one.

## Hard limits
- No credentials in reports.
- No automated store login or publish for KDP or device stores in v1.
- Accessibility is mandatory for every target.
