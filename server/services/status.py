"""What the dashboard says about the bot: where it posts, the sites it reads, and when it next sweeps."""
from typing import Any, Dict

from bot.config import active_parsers, subreddit
from bot.helpers.enums import convert_enum_to_string
from services.scheduler import scheduler


def bot_status() -> Dict[str, Any]:
    return {
        "subreddit": subreddit,
        "sites": [convert_enum_to_string(site) for site, active in active_parsers.items() if active],
        "schedule": scheduler.describe(),
    }
