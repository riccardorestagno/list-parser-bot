import app.helper_scripts.list_parser_helper_methods as helper_methods
import re
import time
from datetime import datetime


def article_info():
    """Gets the link to the article that will be posted on the sub"""

    soup = helper_methods.soup_session(archive_link)

    for link in soup.find_all('h3'):

        article_to_open = link.find('a', href=True)

        # Records number of points in the article
        try:
            no_of_elements = [int(s) for s in article_to_open.text.split() if s.isdigit()]
        except AttributeError:
            continue

        if not no_of_elements:
            continue

        article_title_lowercase = article_to_open.text.lower()

        if any(words in article_title_lowercase for words in helper_methods.BREAK_WORDS):
            continue

        post_made = helper_methods.post_made_check(article_title_lowercase, no_of_elements[0], my_subreddit)

        if post_made:
            continue

        list_article_link = article_to_open['href']

        # Avoids rare case of when there is an index error
        # (occurs when article starts with number immediately followed by a symbol)
        try:
            article_text_to_use = article_text(list_article_link, no_of_elements[0])
            if article_text_to_use == '':
                article_text_to_use = helper_methods.paragraph_article_text(list_article_link, no_of_elements[0])
            if article_text_to_use != '':
                print(list_article_link)
                print(article_to_open.text)
                helper_methods.reddit_bot(article_to_open.text, article_text_to_use, list_article_link, my_subreddit, website_name)

                return True

        except IndexError as e:
            print("Index Error: " + e)

    return False


def article_text(link_to_check, total_elements):
    """Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also ensures the number of list elements in the article is equal to the number the article title starts with"""

    list_counter = 1
    full_list = ''

    soup = helper_methods.soup_session(link_to_check)

    for article_point in soup.find_all('h2', attrs={'class': 'slide-title-text'}):

        if re.search("^[0-9]+[.]", article_point.text):
            full_list = article_point.text + '\n' + full_list
        else:
            full_list = str(list_counter) + '. ' + article_point.text + '\n' + full_list

        list_counter += 1

    if total_elements != list_counter-1 or not helper_methods.is_correctly_formatted_list(full_list, list_counter):
        return ''

    if full_list.startswith(str(list_counter-1)):
        full_list = helper_methods.chronological_list_maker(full_list, list_counter)

    return full_list
   

if __name__ == "__main__":

    my_subreddit = 'buzzfeedbot'
    website_name = 'Business Insider'
    archive_link = 'http://www.businessinsider.com/latest'

    while True:  # Temporary functionality to run every three hours. Will adjust docker setup to avoid this method
        start_time = round(time.time(), 2)
        print("Buzzfeed Bot is starting @ " + str(datetime.now()))
        article_info()
        print("Sweep finished @ " + str(datetime.now()))
        time.sleep(60 * 60 * 3)  # Wait for three hours before running again
    # print('Script ran for ' + str(round((time.time()-start_time), 2)) + ' seconds')
