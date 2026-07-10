# Ambient Time fixture

The `platforms` suite treats `/Users/luke/workspace/ambient-time` as a read-only
acceptance fixture for non-Apple ports.

## Contract

- Ship unit: `appstores/dist/www`
- Test pack ids: `tv-dial`, `tv-cosmic`, `tv-word-grid`, `clk-binary`
- Wearable sidecar: `appstores/pebble/golden-hour` (not in `www/`)
- Target list: root `platforms.yml`

## Commands

```sh
# In ambient-time — isolated pack build (does not touch dist/www)
node appstores/build/build.mjs --test-pack --pack
node appstores/build/smoke-test-pack.mjs
node appstores/build/smoke-test-pack.mjs --from-test-pack

# In platforms — detect / doctor against the fixture
PYTHONPATH=src:tools:. python3 -m platforms detect --project /Users/luke/workspace/ambient-time --json
PYTHONPATH=src:tools:. python3 -m platforms doctor --project /Users/luke/workspace/ambient-time --platform web-kiosk --json
```

Do not edit Ambient Time uncommitted icon/macOS work from this suite.
