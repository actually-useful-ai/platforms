# Review: answering maintainers and updating an open request

Contents: what review looks like, answering a comment, changing the recipe, a new version
while the request is open, closed requests.

Counts behind these statements are in [evidence.md](evidence.md).

## What review looks like

- Most requests get one short round: a maintainer asks for one or two concrete changes in a line
  each ("Please enable R8.", "Install node from debian.") and merges once they are done and the
  pipeline is green.
- Maintainers set and clear the `waiting-on-response` label. Do not ask about it.
- Community members sometimes post test reports. They need no reply beyond thanks, if any.

## Answering a comment

1. Make the change on the fork branch first, run the local checks from
   [local-checks.md](local-checks.md), and wait for the fork pipeline to pass.
2. Reply under the maintainer's comment, not as a new top-level comment. Say it is done and, in one
   sentence, what changed or why, when that is not obvious from the diff. "Done, thanks." is enough
   for a one-line request.
3. If a request cannot be met, say so once with the concrete reason and what you did instead. Do
   not argue policy in the thread.
4. Show the owner the exact reply text and the exact recipe diff before posting or committing.

Do not rebase or force-push unless there is a merge conflict, do not open a second merge request,
and do not ping maintainers for speed.

## Changing the recipe

Change only what the comment asks for, plus anything the pipeline needs. If the comment reveals the
same problem elsewhere (another opaque prebuild line, another missing field), fix it in the same
commit and say so in the reply. Keep the single build entry; update `CurrentVersion` and
`CurrentVersionCode` with it.

If the fix needs a change in the app itself (R8, `dependenciesInfo`, a listing-text folder), it
needs a new release: the owner signs and tags it, then the build entry moves to the new tag.

## A new version while the request is open

1. The owner signs, tags and publishes the release, with the signed APK attached where `Binaries`
   points, before anything changes in fdroiddata.
2. Replace the one build entry (version name, version code, full commit hash) and the two
   `Current*` fields. Do not add a second entry.
3. Run the local checks, including `fdroid build` against the new reference APK.
4. Commit to the same fork branch, check the raw file's hash, wait for the pipeline.
5. Post one short note: the new version and what changed for review (for example "R8 is on now").

If the tag is pushed and the request stays on the old version, auto-update would add the new
version after merge, but the old one is built and listed first. Moving the entry avoids publishing
a version you already replaced.

## Closed requests

- Closed under Quality point 6 (too new): do not reopen or refile until the repository qualifies
  or an exception applies; say which one when you reopen.
- Closed for a policy refusal (website wrapper, non-free dependency): change the app first. An
  appeal goes to team@f-droid.org, not into the thread.
- Closed after a long silence: reopen only with the requested changes already made.
