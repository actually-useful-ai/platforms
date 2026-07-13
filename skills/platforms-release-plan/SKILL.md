---
name: platforms-release-plan
description: Use when converting platform intake findings into explicit per-target build, validation, device-test, staging, and human submission tracks.
allowed-tools: [Read, Write, Glob, Grep, AskUserQuestion]
---

# Platforms Release Plan

Produce a per-platform release plan with separate track states.

## Rules
- One plan row per platform.
- States advance only after evidence exists.
- Every dimension, limit, asset slot, and safe zone must cite the recorded store specification source gathered by `platforms-store-assets`.
- Submission authorization is a separate human step.

## Deliverable
A checklist covering build, validate, device-test, store-stage, and submit for each target.
