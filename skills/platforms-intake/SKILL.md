---
name: platforms-intake
description: Use when collecting project facts, target platforms, accessibility needs, and toolchain risks before platform packaging begins.
allowed-tools: [Read, Write, Glob, Grep, Bash, AskUserQuestion]
---

# Platforms Intake

Collect project facts before packaging.

## Capture
- Product name, version, license, and maintainer
- Source spines (native vs offline web bundle)
- Target platforms and whether each is explicit or detected
- Accessibility requirements and known gaps
- Toolchain blockers from `platforms doctor`

## Output
Write a short intake record listing targets, risks, and the next skill to invoke.
Do not start packaging during intake.
