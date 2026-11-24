import re
import requests
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect, lang_detect_exception

from bot.config import reddit_max_post_text_length, title_exclusion_words
from bot.helpers.enums import ArticleType

ITEM_NUMBER = re.compile(r'^(\d+)\.', flags=re.MULTILINE)  # An item's number starts its line: "3. Foo"
ITEM_START = re.compile(r'\n(?=\d+\.)')  # The line break before each numbered line

DetectorFactory.seed = 0  # langdetect guesses at random otherwise: the same title could pass one sweep and fail the next
MIN_WORDS_TO_DETECT = 5  # with fewer words langdetect guesses: "8 Pizza Hacks" reads as Polish


# One session for every page of a sweep: a site's archive and its articles share a host, so its connection is kept
# between them rather than opened again for each. Only the schedule's thread (or dev/sweep.py) fetches
_session = requests.Session()
# Asked for as Chrome asks for a page it's opening: BuzzFeed answers 406 at times to requests' bare "Accept: */*".
# Accept-Encoding stays requests' own, which lists only what it can decode
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
})


def close_connections():
    """Close the connections a sweep kept open; the next sweep opens its own. Kept until then (90 minutes), Azure's
    outbound NAT forgets a connection idle for 4 minutes without telling either end, so reusing it would send a
    request no site receives and wait the whole timeout for the answer."""

    _session.close()


def soup_session(link):
    """The page at the link, read by BeautifulSoup. An error page (403, 404, 5xx) raises rather than reading as a
    page without articles, so a site that blocks the bot or moved its archive shows as failing, not as quiet."""

    response = _session.get(link, timeout=60)  # A site that never answers would hold up every sweep after it
    response.raise_for_status()
    return BeautifulSoup(response.content, 'html.parser')


def post_previously_made(article_link, recent_posts):
    """
    Checks if the post has already been submitted: whether one of the subreddit's recent posts (reddit.recent_posts,
    read once per sweep) has the article's link in its text.
    """

    return any(article_link in submission.selftext for submission in recent_posts)


def get_title_exclusion_words(website):
    """Returns a list of words that should prevent the article from being posted if contained in the title."""

    if website in title_exclusion_words:
        return title_exclusion_words[ArticleType.All] + title_exclusion_words[website]
    else:
        return title_exclusion_words[ArticleType.All]


def get_article_list_count(article_title):
    """Returns number of points in the list article."""

    text_number_mapping = {
        'one': 1,
        'two': 2,
        'three': 3,
        'four': 4,
        'five': 5,
        'six': 6,
        'seven': 7,
        'eight': 8,
        'nine': 9,
        'ten': 10,
    }
    words = article_title.split()
    if not words:
        return 0  # an empty title (a card whose link is only a picture) isn't a list

    first_word = words[0].lower()

    if first_word in text_number_mapping:
        return text_number_mapping[first_word]

    try:
        list_count = [int(s) for s in words if s.isdigit()][0]
    except (AttributeError, IndexError):
        return 0

    return list_count


def is_english_title(article_title):
    """Whether a title reads as English. A title too short for langdetect to judge only needs
    plain letters (no accents or other scripts), which still keeps out Japanese and most
    Spanish, Portuguese or French titles. A title with no letters at all isn't English."""

    words = [word for word in article_title.split() if not word.isdigit()]
    if len(words) < MIN_WORDS_TO_DETECT:
        letters = [character for character in article_title if character.isalpha()]
        return bool(letters) and all(letter.isascii() for letter in letters)

    try:
        return detect(article_title) == 'en'
    except lang_detect_exception.LangDetectException:
        return False


def article_title_meets_posting_requirements(website, article_title):
    """
    Validates that the article title meets all requirements to post the list to Reddit.

    The validations below check if:
        (1) The article contains a number
        (2) The article title doesn't contain certain pre-defined keywords
        (3) The article title is in english (BuzzFeed only)

    Returns True if all validations are met. Returns False otherwise.
    """

    if website == ArticleType.BuzzFeed and not is_english_title(article_title):
        return False

    if get_article_list_count(article_title) == 0:
        return False

    if any(words in article_title.lower() for words in get_title_exclusion_words(website)):
        return False

    return True


def article_text_meets_posting_requirements(website, article_list_text, list_counter, total_elements):
    """
    Validates that the article text meets all requirements to post the list to Reddit.

    The validations below check if:
        (1) The header count is equal to the list article count
        (2) The items are numbered 1 to N (or N to 1), each once, in order
        (3) The article resembles an ad based on specific regex validations or list element ends with ':' (BuzzFeed only)

    Returns True if all validations are met. Returns False otherwise.
    """

    if list_counter-1 != total_elements \
            or len(article_list_text) >= reddit_max_post_text_length \
            or not is_correctly_formatted_list(article_list_text, list_counter):
        return False

    if website == ArticleType.BuzzFeed:
        percentage_threshold = 0.50  # Max percentage of regex validated ad-like list items where the post will not be made.
        if (len(re.findall('(.amazon.)', article_list_text)) / total_elements) >= percentage_threshold:
            return False
        if (len(re.findall(r'(\[A(n)? |\[(Up to )?[0-9]{2}% |\[This )', article_list_text)) / total_elements) >= percentage_threshold:
            return False
        if (len(re.findall('(. This |. When )', article_list_text)) / total_elements) >= percentage_threshold:
            return False

        # Articles where list items end with a colon will not be posted (most likely referencing an image below).
        if ':\n' in article_list_text:
            return False

    return True


def item_numbers(full_text):
    """Returns the number of each item, in the order they appear."""

    return [int(number) for number in ITEM_NUMBER.findall(full_text)]


def is_correctly_formatted_list(full_text, list_count):
    """Checks that the items are numbered 1 to N, each once and in order
    (counting up, or down for a countdown put_list_in_order reverses later).
    A number only counts at the start of a line, so the "1." in "11." or "$1.99" doesn't."""

    expected = list(range(1, list_count))
    return item_numbers(full_text) in (expected, expected[::-1])


def put_list_in_order(full_text):
    """Returns the list counting up. A countdown has its items reversed, each item keeping its own lines."""

    numbers = item_numbers(full_text)
    if len(numbers) < 2 or numbers[0] < numbers[-1]:
        return full_text

    return '\n'.join(reversed(ITEM_START.split(full_text.strip('\n')))) + '\n'
