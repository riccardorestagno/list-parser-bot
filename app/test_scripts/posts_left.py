from bs4 import BeautifulSoup
from langdetect import detect, lang_detect_exception
from datetime import date, timedelta
import time
import requests
import praw
from os import environ
from dotenv import load_dotenv
load_dotenv()


def total_articles_today(link_completed_count=0, article_completed_count=0, modify=False):
    """Things to do:
        RESET TO 0, 0 WHEN ITS A NEW DAY"""
    filepath = r'C:\Users\Riccardo\Desktop\Python_Scripts\BuzzFeed Reddit Bot\Posts_Made_Today.txt'

    if not modify:
        with open(filepath, 'r') as file:
            links_searched, articles_searched = file.read().split('\n')
        return int(links_searched), int(articles_searched)

    else:
        with open(filepath, 'w') as file:
            file.write(str(link_completed_count) + '\n' + str(article_completed_count))


def post_reset():
    import datetime
    current_time = datetime.datetime.now().time()
    min_time = datetime.time(2, 55)
    max_time = datetime.time(3, 5)
    if min_time <= current_time <= max_time:
        total_articles_today(0, 0, True)
        print('reset done')


def post_made_check(post_title, subpoints):
    """Checks if the post has already been submitted.
Returns True if post was submitted already and returns False otherwise"""

    post_made = False
    reddit = praw.Reddit(client_id=environ["BUZZFEEDBOT_CLIENT_ID"],
                         client_secret=environ["BUZZFEEDBOT_CLIENT_SECRET"],
                         user_agent=environ["BUZZFEEDBOT_USER_AGENT"],
                         username=environ["BUZZFEEDBOT_USERNAME"],
                         password=environ["BUZZFEEDBOT_PASSWORD"])

    subreddit = reddit.subreddit('buzzfeedbot')
    submissions = subreddit.new(limit=40)
    for submission in submissions:
        if submission.title.lower() == post_title:
            post_made = True
            break
        subpoints_to_check = [int(s) for s in submission.title.split() if s.isdigit()]
        if subpoints_to_check == subpoints:
            same_words = set.intersection(set(post_title.split(" ")), set(submission.title.lower().split(" ")))
            number_of_words = len(same_words)
            if number_of_words >= 4:
                post_made = True
                break
    return post_made


def article_info(date, link_count, start_iter):
    """Gets the link to the article that will be posted on the sub.
The three if-statements below check if (1) the article starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english,(4) if the articles main points actually have text and not images and
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will get the articles text using the article_text() module
and then posts the corresponding text to reddit using the reddit_bot() module"""

    current_iter = 0
    break_words = ['gifts']
    session = requests.Session()
    daily_archive = session.get('https://www.buzzfeed.com/archive/' + date )
    soup = BeautifulSoup(daily_archive.content, 'html.parser')

    for link in list(soup.find_all('a', attrs={'class': 'link-gray'}, href=True))[start_iter:]:
        current_iter += 1
        for article_to_open in link.find_all('h2', attrs={'class': 'xs-mb05 xs-pt05 sm-pt0 xs-text-4 sm-text-2 bold'}):

            try:
                if not ((article_to_open.text[0].isdigit() or article_to_open.text.lower().startswith(('top','the'))) \
                and detect(article_to_open.text) == 'en'):
                    break
            except lang_detect_exception.LangDetectException:
                break

            article_title_lowercase = article_to_open.text.lower()
            if any(words in article_title_lowercase for words in break_words):
                break

            # Records number of points in the article
            no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()]
            post_made = post_made_check(article_title_lowercase, no_of_points)
            if post_made == True:
                break

            top_x_link = 'https://www.buzzfeed.com' + link['href']

            # Avoids rare case of when there is an index error
            # (occurs when article starts with number immediately followed by a symbol)
            try:
                article_text_to_use = article_text(top_x_link, no_of_points[0])
                if article_text_to_use == '':
                    pass
                else:
                    start_iter += current_iter
                    current_iter = 0
                    print(article_to_open.text)
                    print(start_iter)
                    total_articles_today(article_completed_count = start_iter, modify=True)

                break
            except IndexError:
                break

    total_articles_today(link_completed_count=link_count + 1, article_completed_count=0, modify=True)


def article_text(link_to_check, total_points):
    """Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of subpoints in the article is equal to the number the atricle title starts with"""

    i = 1
    this_when_counter = 0
    top_x_final = ''
    session = requests.Session()
    article = session.get(link_to_check)
    soup = BeautifulSoup(article.content, 'html.parser')

    for title in soup.find_all('h3'):

        subpoint_check = False

        for subpoint in title.find_all('span', attrs={'class': 'subbuzz__number'}):
            subpoint_check = True
            break

        if not subpoint_check:
            continue

        for article in title.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
            if len(article.text) < 4 or article.text.endswith(':'):
                return ''
            else:
                top_x_final_temp = top_x_final
                if this_when_counter == 3:
                    return ''
                if article.text.startswith(('When ', 'This ', 'And this ')):
                    this_when_counter += 1
                else:
                    this_when_counter = 0
                try:
                    for link in article.find_all('a', href=True):
                        link_to_use = link['href']

                        # removes redirect link if there is any
                        if link_to_use.startswith('http:') and (r'/https:' in link_to_use or r'/http:' in link_to_use):
                            link_to_use = 'http' + link_to_use.split(r'/http', 1)[1]
                        if 'amazon' in link['href']:  # removes buzzfeed tag in all amazon links
                            link_to_use = link_to_use.split('?', 1)[0]
                        link_to_use = link_to_use.replace(')', r'\)')
                        if article.text.startswith((str(i)+'.' , str(i)+')')):
                            top_x_final += '[' + article.text + '](' + link_to_use+')' + '\n'
                        else:
                            top_x_final += str(i) + '. [' + article.text + '](' + link_to_use+')' + '\n'
                        break
                except KeyError:
                    pass
                if top_x_final_temp == top_x_final:
                    if article.text.startswith((str(i)+'.', str(i)+')')):
                        top_x_final += article.text + '\n'
                    else:
                        top_x_final += str(i) + '. ' + article.text + '\n'
            i += 1

    if total_points != i-1:
        top_x_final = ''

    return top_x_final


if __name__ == "__main__":

    start_time = round(time.time(), 2)
    yesterday = date.today() - timedelta(1)
    leading_zero_date = yesterday.strftime("%Y/%m/%d")
    post_reset()

    complete_links_searched, article_count = total_articles_today()

    if complete_links_searched == 0:
        print('Searching first link')
        article_info(leading_zero_date, complete_links_searched, article_count)
        complete_links_searched, article_count = total_articles_today()

    remove_one_leading_zero_date = leading_zero_date.replace('/0', '/', 1)

    # POST MADE BOOLEAN NO LONGER NECESSARY CUZ OF COMPLETED LINKS SEARCHED
    if complete_links_searched == 1 and leading_zero_date != remove_one_leading_zero_date:
        print('Searching second link')
        article_info(remove_one_leading_zero_date, complete_links_searched, article_count)
        complete_links_searched, article_count = total_articles_today()

    remove_all_leading_zero_date = leading_zero_date.replace('/0', '/')
    if complete_links_searched == 2 and remove_one_leading_zero_date != remove_all_leading_zero_date:
        print('Searching third link')
        article_info(remove_all_leading_zero_date, complete_links_searched, article_count)

    print('Script ran for ' + str(round((time.time() - start_time), 2)) + ' seconds')
