from bs4 import BeautifulSoup
import requests
import praw

from credentials import *

BREAK_WORDS = ['pictures', 'photos', 'gifs', 'images',
               'twitter', 'must see', 'tweets', 'memes',
               'instagram', 'tumblr', 'gifts', 'products']


def connect_to_reddit():
    return praw.Reddit(client_id=CLIENT_ID,
                       client_secret=CLIENT_SECRET,
                       user_agent=USER_AGENT)


def soup_session(link):
    """BeautifulSoup session"""
    session = requests.Session()
    daily_archive = session.get(link)
    soup = BeautifulSoup(daily_archive.content, 'html.parser')
    return soup


def reddit_bot(headline, main_text, link, my_subreddit, website_name):
    """Module that takes the title, main text and link to article and posts directly to reddit"""

    reddit = connect_to_reddit()

    reddit.subreddit(my_subreddit).submit(title=headline, selftext=main_text+'\n' + '[Link to article](' + link + ')').\
        mod.flair(text=website_name)


def post_made_check(post_title, subpoints, my_subreddit):
    """Checks if the post has already been submitted.
Returns True if post was submitted already and returns False otherwise"""

    post_made = False
    reddit = connect_to_reddit()
    subreddit = reddit.subreddit(my_subreddit)
    submissions = subreddit.new(limit=40)
    for submission in submissions:
        if submission.title.lower() == post_title:
            post_made = True
            break
        try:
            subpoints_to_check = [int(s) for s in submission.title.split() if s.isdigit()][0]
        except IndexError:
            continue
        if subpoints_to_check == subpoints:
            same_words = set.intersection(set(post_title.split()), set(submission.title.lower().split()))
            number_of_words = len(same_words)
            if number_of_words >= 4:
                post_made = True
                break
    return post_made


def paragraph_article_text(link_to_check, total_points):
    """Parses list articles that are in paragraph form (have the 'p' HTML tag)"""

    i = 1
    top_x_final = ''

    soup = soup_session(link_to_check)

    for subpoint in soup.find_all('p'):
        try:
            if subpoint.text[0].isdigit():
                top_x_final += subpoint.text.replace(')', '. ', 1) + '\n'
                i += 1
        except IndexError:
            continue

    if total_points != i-1:
        top_x_final = ''
    return top_x_final


def chronological_list_maker(full_list_text, list_count):

    count_list = []

    for x, y in zip(range(1, list_count), reversed(range(1, list_count))):
        count_list.append([x, y])

    for i, (x, y) in enumerate(count_list):
        count_list[i] = [str(x) + '.', str(y) + '.']

    for i, (start, end) in enumerate(count_list):
        if i <= len(count_list) / 2:
            full_list_text = full_list_text.replace(end, start)
        else:
            full_list_text = start.join(full_list_text.rsplit(end, 1))

    return full_list_text