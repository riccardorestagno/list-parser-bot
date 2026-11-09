---
name: merge-with-develop
description: Merge the latest origin/develop into the current feature/ or bugfix/ branch, after working out what develop changed since the branch started and whether it touches the branch's own work (same files, renamed or changed functions, types, endpoints, columns, parsers and their settings, conventions). Resolves conflicts, runs the checks, and ends with either a detailed list of the changes the branch needs to fit develop, or why develop's changes have no impact on it. Use when the user asks to merge, update or sync their branch with develop, bring develop in, or check whether develop breaks their branch.
---

# Merge With Develop

Brings the latest **`origin/develop`** into the current `feature/` or `bugfix/` branch with a merge commit, and judges what develop's new changes mean for the work on this branch.

A clean `git merge` is not the goal on its own: two branches can merge without a single conflict and still break each other (develop renames a function the branch calls, adds a run column the branch's dashboard doesn't show, changes a type a new component uses). **Always do the impact analysis in step 3, even when the merge will be clean.**

If the user passes an argument (e.g. `/merge-with-develop check only`), and it asks only for the analysis, do steps 1–3 and the report without merging.

## 1. Check the branch

```bash
git branch --show-current
git status --short
git status -sb | head -n1
ls "$(git rev-parse --git-dir)" | grep -E '^(MERGE_HEAD|rebase-merge|rebase-apply|CHERRY_PICK_HEAD)$'   # empty unless one is in progress
```

- **`develop` or `main`: stop.** Nothing is merged into them by hand; they change only through pull requests.
- **`hotfix/…`: stop.** A hotfix starts from `main` and goes into `main`; merging `develop` into it would ship unreleased work in the fix. Tell the user.
- `feature/…` or `bugfix/…`: carry on. Any other name: ask the user whether it is their own working branch before going on.
- A merge, rebase or cherry-pick already in progress (the last command printed something): stop and tell the user; don't stack a second one on it.
- If `git status -sb` says the branch is **behind** its own remote (`origin/<branch>`), someone pushed to it. Stop and ask before going further, so the merge doesn't fork the branch.
- **Uncommitted work** (staged, unstaged or untracked): tell the user, then put it aside and restore it after the merge with its staged/unstaged split intact:
  ```bash
  git stash push --include-untracked -m "merge-with-develop: carry-over"
  # ... merge ...
  git stash pop --index
  ```
  It still counts as the branch's work in step 3. If `stash pop` conflicts, the stash is kept: never `git stash drop` or `git stash clear` until the work is back; report the files and resolve them with the user.

## 2. Fetch develop and find where the branch started

```bash
git fetch origin develop
git merge-base HEAD origin/develop               # where the branch started: <base>
git log --oneline <base>..origin/develop         # what develop gained since the branch started
git log --oneline <base>..HEAD                   # the branch's own commits
```

**Type the commit `merge-base` printed wherever `$BASE` appears below.** Each command runs in a new shell, so a variable set in one is empty in the next, and `git diff --name-status $BASE HEAD` with an empty `$BASE` quietly lists the uncommitted changes instead of the branch's work.

- Always merge **`origin/develop`**, freshly fetched, never the local `develop` (it is usually stale). If the fetch fails, say so and stop rather than merging a stale `develop`.
- If `$BASE..origin/develop` is empty, the branch already has all of develop. Say so and stop; there is nothing to merge or to judge.

## 3. Work out the impact, before merging

### What each side changed

```bash
# This branch: its intent and its files (plus uncommitted work, if any)
git log --format='--- %h %s%n%b' $BASE..HEAD
git diff --name-status $BASE HEAD
git diff --name-status HEAD            # uncommitted, if step 1 found any

# Develop: one squashed PR per commit, "Subject (#NN)" with bullets in the body
git log --format='--- %h %s%n%b' $BASE..origin/develop
git diff --name-status $BASE origin/develop
```

Read the branch's own diff (`git diff $BASE HEAD`, or file by file when it's large) until you can say in a sentence what the branch does. Do the same for each develop PR, from its body and, where the body is short or unclear, its diff (`git show <sha>`).

### Same files

```bash
comm -12 <(git diff --name-only $BASE HEAD | sort) <(git diff --name-only $BASE origin/develop | sort)
```

For each file in both lists, read both sides' changes to it:

```bash
git diff $BASE HEAD -- <file>
git diff $BASE origin/develop -- <file>
```

Note whether they touch the same lines (a conflict to come), the same function or component (a likely interaction even without a conflict), or unrelated parts.

### Same code, different files

This is where clean merges break. Check both directions:

- **Develop → branch.** List what develop renamed, removed, moved, or changed the signature, return value or behaviour of: functions, classes, React components and props, TypeScript types and fields, API endpoints and request/response models, database tables and columns, `ArticleType` values and `bot/config.py` settings, constants, test fixtures. Look for each one in the branch's work:
  ```bash
  git grep -n '<old name>' HEAD -- $(git diff --name-only $BASE HEAD)
  ```
  Also look at the files the branch **added**: they were written against the old code.
- **Branch → develop.** List what the branch renamed, removed or changed the signature of, and look for **new** uses of the old form that develop added:
  ```bash
  git grep -n '<old name>' origin/develop
  ```
  A call site develop added after the branch started was never updated by the branch, and git won't flag it.
- **Behaviour.** If develop changed a business rule in `server/services/` that the branch relies on (what makes a list postable, how an earlier post is found, how a sweep's failure is recorded or reported, when the next sweep runs), work out whether the branch's results or tests still hold.

### Places in this repo that need a look when either side touched them

| Area | What to check |
| --- | --- |
| `server/db/migrations.py` | Both sides added tables or columns: no duplicate names, both kept, each in the `CREATE TABLE` and as an `ALTER` in `run_migrations`; whether one depends on the other's column. |
| `server/bot/helpers/enums.py`, `server/bot/config.py`, `server/bot/controller.py` | Websites added on both sides: both kept, each with its `ArticleType` (no value used twice), its settings and its place in the controller. A renamed type changes the flair the controller orders parsers by. |
| `server/bot/parsers/`, `server/bot/helpers/` | Both sides fixed the same website's parser: keep the fix that matches the website today. Helpers develop changed that the branch's parsers call, and the reverse. |
| `server/services/sweep.py`, `server/services/scheduler.py`, `server/services/runs.py` | How a sweep is run, timed and recorded: the branch's runs still start and finish, and nothing new posts unless the schedule is on. |
| `server/api/auth.py`, `server/services/auth.py` | The dashboard's token check: new routes stay behind `signed_in`, and the contract with the dashboard (its `docs/apps.md`) still holds. |
| `client/src/utils/types.ts`, `client/src/utils/api.ts` | Types and API calls develop changed that the branch's components use, and the reverse. |
| `server/api/routes/`, `server/schemas/`, `server/main.py`, `client/src/App.tsx` | Changed request models, routes registered on both sides, paths that now clash. |
| `server/tests/conftest.py`, `server/tests/tokens.py` | Fixtures develop changed that the branch's tests use. |
| `server/requirements.txt`, `client/package.json`, `client/yarn.lock` | Dependency changes on both sides. Never merge `yarn.lock` by hand (step 4). |
| `CLAUDE.md`, `README.md`, `.claude/skills/` | New conventions from develop that the branch's work must now follow (e.g. a new rule on where code goes or what every feature must include). |
| `.github/workflows/` | New CI checks the branch's code must now pass. |
| `server/settings.py`, `server/.env.example` | New settings the branch's code should read, or names that changed. |

Keep notes as you go: for each develop PR, whether it affects the branch, and why or why not. Step 6 is built from them.

## 4. Merge

**Always merge, never rebase**: the branch may already be pushed, and its pull request is squashed into `develop` anyway, so the merge commit leaves no trace there.

```bash
git merge --no-ff --no-edit origin/develop
```

If it stops on conflicts:

```bash
git status --short                          # UU / AA / DU ... = unresolved
git diff --name-only --diff-filter=U
```

- Resolve each conflict by **keeping both sides' intent**, hunk by hunk, using what step 3 found about each side. Never resolve wholesale with `-X ours`/`-X theirs` or `git checkout --ours/--theirs .`.
- Ask the user when both sides changed the same logic and either choice loses behaviour; show both versions and what each loses.
- `client/yarn.lock`: take develop's (`git checkout --theirs client/yarn.lock`), then `cd client && yarn install` to regenerate it from the merged `package.json`, and `git add` the result. Same idea for any other generated file: regenerate with the repo's tooling, never hand-edit.
- Once every file is resolved: `git add <files>` and `git commit --no-edit`. The default message (`Merge remote-tracking branch 'origin/develop' into <branch>`) is fine; no attribution lines.
- To give up: `git merge --abort` puts the branch back as it was before the merge.

Fixes for the semantic issues found in step 3 do **not** go in the merge commit. They are listed in the report and made afterwards in their own commit, so the merge stays reviewable.

## 5. Check the merged branch

Run the checks for whichever parts either side touched (CLAUDE.md, *Commands*):

```bash
cd server && python -m pytest -q          # anything under server/ changed on either side
cd client && yarn test --run              # anything under client/ changed on either side
cd client && yarn build                   # type-check; CI runs this
```

Run the server's with its virtual environment (`server\venv\Scripts\python.exe` on Windows, `server/venv/bin/python` on Linux), or `python` in a cloud session once the requirements are installed.

- If dependencies aren't installed (no venv, no `node_modules`), install them per the README, or say which checks couldn't run. Never call the merge verified without running them.
- A failure after the merge: work out whose it is. If unsure, check `origin/develop` alone in a throwaway worktree (`git worktree add <scratch dir> origin/develop`, run the same check, then `git worktree remove <scratch dir>`). Failing on develop too → not the branch's, say so. Passing on both sides but failing merged → an interaction, and it goes in the report's list of changes.

## 6. Report

Do not push unless the user asks. Finish with:

**Merge**
- Branch, the merge commit (`git rev-parse --short HEAD`), and how many develop commits came in.
- The develop PRs merged, one line each: `#NN subject`.
- Conflicts and how each was resolved (or "none").
- Checks run and their result; checks that couldn't run and why.

Then **one** of the two verdicts:

**Changes needed to fit develop** — a numbered list, most important first. Each item gives:
1. **Where:** `path/to/file:line` in this branch's code (or the file to add).
2. **Because of:** the develop PR (`#NN`) and what it changed.
3. **Why it matters:** what breaks or goes wrong if left as is (a failing check, a wrong result, a filter one endpoint lost, an export that won't upload back, a convention not followed).
4. **Change:** exactly what to do, specific enough to make without re-doing the analysis (the new name or signature to use, the setting to add to `bot/config.py`, the `ALTER` to add in `run_migrations`, ...).

Then ask whether to make them now, as a separate commit after the merge.

**No impact on this branch** — say so plainly, then for **each** develop PR one line on why it doesn't touch the branch's work: different files and no shared code, shared file but unrelated parts, a renamed function the branch doesn't use, etc. Mention the checks from step 3 that came back empty (e.g. "no new callers of `post_to_reddit` on develop") so the user can see what was looked at, not just the conclusion.
