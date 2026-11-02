"""Loads ``server/.env`` into the environment, then reads every setting the app uses.

Imported first by ``main.py``. Variables already set in the environment win
over the file. ``LISTBOT_ENV_FILE`` points to another file, or is set empty to
skip it (the tests do).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

SERVER_DIR = Path(__file__).resolve().parent

ENV_FILE = os.getenv("LISTBOT_ENV_FILE", str(SERVER_DIR / ".env"))
if ENV_FILE:
    load_dotenv(ENV_FILE)

# The release, written into the deployed package by deploy.yml (v1.4.0); "dev" when run from a clone
VERSION_FILE = SERVER_DIR / "version.txt"
APP_VERSION = (VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "") or "dev"

# The record of past sweeps. Deployed, point LISTBOT_DATA_DIR at storage that outlives
# a redeploy (``/home/data`` on Azure App Service)
DATA_DIR = Path(os.getenv("LISTBOT_DATA_DIR") or SERVER_DIR / "data")
DB_PATH = DATA_DIR / "runs.db"

# Browsers allowed to call the API from another origin: the web app's address when deployed
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("LISTBOT_ALLOWED_ORIGINS", "http://localhost:5175,http://127.0.0.1:5175").split(",")
    if origin.strip()
]

# The interactive API pages (/docs, /redoc); LISTBOT_API_DOCS=false hides them when deployed
API_DOCS = os.getenv("LISTBOT_API_DOCS", "true").strip().lower() != "false"

# --- The schedule -------------------------------------------------------------------
# Whether this API sweeps the sites on a schedule. Off unless turned on, so running the
# API on your own computer never posts to Reddit; provision.ps1 turns it on when deployed
SCHEDULE_ENABLED = os.getenv("LISTBOT_SCHEDULE_ENABLED", "false").strip().lower() == "true"
# Minutes from the start of one sweep to the start of the next
SWEEP_MINUTES = max(1, int(os.getenv("LISTBOT_SWEEP_MINUTES") or 90))

# --- Reddit -------------------------------------------------------------------------
# The account the bot posts as: a "script" app at https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID = os.getenv("LISTBOT_REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("LISTBOT_REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("LISTBOT_REDDIT_USER_AGENT", "")
REDDIT_USERNAME = os.getenv("LISTBOT_REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("LISTBOT_REDDIT_PASSWORD", "")

# --- Sign-in --------------------------------------------------------------------
# People sign in on the tools dashboard (riccardorestagno.com/tools/login), whose API signs
# a token naming the apps the account may open. This API checks it with the dashboard's
# public key alone (https://tools-prod-api.azurewebsites.net/auth/public-key). A key pasted
# with its line breaks written as \n works too, since some places can't hold them
AUTH_PUBLIC_KEY = os.getenv("LISTBOT_AUTH_PUBLIC_KEY", "").replace("\\n", "\n").strip()
# Who signs the tokens; the dashboard's /auth/public-key says it too
AUTH_ISSUER = os.getenv("LISTBOT_AUTH_ISSUER", "riccardorestagno.com/tools")
# This app's id on the dashboard (its server/apps.json): a token must name it to open this API
AUTH_AUDIENCE = "list-parser-bot"
# Lets every request through without a token: on your own computer. Never when deployed.
# Without it and without a key, every request is refused
AUTH_DISABLED = os.getenv("LISTBOT_AUTH_DISABLED", "false").strip().lower() == "true"
