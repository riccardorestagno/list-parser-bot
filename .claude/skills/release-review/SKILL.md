---
name: release-review
description: Targeted review of origin/develop vs origin/main hunting for critical bugs, security holes, and data risks. Optimized for low token overhead by analyzing diffs and targeting test runs.
---

# Release Review

Reviews **`origin/develop`** against **`origin/main`** for critical production risks (posting to Reddit, sign-in and secrets, data integrity, migrations).

**Rules:**
- Never change `develop` or `main`, never push, and never open a PR unless explicitly asked. Fixes go on a new branch off `origin/develop` (Step 6).
- Never change code before the user chooses what to fix (Step 5).
- Every finding must be verified against a concrete path to failure before reporting.

---

## 1. Pin What Is Being Reviewed

Fetch remote branches and evaluate the release size:

```bash
git fetch origin main develop
MAIN=$(git rev-parse --short origin/main)
DEV=$(git rev-parse --short origin/develop)

git log --oneline origin/main..origin/develop
git log --oneline origin/develop..origin/main
git diff --stat origin/main...origin/develop
```

- **Empty release:** Stop if there are no changes between `origin/main` and `origin/develop`.
- **Hotfix check:** If commits exist in `origin/develop..origin/main`, warn at the top of the report.

Set up a throwaway worktree:
```bash
WT=$(mktemp -d)/develop
git worktree add --detach "$WT" origin/develop
```
*(Always run `git worktree remove --force "$WT"` when finished).*

---

## 2. Targeted Analysis

Review changed code grouped by risk area (**Posting**, **Access/Security**, **Data/Migrations**, **Deploy/Contracts**).

> **Token Optimization:** Read the diff (`git diff origin/main...origin/develop -- <file>`) first. Read whole files in `$WT` **only** for high-risk files (e.g. the sweep and scheduler, `bot/helpers/reddit.py`, `api/auth.py`, migrations).

### Critical Checklist
- **Posting:** Nothing posts twice (the earlier-post check), nothing posts when the schedule is off or in tests, one sweep at a time, the gap between sweeps kept after restarts, parsers still within their limits and pauses, failures reported to the moderator once rather than every sweep.
- **Access & Security:** Every router but `/` and `/health` behind `signed_in` (the dashboard's token, for this app's id), sign-in never turned off when deployed, Reddit credentials and tokens never logged or returned (a run's error details included), query injection, XSS from scraped titles shown on the dashboard.
- **Data & Migrations:** Safe execution of `db/migrations.py` on existing DBs, default values for existing rows, old runs pruned without losing the latest.
- **Deploy & Contracts:** Schema matching between server and client (`client/src/utils/types.ts` / `api.ts`), the client calling `API_BASE_URL` and nothing at `/` (it is served under `VITE_BASE_PATH`), settings and workflows (`server/settings.py`, `.github/workflows/`).

---

## 3. Targeted Checks

**Do not run the full server/client test suites.** (The dev branch CI already executes the full suite). Run tests **only** for modified or high-risk modules:

```bash
# Run python tests only for affected modules
# (the main clone's venv: venv/bin/python on Linux, venv/Scripts/python.exe on Windows)
cd "$WT/server" && <main clone>/server/venv/bin/python -m pytest -q tests/test_affected_module.py

# Run client tests only if client files changed
cd "$WT/client" && yarn test --run <affected-file-or-pattern>
```

A failing test or broken build on modified code is a **Critical** finding.

---

## 4. Verify & Classify Findings

Disprove candidate issues before adding them to the report. Trace entry points to ensure guards or callers don't already prevent the bug.

**Severity:**
- **Critical:** Posting twice, posting when it shouldn't, an endpoint open without sign-in, a credential leaked, migration failure, broken build.
- **High:** Broken functionality on key user flows, export/import corruption, unhandled edge cases in core logic.
- **Medium / Low:** Minor edge cases, unclear error messages, suboptimal performance.

---

## 5. Report & Choice

Write the concise report to `$(git rev-parse --git-common-dir)/release-review/$DEV.md` and present it:

### Report Format
```markdown
### Release Review: `$MAIN` → `$DEV`

#### Findings
**F1 · Critical · Confirmed — <Short Title>**
- **Where:** `server/services/sweep.py:42`
- **What goes wrong:** <Plain description failure of path>
- **Fix:** <Specific fix minimal proposal>

#### Risks (Non-code)
- <Manual considerations contract migration or steps, warnings>
```

Prompt the user using `AskUserQuestion` to select which findings (`F1`, `F2`, etc.) to resolve. If nothing is selected, clean up the worktree and exit.

---

## 6. Fix Chosen Findings

1. Verify `origin/develop` is still at `$DEV` (`git fetch origin develop`).
2. Create a fix branch `feature/release-review-fixes` off `origin/develop` with the `create-feature-branch` skill.
3. Apply the minimal fix for each selected finding with **one commit per finding**.
4. Add or update unit tests covering the specific failure case.
5. Re-run targeted tests to confirm green status.
6. Clean up worktree:
   ```bash
   git worktree remove --force "$WT"
   ```

---

## 7. Final Summary

Provide a short closing summary:
- Created fix branch and commit list (`git log --oneline origin/develop..HEAD`).
- Targeted test results.
- Unfixed findings and risks carried forward.