import time
import traceback
from parsers.businessinsider import find_article_to_parse as parse_businessinsider_archive
from parsers.buzzfeed import find_article_to_parse as parse_buzzfeed_archive
from parsers.collegehumor import find_article_to_parse as parse_collegehumor_archive
from parsers.polygon import find_article_to_parse as parse_polygon_archive
from datetime import datetime
from helpers.enums import *
from helpers.list_parser_helper_methods import connect_to_reddit, send_error_message


def call_article_archive_parser(parser, subreddit):
    """Call the parser function associated to the enum value passed."""

    # Maps the parser enum type to its associated parser method.
    archive_parsers = {
        ArticleType.Business_Insider: lambda: parse_businessinsider_archive(subreddit, ArticleType.Business_Insider),
        ArticleType.BuzzFeed: lambda: parse_buzzfeed_archive(subreddit, ArticleType.BuzzFeed),
        ArticleType.CollegeHumor: lambda: parse_collegehumor_archive(subreddit, ArticleType.CollegeHumor),
        ArticleType.Polygon: lambda: parse_polygon_archive(subreddit, ArticleType.Polygon)
    }

    try:
        call_archive_parser = archive_parsers[parser]
    except KeyError:
        print(f"Unable to find archive parser method for {parser.name}'s website.")
        return False
    else:
        return call_archive_parser()


def order_parsers(subreddit_name, parsers, posts_to_search):
    """Order parsers based on the flair of the latest posts made to the subreddit, if possible."""

    reddit = connect_to_reddit()
    subreddit = reddit.subreddit(subreddit_name)
    submissions = subreddit.new(limit=posts_to_search)
    for submission in reversed(list(submissions)):
        if submission.link_flair_text and string_in_enum_list(parsers, submission.link_flair_text):
            parsers.append(parsers.pop(parsers.index(convert_string_to_articletype_enum(submission.link_flair_text))))

    return parsers


def parser_controller():
    """Controller which determines which parser function should be called for the current iteration of the scripts' execution."""

    subreddit = "buzzfeedbot"

    supported_parsers = []
    supported_parsers_mapping = {
        ArticleType.Business_Insider: True,
        ArticleType.BuzzFeed: True,
        ArticleType.CollegeHumor: False,
        ArticleType.Polygon: False
    }

    for parser in supported_parsers_mapping.items():
        if parser[1]:
            supported_parsers.append(parser[0])

    # If more than one parser is supported, order parsers based on parsers used for latest posts on the subreddit.
    if len(supported_parsers) > 1:
        supported_parsers = order_parsers(subreddit, supported_parsers, len(supported_parsers)-1)

    # Iterate through all supported parsers. If a post was made, break the loop.
    for parser in supported_parsers:
        if call_article_archive_parser(parser, subreddit):
            break


if __name__ == '__main__':
    try:
        while True:
            print("Buzzfeed Bot is starting @ " + str(datetime.now()))
            parser_controller()
            print("Sweep finished @ " + str(datetime.now()))
            time.sleep(2 * 60 * 60)  # Run once every two hours.
    except Exception as error:
        print(f"An error has occurred: {error}")
        send_error_message(traceback.format_exc())
        time.sleep(5 * 60 * 60)  # Stop for 5 hours if an exception occurred.
