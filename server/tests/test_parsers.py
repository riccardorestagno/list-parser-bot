"""The parsers, one per website, on small pages written like each site's: what they find, what they post and when
they stop. No test reaches a website or Reddit: the pages come from the test and posting is recorded instead."""
import time
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Callable

import pytest
from bs4 import BeautifulSoup

import bot.helpers.list_validation_methods as lvm
from bot import config
from bot.helpers.enums import ArticleType
from bot.helpers.post import Post
from bot.parsers import businessinsider, buzzfeed, cracked, screenrant

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
        return BeautifulSoup(web.pages[link], "html.parser")

    monkeypatch.setattr(lvm, "soup_session", soup_session)
    monkeypatch.setattr(time, "sleep", web.paused.append)
    monkeypatch.setattr(lvm, "post_previously_made", lambda link: link in web.posted_before)
    return web


@pytest.fixture
def reddit_posts(monkeypatch):
    """The posts the parsers make, recorded instead of sent."""
    made = []

    def post_to_reddit(title, text, link, website):
        made.append(SimpleNamespace(title=title, text=text, link=link, website=website))
        return REDDIT_URL

    for site in SITES:
        monkeypatch.setattr(site.module, "post_to_reddit", post_to_reddit)
    return made


def publish(web, site: Site, articles: dict, items_by_path: dict | None = None) -> None:
    """Puts the archive (path: title, in order) and each list article (path: page HTML) on the web."""
    web.pages[site.archive] = "".join(site.card(title, path) for path, title in articles.items())
    for path, html in (items_by_path or {}).items():
        web.pages[site.link(path)] = html


def list_page(site: Site, points=POINTS, numbers=None) -> str:
    return "".join(site.item(number, text) for number, text in zip(numbers or range(1, len(points) + 1), points))


@by_name
def test_a_list_article_is_found_without_posting_when_only_looking(web, reddit_posts, site):
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site)})
    assert site.module.find_article_to_parse(create_post=False) == Post(site.name, TITLE, site.link("/owls"), None)
    assert reddit_posts == []


@by_name
def test_a_list_article_is_posted_with_every_point(web, reddit_posts, site):
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site)})
    assert site.module.find_article_to_parse() == Post(site.name, TITLE, site.link("/owls"), REDDIT_URL)
    [post] = reddit_posts
    assert (post.title, post.text, post.link, post.website) == (TITLE, LIST, site.link("/owls"), site.website)


@by_name
def test_an_article_posted_before_is_passed_over_for_the_next(web, reddit_posts, site):
    publish(web, site, {"/owls": TITLE, "/more-owls": TITLE}, {"/owls": list_page(site), "/more-owls": list_page(site)})
    web.posted_before.add(site.link("/owls"))
    assert site.module.find_article_to_parse(create_post=False).article_url == site.link("/more-owls")


@by_name
def test_a_list_shorter_than_its_title_says_isnt_posted(web, reddit_posts, site):
    publish(web, site, {"/owls": "4 Things Owls Can Do That We Cannot"}, {"/owls": list_page(site)})
    assert site.module.find_article_to_parse() is False
    assert reddit_posts == []


@by_name
def test_a_title_without_a_number_isnt_opened(web, reddit_posts, site):
    publish(web, site, {"/owls": "Why Owls Are Better Than Us"})
    assert site.module.find_article_to_parse() is False
    assert web.fetched == [site.archive]


@by_name
def test_each_site_searches_only_its_limit_and_pauses_before_each_article(web, reddit_posts, site):
    publish(web, site, {f"/owls-{letter}": "Why Owls Are Better Than Us" for letter in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"})
    assert site.module.find_article_to_parse() is False
    assert web.paused == [1] * site.limit


def test_a_countdown_is_posted_counting_up(web, reddit_posts):
    site = SITES[1]  # Cracked numbers its points itself
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site, POINTS[::-1], numbers=[3, 2, 1])})
    site.module.find_article_to_parse()
    assert reddit_posts[0].text == LIST


def test_a_buzzfeed_point_with_a_link_is_posted_as_one(web, reddit_posts):
    site = SITES[0]
    points = [f'<a href="https://example.com/{number}">{text}</a>' for number, text in enumerate(POINTS, 1)]
    publish(web, site, {"/owls": TITLE}, {"/owls": list_page(site, points)})
    site.module.find_article_to_parse()
    assert reddit_posts[0].text.splitlines()[0] == f"1. [{POINTS[0]}](https://example.com/1)"


def test_a_buzzfeed_list_written_in_paragraphs_is_read_too(web, reddit_posts):
    site = SITES[0]
    paragraphs = "".join(f"<p>{number}) {text}</p>" for number, text in enumerate(POINTS, 1))
    publish(web, site, {"/owls": TITLE}, {"/owls": f"<p>Owls are great.</p>{paragraphs}"})
    site.module.find_article_to_parse()
    assert reddit_posts[0].text == LIST


def test_a_business_insider_list_in_bold_headings_is_read_too(web, reddit_posts):
    site = SITES[3]
    headings = "".join(f"<h2><strong>{number}. {text}</strong></h2>" for number, text in enumerate(POINTS, 1))
    publish(web, site, {"/owls": TITLE}, {"/owls": headings})
    site.module.find_article_to_parse()
    assert reddit_posts[0].text == LIST
