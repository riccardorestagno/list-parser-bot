"""The bot's own rules, without the network: what counts as a list article, the order a sweep tries the sites in,
how a sweep carries on past a site that fails, and what the bot sends to Reddit (to a Reddit the test makes)."""
from types import SimpleNamespace

import prawcore
import pytest
import requests

import bot.controller as controller
import bot.helpers.list_validation_methods as lvm
import bot.helpers.reddit as reddit_helper
from bot import config
from bot.helpers.enums import ArticleType, convert_enum_to_string, convert_string_to_articletype_enum, string_in_enum_list
from bot.helpers.post import Article, Post, SiteSearch
from support import fake_reddit, reddit_post


@pytest.mark.parametrize("title, count", [
    ("17 Things Only Cat Owners Know", 17),
    ("Five Movies That Changed Everything", 5),
    ("The Best Movies Of The Year, Ranked In 25 Steps", 25),
    ("Why Cats Are Great", 0),
    ("", 0), ("   ", 0),  # a card whose link is only a picture
])
def test_the_list_count_comes_from_the_title(title, count):
    assert lvm.get_article_list_count(title) == count


@pytest.mark.parametrize("title, meets", [
    ("10 Facts About Owls", True),
    ("Owls Are Great", False),  # no number, so not a list
    ("15 Photos Of Owls", False),  # a list of pictures
    ("12 Must See Owl Videos", False),
    ("", False),
])
def test_title_requirements(title, meets):
    assert lvm.article_title_meets_posting_requirements(ArticleType.Cracked, title) is meets


def test_a_site_can_exclude_words_of_its_own():
    assert "amazon" in lvm.get_title_exclusion_words(ArticleType.BuzzFeed)
    assert "amazon" not in lvm.get_title_exclusion_words(ArticleType.Cracked)


def test_a_list_must_have_as_many_points_as_its_title_says():
    text = "1. A\n2. B\n3. C\n"
    assert lvm.article_text_meets_posting_requirements(ArticleType.Cracked, text, 4, 3)
    assert not lvm.article_text_meets_posting_requirements(ArticleType.Cracked, text, 4, 5)
    assert not lvm.is_correctly_formatted_list("1. A\n3. C\n", 4)


@pytest.mark.parametrize("text, correct", [
    ("1. A\n2. B\n3. C\n", True),
    ("3. C\n2. B\n1. A\n", True),  # a countdown, put in order after the check
    ("1. A\nmore about A\n2. B\n3. C\n", True),  # an item can run over more than one line
    ("1. $1.99 deal\n2. B in 2024.\n3. C\n", True),  # numbers inside an item's text don't count
    ("1. A\n3. C\n", False),  # 2 is missing
    ("11. A\n2. B\n3. C\n", False),  # "1." only inside "11."
    ("1. A\n3. B\n2. C\n", False),  # out of order
    ("1. A\n1. B\n3. C\n", False),  # 1 twice, 2 missing
    ("1. A\n2. B\n3. C\n4. D\n", False),  # one more than counted
    ("Apples 1.\nPears 2.\nPlums 3.\n", False),  # numbers at the end of the line
    ("Apples\nPears\nPlums\nPrices: 1.50, 2.25, 3.10\n", False),  # numbers only inside the text
])
def test_each_item_starts_with_its_own_number_once_and_in_order(text, correct):
    assert lvm.is_correctly_formatted_list(text, 4) is correct


@pytest.mark.parametrize("text, ordered", [
    ("3. C\n2. B\n1. A\n", "1. A\n2. B\n3. C\n"),
    ("3. C\n2. B\nmore about B\n1. A\n", "1. A\n2. B\nmore about B\n3. C\n"),  # an item keeps its own lines
    ("1. A\n2. B\n3. C\n", "1. A\n2. B\n3. C\n"),
    ("1.A\n2.B\n", "1.A\n2.B\n"),  # counting up without a space after the dot: left alone
    ("1. Only\n", "1. Only\n"),
])
def test_a_list_counting_down_is_put_in_order(text, ordered):
    assert lvm.put_list_in_order(text) == ordered


FOUND = (Article("21 Owls", "https://www.buzzfeed.com/owls"), "1. A\n")


def sweeping(monkeypatch, found, reddit=None):
    """A sweep over these sites, in this order: each finds what ``found`` says (an article and its list, None, or an
    error it raises). Returns the Reddit the sweep sees."""
    reddit = reddit or fake_reddit()
    monkeypatch.setattr(controller, "connect_to_reddit", lambda: reddit)
    monkeypatch.setattr(controller, "get_ordered_article_parsers", lambda latest_posts: list(found))

    def find_new_list(website, posted_before):
        if isinstance(found[website], Exception):
            raise found[website]
        return found[website]

    monkeypatch.setattr(controller, "find_new_list", find_new_list)
    return reddit


def test_a_sweep_stops_at_the_first_site_with_a_new_list_and_posts_it(monkeypatch):
    reddit = sweeping(monkeypatch, {ArticleType.Cracked: None, ArticleType.BuzzFeed: FOUND, ArticleType.Screen_Rant: None})
    sites = []
    assert controller.sweep(sites=sites) == Post("BuzzFeed", "21 Owls", "https://www.buzzfeed.com/owls",
                                                 "https://www.reddit.com/r/buzzfeedbot/comments/new/")
    assert sites == [SiteSearch("Cracked"), SiteSearch("BuzzFeed")]
    [post] = reddit.submitted
    assert post.flair == "BuzzFeed"
    # One look at the subreddit for the whole sweep, as many posts as one request gives
    assert reddit.asked == [("buzzfeedbot", 100)]


def test_a_site_that_fails_is_noted_and_the_next_one_searched(monkeypatch):
    changed = AttributeError("'NoneType' object has no attribute 'text'")  # the site changed its HTML
    down = requests.exceptions.ReadTimeout("Read timed out")
    sweeping(monkeypatch, {ArticleType.Cracked: changed, ArticleType.Business_Insider: down,
                           ArticleType.BuzzFeed: None, ArticleType.Screen_Rant: FOUND})
    sites = []
    assert controller.sweep(create_post=False, sites=sites).article_url == "https://www.buzzfeed.com/owls"
    assert sites == [SiteSearch("Cracked", changed), SiteSearch("Business Insider", down),
                     SiteSearch("BuzzFeed"), SiteSearch("Screen Rant")]


def test_reddit_failing_ends_the_sweep(monkeypatch):
    def submit(title, selftext):
        raise prawcore.exceptions.ResponseException(SimpleNamespace(status_code=403))

    reddit = fake_reddit()
    reddit.subreddit = lambda name: SimpleNamespace(new=lambda limit: iter([]), submit=submit)
    sweeping(monkeypatch, {ArticleType.Cracked: FOUND, ArticleType.BuzzFeed: FOUND}, reddit)
    sites = []
    with pytest.raises(prawcore.exceptions.ResponseException):
        controller.sweep(sites=sites)
    assert sites == [SiteSearch("Cracked")]  # how far it got


def test_a_sweep_closes_its_connections_however_it_ends(monkeypatch):
    # Kept until the next sweep, a connection Azure has forgotten waits out the whole timeout
    closed = []
    monkeypatch.setattr(lvm._session, "close", lambda: closed.append(True))

    sweeping(monkeypatch, {ArticleType.Cracked: FOUND})
    controller.sweep(create_post=False)
    assert closed == [True]

    def out_of_reach(reddit):
        raise prawcore.exceptions.RequestException(OSError("Network is unreachable"), (), {})

    monkeypatch.setattr(controller, "recent_posts", out_of_reach)
    with pytest.raises(prawcore.exceptions.RequestException):
        controller.sweep()  # Reddit out of reach before any site is searched
    assert closed == [True, True]


def test_a_sweep_searches_only_the_sites_asked_for(monkeypatch):
    sweeping(monkeypatch, {ArticleType.Cracked: None, ArticleType.Screen_Rant: None})
    sites = []
    controller.sweep(create_post=False, sites=sites, websites=[ArticleType.Screen_Rant])
    assert sites == [SiteSearch("Screen Rant")]


@pytest.mark.parametrize("title", [
    "9 Taco Fiestas", "8 Pizza Hacks", "14 Bad Tattoos", "19 Iconic Movie Quotes",  # too short for langdetect to judge
    "16 “Same” Moments 😂",  # curly quotes and emoji aren't letters
    "21 Things Only Cat Owners Will Understand", "13 Netflix Shows To Binge This Weekend",
])
def test_english_titles_short_or_long_read_as_english(title):
    assert lvm.is_english_title(title)


@pytest.mark.parametrize("title", [
    "猫好きにはたまらない10のこと",  # Japanese: no spaces, so one word
    "12 tacos increíbles",  # short, with an accent
    "15 cosas que solo entienden los mexicanos",
    "10 receitas fáceis para o fim de semana",
    "12 Dinge, die jeder Deutsche kennt",
    "9 choses que tous les Français ont vécues",
    "", "12",  # no letters at all
])
def test_titles_in_other_languages_dont(title):
    assert not lvm.is_english_title(title)


def test_the_same_title_always_gets_the_same_answer():
    # Long enough for langdetect, which without a fixed seed reads it as Somali or English about equally often
    assert len({lvm.is_english_title("6 Bad Tattoo Fails Ranked Badly") for _ in range(50)}) == 1


def test_a_buzzfeed_link_without_a_title_is_passed_over():
    assert not lvm.article_title_meets_posting_requirements(ArticleType.BuzzFeed, "")


def test_a_short_english_buzzfeed_title_can_be_posted():
    assert lvm.article_title_meets_posting_requirements(ArticleType.BuzzFeed, "8 Pizza Hacks")


@pytest.mark.parametrize("text", [
    "1. [A](https://www.amazon.com/a)\n2. [B](https://www.amazon.com/b)\n3. C\n4. D\n",  # half the points sell on Amazon
    "1. [A lamp that glows](https://example.com/a)\n2. [An owl mug](https://example.com/b)\n3. C\n4. D\n",  # product names
    "1. A lamp. This one glows\n2. A mug. When it rains\n3. C\n4. D\n",  # product blurbs
    "1. A:\n2. B\n3. C\n4. D\n",  # a point ending in a colon is about the picture below it
])
def test_buzzfeed_lists_that_read_like_ads_or_captions_arent_posted(text):
    assert not lvm.article_text_meets_posting_requirements(ArticleType.BuzzFeed, text, 5, 4)
    assert lvm.article_text_meets_posting_requirements(ArticleType.Cracked, text, 5, 4)  # BuzzFeed's rules only


def test_a_plain_buzzfeed_list_is_posted():
    assert lvm.article_text_meets_posting_requirements(ArticleType.BuzzFeed, "1. A\n2. B\n3. C\n4. D\n", 5, 4)


def test_a_list_too_long_for_a_reddit_post_isnt_posted():
    assert lvm.article_text_meets_posting_requirements(ArticleType.Cracked, "1. " + "o" * 39_990 + "\n", 2, 1)
    assert not lvm.article_text_meets_posting_requirements(ArticleType.Cracked, "1. " + "o" * 40_000 + "\n", 2, 1)


def test_an_article_in_a_recent_post_counts_as_posted():
    posts = [reddit_post(selftext="1. A\n[Link to article](https://www.cracked.com/owls)")]
    assert lvm.post_previously_made("https://www.cracked.com/owls", posts)
    assert not lvm.post_previously_made("https://www.cracked.com/bats", posts)


def test_the_subreddits_recent_posts_are_read_in_one_request():
    reddit = fake_reddit([reddit_post("Cracked"), reddit_post("BuzzFeed")])
    assert [post.link_flair_text for post in reddit_helper.recent_posts(reddit)] == ["Cracked", "BuzzFeed"]
    assert reddit.asked == [("buzzfeedbot", config.post_previously_made_search_limit)]


FOUR_SITES = {ArticleType.Business_Insider: True, ArticleType.BuzzFeed: True, ArticleType.Cracked: True,
              ArticleType.Screen_Rant: True}


def latest_posts(monkeypatch, *flairs):
    """The subreddit's newest posts, newest first, with these flairs."""
    monkeypatch.setattr(controller, "active_parsers", FOUR_SITES)
    return [reddit_post(flair) for flair in flairs]


def test_the_sites_that_posted_last_are_tried_last(monkeypatch):
    # Only one post fewer than there are sites counts: the fourth newest says nothing more
    posts = latest_posts(monkeypatch, "Cracked", "BuzzFeed", "Screen Rant", "Business Insider")
    assert controller.get_ordered_article_parsers(posts) == [
        ArticleType.Business_Insider, ArticleType.Screen_Rant, ArticleType.BuzzFeed, ArticleType.Cracked]


def test_posts_without_a_flair_or_from_a_site_the_bot_doesnt_read_dont_move_a_site(monkeypatch):
    posts = latest_posts(monkeypatch, "Polygon", None, "Cracked")
    assert controller.get_ordered_article_parsers(posts) == [
        ArticleType.Business_Insider, ArticleType.BuzzFeed, ArticleType.Screen_Rant, ArticleType.Cracked]


def test_with_one_site_switched_on_theres_nothing_to_order(monkeypatch):
    monkeypatch.setattr(controller, "active_parsers", {ArticleType.Cracked: True, ArticleType.BuzzFeed: False})
    assert controller.get_ordered_article_parsers([reddit_post("Cracked")]) == [ArticleType.Cracked]


@pytest.mark.parametrize("site", [site for site in ArticleType if site != ArticleType.All])
def test_a_posts_flair_leads_back_to_its_site(site):
    flair = convert_enum_to_string(site)
    assert convert_string_to_articletype_enum(flair) == site
    assert string_in_enum_list([site], flair)


def test_every_site_in_the_config_has_a_parser():
    assert set(config.active_parsers) == set(controller.PARSERS)
    for parser in controller.PARSERS.values():
        assert callable(parser.find_articles) and callable(parser.get_article_list_text)


def page_answering(status, url="https://www.cracked.com/funny-articles.html"):
    response = requests.Response()
    response.status_code, response.url, response._content = status, url, b"<article class='content-card'></article>"
    return response


def test_a_page_is_read_when_it_loads(monkeypatch):
    monkeypatch.setattr(lvm._session, "get", lambda link, timeout: page_answering(200))
    assert lvm.soup_session("https://www.cracked.com/funny-articles.html").find("article") is not None


def test_pages_are_asked_for_as_a_browser_asks_for_them():
    # BuzzFeed answers 406 at times to requests' own "Accept: */*" with no language
    headers = lvm._session.headers
    assert headers["Accept"].startswith("text/html")
    assert headers["Accept-Language"].startswith("en")
    assert "gzip" in headers["Accept-Encoding"]  # requests' own: only what it can decode


@pytest.mark.parametrize("status", [403, 404, 503])
def test_an_error_page_raises_rather_than_reading_as_a_page_without_articles(monkeypatch, status):
    monkeypatch.setattr(lvm._session, "get", lambda link, timeout: page_answering(status))
    with pytest.raises(requests.exceptions.HTTPError):
        lvm.soup_session("https://www.cracked.com/funny-articles.html")


def test_without_its_reddit_account_the_bot_names_the_settings_not_their_values(monkeypatch):
    monkeypatch.setattr(reddit_helper, "REDDIT_CLIENT_SECRET", "not-to-be-shown")
    monkeypatch.setattr(reddit_helper, "REDDIT_USERNAME", "")
    with pytest.raises(RuntimeError) as error:
        reddit_helper.connect_to_reddit()
    assert "LISTBOT_REDDIT_CLIENT_ID" in str(error.value)
    assert "not-to-be-shown" not in str(error.value)


def test_a_post_holds_the_list_then_the_article_with_its_sites_flair(monkeypatch):
    reddit = fake_reddit()
    monkeypatch.setattr(reddit_helper, "connect_to_reddit", lambda: reddit)
    url = reddit_helper.post_to_reddit("3 Owl Facts", "1. A\n2. B\n3. C\n", "https://screenrant.com/owls/",
                                       ArticleType.Screen_Rant)
    [post] = reddit.submitted
    assert (post.title, post.selftext) == ("3 Owl Facts", "1. A\n2. B\n3. C\n\n[Link to article](https://screenrant.com/owls/)")
    assert post.flair == "Screen Rant"  # what the order of sites reads back
    assert url == "https://www.reddit.com/r/buzzfeedbot/comments/new/"


def test_an_error_goes_to_the_moderator(monkeypatch):
    reddit = fake_reddit()
    monkeypatch.setattr(reddit_helper, "connect_to_reddit", lambda: reddit)
    reddit_helper.send_error_message("Traceback (most recent call last): ...")
    assert reddit.messages == [("Improbably_wrong", "ERROR - r/buzzfeedbot", "Traceback (most recent call last): ...")]
