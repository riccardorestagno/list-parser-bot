from typing import List, Optional

from pydantic import BaseModel


class Schedule(BaseModel):
    # Off on a server that doesn't sweep (LISTBOT_SCHEDULE_ENABLED), such as your own computer
    enabled: bool
    interval_minutes: int
    next_run_at: Optional[str] = None


class Status(BaseModel):
    subreddit: str
    sites: List[str]
    schedule: Schedule
