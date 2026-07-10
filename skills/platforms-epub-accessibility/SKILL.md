---
name: platforms-epub-accessibility
description: EPUB accessibility
---

# Platforms EPUB Accessibility

Validate EPUB accessibility before KDP upload.

## Checks
- Heading order and language
- Navigation/landmarks
- Image alternatives
- Table headers when tables exist
- EPUBCheck and Ace by DAISY when installed
- Manual review of reflow, contrast of embedded images, and reading order

Fail closed on missing critical alt text; warn on missing optional tools.
