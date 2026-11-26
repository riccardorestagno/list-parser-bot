"""What the dashboard says about the bot: where it posts, the sites it reads (and any failing), and when it next sweeps."""
from typing import Any

from bot.config import active_parsers, subreddit
from bot.helpers.enums import convert_enum_to_string
from services import runs
from services.scheduler import scheduler


def bot_status() -> dict[str, Any]:
    sites = [convert_enum_to_string(site) for site, active in active_parsers.items() if active]
    return {
        "subreddit": subreddit,
        "sites": sites,
        # Cleared by the next sweep that searches the site and finds it working
        "site_problems": runs.site_problems(sites),
        "schedule": scheduler.describe(),
    }
