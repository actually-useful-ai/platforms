---
name: platforms-android
description: Android packaging
---

# Platforms Android

Shared Android primitives for phone/tablet APK/AAB workflows.

## Checks
- Gradle project detection and JDK readiness (17–21 preferred)
- Manifest permissions minimized
- Accessibility: TalkBack labels, focus, touch targets
- `adb` doctor before device-tested state
- APK/AAB content inspection before store staging

Fire tablet/TV and Android TV have dedicated skills for store and input differences.
