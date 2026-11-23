"""/status: where the bot posts, which sites it reads and which are failing, as the dashboard shows them."""
from datetime import timedelta

from bot.config import active_parsers
from bot.helpers.enums import ArticleType
from db.session import connect
from schemas.enums import RunStatus
from services import runs

CHANGED = {"site": "Cracked", "status": "failed", "error": "found no articles on its archive page; its HTML may have changed"}
DOWN = {"site": "Cracked", "status": "unreachable", "error": "ConnectionError: Connection refused"}


def swept(minutes_ago: int, searched=("Cracked", "BuzzFeed"), *site_errors) -> str:
    """A sweep that began this many minutes ago, searched these sites and noted these errors. Returns when it began."""
    run_id = runs.start_run(runs.utc_now() - timedelta(minutes=minutes_ago))
    runs.finish_run(run_id, RunStatus.NOTHING_NEW, list(searched), site_errors=list(site_errors))
    return runs.get_run(run_id)["started_at"]


def problems(client) -> list:
    return client.get("/status").json()["site_problems"]


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


def test_no_site_is_marked_while_each_works(client, no_runs):
    swept(90)
    assert problems(client) == []


def test_a_failing_site_is_marked_since_it_started_failing(client, no_runs):
    swept(270)
    started = swept(180, ("Cracked", "BuzzFeed"), CHANGED)
    swept(90, ("Cracked", "BuzzFeed"), CHANGED)
    assert problems(client) == [{**CHANGED, "since": started}]


def test_the_mark_shows_how_the_latest_search_went(client, no_runs):
    started = swept(180, ("Cracked", "BuzzFeed"), CHANGED)
    swept(90, ("Cracked", "BuzzFeed"), DOWN)
    assert problems(client) == [{**DOWN, "since": started}]


def test_the_mark_goes_once_a_sweep_finds_the_site_working(client, no_runs):
    swept(180, ("Cracked", "BuzzFeed"), DOWN)
    swept(90)
    assert problems(client) == []


def test_a_sweep_that_didnt_reach_the_site_leaves_its_mark(client, no_runs):
    started = swept(180, ("Cracked", "BuzzFeed"), CHANGED)
    swept(90, ("BuzzFeed",))  # posted before getting to Cracked
    assert problems(client) == [{**CHANGED, "since": started}]


def test_runs_from_before_sites_were_noted_mark_nothing(client, no_runs):
    run_id = runs.start_run()
    runs.finish_run(run_id, RunStatus.FAILED, ["Cracked"], error="ValueError: The page changed")
    conn = connect()
    try:
        conn.execute("UPDATE runs SET site_errors = NULL WHERE id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()
    assert problems(client) == []
