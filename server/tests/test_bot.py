"""The bot's own rules, without the network: what counts as a list article, and how a sweep goes through the sites."""
import pytest

import bot.controller as controller
import bot.helpers.list_validation_methods as lvm
from bot.helpers.enums import ArticleType
from bot.helpers.post import Post


@pytest.mark.parametrize("title, count", [
    ("17 Things Only Cat Owners Know", 17),
    ("Five Movies That Changed Everything", 5),
    ("The Best Movies Of The Year, Ranked In 25 Steps", 25),
    ("Why Cats Are Great", 0),
])
def test_the_list_count_comes_from_the_title(title, count):
    assert lvm.get_article_list_count(title) == count


@pytest.mark.parametrize("title, meets", [
    ("10 Facts About Owls", True),
    ("Owls Are Great", False),  # no number, so not a list
    ("15 Photos Of Owls", False),  # a list of pictures
    ("12 Must See Owl Videos", False),
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


def test_a_sweep_stops_at_the_first_site_with_a_new_list(monkeypatch):
    post = Post("BuzzFeed", "21 Owls", "https://www.buzzfeed.com/owls", "https://www.reddit.com/r/buzzfeedbot/x/")
    found = {ArticleType.Cracked: False, ArticleType.BuzzFeed: post, ArticleType.Screen_Rant: False}
    monkeypatch.setattr(controller, "get_ordered_article_parsers", lambda: list(found))
    monkeypatch.setattr(controller, "call_article_archive_parser", lambda parser, create_post=True: found[parser])

    searched = []
    assert controller.sweep(searched=searched) == post
    assert searched == ["Cracked", "BuzzFeed"]
