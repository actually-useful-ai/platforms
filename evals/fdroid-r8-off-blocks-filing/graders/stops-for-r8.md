---
type: llm
weight: 1
---

The user asked for merge request text, but their tagged release has R8 off (`minifyEnabled false`). Passes when the response does all three:

1. Says not to open the request with the build as it is, because R8 is off.
2. Says to turn R8 on (`minifyEnabled true`) in a new version that is signed and released again.
3. Says to test the minified build on an emulator or device before it is signed.

It still passes if it offers to draft the request text for the new version (now or later, as long as nothing is filed against the R8-off build), mentions other build settings, or names `release_check.py`.

Fails when it hands over request text to file against the R8-off build, suggests filing now with a sentence explaining that R8 is off, or calls R8 optional.
