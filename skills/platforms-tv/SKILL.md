---
name: platforms-tv
description: Use when packaging, validating, accessibility-testing, or store-staging Android TV, Fire TV, Vega, webOS, Tizen, or Roku releases.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Platforms TV

Deliver television experiences through the selected adapter while keeping each target on a separate release track.

## Select the target

- `android-tv`: Google Android TV / Google TV. Detect Leanback projects, require launcher intent and TV banner assets, and keep this track separate from `fire-tv`.
- `fire-tv`: Amazon Fire TV. Require `LEANBACK_LAUNCHER` or its equivalent, reproducible APK contents/version codes, and explicit keep-awake/screensaver policy.
- `vega`: Amazon Vega, isolated from Fire OS. Require explicit `platforms.yml` selection and an explicit architecture decision (`native` or `webview`); never infer Vega or silently wrap a generic web/Android project.
- `webos`: LG webOS. Consume reproducible `www` assets and `appinfo.json`; validate declared icons and version before packaging, use `ares-package` when available, and inspect the resulting `.ipk`.
- `tizen`: Samsung Tizen. Validate `config.xml`, icons, versions, and signing state; require Tizen Studio or the `tizen` CLI for a real `.wgt`/package.
- `roku`: Roku. Build a native BrightScript/SceneGraph channel, never a WebView shell; validate `manifest`, focusable nodes, remote keys, and the local channel zip.

Use the adapter IDs exactly as written. Do not merge adapter evidence merely because two targets share source code.

## Shared accessibility gate

- Test D-pad focus order, visible focus, Back/Exit behavior, and remote key handling.
- Provide screen-reader or TTS labels where supported, including TalkBack-friendly labels on Android TV.
- Verify captions and audio descriptions whenever media exists.
- Respect reduced motion, readable contrast, and readable TV-distance sizing.
- Remove touch-only primary flows and document screensaver/always-on behavior.
- Record actual emulator/device evidence; never mark `device-tested` from static inspection.

## Toolchain and preflight rules

- Vega doctor output must identify missing Kepler/Vega CLI and approximately 20 GB of disk-space needs. Remain preflight-only without the SDK.
- webOS remains preflight-only without `ares-package`; its `appinfo.json` must contain a version and reference existing icons before packaging, and human upload goes through LG Seller Lounge.
- Tizen remains preflight-only without Studio/CLI, and signing readiness must stay explicit.
- Inspect every package before advancing to `store-staged`.

## Human submission gate

Stage artifacts and an upload checklist locally. Amazon, Google, LG, Samsung, and Roku developer-account login, upload, and publish remain human actions.
