# List Parser Bot

A Reddit bot that posts list articles to r/buzzfeedbot, and a dashboard of what it did. A FastAPI server sweeps a few websites on a schedule for list articles (a number in the title) and posts the first one it hasn't posted before as a text post with every list item; it records each sweep in SQLite. A React client shows the sweeps and the bot's status. Deployed at riccardorestagno.com/tools/list-parser-bot, behind the sign-in of the tools dashboard (riccardorestagno/tools-dashboard), which owns the site and deploys this app's build; its `docs/apps.md` is the contract.

## Map

```
server/                  FastAPI + SQLite (sqlite3)
  main.py                app, CORS, router registration, the scheduler's start and stop, /health
  settings.py            every environment variable, read once; loads server/.env
  api/routes/            one module per resource (runs, status); keep them thin
  api/errors.py          turns a service's AppError into the JSON an HTTPException gives
  api/auth.py            the dependency every router but /health has: the dashboard's token
  services/              business rules called by the routes (runs, sweep, scheduler, status, auth)
  bot/                   the bot itself: the controller, one parser per website, Reddit and list helpers
  schemas/               request and response models, enums
  db/session.py          the connection every caller uses
  db/migrations.py       runs on startup: creates missing tables and columns
  dev/                   scripts a developer runs (sweep.py: one sweep by hand)
  tests/                 pytest; shared setup in conftest.py
client/src/              React 19 + TypeScript + Vite + Tailwind
  App.tsx                providers and the screen
  features/<feature>/    one folder per area of the screen
  utils/api.ts, types.ts the API helpers (apiFetch sends the token) and shared types
  utils/auth.ts          the dashboard's token in the browser, sending people to sign in
  utils/format.ts        times, durations and lists in words
deploy/azure/            Azure setup scripts (the API; the site is the dashboard's)
```

## Commands

```bash
cd server && python main.py            # API on :8002, docs at /docs (venv + pip install -r requirements.txt first)
cd server && python -m pytest -q       # server tests (needs pytest)
cd server && python -m dev.sweep       # one sweep by hand (posts; --dry-run only looks)
cd client && yarn dev                  # web app on :5175, /api proxied to :8002
cd client && yarn test --run           # client tests (vitest)
cd client && yarn build                # type-check + build; CI runs this
```

## Conventions

- **Nothing posts to Reddit unless asked to**: the schedule is off unless `LISTBOT_SCHEDULE_ENABLED=true`, a parser run by hand or by a test finds without posting, and tests never reach Reddit or the live websites (they stub them).
- **Be gentle with the websites**: keep the pause between article fetches and each parser's limit on articles searched.
- A new website gets its `ArticleType`, its settings in `bot/config.py` (active, archive link, limits), its module in `bot/parsers/`, and its place in the controller. The type's name is the post's flair, and the controller orders parsers by the flairs of the latest posts, so renaming one changes both.
- Websites change their HTML: a parser fix stays within that parser, and says which website changed what.
- Schema changes: add the column in `db/migrations.py` (`CREATE TABLE` for new databases, an `ALTER` in `run_migrations` for existing ones), with a default (or NULL) that suits the rows already there.
- Each resource has a test module in `server/tests/`; add or extend one with the change.
- Never log or return a Reddit credential or a token.
- In the client, import across folders with `@/` (`@/utils/types`) and within a folder with `./`.
- The client calls `API_BASE_URL` (`utils/constants.ts`) through `apiFetch` (`utils/api.ts`), never a bare `fetch` or a hard-coded host, and links nothing to `/`: the app is served under `VITE_BASE_PATH`. The dashboard's pages are `LOGIN_URL` and `DASHBOARD_URL`.
- A new router is included in `main.py` with `dependencies=signed_in`: only `/` and `/health` answer without a sign-in.
- Match the surrounding style: short docstrings and comments that say why, in plain words.
- Scripts a developer runs (`server/dev/`, `deploy/`, package scripts) work on Windows in PowerShell as well as on Linux, where CI runs them: build paths with `path`/`pathlib`. Commands given to the user to run locally are for PowerShell, each saying which folder it runs from.

## Layering: fix it where you touch it

**On every change, bring the code the change touches in line with these rules**, in the same PR: the functions and imports you edit, not whole files or areas the change doesn't reach. Keep each move behaviour-preserving and covered by the existing tests, and list what moved in the PR description. Never add new code that breaks them.

- **Routes stay thin**: read the request, call a service, return. Business rules, the schedule and database access live in `services/`.
- **Routes don't import other routes.** Helpers two routes share live in `services/`; configuration lives in `settings.py`.
- **Environment variables are read once, in `settings.py`**, prefixed `LISTBOT_`, never in route, service or `bot/` modules.
- **`services/`, `bot/` and `db/` don't import from `api/` or FastAPI.** Services raise `AppError` (`services/errors.py`), never `HTTPException`; `api/errors.py` turns it into the same JSON. `bot/` knows nothing of runs or the database: `services/sweep.py` calls it and records what happened. `db/` takes no imports from `services/`.
- **Parsers parse**: they fetch and read a website and return what they found. The rules a list must meet live in `bot/helpers/list_validation_methods.py`, and every Reddit call goes through `bot/helpers/reddit.py`.
- **One owner per transaction**: a service function that opens a connection (`db/session.py`) commits its unit of work once. Helpers that take a connection never commit.

## Working style

- Before changing anything, list every file you'll need and read them in one pass, then make all the edits, then run the tests once.
- Treat all work as a queue of todos: when the user proposes tweaks, changes or corrections, append them to the queue instead of interrupting the current item, and stop only when the whole queue is clear.
- Mistakes are not your fault, so don't apologize: they point to a gap in these instruction files. Describe which instruction (or missing one) caused the mistake and suggest the fix.
- On major changes, spin up a sub-agent with minimal context on a cheap model to review the changes with fresh eyes for possible problems.

## Git

- Create branches with the `create-feature-branch` skill: `feature/<desc>` off `origin/develop`. Never commit on `develop` or `main`.
- Bring `develop` into a feature or bugfix branch with the `merge-with-develop` skill: it merges `origin/develop`, checks what develop changed against the branch's work, and lists what the branch must change to fit, or why nothing needs to.
- Bring improvements from a sibling repository (sdc-management-app, tools-dashboard, spending-insights, list-parser-bot) here, or from here to the others, with the `port-improvements` skill: it finds what was merged there (the last 7 days, or `all`), skills and `CLAUDE.md` rules included, measures what each would gain in the others, and on a go-ahead applies them, one branch and PR per repository.
- When a change is done, the `done-message` skill writes its commit message, PR title and description.
- Outside a release, the `codebase-review` skill reviews the code as it stands (all of it, or one area) for what doesn't work as designed, what could be faster and what is written twice, verifies and ranks what it finds, and on a go-ahead fixes it on branches that share no file, one PR each. **Keep it current in the same PR**: a new kind of problem fixed goes in its checklist, a finding declined or by design in its *Already decided* list, and a new background loop, outside service or top-level folder in its reading order.
- Before a release, the `release-review` skill deep-reviews `origin/main..origin/develop` for bugs and risks, asks which findings to fix, and fixes those on a branch off `develop`. The `release-pr-message` skill then writes the release PR's title, label and description.
- PRs go into `develop` (squash). Releases go `develop` → `main` (merge commit); `hotfix/` branches may go straight to `main`. `.githooks/pre-push` blocks direct pushes to both (`git config core.hooksPath .githooks`).
- Merging into `main` deploys the API, tags the next version with the client's `web.zip` on its release, and starts the tools dashboard's deploy (`.github/workflows/deploy.yml`).
- No Claude attribution in commits or PRs (`.claude/settings.json` turns it off).
- After opening a PR, don't offer to watch it for CI failures or review comments, and don't subscribe to its activity.

## Saving context

- `README.md` covers setup, usage and deploys. Grep for a heading (`grep -n '^#' README.md`) and read only that section.
- Skip `__pycache__/`, `server/data/` (the record of sweeps), `server/venv/`, `client/node_modules/`, `.idea/`, `.vs/` and `server/.env` (the Reddit credentials).
