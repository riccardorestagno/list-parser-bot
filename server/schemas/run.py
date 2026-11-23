from typing import List, Optional

from pydantic import BaseModel

from schemas.enums import RunStatus


class PostedArticle(BaseModel):
    site: str
    title: str
    article_url: str
    reddit_url: Optional[str] = None


class SiteError(BaseModel):
    """A site a sweep couldn't search to the end, and why."""

    site: str
    status: RunStatus  # unreachable (for a moment) or failed
    error: str


class Run(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    status: RunStatus
    sites_searched: List[str]
    site_errors: List[SiteError] = []
    post: Optional[PostedArticle] = None
    error: Optional[str] = None
    error_details: Optional[str] = None


class RunList(BaseModel):
    runs: List[Run]
