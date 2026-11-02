from types import SimpleNamespace

import prawcore
import pytest
import requests

import services.sweep as sweep_module
from bot.helpers.post import Post
from services import runs
from services.sweep import run_sweep

POST = Post("Cracked", "10 Facts About Owls", "https://www.cracked.com/owls",
            "https://www.reddit.com/r/buzzfeedbot/comments/abc/10_facts_about_owls/")


@pytest.fixture
def messages(monkeypatch):
    """What the moderator would be sent on Reddit."""
    sent = []
    monkeypatch.setattr(sweep_module, "send_error_message", sent.append)
    return sent


def sweeping(monkeypatch, outcome, sites=("Cracked", "BuzzFeed")):
    """The bot searching these sites, then posting, finding nothing, or raising."""
    def fake_sweep(create_post=True, searched=None):
        searched.extend(sites)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(sweep_module, "sweep", fake_sweep)


def reddit_error(status: int) -> Exception:
    return prawcore.exceptions.ResponseException(SimpleNamespace(status_code=status))


def test_a_post_is_recorded(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, POST)
    run = runs.get_run(run_sweep())
    assert run["status"] == "posted"
    assert run["post"] == {"site": "Cracked", "title": "10 Facts About Owls",
                           "article_url": "https://www.cracked.com/owls", "reddit_url": POST.reddit_url}
    assert run["sites_searched"] == ["Cracked", "BuzzFeed"]
    assert run["finished_at"] is not None
    assert messages == []


def test_nothing_new_is_recorded(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, None, sites=("Business Insider", "BuzzFeed", "Cracked", "Screen Rant"))
    run = runs.get_run(run_sweep())
    assert run["status"] == "nothing-new"
    assert run["post"] is None
    assert run["sites_searched"] == ["Business Insider", "BuzzFeed", "Cracked", "Screen Rant"]


@pytest.mark.parametrize("error", [
    reddit_error(503),
    requests.exceptions.ConnectionError("Connection refused"),
    requests.exceptions.ReadTimeout("Read timed out"),
])
def test_reddit_or_a_site_out_of_reach_is_only_recorded(no_runs, monkeypatch, messages, error):
    sweeping(monkeypatch, error)
    run = runs.get_run(run_sweep())
    assert run["status"] == "unreachable"
    assert run["sites_searched"] == ["Cracked", "BuzzFeed"]
    assert messages == []


def test_a_failure_messages_the_moderator_once_until_a_sweep_works(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, ValueError("The page changed"))
    first = runs.get_run(run_sweep())
    assert first["status"] == "failed"
    assert first["error"] == "ValueError: The page changed"
    assert "Traceback" in first["error_details"]
    assert len(messages) == 1

    run_sweep()
    assert len(messages) == 1  # still failing: the dashboard shows it, Reddit doesn't hear again

    sweeping(monkeypatch, None)
    run_sweep()
    sweeping(monkeypatch, reddit_error(403))
    last = runs.get_run(run_sweep())
    assert last["error"] == "Reddit answered with HTTP 403"
    assert len(messages) == 2


def test_a_sweep_a_restart_cut_short_doesnt_hush_the_next_failure(no_runs, monkeypatch, messages):
    runs.start_run()
    runs.close_interrupted_runs()
    sweeping(monkeypatch, ValueError("The page changed"))
    run_sweep()
    assert len(messages) == 1


def test_a_message_that_cant_be_sent_doesnt_stop_the_sweep(no_runs, monkeypatch):
    def reddit_down(_):
        raise requests.exceptions.ConnectionError("Reddit is down")
    monkeypatch.setattr(sweep_module, "send_error_message", reddit_down)
    sweeping(monkeypatch, ValueError("The page changed"))
    assert runs.get_run(run_sweep())["status"] == "failed"
