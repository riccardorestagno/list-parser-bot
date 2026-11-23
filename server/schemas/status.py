from typing import List, Optional

from pydantic import BaseModel

from schemas.run import SiteError


class Schedule(BaseModel):
    # Off on a server that doesn't sweep (LISTBOT_SCHEDULE_ENABLED), such as your own computer
    enabled: bool
    interval_minutes: int
    next_run_at: Optional[str] = None


class SiteProblem(SiteError):
    """A site whose latest search went wrong, since the first of the searches in a row that did."""

    since: str


class Status(BaseModel):
    subreddit: str
    sites: List[str]
    site_problems: List[SiteProblem] = []
    schedule: Schedule
