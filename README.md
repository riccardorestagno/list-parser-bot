# List Parser Bot

A Reddit bot that posts list articles to [r/buzzfeedbot](https://www.reddit.com/r/buzzfeedbot).
It reads the latest articles of Business Insider, BuzzFeed, Cracked and Screen Rant, finds the
lists (a number in the title), and posts the title and every point of the list as a text
post, so nobody has to click through to read them.

It runs as an API on Azure that sweeps the sites every 90 minutes, and a small page on the
tools dashboard, at **https://www.riccardorestagno.com/tools/list-parser-bot/**, shows the
latest sweeps: what each posted, or why it didn't.

## How it runs

Each **sweep** goes through the sites in turn, starting with the one posted from least
recently (the flairs of the subreddit's latest posts say which), and stops at the first
that has a list article not posted yet. Which sites are read, their archive pages and the
words that keep an article out are in `server/bot/config.py`.

The API sweeps on a **schedule** (`server/services/scheduler.py`): a thread in the API's
process starts one every `LISTBOT_SWEEP_MINUTES` (90), timed from the start of the last
one, so a restart or a deploy neither sweeps early nor skips one. App Service's Always On
keeps the API, and so the schedule, running. Every sweep is recorded in a small SQLite
database (`runs.db`), which the page reads; the latest 500 are kept.

When a sweep fails:

  - **Reddit or a site couldn't be reached** (Reddit answering 500, 502 or 503, a connection
    error or a timeout): it's recorded, and the next sweep tries again.
  - **Anything else**: it's recorded with its traceback, and the moderator gets a Reddit
    message, once when sweeps start failing rather than on every sweep after.

## Quick Start

### Server

```bash
cd server
python -m venv venv
venv\Scripts\activate             # or: source venv/bin/activate
pip install -r requirements.txt

# The Reddit account, and sign-in turned off on your own computer
copy .env.example .env            # or: cp .env.example .env, then fill in LISTBOT_REDDIT_*

python main.py                    # API on http://localhost:8002, docs at /docs
```

The API doesn't sweep on your computer unless `LISTBOT_SCHEDULE_ENABLED=true` is in
`server/.env`: sweeping posts to Reddit. To sweep once, now:

```bash
cd server
python -m dev.sweep --dry-run     # finds what it would post, posts and records nothing
python -m dev.sweep               # posts it, and records the run like the schedule does
python -m bot.parsers.cracked     # one site's parser alone, without posting
```

### Client

```bash
cd client
yarn install
yarn dev                          # http://localhost:5175, /api proxied to the API on :8002
```

## Tests

```bash
cd server && python -m pytest -q       # server tests (pip install pytest first)
cd client && yarn test --run           # client tests (vitest)
cd client && yarn build                # type-check + build; CI runs this
```

The tests never reach Reddit or the sites: the sweep is replaced with stand-ins.

## Branches and releases

Work goes on a `feature/<desc>` branch off `develop`, and into `develop` through a
pull request (squash). A release is a pull request from `develop` into `main`
(merge commit); an urgent fix can go from a `hotfix/` branch straight into `main`.
`.githooks/pre-push` refuses direct pushes to either; turn it on once per clone:

```bash
git config core.hooksPath .githooks
```

  - **CI** (`.github/workflows/ci.yml`) runs the server and client tests and the
    build on every pull request into `develop` or `main`, and fails a pull request
    into `main` that doesn't come from `develop` or `hotfix/`.
  - **Deploy** (`.github/workflows/deploy.yml`) runs on every push to `main`:
    it tests and builds, deploys `server/` to the API, then tags the commit with the
    next version and publishes a GitHub Release with the build of `client/` attached
    (`web.zip`). Then it asks the tools dashboard to deploy the site, which puts
    that build in place. A release from `develop` raises the minor number, a
    `hotfix/` the patch, and a pull request labelled `release:major` the major.
  - **Dependabot** opens weekly update pull requests into `develop`.

## Sign-in

People sign in on the tools dashboard ([riccardorestagno/tools-dashboard](https://github.com/riccardorestagno/tools-dashboard)),
at `/tools/login`, and open this app from `/tools/dashboard`. The dashboard keeps a token in
the browser under `tools.token`; this app sends it with every request
(`client/src/utils/api.ts: apiFetch`). The API checks it with the dashboard's public key
(`server/services/auth.py`): genuine, unexpired, and naming `list-parser-bot`, which the
dashboard gives only to accounts that have the app. Without it the API answers 401 and the
page sends you to sign in, coming back here afterwards.

Who may use the app is decided on the dashboard: `python -m dev.accounts grant EMAIL list-parser-bot`
there. Its `docs/apps.md` is the contract this app follows.

`/` and `/health` need no sign-in: App Service's Always On calls `/`.

## Deploying to Azure

  - **Page**: the site belongs to the tools dashboard, which deploys it to Azure Static
    Web Apps with this app's latest `web.zip` at `/tools/list-parser-bot/`.
  - **API**: Azure App Service, Python 3.14 (`list-parser-bot-prod-api`), at
    `https://list-parser-bot-prod-api.azurewebsites.net`. It sweeps on the schedule; the
    record of sweeps lives in `/home/data`, which outlives redeploys.

Once, from the repository root in PowerShell (needs the Azure CLI, signed in with `az login`),
after the tools dashboard's API is deployed, with the Reddit account in `server/.env`:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\azure\provision.ps1     # the API, the dashboard's sign-in key, the Reddit account
powershell -ExecutionPolicy Bypass -File deploy\azure\setup-github.ps1  # lets deploy.yml sign in to Azure
```

`setup-github.ps1` prints `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
`AZURE_SUBSCRIPTION_ID`: add them to the repository's Actions **variables**
(they're identifiers, not secrets). Then add the Actions **secret**
`DASHBOARD_DISPATCH_TOKEN`: a [fine-grained token](https://github.com/settings/personal-access-tokens/new)
with only `riccardorestagno/tools-dashboard` and **Contents: read and write**, so each
deploy can start the site's. It expires; make a new one when it does. From then on,
merging into `main` deploys. `deploy\azure\deploy.ps1` deploys the API from your
computer instead.

The tools dashboard lists the app in its `server/apps.json`, and its secret `APPS_READ_TOKEN`
needs this repository added (**Contents: read**) to download `web.zip`.

Once the first deploy is live, stop the bot running anywhere else (the old Docker
container), or both will post.

If the dashboard's signing key changes, or the Reddit account's password does, run
`provision.ps1` again: it fetches the new public key and sends what's in `server/.env`.
Until then, every request is refused, or every sweep fails.

The API runs on the tools dashboard's App Service plan, `tools-prod-plan`, which every tool
shares; this repository has no plan of its own.

**The API must stay on one instance.** Each instance runs its own schedule, so two would both
post, and its SQLite database sits on `/home`, a network share where two writers lock each other
out or corrupt it. The plan has per-site scaling on, so other tools can scale out while
`provision.ps1` pins this app to one instance (`siteConfig.numberOfWorkers=1`). With per-site
scaling off, the script refuses to run if the plan can have more than one instance, and warns
otherwise.

### Environment Variables

Every setting is optional but the Reddit account; put them in `server/.env` (see
`server/.env.example`).

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `LISTBOT_REDDIT_CLIENT_ID`, `_CLIENT_SECRET`, `_USER_AGENT`, `_USERNAME`, `_PASSWORD` | empty | The Reddit account the bot posts as (a "script" app at https://www.reddit.com/prefs/apps) |
| `LISTBOT_SCHEDULE_ENABLED` | `false` | `true` sweeps on the schedule, posting to Reddit: the deployed API |
| `LISTBOT_SWEEP_MINUTES` | `90` | Minutes from the start of one sweep to the start of the next |
| `LISTBOT_DATA_DIR` | `server/data` | Where the record of sweeps lives |
| `LISTBOT_ALLOWED_ORIGINS` | `http://localhost:5175,http://127.0.0.1:5175` | Origins allowed to call the API |
| `LISTBOT_API_DOCS` | `true` | `false` hides `/docs` and `/redoc` |
| `LISTBOT_AUTH_PUBLIC_KEY` | empty | The tools dashboard's public key (its `/auth/public-key`); line breaks may be written `\n` |
| `LISTBOT_AUTH_ISSUER` | `riccardorestagno.com/tools` | Who signs the tokens; the dashboard's `/auth/public-key` says |
| `LISTBOT_AUTH_DISABLED` | `false` | `true` lets every request through: development only, never deployed. Without it or a key, every request is refused |

The client reads `VITE_API_URL` (the API's address; a relative `/api` when
unset) and `VITE_BASE_PATH` (where it's served; `/` when unset).

## Author

Rick Restagno
