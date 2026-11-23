"""A sweep as the server records it: what was posted, found or failed, and when the moderator hears."""
from types import SimpleNamespace

import prawcore
import pytest
import requests

import services.sweep as sweep_module
from bot.controller import NoArticlesFound
from bot.helpers.post import Post, SiteSearch
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


def sweeping(monkeypatch, outcome, names=("Cracked", "BuzzFeed"), failing=None):
    """The bot searching these sites (``failing`` maps a site to the error that stopped it), then posting, finding
    nothing, or raising."""
    def fake_sweep(create_post=True, sites=None):
        sites.extend(SiteSearch(name, (failing or {}).get(name)) for name in names)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(sweep_module, "sweep", fake_sweep)


def reddit_error(status: int) -> Exception:
    return prawcore.exceptions.ResponseException(SimpleNamespace(status_code=status))


def site_error(status: int, url: str = "https://screenrant.com/lists/") -> Exception:
    response = requests.Response()
    response.status_code, response.url = status, url
    return requests.exceptions.HTTPError(f"{status} Error for url: {url}", response=response)


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
    sweeping(monkeypatch, None, names=("Business Insider", "BuzzFeed", "Cracked", "Screen Rant"))
    run = runs.get_run(run_sweep())
    assert run["status"] == "nothing-new"
    assert run["post"] is None
    assert run["sites_searched"] == ["Business Insider", "BuzzFeed", "Cracked", "Screen Rant"]


@pytest.mark.parametrize("error", [
    reddit_error(503),
    requests.exceptions.ConnectionError("Connection refused"),
    requests.exceptions.ReadTimeout("Read timed out"),
])
def test_reddit_out_of_reach_is_only_recorded(no_runs, monkeypatch, messages, error):
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


def test_a_site_that_fails_is_noted_under_the_post_and_the_moderator_hears_once(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, POST, names=("Screen Rant", "Cracked"), failing={"Screen Rant": site_error(403)})
    run = runs.get_run(run_sweep())
    assert run["status"] == "posted"
    assert run["site_errors"] == [{"site": "Screen Rant", "status": "failed",
                                   "error": "HTTP 403 from https://screenrant.com/lists/"}]
    assert run["error"] is None
    assert run["error_details"].startswith("Screen Rant:\n")
    [message] = messages
    assert message.startswith("Screen Rant failed: HTTP 403 from https://screenrant.com/lists/")

    run_sweep()
    assert len(messages) == 1  # still failing: the dashboard shows it, Reddit doesn't hear again


@pytest.mark.parametrize("error", [
    requests.exceptions.ConnectionError("Connection refused"),
    requests.exceptions.ReadTimeout("Read timed out"),
    site_error(503),
    site_error(429),
])
def test_a_site_out_of_reach_for_a_moment_is_only_noted(no_runs, monkeypatch, messages, error):
    sweeping(monkeypatch, None, failing={"Cracked": error})
    run = runs.get_run(run_sweep())
    assert run["status"] == "nothing-new"  # BuzzFeed was searched to the end
    assert [problem["status"] for problem in run["site_errors"]] == ["unreachable"]
    assert run["error_details"] is None
    assert messages == []


def test_an_archive_without_articles_says_its_page_may_have_changed(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, None, failing={"Cracked": NoArticlesFound("found no articles on its archive page; its HTML may have changed")})
    run = runs.get_run(run_sweep())
    assert run["site_errors"][0]["error"] == "found no articles on its archive page; its HTML may have changed"
    assert len(messages) == 1


def test_when_no_site_can_be_searched_the_sweep_failed(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, None, failing={"Cracked": ValueError("The page changed"), "BuzzFeed": site_error(503)})
    run = runs.get_run(run_sweep())
    assert run["status"] == "failed"
    assert run["error"] is None  # the sweep itself went fine: each site says why it failed
    assert len(run["site_errors"]) == 2


def test_when_no_site_can_be_reached_the_sweep_was_unreachable(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, None, failing={"Cracked": site_error(502), "BuzzFeed": requests.exceptions.ReadTimeout("x")})
    assert runs.get_run(run_sweep())["status"] == "unreachable"
    assert messages == []


def test_a_failing_site_isnt_sent_again_after_a_sweep_that_couldnt_reach_it(no_runs, monkeypatch, messages):
    changed = {"Cracked": ValueError("The page changed")}
    down = {"Cracked": requests.exceptions.ConnectionError("Connection refused")}
    for failing in (changed, down, changed, down, changed):
        sweeping(monkeypatch, None, failing=failing)
        run_sweep()
    assert len(messages) == 1

    sweeping(monkeypatch, None)  # Cracked works again
    run_sweep()
    sweeping(monkeypatch, None, failing=changed)
    run_sweep()
    assert len(messages) == 2  # and starts failing again


def test_sites_not_searched_dont_hush_a_site_or_wake_it(no_runs, monkeypatch, messages):
    sweeping(monkeypatch, None, failing={"Cracked": ValueError("The page changed")})
    run_sweep()
    sweeping(monkeypatch, POST, names=("BuzzFeed",))  # posted before reaching Cracked
    run_sweep()
    sweeping(monkeypatch, None, failing={"Cracked": ValueError("The page changed")})
    run_sweep()
    assert len(messages) == 1


def test_the_sweep_failing_isnt_sent_again_after_reddit_couldnt_be_reached(no_runs, monkeypatch, messages):
    for outcome in (ValueError("A bug"), reddit_error(503), ValueError("A bug")):
        sweeping(monkeypatch, outcome)
        run_sweep()
    assert len(messages) == 1


def test_a_message_too_long_for_reddit_keeps_who_failed_and_the_error(monkeypatch):
    sent = []
    monkeypatch.setattr(sweep_module, "send_error_message", sent.append)
    sweep_module.notify_moderator("Cracked failed: ValueError\n\n" + "  File ...\n" * 3_000 + "ValueError: The page changed")
    [message] = sent
    assert len(message) <= sweep_module.MESSAGE_LIMIT
    assert message.startswith("Cracked failed: ValueError")
    assert message.endswith("ValueError: The page changed")
