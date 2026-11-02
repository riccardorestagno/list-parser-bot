import praw

from bot.config import subreddit
from bot.helpers.enums import convert_enum_to_string
from settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_PASSWORD, REDDIT_USER_AGENT, REDDIT_USERNAME


def connect_to_reddit():
    """Connects the bot to the Reddit client."""

    if not all((REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, REDDIT_USERNAME, REDDIT_PASSWORD)):
        raise RuntimeError("The bot's Reddit account isn't set up: it needs LISTBOT_REDDIT_CLIENT_ID, "
                           "_CLIENT_SECRET, _USER_AGENT, _USERNAME and _PASSWORD (server/.env.example)")

    return praw.Reddit(client_id=REDDIT_CLIENT_ID,
                       client_secret=REDDIT_CLIENT_SECRET,
                       user_agent=REDDIT_USER_AGENT,
                       username=REDDIT_USERNAME,
                       password=REDDIT_PASSWORD)


def post_to_reddit(headline, main_text, link, website):
    """Module that takes the title, main text and link to article and posts directly to Reddit. Returns the post's address."""

    reddit = connect_to_reddit()

    submission = reddit.subreddit(subreddit).submit(title=headline, selftext=f"{main_text}\n[Link to article]({link})")
    submission.mod.flair(text=convert_enum_to_string(website))

    return f"https://www.reddit.com{submission.permalink}"


def send_error_message(stack_trace):
    """If a runtime error has occurred, PM a mod with the error details."""
    reddit = connect_to_reddit()

    reddit.redditor('Improbably_wrong').message(f'ERROR - r/{subreddit}', stack_trace)
