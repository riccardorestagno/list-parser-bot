import praw
from os import environ

from helpers.enums import convert_enum_to_string


def connect_to_reddit():
    """Connects the bot to the Reddit client."""

    return praw.Reddit(client_id=environ["BUZZFEEDBOT_CLIENT_ID"],
                       client_secret=environ["BUZZFEEDBOT_CLIENT_SECRET"],
                       user_agent=environ["BUZZFEEDBOT_USER_AGENT"],
                       username=environ["BUZZFEEDBOT_USERNAME"],
                       password=environ["BUZZFEEDBOT_PASSWORD"])


def post_to_reddit(headline, main_text, link, subreddit, website):
    """Module that takes the title, main text and link to article and posts directly to Reddit."""

    reddit = connect_to_reddit()

    reddit.subreddit(subreddit).submit(title=headline, selftext=main_text+'\n' + '[Link to article](' + link + ')')\
                               .mod.flair(text=convert_enum_to_string(website))


def send_error_message(stack_trace):
    """If a runtime error has occurred, PM a mod with the error details."""
    reddit = connect_to_reddit()

    reddit.redditor('Improbably_wrong').message('ERROR - r/buzzfeedbot', stack_trace)
