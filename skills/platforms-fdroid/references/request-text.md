# The "New app" request text

Contents: title and template, what goes above the checklist, length, what to leave out,
checklist, a skeleton.

Counts are in [evidence.md](evidence.md).

## Title and template

- Title: `New app: <App name>`.
- Use fdroiddata's own template, `.gitlab/merge_request_templates/Default.md`, fetched fresh: keep
  its headings and copy its checklist verbatim. Maintainers close requests that do not follow the
  template and reopen them once fixed; this was the most common reason a request that later merged
  was closed on the way.

## Above the checklist

In this order, each as short as the app allows:

1. **What it does.** One paragraph: what the app is and the main thing you do with it.
2. **Screenshots.** Two to four, embedded from the app's own Fastlane folder (raw URLs) or GitLab
   uploads, with alt text, at a modest width (`{width=240}`).
3. **Why it exists and what it adds.** One paragraph. Name the closest app already in the catalog
   and the concrete difference. Maintainers ask "what unique functions does this provide over other
   similar apps" when this is missing.
4. **Facts that could change the decision, one plain sentence each:**
   - every network service the app contacts and when (at launch, on a tap, opt-in);
   - anti-features that apply, or a sentence saying there are no ads, tracking or accounts;
   - assets or data with no stated license, and where they are listed;
   - a policy exception relied on (Quality point 6: link the author's merged app, or the evidence
     of users);
   - anything in the recipe a reviewer will otherwise ask about (a `scanignore`, for example).

Community testers check the app's network traffic against the description, so an undisclosed
connection becomes a question.

## Length

Merged requests are short: a median near 190 words above the checklist, with the middle half
between about 130 and 290. A simple app needs about 200 words. A complex app (bundled model,
training data, several scanner exceptions) can run longer because there is more to introduce.
Length showed no relationship to how many changes reviewers asked for or how long a merge took.
Count with `python3 scripts/request_words.py <file>`.

## Leave out

- Framing such as "things I would rather raise myself" and hedges that hand the call to the
  reviewer ("that is your call", "tell me if I have this wrong").
- Offers to drop features, refile or change the app if asked.
- Arguments for why something should be allowed, before anyone has asked.
- Build logs, test inventories, recipe history, button walkthroughs and object counts.
- Anything you cannot back with a file, a log or a link.

Keep the detail ready for the first reviewer who asks.

## Checklist

Tick only what is true. If a box cannot be ticked (no reproducible build, no Fastlane changelog),
leave it unticked and give the reason in one sentence under the checklist.

## Skeleton

```markdown
## Abstract for new app inclusion

### Please introduce the functions and usage of your app in summary, and also attach some screenshots.

<App> is <one sentence>. <One or two sentences on what you do with it.>

![<alt text>](<raw URL to fastlane phoneScreenshots/1.png>){width=240} ![<alt text>](<…/2.png>){width=240}

<It works offline / It contacts <service> when <trigger>.> No ads, account or analytics.

### Please elaborate why you wrote this app. Please highlight the unique functions it provides over other similar apps in F-Droid.

<Why, in one or two sentences.> The closest app in F-Droid is <name>; <app> adds <concrete difference>.

<One sentence per decision fact, if any.>

## Checklist
<copied verbatim from the current template>
```
