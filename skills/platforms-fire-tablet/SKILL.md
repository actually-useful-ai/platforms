---
name: platforms-fire-tablet
description: Fire tablet delivery
---

# Platforms Fire Tablet

Amazon Fire tablet packaging on the Android family spine.

## Differences from phone Android
- Amazon store metadata and capability declarations
- Touch-first UI still needs keyboard alternatives where relevant
- Validate WebView/offline bundle assumptions used by Ambient Time ports
- Sideload with `adb` for device-tested evidence; Amazon submission stays manual
