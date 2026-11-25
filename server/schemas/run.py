from pydantic import BaseModel

from schemas.enums import RunStatus


class PostedArticle(BaseModel):
    site: str
    title: str
    article_url: str
    reddit_url: str | None = None


class SiteError(BaseModel):
    """A site a sweep couldn't search to the end, and why."""

    site: str
    status: RunStatus  # unreachable (for a moment) or failed
    error: str


class Run(BaseModel):
    id: int
    started_at: str
    finished_at: str | None = None
    status: RunStatus
    sites_searched: list[str]
    site_errors: list[SiteError] = []
    post: PostedArticle | None = None
    error: str | None = None
    error_details: str | None = None


class RunList(BaseModel):
    runs: list[Run]
