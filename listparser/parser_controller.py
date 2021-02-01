import prawcore
import socket
import time
import traceback
from datetime import datetime

from config import active_parsers, script_execution_delay, subreddit
from helpers.enums import *
from helpers.reddit import connect_to_reddit, send_error_message
from parsers.businessinsider import find_article_to_parse as parse_business_insider_archive
from parsers.buzzfeed import find_article_to_parse as parse_buzzfeed_archive
from parsers.collegehumor import find_article_to_parse as parse_collegehumor_archive
from parsers.cracked import find_article_to_parse as parse_cracked_archive
from parsers.polygon import find_article_to_parse as parse_polygon_archive


def call_article_archive_parser(parser):
    """Call the parser function associated to the enum value passed."""

    # Maps the parser enum type to its associated parser method.
    archive_parsers = {
        ArticleType.Business_Insider: lambda: parse_business_insider_archive(),
        ArticleType.BuzzFeed: lambda: parse_buzzfeed_archive(),
        ArticleType.CollegeHumor: lambda: parse_collegehumor_archive(),
        ArticleType.Cracked: lambda: parse_cracked_archive(),
        ArticleType.Polygon: lambda: parse_polygon_archive()
    }

    try:
        call_archive_parser = archive_parsers[parser]
    except KeyError:
        print(f"Unable to find archive parser method for {parser.name}'s website.")
        return False
    else:
        return call_archive_parser()


def get_ordered_article_parsers():
    """Gets ordered article parsers based on the flairs of the latest posts made to the subreddit."""

    parsers = [website for website, active in active_parsers.items() if active]  # Get list of active parsers.

    # Skip ordering of parsers list if one or less parsers are active.
    if not len(parsers) > 1:
        return parsers

    posts_to_search = len(parsers) - 1
    reddit = connect_to_reddit()
    submissions = reddit.subreddit(subreddit).new(limit=posts_to_search)

    for submission in reversed(list(submissions)):
        if submission.link_flair_text and string_in_enum_list(parsers, submission.link_flair_text):
            parsers.append(parsers.pop(parsers.index(convert_string_to_articletype_enum(submission.link_flair_text))))

    return parsers


def parser_controller():
    """Iterates through all active parsers. If a post was made, break the loop."""

    for parser in get_ordered_article_parsers():
        if call_article_archive_parser(parser):
            break


if __name__ == '__main__':

    while True:
        try:
            print("Buzzfeed Bot is starting @ " + str(datetime.now()))
            parser_controller()
            print("Sweep finished @ " + str(datetime.now()))
            time.sleep(script_execution_delay)
        except prawcore.exceptions.ResponseException as httpError:
            if httpError.response.status_code == 503:
                time.sleep(5 * 60)  # Temporary connection error. Wait 5 minutes before running again.
            else:
                print(f"A HTTP error has occurred. Received {httpError.response.status_code} HTTP response.")
                send_error_message(f"A HTTP error has occurred. Received {httpError.response.status_code} HTTP response.")
                time.sleep(1 * 60 * 60)  # Stop for 1 hour if a HTTP exception occurred (Not 503).
        except socket.gaierror:
            time.sleep(5 * 60)  # Temporary connection error. Wait 5 minutes before running again.
        except Exception as error:
            print(f"An error has occurred: {error}")
            send_error_message(traceback.format_exc())
            time.sleep(5 * 60 * 60)  # Stop for 5 hours if an unknown exception occurred.
