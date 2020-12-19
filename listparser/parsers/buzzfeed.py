import time
from datetime import date, timedelta
from os import path

import helpers.list_validation_methods as lvm
from helpers.enums import *
from helpers.reddit import post_to_reddit


BUZZFEED_ARTICLES_SEARCHED_FILE = 'buzzfeed_articles_searched.txt'


def get_articles_searched_count():
    """Gets the number of articles the bot already searched in yesterdays archive"""

    yesterdays_date = (date.today() - timedelta(1)).strftime("%Y/%m/%d")

    if not path.exists(BUZZFEED_ARTICLES_SEARCHED_FILE):
        set_total_articles_searched_today(yesterdays_date, 0)
        return 0

    with open(BUZZFEED_ARTICLES_SEARCHED_FILE, 'r') as file:
        if yesterdays_date != file.readline().strip():
            set_total_articles_searched_today(yesterdays_date, 0)
            return 0
        for i, line in enumerate(file):
            if i == 0:  # Second line since first line was read above.
                return int(line)

    return 0


def set_total_articles_searched_today(current_date, article_completed_count=0):
    """Modifies the file to contain the current archive date and the number of articles already searched."""

    with open(BUZZFEED_ARTICLES_SEARCHED_FILE, 'w+') as file:
        file.write(current_date + '\n' + str(article_completed_count) + '\n')


def paragraph_article_text(link_to_check, total_list_elements):
    """Parses BuzzFeed list articles that are in paragraph form (have the 'p' HTML tag)."""

    list_counter = 1
    full_list = ""

    soup = lvm.soup_session(link_to_check)

    for list_element in soup.find_all('p'):
        if list_element.text and list_element.text[0].isdigit():
            full_list += list_element.text.replace(')', '. ', 1) + '\n'
            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.BuzzFeed, full_list, list_counter, total_list_elements):
        if not full_list.startswith('1. '):
            full_list = lvm.reverse_list(full_list)

        return full_list


def find_article_to_parse(subreddit, website):
    """Finds a list article in BuzzFeed's article archive of yesterday's and posts the list article to Reddit."""

    current_iter = 0
    articles_searched_count = get_articles_searched_count()
    yesterdays_date = (date.today() - timedelta(1)).strftime("%Y/%m/%d")

    archive_link = 'https://www.buzzfeed.com/archive/'
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive on " + yesterdays_date)
    soup = lvm.soup_session(archive_link + yesterdays_date)

    for link in soup.find_all('article', attrs={'data-buzzblock': 'story-card'})[articles_searched_count:]:

        current_iter += 1

        article_title = link.find('a', href=True)
        article_link = article_title['href']
        print("Parsing article: " + article_link)
        time.sleep(1)

        if not lvm.article_title_meets_posting_requirements(website, article_title.text):
            continue

        no_of_elements = lvm.get_article_list_count(article_title.text)

        article_list_text = get_article_list_text(article_link, no_of_elements)
        if not article_list_text:
            article_list_text = paragraph_article_text(article_link, no_of_elements)

        if article_list_text and not lvm.post_previously_made(subreddit, article_link):
            print(f"{website_name} list article found: " + article_title.text)
            post_to_reddit(article_title.text, article_list_text, article_link, subreddit, website)
            set_total_articles_searched_today(yesterdays_date, articles_searched_count + current_iter)
            return True

    set_total_articles_searched_today(yesterdays_date, articles_searched_count + current_iter)

    print(f"No {website_name} list articles were found to parse at this time.")
    return False


def get_article_list_text(link_to_check, total_list_elements):
    """Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

    list_counter = 1
    full_list = ""

    soup = lvm.soup_session(link_to_check)

    for article in soup.find_all('h2'):

        list_item_number_element = article.find('span', attrs={'class': 'subbuzz__number'})
        list_item_text_element = article.find('span', attrs={'class': 'js-subbuzz__title-text'})

        if list_item_number_element and list_item_text_element:

            list_item_number = list_item_number_element.text

            # Tries to add a hyperlink to the article list element being searched, if it has any.
            try:
                for link in list_item_text_element.find_all('a', href=True):
                    link_to_use = link['href']

                    # Removes redirect link if there is any.
                    if link_to_use.startswith('http:') and (r'/https:' in link_to_use or r'/http:' in link_to_use):
                        link_to_use = 'http' + link_to_use.split(r'/http', 1)[1]

                    link_to_use = link_to_use.replace(')', r'\)')

                    full_list += list_item_number + ' [' + list_item_text_element.text + '](' + link_to_use + ')' + '\n'
                    break
            except KeyError as e:
                print("Key Error: " + str(e))
                pass

            # If the list element doesn't have a link associated to it, post it as plain text.
            if not list_item_text_element.find_all('a', href=True):
                full_list += list_item_number + ' ' + list_item_text_element.text + '\n'

            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.BuzzFeed, full_list, list_counter, total_list_elements):
        if not full_list.startswith('1. '):
            full_list = lvm.reverse_list(full_list)

        return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse("buzzfeedbot", ArticleType.BuzzFeed)
    print("BuzzFeed script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
