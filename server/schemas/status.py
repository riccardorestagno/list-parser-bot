from pydantic import BaseModel

from schemas.run import SiteError


class Schedule(BaseModel):
    # Off on a server that doesn't sweep (LISTBOT_SCHEDULE_ENABLED), such as your own computer
    enabled: bool
    interval_minutes: int
    next_run_at: str | None = None


class SiteProblem(SiteError):
    """A site whose latest search went wrong, since the first of the searches in a row that did."""

    since: str


class Status(BaseModel):
    subreddit: str
    sites: list[str]
    site_problems: list[SiteProblem] = []
    schedule: Schedule
