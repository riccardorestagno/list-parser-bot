from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Post:
    """A list article a parser found, and the Reddit post made of it (None when the parser only looked)."""

    site: str
    title: str
    article_url: str
    reddit_url: Optional[str] = None
