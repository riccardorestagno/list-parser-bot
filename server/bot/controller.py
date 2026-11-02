from bot.config import active_parsers, subreddit
from bot.helpers.enums import *
from bot.helpers.reddit import connect_to_reddit
from bot.parsers.businessinsider import find_article_to_parse as parse_business_insider_archive
from bot.parsers.buzzfeed import find_article_to_parse as parse_buzzfeed_archive
from bot.parsers.collegehumor import find_article_to_parse as parse_collegehumor_archive
from bot.parsers.cracked import find_article_to_parse as parse_cracked_archive
from bot.parsers.polygon import find_article_to_parse as parse_polygon_archive
from bot.parsers.screenrant import find_article_to_parse as parse_screen_rant_archive


def call_article_archive_parser(parser, create_post=True):
    """Call the parser function associated to the enum value passed."""

    # Maps the parser enum type to its associated parser method.
    archive_parsers = {
        ArticleType.Business_Insider: parse_business_insider_archive,
        ArticleType.BuzzFeed: parse_buzzfeed_archive,
        ArticleType.CollegeHumor: parse_collegehumor_archive,
        ArticleType.Cracked: parse_cracked_archive,
        ArticleType.Polygon: parse_polygon_archive,
        ArticleType.Screen_Rant: parse_screen_rant_archive,
    }

    try:
        call_archive_parser = archive_parsers[parser]
    except KeyError:
        print(f"Unable to find archive parser method for {parser.name}'s website.")
        return False
    else:
        return call_archive_parser(create_post=create_post)


def get_ordered_article_parsers():
    """Gets ordered article parsers based on the flairs of the latest posts made to the subreddit."""

    parsers = [website for website, active in active_parsers.items() if active]  # Get list of active parsers.

    # Skip ordering of parsers list if one or fewer parsers are active.
    if not len(parsers) > 1:
        return parsers

    posts_to_search = len(parsers) - 1
    reddit = connect_to_reddit()
    submissions = reddit.subreddit(subreddit).new(limit=posts_to_search)

    for submission in reversed(list(submissions)):
        if submission.link_flair_text and string_in_enum_list(parsers, submission.link_flair_text):
            parsers.append(parsers.pop(parsers.index(convert_string_to_articletype_enum(submission.link_flair_text))))

    return parsers


def sweep(create_post=True, searched=None):
    """
    Iterates through all active parsers. If a post was made, break the loop.

    Returns the Post made, or None when no site had a new list article. Each site's name is
    added to ``searched`` before its archive is parsed, so a sweep that fails part way still
    says how far it got. The schedule (server/services/scheduler.py) runs one every so often.
    """

    for parser in get_ordered_article_parsers():
        if searched is not None:
            searched.append(convert_enum_to_string(parser))
        post = call_article_archive_parser(parser, create_post)
        if post:
            return post

    return None
