---
name: create-feature-branch
description: Create a new feature branch named feature/<short-description> based off the latest origin/develop (never main), deriving the description from the currently staged changes and carrying all uncommitted work (staged, unstaged, untracked) over to the new branch. The branch pushes to its own origin/feature/<desc>, never to develop. Use when the user asks to create/start a feature branch or move current work onto a new branch, AND whenever Claude itself needs a branch before changing code (e.g. work requested while on develop or main) — never create branches by hand with `git switch -c`/`git checkout -b`.
---

# Create Feature Branch

Creates `feature/<short-description>` from the latest **`origin/develop`** and moves the current uncommitted work onto it.

**Feature branches always start from `develop`, never from `main`.** `main` is the release branch that deploys to Azure; work goes into `develop` first through pull requests. Do this whatever branch is checked out when the skill runs, including `main`.

If the user passes an argument (e.g. `/create-feature-branch polygon parser fix`), use it as the description instead of deriving one — still normalize it per step 2.

## 1. Inspect the changes

Run these to understand the current state:

```bash
git status --short
git branch --show-current
git diff --cached --stat
git diff --cached
```

- Derive the description from the **staged** changes (`git diff --cached`). For large diffs, read `--stat` first and sample the most significant files rather than the whole diff.
- If nothing is staged, fall back to unstaged + untracked changes (`git diff --stat`, `git status --short`) and tell the user you did so.
- If there are no changes at all, as when the branch is made before the work starts, name it from the task at hand: what the user asked for, or what you're about to change. Ask the user for a description only when there's no task to name it from.
- **Commits don't come along.** Only uncommitted work moves to the new branch. If the current branch has commits `develop` doesn't (`git log --oneline origin/develop..HEAD`, after the fetch in step 3), and it isn't `develop` or `main`, tell the user they stay on that branch and ask whether that's what they want before going on.

## 2. Build the branch name

- Format: `feature/<short-description>`
- `<short-description>`: 2–5 words, lowercase kebab-case, `[a-z0-9-]` only, max ~40 characters, describing *what the change does* (e.g. `feature/polygon-parser-fix`, `feature/sweep-history-filters`). Avoid generic names like `updates` or `changes`.
- Check it doesn't already exist locally or on the remote:
  ```bash
  git show-ref --verify --quiet refs/heads/feature/<desc>
  git ls-remote --exit-code --heads origin feature/<desc>
  ```
  If it exists, append a distinguishing word or `-2`.

## 3. Create the branch off the latest develop, carrying changes over

Always base on the most recent `develop` from the remote, not on `main` and not on whatever is checked out:

```bash
git fetch origin develop
```

Then stash everything (including untracked files), create the branch from `origin/develop`, and restore the work with its staged/unstaged split intact:

```bash
git stash push --include-untracked -m "create-feature-branch: carry-over"
git switch --no-track -c feature/<desc> origin/develop
git config branch.feature/<desc>.remote origin
git config branch.feature/<desc>.merge refs/heads/feature/<desc>
git stash pop --index
```

- **Never omit `--no-track`.** Without it, `git switch -c <branch> origin/develop` makes `origin/develop` the upstream, so the user's plain `git push` targets `develop` and the repo's `.githooks/pre-push` refuses it ("failed to push some refs").
- The two `git config` lines make the upstream the branch's own `origin/feature/<desc>` without pushing anything. A plain `git push` then creates and updates that remote branch. Without them it fails with "has no upstream branch".
- If `git fetch` fails (offline / no remote), use local `develop` instead of `origin/develop` and tell the user. Never fall back to `main`.
- If there were no changes to stash, skip the stash/pop steps.
- Do not push the branch unless the user asks.

## 4. Handle conflicts on `stash pop`

If the current branch diverged from `develop`, `git stash pop --index` may conflict. In that case:

- The stash is **kept** (git does not drop it on conflict) — never run `git stash drop` or `git stash clear` until the work is fully restored.
- Report the conflicting files (`git status --short`) to the user and ask whether to resolve them together or abort.
- To abort: `git reset --hard` is destructive — confirm with the user first, then `git switch <original-branch>` and `git stash pop --index` to restore the original state.
- If `--index` alone fails (staged state can't be reapplied cleanly) but a plain `git stash pop` would work, tell the user staging was lost and retry without `--index`.

## 5. Check where it pushes

```bash
git config branch.feature/<desc>.merge
git push --dry-run --porcelain
```

- The first must print `refs/heads/feature/<desc>`. `develop` or `main` means it was set up wrong; repeat the two `git config` lines from step 3.
- The dry run must show `refs/heads/feature/<desc>:refs/heads/feature/<desc>` and send nothing. If it names `develop` or `main`, or errors, fix the upstream before reporting.

## 6. Report

Finish with a short summary:
- The new branch name and that it's based on `origin/develop` (with the commit short SHA: `git rev-parse --short HEAD`).
- That a plain `git push` publishes it to `origin/feature/<desc>`.
- The branch the work was moved from.
- `git status --short` output summary confirming the changes came across (staged vs unstaged counts).
- Do not commit or push unless the user asks.
