"""A sweep: search each site switched on for a list article the subreddit doesn't have yet, and post the first found.

Each site is searched on its own: one that fails (its page changed, it blocks the bot, it's down) is noted against
that site and the next one is searched. Reddit failing ends the sweep, since nothing could be checked or posted.
"""
import time

import requests

import bot.helpers.list_validation_methods as lvm
from bot.config import active_parsers, pause_before_each_article
from bot.helpers.enums import *
from bot.helpers.post import Post, SiteSearch
from bot.helpers.reddit import connect_to_reddit, post_to_reddit, recent_posts
from bot.parsers import businessinsider, buzzfeed, cracked, screenrant

# Each site's parser: find_articles() reads its archive, get_article_list_text(link, count) one article's list
PARSERS = {
    ArticleType.Business_Insider: businessinsider,
    ArticleType.BuzzFeed: buzzfeed,
    ArticleType.Cracked: cracked,
    ArticleType.Screen_Rant: screenrant,
}


class NoArticlesFound(Exception):
    """A site's archive page loaded but listed no articles: its HTML has most likely changed."""


def is_gone(error):
    """An article page answering 4xx (404 deleted, 410 gone, 403 locked) other than 429 (slow down): the archive
    still lists it, but there's nothing to read. The archive page answering so means the site is failing."""
    status = error.response.status_code if error.response is not None else None
    return status is not None and 400 <= status < 500 and status != 429


def get_ordered_article_parsers(latest_posts):
    """The sites switched on, those that posted most recently last, by the flairs of the subreddit's latest posts
    (newest first)."""

    parsers = [website for website, active in active_parsers.items() if active]  # Get list of active parsers.

    # Skip ordering of parsers list if one or fewer parsers are active.
    if not len(parsers) > 1:
        return parsers

    for submission in reversed(latest_posts[:len(parsers) - 1]):
        if submission.link_flair_text and string_in_enum_list(parsers, submission.link_flair_text):
            parsers.append(parsers.pop(parsers.index(convert_string_to_articletype_enum(submission.link_flair_text))))

    return parsers


def find_new_list(website, posted_before):
    """The first article in the site's archive with a list worth posting that ``posted_before`` doesn't know, as
    (article, list text), or None. An article its title or an earlier post rules out is never opened, and the bot
    pauses before opening each of the others."""

    parser = PARSERS[website]
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    articles = parser.find_articles()
    if not articles:
        raise NoArticlesFound("found no articles on its archive page; its HTML may have changed")

    for article in articles:
        if not lvm.article_title_meets_posting_requirements(website, article.title) or posted_before(article.link):
            continue

        print(f"Parsing article: {article.link}")
        time.sleep(pause_before_each_article)
        try:
            article_list_text = parser.get_article_list_text(article.link, lvm.get_article_list_count(article.title))
        except requests.exceptions.HTTPError as error:
            if not is_gone(error):
                raise
            print(f"Passing over {article.link}: {error}")
            continue
        if article_list_text:
            print(f"{website_name} list article found: {article.title}")
            return article, article_list_text

    print(f"No {website_name} list articles were found to parse at this time.")
    return None


def sweep(create_post=True, sites=None, websites=None):
    """
    Searches the sites in turn and posts the first new list article found. Returns the Post, or None when no site had
    one (``create_post=False`` finds without posting).

    Each site searched is added to ``sites`` as a SiteSearch, with the error that stopped it if one did, so a sweep
    Reddit cuts short still says how far it got. ``websites`` searches only those, in that order. The schedule
    (server/services/scheduler.py) runs one every so often, through server/services/sweep.py.
    """

    sites = [] if sites is None else sites
    reddit = connect_to_reddit()
    # One request for the whole sweep: it orders the sites, and tells which articles were posted before
    latest_posts = recent_posts(reddit)

    for website in websites or get_ordered_article_parsers(latest_posts):
        website_name = convert_enum_to_string(website)
        try:
            found = find_new_list(website, lambda link: lvm.post_previously_made(link, latest_posts))
        except Exception as error:
            # This site alone: the next may well have something to post
            sites.append(SiteSearch(website_name, error))
            continue

        sites.append(SiteSearch(website_name))
        if found:
            article, article_list_text = found
            reddit_url = post_to_reddit(article.title, article_list_text, article.link, website, reddit) if create_post else None
            return Post(website_name, article.title, article.link, reddit_url)

    return None
