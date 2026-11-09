---
name: release-review
description: Review what a release would ship (origin/develop against origin/main) for critical bugs, security holes and data risks, verify each finding, ask which to fix, and fix those on a branch off develop. Reads the diff first and runs only the tests the changes reach. Use when the user asks to review a release, check develop before it goes to main, or look for what could go wrong in production with what's about to ship.
---

# Release Review

Reviews **`origin/develop`** against **`origin/main`** for what could go wrong in production: posting to Reddit, sign-in and secrets, data integrity, migrations.

**Rules:**
- Never change `develop` or `main`, never push, and never open a PR unless asked. Fixes go on a new branch off `origin/develop` (step 6).
- Change no code before the user chooses what to fix (step 5).
- Every finding is checked against a concrete path to failure before it's reported (step 4).

**Values found in one command are written out in the next.** Each command runs in a new shell, so a variable set earlier (`$WT`, `$DEV`) is empty later, and `git diff $BASE HEAD` with an empty `$BASE` quietly shows something else. Below, `<main>`, `<develop>` and `<worktree>` stand for the values step 1 printed: type them in.

---

## 1. Pin what is being reviewed

```bash
git fetch origin main develop
git rev-parse --short origin/main        # <main>
git rev-parse --short origin/develop     # <develop>
git log --oneline origin/main..origin/develop
git log --oneline origin/develop..origin/main
git diff --stat origin/main...origin/develop
```

- **Nothing to release:** stop if `origin/main..origin/develop` is empty.
- **A hotfix on main:** if `origin/develop..origin/main` isn't empty, say so at the top of the report.

Review a throwaway worktree, so the user's working tree isn't touched. Put it in your scratchpad:

```bash
git worktree add --detach <scratchpad>/release-review-<develop> origin/develop     # <worktree>
```

Remove it when the review ends, however it ends: `git worktree remove --force <worktree>`.

---

## 2. Read the changes by risk

Group what changed by risk: **Posting**, **Access/Security**, **Data/Migrations**, **Deploy/Contracts**.

Read the diff first (`git diff origin/main...origin/develop -- <file>`). Read a whole file in the worktree only where the diff can't be judged alone: the sweep and scheduler, `bot/helpers/reddit.py`, `api/auth.py`, migrations.

### What to check
- **Posting:** Nothing posts twice (the earlier-post check), nothing posts when the schedule is off or in tests, one sweep at a time, the gap between sweeps kept after restarts, parsers still within their limits and pauses, failures reported to the moderator once rather than every sweep.
- **Access & Security:** Every router but `/` and `/health` behind `signed_in` (the dashboard's token, for this app's id), sign-in never turned off when deployed, Reddit credentials and tokens never logged or returned (a run's error details included), query injection, XSS from scraped titles shown on the dashboard.
- **Data & Migrations:** Safe execution of `db/migrations.py` on existing DBs, default values for existing rows, old runs pruned without losing the latest.
- **Deploy & Contracts:** Schema matching between server and client (`client/src/utils/types.ts` / `api.ts`), the client calling `API_BASE_URL` and nothing at `/` (it is served under `VITE_BASE_PATH`), settings and workflows (`server/settings.py`, `.github/workflows/`).

---

## 3. Run only what the changes reach

Develop's own CI ran the full suites. Run the tests of the changed modules, and the build when the client changed:

```bash
cd <worktree>/server && <python> -m pytest -q tests/test_<resource>.py
cd <worktree>/client && yarn install --frozen-lockfile && yarn test --run <changed file or pattern> && yarn build
```

- Test modules are in `server/tests/`, named for the route or service they cover.
- `<python>` is the main clone's virtual environment: `server\venv\Scripts\python.exe` on Windows, `server/venv/bin/python` on Linux. In a cloud session there is none: use `python` after `pip install -r requirements.txt pytest pytest-xdist`.
- If a check can't run, say which and why. Don't call it passing.

A failing test or a build that breaks is a **Critical** finding.

---

## 4. Verify and classify

Try to disprove each candidate before it goes in the report: follow it from its entry point and see whether a guard or a caller already prevents it. Mark each one **Confirmed** (reproduced, or the path read end to end) or **Suspected** (with what would settle it).

- **Critical:** Posting twice, posting when it shouldn't, an endpoint open without sign-in, a credential leaked, migration failure, broken build.
- **High:** Broken functionality on key user flows, export/import corruption, unhandled edge cases in core logic.
- **Medium:** an edge case few will meet, an unclear message, something noticeably slower.
- **Low:** cosmetic, or worth knowing but not worth holding the release.

Report all four. Critical and High get the full entry below; Medium and Low one line each.

---

## 5. Report, then ask

Write the report to `<scratchpad>/release-review-<develop>.md` and show it:

```markdown
### Release review: `<main>` → `<develop>`

#### Findings
**F1 · Critical · Confirmed — <what goes wrong, in a few words>**
- **Where:** `server/services/<module>.py:142`
- **What goes wrong:** <who does what, and what they get instead of what they should>
- **Fix:** <the smallest change that fixes it>

**F2 · Medium · Suspected — <one line: where, and what goes wrong>**

#### To do by hand
- <What someone must do around this release that no code change covers: a setting or secret to add, a one-time step, a hotfix to merge back into develop first>
```

Ask which findings to fix (`F1`, `F2`, ...), with the AskUserQuestion tool, or in chat if it isn't available. If none, remove the worktree and stop.

---

## 6. Fix what was chosen

1. Check `origin/develop` is still at `<develop>` (`git fetch origin develop`). If it moved, say so and review what's new before fixing.
2. Create the branch as the `create-feature-branch` skill does, named for what it fixes (`feature/fix-<what>`), never by hand with `git checkout -b`:
   ```bash
   git switch --no-track -c feature/fix-<what> origin/develop
   git config branch.feature/fix-<what>.remote origin
   git config branch.feature/fix-<what>.merge refs/heads/feature/fix-<what>
   ```
3. Make the smallest fix for each chosen finding, **one commit per finding**, each with a test that fails without it.
4. Run the tests of what was touched again.
5. Remove the worktree: `git worktree remove --force <worktree>`.

Don't push or open a PR unless asked.

---

## 7. Close

- The branch and its commits (`git log --oneline origin/develop..HEAD`).
- What was run and how it went.
- The findings left unfixed, and what must be done by hand.
