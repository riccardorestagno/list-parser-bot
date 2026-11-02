from typing import List, Optional

from pydantic import BaseModel

from schemas.enums import RunStatus


class PostedArticle(BaseModel):
    site: str
    title: str
    article_url: str
    reddit_url: Optional[str] = None


class Run(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    status: RunStatus
    sites_searched: List[str]
    post: Optional[PostedArticle] = None
    error: Optional[str] = None
    error_details: Optional[str] = None


class RunList(BaseModel):
    runs: List[Run]
