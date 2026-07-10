# Adding a Platform

1. Add a skill id to `suite.toml`.
2. Implement an adapter in `src/platforms/adapters/` using `BaseAdapter`.
3. Register it in `registry.py`.
4. Write `skills/<id>/SKILL.md` with accessibility and submission gates.
5. Add tests for detect/plan/doctor/build/validate/package/report.
6. Run `python3 tools/generate_manifests.py` and commit generated manifests with metadata.
7. Update `docs/platform-matrix.md` and CHANGELOG.
