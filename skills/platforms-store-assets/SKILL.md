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
- Prefer reproducible icon/version generation over hand-edited one-offs.
- Keep captions and alt text with every marketing image.
- Do not upload assets; stage locally and hand off a checklist.
