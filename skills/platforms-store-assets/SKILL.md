---
name: platforms-store-assets
description: Use when preparing accessible screenshots, icons, descriptions, ratings, and local store-ready asset bundles without uploading them.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch]
---

# Platforms Store Assets

Prepare store screenshots, icons, descriptions, and age ratings without uploading.

## Requirements
- Resolve dimensions, limits, slot counts, formats, and safe zones from the
  current official vendor documentation, not from uncited adapter prose.
- Record the source URL, retrieved date, target store, and applicable
  platform/version beside every captured requirement.
- Always fail closed: if an official requirement is unavailable, ambiguous, or
  conflicts with an older record, mark the asset blocked instead of guessing.
- For Apple targets, keep screenshot and preview sizes in one dated record with
  source URLs and retrieval dates; re-check the live page before staging and
  fail closed on a mismatch.
- Stage the store's accessibility declarations with the bundle when it has
  them (Apple: Accessibility Nutrition Labels, declared per device family,
  since 2025). Claim a feature only when every common task works with it, and
  keep the device evidence beside the claim.
- Prefer reproducible icon/version generation over hand-edited one-offs.
- Keep captions and alt text with every marketing image.
- Check icons and screenshots under simulated deuteranopia, protanopia, and grayscale; a feature shown only by a red or green highlight must read without hue.
- Do not upload assets; stage locally and hand off a checklist.
