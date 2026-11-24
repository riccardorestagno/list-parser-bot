---
name: codebase-review
description: Review the whole codebase, or one area of it, for things that don't work as designed, inefficiencies, duplicated code and possible optimizations, verify each finding, report them ranked, and on the user's go-ahead fix them on feature branches grouped so no two branches touch the same file, one PR per branch. Use when the user asks to analyze, audit or review the codebase (or the server, the client, CI, one feature) for bugs, inefficiencies, duplication (DRY), performance or optimizations, outside of a release. For what a release would ship, use release-review instead.
---

# Codebase Review

Looks at the code as it stands on **`origin/develop`**, not at a diff: what a release changes is `release-review`'s job.

An argument narrows it (`/codebase-review server`; `server`, `client`, `ci`, `bot`, one parser, a folder or a file). Without one, review everything, and say at the top of the report what was read closely, what was only skimmed and what was left out.

**Rules:**
- Change nothing before the user says which findings to fix (step 5). Reading, running the tests and running throwaway scripts in the scratchpad are fine.
- Every finding is verified before it's reported (step 3). A finding that can't be verified is reported as suspected, with what would settle it, or dropped.
- Don't spawn sub-agents to do the reading. The one sub-agent is the fresh-eyes review of the larger fixes (step 6).
- Never commit on `develop` or `main`. Branches come from the `create-feature-branch` skill's steps, PR text from `done-message`.
- Never run a sweep without `--dry-run`, never post to Reddit, and never fetch the live websites in a loop: tests stub them, and a review reads the code.

---

## 1. Start from a known state

```bash
git fetch origin develop
git log --oneline -1 origin/develop
git status --short
```

Review `origin/develop`. If the checked-out branch differs from it, say so and review a detached worktree of `origin/develop` in your scratchpad instead of the working tree.

Start the server tests in the background while reading, so their result is in the report:

```bash
cd server && python -m pytest -q
```

Use the server's virtual environment (`venv\Scripts\python.exe` on Windows, `venv/bin/python` on Linux), or `python` in a cloud session once the requirements are installed.

Open pull requests may already fix what you're about to find. List them and skip what they cover (`gh pr list --state open`, or the GitHub tools where there is no `gh`).

## 2. Read in this order

The repository is small (about 1,500 lines of server code): read the server whole.

1. **What every request goes through**: `server/main.py` (it also starts and stops the scheduler), `settings.py`, `db/session.py`, `api/auth.py`, `api/errors.py`.
2. **What runs without a request**: `services/scheduler.py` (its thread), `services/sweep.py`, `bot/controller.py`.
3. **What reaches outside**: `bot/helpers/reddit.py`, each module of `bot/parsers/`, `bot/config.py` (limits and pauses).
4. **The record of sweeps**: `services/runs.py`, `services/status.py`, `db/migrations.py`.
5. **Client**: `client/src/App.tsx`, `utils/api.ts`, `utils/auth.ts`, `utils/format.ts`, then `features/`.
6. **CI and deploy**: `.github/workflows/`, `deploy/azure/`.

## 3. What to look for, and how to verify it

Each line is a kind of problem. Check the kind, not only one place.

**In this repository especially**
- **Anything that could post twice, or post when it shouldn't**: the earlier-post check skipped on some path, two sweeps at once, the schedule honoured when `LISTBOT_SCHEDULE_ENABLED` is off, a test or a hand-run parser that reaches Reddit.
- **The gap between sweeps lost** over a restart, or a failure reported to the moderator every sweep instead of once. Looking back for "already told", pass over the sweeps that say nothing either way (cut short by a restart, or where the site or Reddit couldn't be reached), as `runs.sweep_failed_before` and `runs.sites_failing_before` do.
- **A parser that no longer respects its limit or its pause** between fetches, or fetches more pages than it reads: the same page fetched again by a second reader (read it once and hand the soup to both, as BuzzFeed's `get_article_list_text` does), or an article opened before checking whether it was posted.
- **One site's failure stopping the others**: anything that raises out of a site's search ends the sweep and every site after it, and a site that never posts stays first in the order, so it would fail every sweep. Each site's search is caught on its own in `bot/controller.py`'s `sweep`; only Reddit failing ends a sweep.
- **A failure that reads as "nothing new"**: a fetch that doesn't check the HTTP status, or an archive page that matches no articles, looks like a quiet day. `soup_session` raises on an error page and the controller raises `NoArticlesFound` on an empty archive, so the site shows as failing. Only the archive counts: an article page that's gone (4xx but 429) is passed over for the next, as `is_gone` does, or one deleted article would fail its site every sweep.
- **Repeated work per article**: a new Reddit connection, a subreddit listing or an HTTP session per check. One connection and one listing per sweep, one session for every page.
- **A connection kept from one sweep to the next**: sweeps are 90 minutes apart and Azure's outbound NAT silently forgets a connection idle for 4 minutes, so a request sent on it is never answered and the site reads as timing out (`ReadTimeout` on the first page). `sweep` closes the session's connections when it ends, however it ends (`lvm.close_connections`); anything else kept open between sweeps needs the same.
- **A request no browser would send**: requests' own `Accept: */*` with no `Accept-Language` can get a 406 or 403 from a site's firewall (BuzzFeed's 406). Every page goes through `lvm._session`, which asks as Chrome does; a fetch that bypasses it, or headers that drift apart (a User-Agent for one browser, Accept for another), undo that.
- **A check that answers differently each time, or guesses on too little**: a library that picks a random seed per call (langdetect without `DetectorFactory.seed`), or a language or similarity check run on a few words. Fix the seed, and judge only what's long enough to judge, as `is_english_title` does.
- **A list rule that matches text anywhere instead of where it belongs**: a number looked for with `in` (the "1." in "11." or "$1.99"), or a list handled line by line where an item can run over several lines. Anchor the pattern (`^` with `re.MULTILINE`) and compare the whole sequence, as `is_correctly_formatted_list` and `put_list_in_order` do.
- **A thread and a request sharing state** without a lock: the scheduler's thread writes while a route reads.
- **A credential or token in a log, an error detail or a response.**
- **Scraped text shown unescaped** on the dashboard.

**Not working as designed**
- **Blocking work on the event loop.** An `async def` route or loop that queries SQLite, reads or writes a file, or calls something synchronous holds every other request meanwhile. `def` routes run on threads and are fine. Find them: `grep -rn "async def" server/api server/services`.
- **Check, then write, with nothing between to stop a second request**: a `SELECT` then an `INSERT`, a count then a record. Needs a unique index, a conditional `UPDATE`, or a lock.
- **A read that writes**: a GET route that commits.
- **Memory read before it's bounded**: an upload read whole before its size is checked, a table loaded whole to count it.
- **In-memory state that only grows**: module-level dicts keyed by something a visitor chooses (an email, an address).
- **The client treating every failure as one kind**: a `catch` that signs out, clears state or redirects on a 5xx or a dropped connection as it would on a 401. Also the reverse: a dropped connection shown in each browser's own words ("Failed to fetch") rather than said plainly (`apiFetch`).
- **Bytes read as text**: `atob` gives one character per byte, so a token's UTF-8 claims (a name with an accent) come out garbled. Decode the bytes with `TextDecoder`, as `readPerson` does.
- **A connection or cursor left open** on an error path, or a transaction left uncommitted across a slow call.
- **Days counted in the wrong time zone**: `.date()` on a UTC time where the local day is meant.
- **A layering rule broken in a way that causes a bug**, not only one that's untidy: see `CLAUDE.md`'s *Layering*.

**Inefficiencies**
- **One query per row**: `.execute(` inside a loop, in a list route or what serializes its rows.
- **A filter the index can't serve**: a function around the column (`lower(x)`, `strftime(...)`), `LIKE '%x'`.
- **A missing index** on a column filtered or grouped on every page load.
- **A new HTTP client or connection per outgoing call**: a TLS handshake each time.
- **The same work repeated by requests a page sends together**, or sequential round trips the client could send together.
- **CI** downloading or rebuilding what a cache could keep; steps that run when nothing they test changed. `ci.yml` is also called by `deploy.yml`, where everything must still run.

**Duplication**

Only what must change together counts: the same rule, query or sequence written in two places, where changing one and not the other would be a bug. Code that merely looks alike, or two short lines repeated, is not a finding, and neither are tests that spell out their own setup.
- **The same query or rule in two services**: one of them owns it and the other calls it.
- **The same few lines repeated with one word changed.**
- **A serializer or helper two routes each have their own copy of**, or one route importing it from another: it lives in `services/` (*Layering*).
- **A rule kept on both sides**, server and client: these can't be merged; check the two still agree and that each names the other.
- **Client screens repeating a fetch, a form or a dialog** that a shared hook or component already has, or should.

Find candidates by grepping a distinctive line of one copy for the others; say how many copies there are and what differs between them. A merge that needs flags to cover the differences is worse than the copies: say so and leave them.

**Verify before reporting**
- **Read the callers.** A guard two frames up, a router-level dependency or a constraint in `db/migrations.py` often already prevents it.
- **Ask the database, not the code that made it.** `PRAGMA index_list(<table>)` on a database the migrations just made, and `EXPLAIN QUERY PLAN` for whether a query reads an index.
- **Reproduce what's cheap to reproduce**: a failing test in the scratchpad, a query count, a build size. Say "reproduced", "verified by reading" or "suspected" on each finding.
- **Size it honestly.** A scan of a table that holds tens of rows is not a finding; one that grows with history, or runs on a schedule, is.

## 4. Already decided: don't report these again

Report one of these only if something new changes the decision, and say what.

- **A title's list count can be a year**: `get_article_list_count` takes the first number in the title, so "Best 2024 Albums: 10 Picks" counts 2024 and the article is skipped. The user chose to leave it: skipping an article is safe, and such titles are rare.
- **Cracked's parser reads each link's `title` attribute directly**, so a card without one would fail that sweep. The user chose to leave it: Cracked's cards carry it, and a page that changed is a parser fix when it happens (CLAUDE.md).

## 5. Report, then ask

Lead with whether the tests pass and what was and wasn't read. Then findings, most serious first, in three groups (**Not working as designed**, **Optimizations**, **Duplication**), each one a short paragraph:

```markdown
N. **<What goes wrong, in plain words>.** <Where: `path/file.py:line`>. <The path to failure, or what it costs>. <Reproduced | verified by reading | suspected>.
```

End with which few to start with and why. Keep it to what the reader would act on: no list of everything checked and found fine.

Then stop and let the user choose. "Fix all" includes only what can be fixed safely as a change of its own: name what's left out and why, rather than half-doing it.

## 6. Fix what was chosen

**Group the fixes into branches so that no two branches touch the same file**, tests included. Fixes that share a file go together; small unrelated ones can share one branch. Independent branches merge in any order and are reviewed one at a time. Typical groups here: the scheduler and sweep, the parsers, the record of runs, the client.

For each branch:
1. Create it as the `create-feature-branch` skill does: `git switch --no-track -c feature/<desc> origin/develop`, then the two `git config` lines.
2. List every file the group needs, read them in one pass, make the edits, then run the tests once.
3. Follow the conventions that apply: a new column is an `ALTER` in `run_migrations` (`db/migrations.py`) with a default that suits the rows already there; a unique index on rows that weren't always unique first removes the doubles there, or the server won't start. Bring what you touch in line with *Layering*.
4. Add or extend a test for each fix that fails without it. Merging duplicates changes no behaviour: the tests that covered each copy must still pass untouched, and that is its test.
5. Run what CI runs for what changed: `python -m pytest -q` for the server; `npx tsc --noEmit`, `yarn test --run` and `yarn build` for the client.
6. For a branch that changes migrations, background work, sign-in or access: have a sub-agent on a cheap model, given only the diff and one paragraph of intent, look for real bugs. Judge each thing it reports against the code before acting on it.
7. Commit, push, and open the PR into `develop` with a title and description written as `done-message` writes them. No attribution lines. List under `### Notes` anything that changes behaviour, deletes data or runs at startup, and what moved between layers.

Don't offer to watch the PRs.

## 7. Close

- A table of the PRs: number, branch, what each fixes.
- What changes behaviour, in one list the user reads before merging.
- What wasn't done, and why.
- Any correction to the report: a finding that turned out wrong while fixing it is said plainly.

## Keeping this skill current

This file is the memory between reviews. In the PR that makes the change:
- A new kind of problem found and fixed gets a line in step 3, worded as the kind, with the pattern that fixes it.
- A finding the user declines, or one that turns out to be by design, goes in step 4 with the reason.
- A new background loop, outside service, top-level folder or big file goes in step 2's reading order.
- A step-4 decision that's reversed is taken off the list.

The other repositories (sdc-management-app, tools-dashboard, spending-insights, list-parser-bot) each have their own copy, with their own reading order, checks and decisions: a kind of problem found here that they could have too is worth porting (`port-improvements`).
