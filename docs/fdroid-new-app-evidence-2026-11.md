# F-Droid "New App" requests, October and November 2026: what merged and what was closed

Read on 24 November 2026. This is the evidence the `platforms-fdroid` skill is built on. Every
number below comes from `summary.json` written by `docs/research/fdroid-new-apps/analyze.py`.

## Sample and method

- **Merged:** the 180 most recently created merge requests in `fdroid/fdroiddata` (GitLab project
  36528) labeled "New App" and merged, created 6 October to 24 November 2026.
- **Closed without merging:** the 300 most recently created "New App" requests in the closed state,
  created 8 October to 24 November 2026.
- **Per request:** the description, every comment (discussions JSON), the list of diff versions,
  and the recipe file at the first and the last version (raw file at each version's head commit).
- **Maintainers:** the people who merged or closed requests other than their own: linsui (174 of
  180 merges), seekme-seekyou (6) and licaon-kter. A "request" is a maintainer comment that is not
  a plain thanks, the standard "This MR is mostly ready" note or "Triggered a pipeline".
- **Kinds of request** come from keyword rules run on comments with quoted lines, code blocks and
  URLs removed. I read samples of every kind to correct the rules; small counts are approximate.
- **Description length** counts words above the template's `## Checklist` heading, without the
  template's own headings, HTML comments, image markup or bare URLs.

Reproduce:

```sh
python3 docs/research/fdroid-new-apps/collect.py 3 5        # 3 pages merged, 5 closed, 60 each
python3 docs/research/fdroid-new-apps/analyze.py            # needs PyYAML
```

Set `FDROID_STUDY_DATA` and `FDROID_STUDY_OUT` to choose folders. The unauthenticated GitLab API
refuses notes, discussions and versions (HTTP 401), so the collector uses the web endpoints
`/-/merge_requests/<n>/discussions.json`, `/-/merge_requests/<n>/diffs.json` and `/-/raw/`.

## 1. The request text (merged)

| Measure | Count or value |
| --- | --- |
| Used the template (has its checklist) | 179 of 180 |
| Words above the checklist | median 188, quartiles 130 and 287, maximum 1,143; 119 at 250 or fewer, 9 over 500 |
| Embedded screenshots | 116 of 180; 89 with two to four; median 3.5 when present; 60 with none at all |
| Bullet lists / extra headings | 90 / 129 |
| Some checklist boxes left unticked | 99 |
| Mention network use or offline operation | 143 |
| Mention permissions | 75 |
| Say there are no ads, tracking or analytics | 90 |
| Compare with another app | 56 |
| Mention reproducible builds | 42 |
| Mention a license detail | 31 |
| Mention anti-features | 16 |
| Mention R8 | 6 |
| Mention Quality point 6 | 6 |
| Description edited after filing | 80 |

The common shape: a paragraph on what the app does, a few screenshots, a paragraph on why it exists
and how it differs, and short notes on network use and tracking. Long build or disclosure sections
are rare.

**Length and review load.** Among the 179 requests using the template, the rank correlation between
words and the number of maintainer requests is 0.12, and between words and days to merge 0.07.
The shortest third had a median of 1 request (quartiles 1 and 2), the longest third 2 (quartiles
0.5 and 3); median days to merge were 5.3 and 4.9. Length does not predict review effort in this
sample. Because 80 descriptions were edited after filing, this measures the final text.

## 2. What maintainers asked for (merged, n = 180)

Requests counted once per merge request.

| Kind | Requests | Typical wording |
| --- | --- | --- |
| Enable R8 | 30 | "Please enable R8." |
| Add `Binaries` / `AllowedAPKSigningKeys` | 28 | "Please add Binaries … and AllowedAPKSigningKeys for reproducible build." |
| Choose a better category | 27 | "Please choose a better category from … categories.yml" |
| Follow the merge request template | 24 | "Closing because Merge Request template is not followed." |
| GitLab suggestion editing the recipe | 24 | a `suggestion` block on a recipe line |
| Flutter (pin SDK, ABI split, version codes) | 14 | "Please setup abi split. For Flutter apps …" (12) |
| Fastlane listing | 11 | icon in every locale, summary under 80 characters, `images/` folder |
| Unique value over similar apps | 9 | "we already have many similar apps" |
| Declare anti-features | 8 | "Add NonFreeNet.", "Use AntiFeatures." |
| Install from Debian (Node, rustup) | 8 | "Install node from debian." |
| Quality point 6 | 8 | closed for it, later reopened and merged |
| JDK version | 7 | "Can you use jdk 21?" |
| `subdir` / `output` | 7 | "Please set the subdir and remove the output." |
| Fix the pipeline | 4 | "Please fix the pipeline." |
| Enable auto-update | 4 | "Enable autoupdate." |
| Network: check connections, explain INTERNET | 4 | addressed to testers, or "Why does it require INTERNET?" |
| Old versions or commit hash | 4 | "Remove old versions", "update the commit hash" |
| Commands as a list, not joined with `;` or `&&` | 3 | |
| Prebuild or scripts | 2 | "Put these steps in prebuild. They don't need to run as root." |
| License header | 2 | |

Rounds, counted as distinct days with at least one request: 39 requests merged with none, 83
needed one day, 42 two, 12 three, 4 four.

The CI pipeline, not maintainers, raised the reproducibility problems: the dependency-metadata
signing block came up in 11 threads (the `check apk` job in 24), `version-control-info.textproto`
in 3, `baseline.prof` in 1. No maintainer comment in the sample mentions `dependenciesInfo`,
`vcsInfo` or `SOURCE_DATE_EPOCH` by name.

## 3. The recipe as filed against as merged

Both versions were readable for 171 requests.

| Change between first and last version | Requests |
| --- | --- |
| Build moved to a newer release | 116 |
| `Categories` changed | 50 |
| `AllowedAPKSigningKeys` added | 35 (0 removed) |
| `Binaries` added | 31 |
| `prebuild` changed | 23 |
| `sudo` changed (18) or removed (13) | 31 |
| `AutoUpdateMode` changed | 16 |
| `UpdateCheckMode` changed | 15 |
| `AntiFeatures` added | 11 |
| `VercodeOperation` added (Flutter ABI split) | 11 |
| `UpdateCheckData` added | 7 |
| Only the version changed, or nothing | 53 |

Fields across all 171, first version → merged version:

| Field | First | Merged |
| --- | --- | --- |
| `AllowedAPKSigningKeys` (owner's signature) | 91 | 126 |
| `Binaries` | 76 | 105 |
| `AutoUpdateMode: None` | 7 | 0 |
| `UpdateCheckMode: Tags` | 164 | 169 |
| `UpdateCheckData` | 55 | 60 |
| Node from a `nodejs.org` tarball | 6 | 0 (5 moved to Debian `apt-get`) |
| `AntiFeatures` | 21 | 32 |
| `sudo` | 49 | 39 |
| `prebuild` | 62 | 62 |

Build families as merged (from recipe text): plain Gradle 109, Flutter 28, Node-based other than
Capacitor 12, Gradle with NDK 10, Rust 6, React Native 5, Capacitor 1.

**Reproducible builds.** 126 of 171 merged recipes ship the author's signature
(`AllowedAPKSigningKeys`); 108 of 180 requests carry the `reproducible-builds` label. Median days to
merge: 6.0 with the author's signature, 4.5 without. No request moved from the author's signature to
F-Droid's.

## 4. Review timing (merged)

| Measure | Value |
| --- | --- |
| First maintainer comment | median 4.2 hours (quartiles 1.2 and 11.5); within 24 hours for 161 of 176 |
| "This MR is mostly ready … We'll test it later" | 119 requests, median 0.7 days after filing |
| From that note to merge | median 2.9 days (quartiles 1.1 and 6.5) |
| Filing to merge | median 5.5 days (quartiles 2.1 and 11.4), longest 41.9 |
| By days with requests: 0, 1, 2, 3 or more | median 2.1, 4.7, 9.5, 11.1 days |
| Maintainer started a pipeline ("Triggered a pipeline. Please check.") | 36 requests |
| Closed and reopened before merge | 30 (template 18, Quality point 6 7, other 5) |
| Title changed after filing | 27 |

**Community testing.** 86 merged requests have a test report from someone other than the author
and maintainers. Of 97 such reports, 76 mention network traffic, connections or the INTERNET
permission: testers compare what the app contacts with what the description says.

By build family, median days to merge: plain Gradle 5.2 (109), Flutter 3.8 (28), Node-based 8.6
(12), Gradle with NDK 6.3 (10), Rust 7.0 (6), React Native 8.1 (5).

## 5. Closed without merging

300 closed requests, created 8 October to 24 November 2026. Authors closed 25 themselves,
often after a maintainer's question; maintainers closed 275. Reasons below come
from the last two maintainer comments, where the closing message sits; one request can have
several.

| Reason given by the maintainer | Requests (of 275) |
| --- | --- |
| Not actively developed for three months (Quality point 6) | 211 |
| Merge request template not followed | 60 |
| No unique value over apps already in the catalog | 31 |
| No activity for a long time after a request | 25 |
| Not ready, or no recipe file | 5 (all also Quality point 6) |
| Website wrapper ("We don't accept website wrappers.") | 1 |
| Content that is not an app ("Just provide your book via a pdf file.") | 1 |
| No reason matched (7 had no maintainer comment at all) | 12 |

Most common combinations: three months alone 156; three months and template 26; inactivity 24;
template alone 18; three months, template and unique value 14.

- Closures are fast: median 1.9 days open (quartiles 0.5 and 9.3); 1.5 days for three-month
  closures, and for 186 of the 211 that closing comment was the only maintainer comment.
- Several three-month closures name the evidence used: "the public repository was created …",
  "first commit on github is 2 weeks ago". One says it "will only be reviewed once it reach 3 month".
- Build families among closed requests: plain Gradle 182, Flutter 35, Node-based 21, Gradle with
  NDK 20, Rust 13, React Native 12, Capacitor 9, Go 1, no readable recipe 7. Capacitor has 9 closed
  against 1 merged in the same window. None was closed for being web-based: four for the
  three-month rule (two also for the template), one for the template alone, three went quiet
  after a request (twice "Install node from debian.", once a unique-value question), and its
  author closed one.
- No closed request in the sample was refused for a non-free dependency.

## 6. What this does not show

- Merged and closed requests only; open requests and requests outside this window are not counted.
- Counts of maintainer requests are of written comments. Changes asked for in person, in Matrix or
  through labels are invisible.
- Descriptions were often edited after filing (80 of 180), so length and disclosure counts describe
  the final text.
- Keyword rules miss paraphrases and can misfile a comment; I corrected the rules where reading
  showed it, but did not hand-label every comment.
- The sample holds one website-wrapper refusal (!52244) and no Trusted Web Activity refusal, so
  the wrapper rule rests mostly on the Inclusion Policy and on maintainer lines from other requests.

## 7. What the skill takes from this

| Skill rule | Basis |
| --- | --- |
| Use the template exactly | Measured: template comments in 24 merged and 60 closed requests; 18 of 30 close-and-reopen cycles |
| Three months of public history, or name the exception | Measured: 211 closed requests; 8 merged only after reopening |
| R8 on | Measured: 30 requests |
| Reproducible build fields | Measured: 28 requests, 35 recipes added them, 126 of 171 use them |
| Category from `categories.yml` | Measured: 27 requests, 50 recipes changed |
| Auto-update on, Tags | Measured: 7 of 7 `None` changed, none merged with it |
| Node and Rust tools from Debian | Measured: 8 requests, 6 → 0 tarballs |
| State network use | Measured: 143 descriptions; testers check it in 76 of 97 reports |
| About 200 words, two to four screenshots | Measured: median 188, quartiles 130 and 287; no link between length and review load |
| Name the closest catalog app and the difference | Measured: 9 "unique value" requests in merged, 31 closures |
| Dependency-metadata block off, vcsInfo, baseline profile | Measured only through CI threads (11, 3, 1); guidance from F-Droid's Reproducible Builds page |
| Website wrappers and TWAs refused | Policy text; one refusal in this sample (!52244), the TWA line from outside it |
| No opaque prebuild script; "enable autoupdate not none" | Single case (Mandaza !55922), consistent with the measured auto-update and prebuild changes |
| A root `metadata/` folder replaces the Fastlane text | Single case (Mandaza 1.3.12), confirmed with fdroidserver's own scan function |
| Private history does not count toward three months | Single case (Mandaza, closed 9 November 2026) |
| ruamel.yaml 0.18.10 for `rewritemeta` | Read from the CI configuration once, 24 November 2026 |
