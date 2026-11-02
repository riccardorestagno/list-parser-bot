---
name: release-pr-message
description: Compare origin/develop with origin/main and write a PR title, label and description for a release pull request merging develop into main, after asking whether it is a major release. Text only, it never creates, pushes or merges anything. Use when the user asks what a develop-to-main / release PR should say, or wants to know what a release would ship.
---

# Release PR Message

Writes the title, label and description of a release pull request from `develop` into `main`, from what `develop` has that `main` doesn't.

**This skill only outputs text.** Never run `gh pr create`, `gh pr merge`, `git push`, `git merge` or anything else that changes a branch or GitHub. If the user then wants the PR opened, they ask for it separately.

## 1. Compare the branches

Always compare the remote branches, freshly fetched, not the local ones:

```bash
git fetch origin main develop
git log --oneline origin/main..origin/develop     # what the release ships
git log --oneline origin/develop..origin/main     # on main but not develop
git log --format='--- %h %s%n%b' origin/main..origin/develop
git diff --stat origin/main...origin/develop
```

- If `origin/main..origin/develop` is empty, say there is nothing to release and stop.
- If `origin/develop..origin/main` is not empty, `main` has commits `develop` lacks (usually a `hotfix/`). Say so at the top. `main` should be merged into `develop` before releasing, otherwise the release PR can conflict or undo the fix.
- Each commit on `develop` is normally one squashed feature PR (`Subject (#NN)`) with its bullets in the body. Build the summary from those bodies, and read the diff of a file whenever a body is missing or unclear.
- Look specifically for changes that matter when they reach production, and read their diff:
  - `.github/workflows/`: deploy or CI behaviour
  - `deploy/`: Azure scripts, one-time setup steps
  - `server/settings.py`, `server/.env.example`: new settings or secrets
  - `server/db/migrations.py`
  - `server/bot/config.py`: websites turned on or off, the subreddit
  - the schedule (`services/scheduler.py`, `LISTBOT_SCHEDULE_ENABLED`, `LISTBOT_SWEEP_MINUTES`): how often production posts
  - anything the README says must be done by hand

## 2. Work out the version

Merging the PR deploys `main`, and the deploy workflow tags it as the next version (README, *Branches and releases*): a release from `develop` raises the minor number, and a PR labelled `release:major` raises the major one.

```bash
git fetch origin --tags
git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1   # none yet means v0.0.0
```

**Always ask the user whether this is a major release** before writing anything, with the AskUserQuestion tool. Never decide it yourself, even when the changes look large or small. Show both versions in the options, e.g. *Minor: v0.4.0 → v0.5.0* (first, as the usual answer) and *Major: v0.4.0 → v1.0.0*, and mention any breaking change you found in step 1 in the question.

## 3. Write the outputs

### PR title
- Imperative, ≤ 70 characters, naming the release's main changes, e.g. `Release: sweep history on the dashboard, Screen Rant parser fix`.
- The GitHub Release is titled `<version>: <PR title without "Release: ">`, so don't put the version in the title.

### PR label
- Major release: `release:major`. Without it the release is minor, whatever the description says.
- Minor release: no label.

### PR description
- Bullets only, short lines, at the feature level. One bullet (or two) per feature PR, not one per file.
- Order by what users notice first, then infrastructure and tooling.
- Add `### Included pull requests` listing each `#NN` with its subject, in the order they were merged.
- Add `### Before merging` only for things that must happen first: one-time setup, settings or secrets to add, a `main` → `develop` merge for a hotfix.
- Add `### Notes` only for what a reviewer must know: what deploys on merge, breaking changes, data migrations.
- Start `### Notes` with the version it deploys as: `Deploys as v0.5.0.` For a major release: `Deploys as v1.0.0 (major: needs the release:major label).`
- Always end `### Notes` with the reminder to merge with a **merge commit, never a squash**. The README explains why.
- The description becomes the GitHub Release notes, so write it for someone reading what changed in that version.
- No filler, no attribution lines (`Co-Authored-By`, "Generated with Claude Code").

## 4. Output format

Start with one line saying how many commits `develop` is ahead of `main` and behind it. Then:

**PR title**
```text
<title>
```

**PR label**
```text
release:major
```
(For a minor release, write `None (minor release)` instead of the block.)

**PR description**
```markdown
- <change>
- <change>

### Included pull requests
- #NN <subject>

### Before merging
- <only if needed>

### Notes
- Deploys as <version>.
- Merge with a merge commit, not a squash.
```

If the user then asks for the PR to be opened, a major release needs `--label release:major` on `gh pr create` (or `gh pr edit <n> --add-label release:major` on an open one).
