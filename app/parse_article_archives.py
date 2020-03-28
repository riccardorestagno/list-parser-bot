import time
from article_archive_parsers.businessinsider import find_article_to_parse as parse_businessinsider_archive
from article_archive_parsers.buzzfeed import find_article_to_parse as parse_buzzfeed_archive
from article_archive_parsers.collegehumor import find_article_to_parse as parse_collegehumor_archive
from datetime import datetime
from helper_methods.enums import *
from helper_methods.list_parser_helper_methods import connect_to_reddit


def call_article_archive_parser(parser, subreddit):
    if parser == ArticleType.Business_Insider:
        return parse_businessinsider_archive(subreddit, convert_enum_to_string(ArticleType.Business_Insider))
    elif parser == ArticleType.BuzzFeed:
        return parse_buzzfeed_archive(subreddit, convert_enum_to_string(ArticleType.BuzzFeed))
    elif parser == ArticleType.CollegeHumor:
        return parse_collegehumor_archive(subreddit, convert_enum_to_string(ArticleType.CollegeHumor))


def order_parsers(subreddit_name, parsers, posts_to_search):
    """Order parsers based on latest posts made to subreddit, if possible."""

    reddit = connect_to_reddit()
    subreddit = reddit.subreddit(subreddit_name)
    submissions = subreddit.new(limit=posts_to_search)
    for submission in reversed(list(submissions)):
        if submission.link_flair_text and string_in_enum_list(parsers, submission.link_flair_text):
            parsers.append(parsers.pop(parsers.index(convert_string_to_articletype_enum(submission.link_flair_text))))

    return parsers


def parser_controller():

    subreddit_name = "buzzfeedbot"

    supported_parsers = []
    supported_parsers_mapping = {
        ArticleType.Business_Insider: True,
        ArticleType.BuzzFeed: False,
        ArticleType.CollegeHumor: False,
        ArticleType.Polygon: False
    }

    for parser in supported_parsers_mapping.items():
        if parser[1]:
            supported_parsers.append(parser[0])

    # If more than one parser is supported, order parsers based on parsers used for latest posts on the subreddit.
    if len(supported_parsers) > 1:
        supported_parsers = order_parsers(subreddit_name, supported_parsers, len(supported_parsers)-1)

    # Iterate through all supported parsers. If a post was made, break the loop.
    for parser in supported_parsers:
        if call_article_archive_parser(parser, subreddit_name):
            break


if __name__ == '__main__':

    while True:  # Temporary functionality to run every three hours. Will adjust Docker setup to avoid this method
        print("Buzzfeed Bot is starting @ " + str(datetime.now()))
        parser_controller()
        print("Sweep finished @ " + str(datetime.now()))
        time.sleep(3 * 60 * 60)
