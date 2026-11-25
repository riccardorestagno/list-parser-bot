"""The API starts without loading the bot: praw, BeautifulSoup, langdetect and requests are a third of its start,
and only a sweep uses them (``services/sweep.py`` imports them lazily)."""
import os
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent

# What only a sweep needs
SWEEP_ONLY = ("praw", "prawcore", "bs4", "langdetect", "requests", "bot.controller", "bot.helpers.reddit")


def test_the_api_starts_without_loading_the_bot():
    # A fresh interpreter: this one has loaded the bot for the other tests
    code = f"import main, sys; print(','.join(m for m in {SWEEP_ONLY!r} if m in sys.modules))"
    result = subprocess.run([sys.executable, "-c", code], cwd=SERVER_DIR, capture_output=True, text=True, timeout=60,
                            env={**os.environ, "LISTBOT_ENV_FILE": "", "LISTBOT_SCHEDULE_ENABLED": "false"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", f"loaded at startup: {result.stdout.strip()}"
