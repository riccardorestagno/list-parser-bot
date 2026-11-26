"""One sweep of the bot, recorded: the job the schedule runs (and ``python -m dev.sweep``, by hand).

A site or Reddit out of reach for a moment is only recorded. Anything else (a site whose page changed or that
blocks the bot, Reddit refusing the bot, a bug) also messages the subreddit's moderator on Reddit, once when it
starts failing rather than on every sweep after.
"""
import logging
import traceback

# Lazy: the bot (praw, BeautifulSoup, langdetect, requests) is a third of the API's start, and only a sweep uses it,
# so it loads with the first sweep rather than before the API can answer (tests/test_startup.py)
lazy import prawcore
lazy import requests

lazy from bot.controller import NoArticlesFound, sweep
from bot.helpers.post import SiteSearch
lazy from bot.helpers.reddit import send_error_message
from schemas.enums import RunStatus
from services import runs

log = logging.getLogger(__name__)

# Reddit answering with these is having a moment, not saying the bot is broken
TEMPORARY_STATUSES = {500, 502, 503}
# The same from a website, or it asking the bot to slow down
SITE_TEMPORARY_STATUSES = {429, 500, 502, 503, 504}

# Reddit refuses a private message longer than this: a long traceback is cut in the middle, keeping who failed
# (its start) and the error (its end)
MESSAGE_LIMIT = 10_000
MESSAGE_HEAD = 2_000


def is_temporary(error: Exception) -> bool:
    if isinstance(error, prawcore.exceptions.ResponseException):
        return error.response.status_code in TEMPORARY_STATUSES
    if isinstance(error, requests.exceptions.HTTPError):
        return error.response is not None and error.response.status_code in SITE_TEMPORARY_STATUSES
    return isinstance(error, (prawcore.exceptions.RequestException, requests.exceptions.ConnectionError,
                              requests.exceptions.Timeout))


def describe(error: Exception) -> str:
    """One line for the dashboard."""
    if isinstance(error, prawcore.exceptions.ResponseException):
        return f"Reddit answered with HTTP {error.response.status_code}"
    if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
        return f"HTTP {error.response.status_code} from {error.response.url}"
    if isinstance(error, NoArticlesFound):
        return str(error)
    return f"{type(error).__name__}: {error}"


def format_error(error: Exception) -> str:
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


def site_errors(sites: list[SiteSearch]) -> list[dict[str, str]]:
    """Each site the sweep couldn't search to the end, as the run records it."""
    return [{"site": search.site,
             "status": (RunStatus.UNREACHABLE if is_temporary(search.error) else RunStatus.FAILED).value,
             "error": describe(search.error)}
            for search in sites if search.error is not None]


def failing_sites(sites: list[SiteSearch]) -> list[SiteSearch]:
    """The sites that failed for more than a moment."""
    return [search for search in sites if search.error is not None and not is_temporary(search.error)]


def error_details(sites: list[SiteSearch], error: Exception | None = None) -> str | None:
    """The tracebacks behind the failures, each site's under its name, for the dashboard's Details."""
    parts = [f"{search.site}:\n{format_error(search.error)}" for search in failing_sites(sites)]
    if error is not None:
        parts.append(format_error(error))
    return "\n\n".join(parts) or None


def ending(sites: list[SiteSearch]) -> RunStatus:
    """How a sweep that posted nothing ended: nothing new, unless no site could be searched to the end."""
    errors = [search.error for search in sites if search.error is not None]
    if not sites or len(errors) < len(sites):
        return RunStatus.NOTHING_NEW
    return RunStatus.UNREACHABLE if all(is_temporary(error) for error in errors) else RunStatus.FAILED


def notify_moderator(message: str) -> None:
    """Message the moderator on Reddit, without letting a failure to do so stop the schedule."""
    if len(message) > MESSAGE_LIMIT:
        message = f"{message[:MESSAGE_HEAD]}\n\n[…]\n\n{message[-(MESSAGE_LIMIT - MESSAGE_HEAD - 10):]}"
    try:
        send_error_message(message)
    except Exception:
        log.exception("Couldn't message the moderator about a failed sweep")


def tell_moderator(run_id: int, sites: list[SiteSearch], error: Exception | None = None) -> None:
    """Message the moderator about what started failing with this sweep: the sweep itself, or a site.

    What was already failing the last time it was tried isn't sent again. A sweep a restart cut short, or one where
    a site or Reddit couldn't be reached, says nothing either way, so it's passed over when looking back.
    """
    news = []
    if error is not None and not runs.sweep_failed_before(run_id):
        news.append(("The sweep", error))
    failing = failing_sites(sites)
    already = runs.sites_failing_before(run_id, [search.site for search in failing])
    news += [(search.site, search.error) for search in failing if search.site not in already]
    if news:
        notify_moderator("\n\n".join(f"{who} failed: {describe(problem)}\n\n{format_error(problem)}"
                                     for who, problem in news))


def run_sweep() -> int:
    """Search the sites, post the first new list article found, and record how it went. Returns the run's id."""
    run_id = runs.start_run()
    # The sweep adds each site as it goes, so a sweep Reddit cuts short still shows how far it got
    sites: list[SiteSearch] = []
    try:
        found = sweep(sites=sites)
    except Exception as error:
        temporary = is_temporary(error)
        runs.finish_run(run_id, RunStatus.UNREACHABLE if temporary else RunStatus.FAILED,
                        [search.site for search in sites], site_errors=site_errors(sites), error=describe(error),
                        error_details=error_details(sites, None if temporary else error))
        tell_moderator(run_id, sites, None if temporary else error)
        return run_id

    runs.finish_run(run_id, RunStatus.POSTED if found else ending(sites), [search.site for search in sites],
                    post=found or None, site_errors=site_errors(sites), error_details=error_details(sites))
    tell_moderator(run_id, sites)
    return run_id
