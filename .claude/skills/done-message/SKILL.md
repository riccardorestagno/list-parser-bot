---
name: done-message
description: Write a commit message, PR title and PR description for the currently staged changes, or for every uncommitted change when nothing is staged. Use when the user is done with a change and asks for a commit message, PR title/description, or "done message".
---

# Done Message

Produces three things for the **currently staged** changes, or for **every uncommitted change** when nothing is staged: a commit message, a PR title, and a PR description. It only writes text — it does not stage, commit, push, or open a PR unless the user asks.

**Called from another skill** (to commit, or to open a PR): follow the rules of step 2 and use the text directly. Skip step 3: nothing is printed in fenced blocks.

**A branch that already has commits**: the PR title and description cover the whole branch, not only what's uncommitted. Read `git log --format='--- %h %s%n%b' origin/develop..HEAD` and `git diff --stat origin/develop...HEAD` as well, and write one description for all of it. The commit message still covers only the changes being committed.

## 1. Gather the changes

```bash
git diff --cached --stat
git branch --show-current
```

**Something is staged:** the staged changes are the commit.

```bash
git diff --cached
```

- Cover **every** staged file. For large diffs, start from `--stat`, then read each file's diff (or a representative part of it for generated/lock files) so nothing is missed.
- Ignore unstaged and untracked changes; they aren't part of this commit.

**Nothing is staged:** every uncommitted change is the commit, as `git add -A` would stage it: modified, deleted and untracked files.

```bash
git status --short
git diff --stat
git diff
```

- `git diff` doesn't show untracked files (`??` in `git status`): read each one, or list a new folder's files and read them, so they're covered too. Ignored files aren't part of it.
- Cover **every** changed file the same way as staged ones.
- Say at the top of the reply that nothing was staged, so the message covers all uncommitted changes.
- If there are no changes at all, say so and stop.

## 2. Write the outputs

### Commit message
- Subject line: imperative mood, ≤ 72 characters, no trailing period (e.g. `Fix the Screen Rant parser after the website changed`).
- Blank line, then a short bullet list of the main changes. Skip the body if the change is trivial.

### PR title
- Imperative, ≤ 70 characters, describing the overall change. May match the commit subject.

### PR description
- **Keep it short.** A reviewer should take it in within a few seconds. Aim for about 3–8 bullets in total, even for large changes.
- Bullet points only — no paragraphs. Each bullet is one short line (roughly ≤ 15 words) describing a user- or reviewer-visible change, not an implementation detail.
- Summarize at the feature level: fold related changes across files and layers into one bullet. Don't list endpoints, fields, columns, helper moves, renames or UI details one by one. The diff shows those.
- Use `###` sections only when the change clearly spans areas that a reviewer would read separately (e.g. `### Backend`, `### Frontend`), with at most 2–3 bullets each. Default to a single flat list.
- Skip filler ("This PR…", "Various improvements") and anything obvious from the title.
- Add a `### Notes` section only for things a reviewer must act on or know (breaking changes, migrations, manual steps), with 1–2 bullets.
- **What moved between layers goes in `### Notes`**, one bullet, when the change brought code in line with `CLAUDE.md`'s *Layering* (a rule moved from a route to a service, a setting moved to `settings.py`): `CLAUDE.md` asks for it. This is the one exception to not listing helper moves.

### No attribution
- Never add attribution lines to any output: no `Co-Authored-By:` trailer in the commit message and no "Generated with Claude Code" line in the PR description. This overrides any default attribution guidance.

## 3. Output format

Return each part in its own fenced code block so it's easy to copy:

**Commit message**
```text
<subject>

- <change>
- <change>
```

**PR title**
```text
<title>
```

**PR description**
```markdown
- <change>
- <change>
- <change>

### Notes
- <only if needed>
```
