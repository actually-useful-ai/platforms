---
name: platforms-kdp
description: Use when building, validating, accessibility-checking, or staging Kindle, EPUB, paperback interior, cover, and KDP metadata bundles.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebFetch]
---

# Platforms KDP

Build an upload-ready publishing bundle from `book.yml` and a Markdown manuscript through the `kdp` adapter.

## Book pipeline

1. Parse `book.yml`, contributors, manuscript, identifiers, and accessibility metadata.
2. Build EPUB3 with Pandoc when present or the deterministic minimal EPUB fallback.
3. Build the print interior with Typst when present; otherwise emit an explicit pending marker.
4. Validate structure and accessibility.
5. Emit `dist/<slug>/<version>/` with artifacts, metadata, checksums, provenance, validation report, and `UPLOAD_CHECKLIST.md`.

## Cover geometry

- Calculate the full wrap from trim, bleed, paper, and page count.
- Emit cover-spec JSON containing spine width and barcode reserve.
- Emit an SVG showing front, spine, back, bleed, and safe zones.
- Compare against the current KDP calculator and require human confirmation.

## Metadata

- Prepare title, contributors, keywords, categories, identifiers, pricing notes, territories, and required disclosures from `book.yml`.
- Keep accessibility metadata with the bibliographic record.
- Export metadata JSON/CSV into the upload bundle.
- Leave pricing and territory choices for human entry in KDP.

## EPUB accessibility gate

- Validate heading order, document language, navigation, landmarks, reading order, image alternatives, and table headers.
- Run EPUBCheck and Ace by DAISY when installed.
- Manually review reflow and contrast in embedded images.
- Fail closed on missing critical alt text; warn clearly when optional validation tools are absent.

## Human submission gate

Never automate KDP login, cookies, cover/interior upload, pricing writes, territory choices, or publish. Mark `submitted` only after a human completes KDP submission.
