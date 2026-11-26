"""The parsers, one per website, on small pages written like each site's, searched as a sweep searches them: what
they find, what they post and when they stop. No test reaches a website or Reddit: the pages come from the test and
Reddit is one the test makes."""
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest
import requests
from bs4 import BeautifulSoup

import bot.controller as controller
import bot.helpers.list_validation_methods as lvm
from bot import config
from bot.helpers.enums import ArticleType
from bot.helpers.post import Article, Post
from bot.parsers import businessinsider, buzzfeed, cracked, screenrant
from support import fake_reddit, reddit_post

REDDIT_URL = "https://www.reddit.com/r/buzzfeedbot/comments/new/"


@dataclass(frozen=True)
class Site:
    """How one website writes its archive and its list articles, as its parser reads them."""

    name: str
    module: ModuleType
    website: ArticleType
    archive: str
    limit: int
    card: Callable[[str, str], str]  # an article in the archive, from its title and path
    link: Callable[[str], str]  # the address the parser follows for that path
    item: Callable[[int, str], str]  # one point of a list article, from its number and text


SITES = [
    Site("BuzzFeed", buzzfeed, ArticleType.BuzzFeed, config.buzzfeed_article_archive_link,
         config.buzzfeed_max_articles_to_search,
         card=lambda title, path: f'<article data-buzzblock="story-card"><a href="https://www.buzzfeed.com{path}">{title}</a></article>',
         link=lambda path: f"https://www.buzzfeed.com{path}",
         item=lambda number, text: f'<h2><span class="subbuzz__number">{number}.</span>'
                                   f'<span class="js-subbuzz__title-text">{text}</span></h2>'),
    Site("Cracked", cracked, ArticleType.Cracked, config.cracked_article_archive_link,
         config.cracked_max_articles_to_search,
         card=lambda title, path: f'<article class="content-card"><a href="https://www.cracked.com{path}" title="{title}">{title}</a></article>',
         link=lambda path: f"https://www.cracked.com{path}",
         item=lambda number, text: f'<h2 class="subheading subheading-num"><label>{number}</label><span>{text}</span></h2>'),
    Site("Screen Rant", screenrant, ArticleType.Screen_Rant, config.screen_rant_article_archive_link,
         config.screen_rant_max_articles_to_search,
         card=lambda title, path: f'<h5 class="display-card-title"><a href="{path}">{title}</a></h5>',
         link=lambda path: f"http://www.screenrant.com{path}",
         item=lambda number, text: f'<h2><span class="item-num">{number}</span><span>{text}</span></h2>'),
    Site("Business Insider", businessinsider, ArticleType.Business_Insider, config.business_insider_article_archive_link,
         config.business_insider_max_articles_to_search,
         card=lambda title, path: f'<h3 class="tout-title"><a href="{path}">{title}</a></h3>',
         link=lambda path: f"http://www.businessinsider.com{path}",
         item=lambda number, text: f'<div class="slide-content"><h2 class="heading-md">{text}</h2></div>'),
]
by_name = pytest.mark.parametrize("site", SITES, ids=[site.name for site in SITES])

TITLE = "3 Things Owls Can Do That We Cannot"
POINTS = ["They turn their heads almost all the way round", "They fly without a sound", "They see in the dark"]
LIST = "1. They turn their heads almost all the way round\n2. They fly without a sound\n3. They see in the dark\n"


@pytest.fixture
def web(monkeypatch):
    """The websites, as pages the test hands over: a page it didn't hand over fails the test instead of being
    fetched. Also records the pauses between fetches, and which articles Reddit already has."""
    web = SimpleNamespace(pages={}, fetched=[], paused=[], posted_before=set())

    def soup_session(link):
        web.fetched.append(link)
        assert link in web.pages, f"the parser fetched {link}, which the test didn't hand over"
        if isinstance(web.pages[link], Exception):
            raise web.pages[link]  # the page answered with an error
        return BeautifulSoup(web.pages[link], "html.parser")

    monkeypatch.setattr(lvm, "soup_session", soup_session)
    monkeypatch.setattr(time, "sleep", web.paused.append)
    return web


def search(web, site: Site):
    """The site searched as a sweep searches it: the article it would post and its list, or None."""
    return controller.find_new_list(site.website, lambda link: link in web.posted_before)


def reddit_with(monkeypatch, *posts):
    """The Reddit a sweep signs in to: the subreddit's posts, newest first, and the posts the sweep makes."""
    reddit = fake_reddit(posts)
    monkeypatch.setattr(controller, "connect_to_reddit", lambda: reddit)
    return reddit


def publish(web, site: Site, articles: dict, items_by_path: dict | None = None) -> None:
    """Puts the archive (path: title, in order) and each list article (path: page HTML) on the web."""
    web.pages[site.archive] = "".join(site.card(title, path) for path, title in articles.items())
    for path, html in (items_by_path or {}).items():
        web.pages[site.link(path)] = html


def list_page(site: Site, points=POINTS, numbers=None) -> str:
    return "".join(site.item(number, text) for number, text in zip(numbers or range(1, len(points) + 1), points))


@by_name
def test_a_list_article_is_found_with_every_point(web, site):
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site)})
    assert search(web, site) == (Article(TITLE, site.link("/owls")), LIST)


@by_name
def test_a_list_article_is_posted_with_every_point_and_its_sites_flair(web, monkeypatch, site):
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site)})
    reddit = reddit_with(monkeypatch)
    assert controller.sweep(websites=[site.website]) == Post(site.name, TITLE, site.link("/owls"), REDDIT_URL)
    [post] = reddit.submitted
    assert (post.title, post.selftext, post.flair) == (TITLE, f"{LIST}\n[Link to article]({site.link('/owls')})", site.name)


@by_name
def test_only_looking_posts_nothing(web, monkeypatch, site):
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site)})
    reddit = reddit_with(monkeypatch)
    assert controller.sweep(create_post=False, websites=[site.website]) == Post(site.name, TITLE, site.link("/owls"), None)
    assert reddit.submitted == []


@by_name
def test_an_article_posted_before_is_passed_over_without_being_opened(web, monkeypatch, site):
    publish(web, site, {"/owls": TITLE, "/more-owls": TITLE}, {"/owls": list_page(site), "/more-owls": list_page(site)})
    reddit_with(monkeypatch, reddit_post(site.name, f"{LIST}\n[Link to article]({site.link('/owls')})"))
    assert controller.sweep(create_post=False, websites=[site.website]).article_url == site.link("/more-owls")
    assert web.fetched == [site.archive, site.link("/more-owls")]


@by_name
def test_a_list_shorter_than_its_title_says_isnt_found(web, site):
    publish(web, site, {"/owls": "4 Things Owls Can Do That We Cannot"}, {"/owls": list_page(site)})
    assert search(web, site) is None


@by_name
def test_a_title_without_a_number_isnt_opened_nor_waited_for(web, site):
    publish(web, site, {"/owls": "Why Owls Are Better Than Us"})
    assert search(web, site) is None
    assert web.fetched == [site.archive]
    assert web.paused == []


@by_name
def test_each_site_opens_only_its_limit_and_pauses_before_each_article(web, site):
    paths = [f"/owls-{letter}" for letter in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"]
    # Titles promising one point more than each page has: every article is opened, none is found
    publish(web, site, {path: "4 Things Owls Can Do That We Cannot" for path in paths},
            {path: list_page(site) for path in paths})
    assert search(web, site) is None
    assert web.fetched == [site.archive] + [site.link(path) for path in paths[:site.limit]]
    assert web.paused == [config.pause_before_each_article] * site.limit


def error_page(status: int, link: str) -> Exception:
    response = requests.Response()
    response.status_code, response.url = status, link
    return requests.exceptions.HTTPError(f"{status} Error for url: {link}", response=response)


@by_name
@pytest.mark.parametrize("status", [404, 410, 403])
def test_an_article_thats_gone_is_passed_over_for_the_next(web, site, status):
    publish(web, site, {"/owls": TITLE, "/more-owls": TITLE}, {"/more-owls": list_page(site)})
    web.pages[site.link("/owls")] = error_page(status, site.link("/owls"))
    assert search(web, site)[0].link == site.link("/more-owls")


@by_name
@pytest.mark.parametrize("status", [429, 503])
def test_an_article_the_site_cant_serve_right_now_stops_the_site(web, site, status):
    publish(web, site, {"/owls": TITLE, "/more-owls": TITLE}, {"/more-owls": list_page(site)})
    web.pages[site.link("/owls")] = error_page(status, site.link("/owls"))
    with pytest.raises(requests.exceptions.HTTPError):
        search(web, site)


@by_name
def test_an_archive_without_articles_means_its_page_changed(web, site):
    publish(web, site, {})
    with pytest.raises(controller.NoArticlesFound):
        search(web, site)


def test_a_countdown_is_found_counting_up(web):
    site = SITES[1]  # Cracked numbers its points itself
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site, POINTS[::-1], numbers=[3, 2, 1])})
    assert search(web, site)[1] == LIST


def test_a_buzzfeed_point_with_a_link_is_found_as_one(web):
    site = SITES[0]
    points = [f'<a href="https://example.com/{number}">{text}</a>' for number, text in enumerate(POINTS, 1)]
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site, points)})
    assert search(web, site)[1].splitlines()[0] == f"1. [{POINTS[0]}](https://example.com/1)"


def test_a_buzzfeed_list_written_in_paragraphs_is_read_too_from_one_fetch(web):
    site = SITES[0]
    paragraphs = "".join(f"<p>{number}) {text}</p>" for number, text in enumerate(POINTS, 1))
    publish(web, site, {"/owls": TITLE}, {"/owls": f"<p>Owls are great.</p>{paragraphs}"})
    assert search(web, site)[1] == LIST
    assert web.fetched == [site.archive, site.link("/owls")]


def test_a_business_insider_list_in_bold_headings_is_read_too(web):
    site = SITES[3]
    headings = "".join(f"<h2><strong>{number}. {text}</strong></h2>" for number, text in enumerate(POINTS, 1))
    publish(web, site, {"/owls": TITLE}, {"/owls": headings})
    assert search(web, site)[1] == LIST
