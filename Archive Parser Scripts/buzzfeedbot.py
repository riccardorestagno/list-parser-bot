from langdetect import detect, lang_detect_exception
from datetime import date, timedelta
import time

import list_parser_helper_functions
from credentials import *


def get_total_articles_searched_today(current_date):
    """Gets the number of articles the bot already searched today"""

    filepath = FILEPATH

    with open(filepath, 'r') as file:
        if current_date != file.readline().strip():
            set_total_articles_searched_today(current_date, 0)
            return 0
        for i, line in enumerate(file):
            if i == 0:  # Second line since first line was read above
                return int(line)

    return 0


def set_total_articles_searched_today(current_date, article_completed_count=0):
    """Modifies the file to contain the current archive date and the number of articles already searched"""

    filepath = FILEPATH

    with open(filepath, 'w') as file:
        file.write(current_date + '\n' + str(article_completed_count) + '\n')


def article_info(article_date, start_iter):
    """Gets the link to the article that will be posted on the sub.
The three if-statements below check if
(1) The article starts with a number,
(2) The post hasn't been made already,
(3) The articles language is in english,
(4) The articles main points actually have text and not images,
(5) The article title doesn't contain any keywords listed below
If all these conditions are met, this module will get the articles text using the article_text() module
and then posts the corresponding text to Reddit using the reddit_bot() module"""

    current_iter = 0

    print(archive_link + article_date)
    soup = list_parser_helper_functions.soup_session(archive_link + article_date)

    for block in soup.find_all('article', attrs={'data-buzzblock': 'story-card'})[start_iter:]:

        for article in list(block.find_all('a', href=True)):
            current_iter += 1
            print(article['href'])
            time.sleep(3)

            try:
                if not detect(article.text) == 'en':
                    break
            except lang_detect_exception.LangDetectException:
                break

            # Records number of points in the article
            no_of_elements = [int(s) for s in article.text.split() if s.isdigit()]
            if not no_of_elements:
                break

            article_title_lowercase = article.text.lower()
            if any(words in article_title_lowercase for words in list_parser_helper_functions.BREAK_WORDS):
                break
            try:
                post_made = list_parser_helper_functions.post_made_check(article_title_lowercase, no_of_elements[0], my_subreddit)
            except IndexError:
                post_made = list_parser_helper_functions.post_made_check(article_title_lowercase, 0, my_subreddit)

            if post_made:
                break

            list_article_link = article['href']

            # Avoids rare case of when there is an index error
            # (occurs when article starts with number immediately followed by a symbol)
            try:
                article_text_to_use = article_text(list_article_link, no_of_elements[0])
                if article_text_to_use == '':
                    article_text_to_use = list_parser_helper_functions.paragraph_article_text(list_article_link, no_of_elements[0])

                if article_text_to_use != '':
                    list_parser_helper_functions.reddit_bot(article.text, article_text_to_use, list_article_link, my_subreddit, website_name)
                    print(article.text)
                    start_iter += current_iter
                    set_total_articles_searched_today(article_date, start_iter)
                    return
            except IndexError:
                pass
            break  # Only finds first link

    set_total_articles_searched_today(article_date, start_iter + current_iter)


def article_text(link_to_check, total_points):
    """Concatenates the list elements of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure the number of list elements in the article is equal to the number the article title starts with"""

    list_counter = 1
    this_when_counter = 0
    full_list = ''

    soup = list_parser_helper_functions.soup_session(link_to_check)

    for articles in soup.find_all('h2'):

        list_element_check = False

        for list_element in articles.find_all('span', attrs={'class': 'subbuzz__number'}):
            if list_element:
                list_element_check = True
                break

        if not list_element_check:
            continue

        for article in articles.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
            if len(article.text) < 4 or article.text.endswith(':'):
                return ''
            else:
                full_list_temp = full_list
                if this_when_counter == 3:
                    return ''

                if article.text.startswith(('When ', 'This ', 'And this ')):
                    this_when_counter += 1
                else:
                    this_when_counter = 0

                # Tries to add a hyperlink to the article list element being searched, if it has any
                try:
                    for link in article.find_all('a', href=True):
                        if 'amazon' in link['href']:
                            link_to_use = link['href'].split('?', 1)[0]
                        else:
                            link_to_use = link['href']

                        # removes redirect link if there is any
                        if link_to_use.startswith('http:') and (r'/https:' in link_to_use or r'/http:' in link_to_use):
                            link_to_use = 'http' + link_to_use.split(r'/http', 1)[1]

                        link_to_use = link_to_use.replace(')', r'\)')

                        if article.text.startswith((str(list_counter)+'.', str(list_counter)+')')):
                            full_list += '[' + article.text + '](' + link_to_use + ')' + '\n'
                        else:
                            full_list += str(list_counter) + '. ' + '[' + article.text + '](' + link_to_use + ')' + '\n'
                        break
                except KeyError:
                    pass

                # If the list element doesn't have a link associated to it, post it as plain text
                if full_list_temp == full_list:
                    if article.text.startswith(str(list_counter)+')'):
                        article.text.replace(str(list_counter)+')', str(list_counter)+'. ')
                    if article.text.startswith(str(list_counter)+'.'):
                        full_list += article.text + '\n'
                    else:
                        full_list += str(list_counter) + '. ' + article.text + '\n'
            list_counter += 1

    if total_points != list_counter-1:
        full_list = ''

    return full_list


def url_to_search():

    yesterday = date.today() - timedelta(1)
    date_format = yesterday.strftime("%Y/%m/%d")

    total_articles_searched_today = get_total_articles_searched_today(date_format)

    article_info(date_format, total_articles_searched_today)


if __name__ == "__main__":

    my_subreddit = 'buzzfeedbot'
    website_name = 'BuzzFeed'
    archive_link = 'https://www.buzzfeed.com/archive/'

    start_time = round(time.time(), 2)

    print('Searching Yesterdays Archive')
    url_to_search()

    print('Script ran for ' + str(round((time.time() - start_time), 2)) + ' seconds')
