"""One sweep of the bot, recorded: the job the schedule runs (and ``python -m dev.sweep``, by hand).

What counts as a failure, and who hears about it, used to be decided by the bot's
sleep loop. It still is the same way: Reddit or a site being out of reach for a
moment is only recorded, and anything else also messages the subreddit's moderator
on Reddit, once when sweeps start failing rather than on every sweep after.
"""
import logging
import traceback
from typing import List

import prawcore
import requests

from bot.controller import sweep
from bot.helpers.reddit import send_error_message
from schemas.enums import RunStatus
from services import runs

log = logging.getLogger(__name__)

# Reddit answering with these is having a moment, not saying the bot is broken
TEMPORARY_STATUSES = {500, 502, 503}


def is_temporary(error: Exception) -> bool:
    if isinstance(error, prawcore.exceptions.ResponseException):
        return error.response.status_code in TEMPORARY_STATUSES
    return isinstance(error, (prawcore.exceptions.RequestException, requests.exceptions.ConnectionError,
                              requests.exceptions.Timeout))


def describe(error: Exception) -> str:
    """One line for the dashboard."""
    if isinstance(error, prawcore.exceptions.ResponseException):
        return f"Reddit answered with HTTP {error.response.status_code}"
    return f"{type(error).__name__}: {error}"


def notify_moderator(message: str) -> None:
    """Message the moderator on Reddit, without letting a failure to do so stop the schedule."""
    try:
        send_error_message(message)
    except Exception:
        log.exception("Couldn't message the moderator about a failed sweep")


def run_sweep() -> int:
    """Search the sites, post the first new list article found, and record how it went. Returns the run's id."""
    run_id = runs.start_run()
    # The sweep adds each site as it goes, so a failure still shows how far it got
    searched: List[str] = []
    try:
        found = sweep(searched=searched)
    except Exception as error:
        if is_temporary(error):
            runs.finish_run(run_id, RunStatus.UNREACHABLE, searched, error=describe(error))
            return run_id
        details = traceback.format_exc()
        runs.finish_run(run_id, RunStatus.FAILED, searched, error=describe(error), error_details=details)
        if runs.previous_status(run_id) != RunStatus.FAILED:
            notify_moderator(details)
        return run_id

    runs.finish_run(run_id, RunStatus.POSTED if found else RunStatus.NOTHING_NEW, searched, post=found or None)
    return run_id
