---
name: port-improvements
description: Find the improvements merged into one of the sibling repositories (sdc-management-app, tools-dashboard, spending-insights, list-parser-bot) in the last 7 days, or over its whole history, and work out which ones the other repositories should get. Improvements include performance, CI, deploy, test speed, caching or robustness work, and new or changed skills and CLAUDE.md rules that would serve the others too. Measure what each would gain there, report it, then on the user's go-ahead apply them to each target on one feature branch per repository, one commit per improvement, with a PR into develop. Use when the user asks to port, copy, carry over or apply another repo's optimizations, improvements, skills or instructions, or asks whether another repo's recent changes apply here.
---

# Port Improvements

The four repositories share one architecture: a FastAPI + SQLite server (`server/`), a React + Vite + Tailwind client (`client/`), Azure deploys from `.github/workflows/`, and the same `.claude/skills/`. An improvement made in one of them often fits the others, but **adapt each one, never copy it**: the repositories differ in ways that matter (see *Differences*).

**This runs on the user's own computer**, where the four repositories sit side by side. If the other folders aren't there (a cloud session has only this repository), say so and stop: don't guess at a repository you can't read.

It runs in two phases: **analyze** (read-only, ends with a report and one question), then **apply** (branches, commits, PRs). Don't start applying until the user says which improvements to apply, unless the arguments already say so (e.g. `apply all`).

## Arguments

`/port-improvements <source> [since] [targets] [apply all]`

- `<source>`: the repository the improvements come from, by folder name (`sdc-management-app`). Required; ask if missing.
- `[since]`: which of its commits to look at: a date (`2026-11-07`), `today`, `yesterday`, `last 3 days`, PR numbers (`#152 #166`), a commit range, or `all` for every commit on `origin/develop`, however old. Default: the last 7 days.
- `[targets]`: the repositories to bring them to. Default: the other three.
- `apply all`: skip the question at the end of phase 1 and apply everything marked **Apply**.

## Repositories

All four are folders next to each other, in the parent folder of this repository (find it from this repository's own path; don't assume a drive or a user folder):

| Folder | Env prefix | Database access | Notes |
| --- | --- | --- | --- |
| `sdc-management-app` | `SDC_` | SQLAlchemy ORM | has its own `site/`; client served by its own Static Web App |
| `tools-dashboard` | `TOOLS_` | raw `sqlite3` | owns the site: `client/web-root/staticwebapp.config.json` is the config for **every** app under `/tools/` |
| `spending-insights` | `SPENDING_` | raw `sqlite3` | `shared/` holds test cases both server and client tests read |
| `list-parser-bot` | `LISTBOT_` | raw `sqlite3` | a scheduler thread runs sweeps in the API process |

Re-check this table against each repository's `CLAUDE.md` before relying on it; update it here when it's wrong.

This skill is the same file in all four repositories (`.claude/skills/port-improvements/SKILL.md`). A change to it goes into all four, so they stay identical.

## Phase 1: analyze

### 1. Get every repository up to date, read-only

For the source and each target:

```bash
git -C <repo> fetch origin
git -C <repo> status --short
git -C <repo> branch --show-current
```

Analysis reads `origin/develop`, so a target on another branch or with uncommitted work is fine for now; note it, since phase 2 needs it clean.

### 2. List the source's improvements

```bash
git -C <source> log origin/develop --since="7 days ago" --format='--- %h %ad %s%n%b' --date=short --stat
```

With `all`, drop `--since`. A whole history is long: start from `--format='%h %ad %s' --date=short` with `--stat`, skip by subject and files what is clearly feature work or a bump, and read in full only the rest.

Sort each commit into one of:

- **Improvement**: performance (startup, queries, bundle size, caching), test speed, CI time, deploy reliability, security headers, robustness. These are candidates.
- **Workflow and instructions**: a new or changed skill (`.claude/skills/`), a `CLAUDE.md` rule (conventions, layering, working style, git), `.claude/settings.json`, `.githooks/`, `.github/dependabot.yml`. Candidates too, when the rule or skill isn't about the source's own domain: a git, review, testing, deploy or writing rule usually fits every repository; one about the source's own screens or data doesn't.
- **Feature or fix specific to the source** (its own screens, billing, domain rules): skip, one line each in the report.
- **Dependency bumps**: skip.

A commit can mix them: take only the improvement or workflow part. Instruction changes often ride along in a feature commit, so look at the `--stat` of every commit for `CLAUDE.md` and `.claude/` files, not only at the subjects. Read each candidate's full diff (`git -C <source> show <sha>`) and its PR description; split it into its separate ideas (one commit may hold several, e.g. parallel tests + disk syncing + a shared TLS context).

### 3. Judge each idea against each target

For every idea × target, find out, with evidence rather than guesses:

1. **Already there?** Grep the target for the change itself (a flag, a header, a pattern) and `git log origin/develop --grep` for the same subject. Ported already → *Already has*.
2. **Does the target have the problem?** Find the target's equivalent code. A lazy import of an SDK only helps if the target imports something heavy at start; query batching only helps where the target queries in a loop; a shared TLS context only helps if the target makes outgoing HTTPS calls.
3. **Measure what it would gain**, on the target as it is now. Use these, writing anything temporary to the scratchpad, never into the repository:
   - `<python>` below is the target's own virtual environment: `venv\Scripts\python.exe` on Windows, `venv/bin/python` on Linux, from its `server/`.
   - Test suites: `cd server && <python> -m pytest -q -p no:cacheprovider --durations=5`; to try a test-only change, put it in a pytest plugin in the scratchpad and load it with `PYTHONPATH=<scratch> python -m pytest -p <plugin>`. Run twice when timings are close: this machine is noisy.
   - Startup: `<python> -X importtime -c "import main" 2>&1 | sort -t'|' -k2 -n | tail`.
   - Client bundle: `npx vite build --outDir <scratch>/build-<repo> --emptyOutDir` from `client/` (never into `client/dist`).
   - Queries: look for `.execute(` or ORM loads inside loops; count them per request if it's unclear.
   - Skills and `CLAUDE.md`: compare with the target's own copy (`diff <source>/.claude/skills/<name>/SKILL.md <target>/.claude/skills/<name>/SKILL.md`, and the matching `CLAUDE.md` section). The copies differ on purpose in examples, paths and names, so judge whether the rule or step is missing, not whether the text matches. The gain is what the rule prevents: name the mistake it stops, or the step it saves.
4. **Verdict**:
   - **Apply**: a clear gain for little risk.
   - **Small gain**: works but gains little; say how little.
   - **Not worth it**: gain too small for the risk or noise (say why, with the number).
   - **Not applicable**: the target doesn't have the problem (say what you checked).
   - **Already has**.

### 4. Report and ask

Report, per idea: one line on what the source changed (`#NN`), then the verdict for each target with its evidence (the measured before/after, or what was checked). Order: **Apply** first, biggest gain first; then **Small gain**, **Not worth it**, **Not applicable**; skipped source commits last, one line each.

Then ask **one** question: which to apply (default: everything marked **Apply**). Stop here unless the arguments said `apply all`.

## Phase 2: apply

Work through the targets one at a time. Finish a target (PR open) before starting the next.

### For each target

1. **Read its rules first**: its `CLAUDE.md`, and the files each change touches, in one pass. Its conventions win over the source's: layering, env var prefix, comment style, where tests go.
2. **Branch first**, before editing anything, so nothing is changed while `develop` is checked out. The working tree must be clean (if it isn't, ask the user first). Then follow the target's own `.claude/skills/create-feature-branch/SKILL.md` (read the file in the target: the Skill tool loads this repository's copy, and the copies differ slightly). One branch per target for all its improvements, named for what they do (`feature/faster-tests-and-ci`).
3. **Make the changes** on that branch. Adapt each one (see *Differences*). A skill or `CLAUDE.md` rule takes the target's names, paths, commands, env prefix and examples; a rule goes into the matching section of the target's `CLAUDE.md`, in its wording style; a new skill is also named where the target's `CLAUDE.md` lists its skills. Add or extend a test where the change has behaviour a test can hold (a config rule every app must follow, an import that must stay lazy, a query count that mustn't grow). Update the docs a change makes wrong (README commands, `docs/apps.md`, `requirements-dev.txt` notes).
4. **Run its checks once**: server tests, client tests, `yarn build`. Fix failures before going on. Compare against the phase 1 measurement and use the new numbers in the commit and PR text.
5. **Commit each improvement separately**, staging only its files, with the message the target's `.claude/skills/done-message/SKILL.md` describes. No attribution lines.
6. **Push and open the PR into `develop`** with `gh pr create --base develop` (or the GitHub tools, where there is no `gh`), title and description per the target's `done-message` skill. In `### Notes`, put what someone must do (a new dev requirements file, a doc an app must follow, `fetch-depth: 0`).

Never merge the PRs, and don't offer to watch them for CI.

### When all targets are done

When the changes are large or touch CI or deploys, spawn a sub-agent on a cheap model, with only the branch names and a short list of what changed, to review all the branches with fresh eyes (CI conditions that skip needed steps, configs that could break the deploy, names left undefined by a lazy import, removed packages still imported). Check each finding yourself before acting on it: fix real ones on the same branch, and say which you dismissed and why.

Finish with, per target: the PR link, each commit and its measured effect, and anything the user must do.

## Differences to adapt for

These are what made earlier ports differ from the source. Check each one that the change touches.

- **ORM vs raw `sqlite3`**: an SQLAlchemy `event.listens_for(Engine, "connect")` hook becomes a wrapper around `sqlite3.connect` in `tests/conftest.py`, set before the app is imported (`from db.session import connect` copies the name, so patching `db.session.connect` misses callers). `selectinload` batching becomes a joined or grouped SQL query.
- **The site config lives in tools-dashboard**: a header or route for any app's built files goes in tools-dashboard's `client/web-root/staticwebapp.config.json`, once per app path, and `test_site_config.py` checks every app in `server/apps.json` has it. Static Web Apps allows a wildcard only at a route's end.
- **Tests that read across folders**: tools-dashboard's server tests read `client/web-root/` and `client/public/`; spending-insights' server and client tests both read `shared/`. A CI rule that skips a side by changed paths must count those as that side.
- **CI reused by deploys**: `ci.yml` is called by `deploy.yml` (`workflow_call`), where the event is never `pull_request`. Anything that skips steps must still run everything there and for PRs into `main`.
- **Import-time work**: a lazy import must come with no module-level use of the name; keep type hints as strings with `if TYPE_CHECKING:`. Check for work done while a module imports (e.g. a hash computed at import) before patching things in `conftest.py`: patches must come before `from main import app`.
- **What the deployed API installs**: Azure installs `server/requirements.txt`. A package only `server/dev/` scripts use belongs in `requirements-dev.txt`.
- **Background work in the process**: list-parser-bot's scheduler uses praw soon after start, so deferring that import saves nothing.
- **Python 3.14** everywhere (CI and Azure): annotations aren't evaluated until read.

When a port goes wrong because of a difference not listed here, add it to this list in the same PR.
