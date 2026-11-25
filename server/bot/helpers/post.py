from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    """An article as a site's archive lists it."""

    title: str
    link: str


@dataclass(frozen=True)
class Post:
    """A list article a sweep found, and the Reddit post made of it (None when the sweep only looked)."""

    site: str
    title: str
    article_url: str
    reddit_url: str | None = None


@dataclass(frozen=True)
class SiteSearch:
    """One site a sweep searched, by its name as the post's flair, and the error that stopped it, if one did."""

    site: str
    error: Exception | None = None
