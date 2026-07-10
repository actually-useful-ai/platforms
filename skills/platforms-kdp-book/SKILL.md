---
name: platforms-kdp-book
description: KDP book pipeline
---

# Platforms KDP Book

Build an upload-ready Kindle/paperback bundle from `book.yml`.

## Pipeline
1. Parse `book.yml` and manuscript.
2. Build EPUB3 (Pandoc when present; deterministic minimal EPUB otherwise).
3. Build print interior (Typst when present).
4. Validate structure/accessibility.
5. Emit `dist/<slug>/<version>/` with checksums and `UPLOAD_CHECKLIST.md`.

## Hard limits
Never automate KDP login, cookies, pricing writes, or publish.
Mark `submitted` only after a human publishes.
