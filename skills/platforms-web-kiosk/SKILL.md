---
name: platforms-web-kiosk
description: Use when packaging and validating an accessible offline web experience for kiosk, full-screen, or always-on display deployment.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Platforms Web Kiosk

Package offline web experiences for kiosk or always-on displays.

## Checks
- Offline integrity (no unexpected network calls during validation)
- Keyboard and switch access, logical order, and visible focus
- Correct landmarks, labels, language, and screen-reader semantics
- Readable contrast, reduced motion, and text zoom without clipped content
- Full-screen / kiosk policy documented
- Stage files under `dist/platforms/web-kiosk` with an upload checklist when a host store exists

## Human publication gate

Building and validating a kiosk bundle never authorizes deployment. Host login,
upload, device enrollment, kiosk-policy activation, and publish remain human
actions, and `submitted` must never be inferred from a local package.
