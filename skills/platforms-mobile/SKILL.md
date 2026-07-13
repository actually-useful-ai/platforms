---
name: platforms-mobile
description: Use when building, validating, device-testing, or store-staging Android phone/tablet and Amazon Fire tablet packages.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Platforms Mobile

Deliver shared Android-family mobile artifacts while preserving store and device differences.

## Select the adapter

- `android`: phone/tablet APK or AAB from Gradle and `AndroidManifest.xml`.
- `fire-tablet`: Amazon Fire tablet APK on the Android spine, with Amazon metadata and capability declarations.

Do not use this skill for `android-tv` or `fire-tv`; route those adapters to `platforms-tv`.

## Android checks

- Confirm Gradle project detection and JDK readiness; JDK 17–21 is preferred.
- Minimize manifest permissions and document every sensitive capability.
- Inspect APK/AAB contents and reproducible version values before store staging.
- Run the `adb` doctor and collect install/device evidence before marking `device-tested`.
- Test TalkBack labels, logical focus, keyboard alternatives, and adequate touch targets.

## Fire tablet differences

- Validate Amazon store metadata and capability declarations separately.
- Keep touch-first interaction accessible through keyboard alternatives where relevant.
- Validate any WebView/offline-bundle assumptions used by Ambient Time ports.
- Require `adb` sideload evidence from a Fire device or supported emulator.

## Human submission gate

Stage signed-ready artifacts, metadata, and a checklist locally. Google Play and Amazon Appstore login, upload, pricing, and publish remain human actions.
