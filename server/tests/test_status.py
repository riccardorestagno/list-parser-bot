from bot.config import active_parsers
from bot.helpers.enums import ArticleType


def test_status_says_where_it_posts_and_what_it_reads(client):
    status = client.get("/status").json()
    assert status["subreddit"] == "buzzfeedbot"
    # The sites' names as the dashboard shows them, only those switched on in bot/config.py
    assert len(status["sites"]) == sum(active_parsers.values())
    if active_parsers[ArticleType.Screen_Rant]:
        assert "Screen Rant" in status["sites"]


def test_a_server_that_doesnt_sweep_says_so(client):
    # The tests' server doesn't sweep (LISTBOT_SCHEDULE_ENABLED is off)
    assert client.get("/status").json()["schedule"] == {"enabled": False, "interval_minutes": 90, "next_run_at": None}
