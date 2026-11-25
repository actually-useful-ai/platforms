# Local checks, fork branch and pipeline

Contents: match CI's tool versions, the checks in order, listing text sources, fork branch,
pipeline, rate limits.

## Match CI's tool versions

fdroiddata's CI (`.gitlab-ci.yml`, checked 2026-11-24) runs on `debian:trixie-slim`, installs
Debian's `fdroidserver` package for its dependencies, then runs fdroidserver from git master (a
pinned root commit, fast-forwarded to master). The YAML library is Debian trixie's
`python3-ruamel.yaml`, 0.18.10. The build job uses the image
`registry.gitlab.com/fdroid/fdroidserver:buildserver-trixie`.

Set up a matching virtualenv once:

```bash
python3 -m venv venv-ci
venv-ci/bin/pip install "git+https://gitlab.com/fdroid/fdroidserver.git" "ruamel.yaml==0.18.10" check-jsonschema
```

Re-read `.gitlab-ci.yml` before relying on these versions; they move.

Work in a sparse clone of fdroiddata master (for `config/`, `schemas/`, `srclibs/` and the recipe)
and a separate fdroidserver workspace with a `config.yml` naming `sdk_path`, `java_paths` and
`refresh_scanner: true` for builds. Unset any signing variables in the environment before building.

## The checks, in order

Run each on the exact file you will commit. Keep the logs.

1. `fdroid readmeta` and `fdroid lint <appid>`: no errors, no warnings you cannot explain.
2. `fdroid rewritemeta <appid>`, then `cmp` against your file: identical means CI's formatter will
   not complain. If it changes the file, take its version.
3. `check-jsonschema --schemafile schemas/metadata.json metadata/<appid>.yml`.
4. `fdroid checkupdates -v --allow-dirty <appid>`: it must find the current version from the tags
   and report the recipe up to date. Then set the recipe back one version and run with `--auto`:
   it must write a correct build entry with the full commit hash. This is what auto-update will do
   after merge.
5. `fdroid scanner` on a clean checkout of the tagged commit: zero problems, or every problem
   covered by a `scandelete` or `scanignore` you can justify in one line.
6. `fdroid build -v -l <appid>` (add `--test` if you only want the build): look for "compared built
   binary to supplied reference binary successfully" and the allowed signer when `Binaries` is set.
7. Independently: two clean clones of the tag built with the recipe's commands give the same
   unsigned APK hash, and copying the signature from the release APK (apksigcopier) gives the
   release APK byte for byte.

## Listing text sources

Run `python3 scripts/listing_sources.py <checkout> --subdir <subdir>` on the tagged commit. It lists
the folders fdroidserver reads, in order; the last one read wins. Exit code 1 means a root
`metadata/<locale>` folder (often another store's text) would replace the Fastlane text. Add
`--fdroidserver --app-id <appid>` inside the CI-matched virtualenv to run fdroidserver's own scan and
print the summary and description it would publish. Fix it in the app repo and re-tag; a recipe
change cannot fix it because fdroidserver reads the checkout at the built commit.

## Fork branch

1. Fork `gitlab.com/fdroid/fdroiddata` (public fork, unprotected branch).
2. Create a branch named after the application ID with only `metadata/<appid>.yml` added.
3. Without GitLab credentials on the machine, use the signed-in GitLab web editor:
   `https://gitlab.com/<user>/fdroiddata/-/new/master/metadata?file_name=<appid>.yml`. Typing into
   the editor auto-indents and breaks YAML; paste the whole file instead. Commit to a new branch and
   untick "Create a merge request" (ticked by default).
4. Compare the raw file on the fork with your local file by sha256
   (`https://gitlab.com/<user>/fdroiddata/-/raw/<branch>/metadata/<appid>.yml`).

## Pipeline

GitLab may not start a pipeline for a branch's first commit. Start one under Build → Pipelines →
New pipeline with the branch as the ref. All jobs should pass, including `fdroid build` and
`checkupdates`. Explain any warning in the Reports tab before opening the request. If GitLab asks for
a phone number or card to run CI, stop and say so in the request instead.

## Rate limits

Unauthenticated GitLab calls are rate limited; on HTTP 429 wait for the `Retry-After` time (about
300 seconds). Several API endpoints for merge requests (notes, discussions, versions) return 401
without a token; the web endpoints `/-/merge_requests/<n>/discussions.json`, `/-/merge_requests/<n>/diffs.json`
and `/-/raw/<sha>/<path>` work without one and count against a separate allowance.
