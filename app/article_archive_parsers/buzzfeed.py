import app.helper_methods.list_parser_helper_methods as helper_methods
import re
import time
from datetime import date, timedelta
from langdetect import detect, lang_detect_exception
from os import environ


def get_articles_searched_count():
    """Gets the number of articles the bot already searched in yesterdays archive"""

    yesterdays_date = (date.today() - timedelta(1)).strftime("%Y/%m/%d")
    filepath = environ["BUZZFEEDBOT_ARTICLES_SEARCHED_FILE"]

    with open(filepath, 'r') as file:
        if yesterdays_date != file.readline().strip():
            set_total_articles_searched_today(yesterdays_date, 0)
            return 0
        for i, line in enumerate(file):
            if i == 0:  # Second line since first line was read above
                return int(line)

    return 0


def set_total_articles_searched_today(current_date, article_completed_count=0):
    """Modifies the file to contain the current archive date and the number of articles already searched"""

    filepath = environ["BUZZFEEDBOT_ARTICLES_SEARCHED_FILE"]

    with open(filepath, 'w') as file:
        file.write(current_date + '\n' + str(article_completed_count) + '\n')


def paragraph_article_text(link_to_check, total_points):
    """Parses BuzzFeed list articles that are in paragraph form (have the 'p' HTML tag)."""

    list_counter = 1
    full_list = ""

    soup = helper_methods.soup_session(link_to_check)

    for list_element in soup.find_all('p'):
        try:
            if list_element.text[0].isdigit():
                full_list += list_element.text.replace(')', '. ', 1) + '\n'
                list_counter += 1
        except IndexError:
            continue

    if total_points != list_counter-1:
        full_list = ""

    return full_list


def find_article_to_parse(subreddit_name, website_name):
    """Gets the link to the article that will be posted on the sub.
    The validations below check if:
        (1) The article contains a number
        (2) The post hasn't been made already
        (3) The articles language is in english
        (4) The articles main points actually have text and not images
        (5) The article title doesn't contain any keywords listed below
    If all these conditions are met, this module will get the articles list elements using the get_article_list()
    module and then posts the corresponding text to Reddit using the post_to_reddit() module."""

    archive_link = 'https://www.buzzfeed.com/archive/'

    current_iter = 0
    articles_searched_count = get_articles_searched_count()
    yesterdays_date = (date.today() - timedelta(1)).strftime("%Y/%m/%d")

    print("Searching Buzzfeed's archive on " + yesterdays_date)
    soup = helper_methods.soup_session(archive_link + yesterdays_date)

    for block in soup.find_all('article', attrs={'data-buzzblock': 'story-card'})[articles_searched_count:]:

        for article in list(block.find_all('a', href=True)):
            current_iter += 1
            print("Parsing article: " + article['href'])
            time.sleep(1)

            try:
                if not detect(article.text) == 'en':
                    break
            except lang_detect_exception.LangDetectException:
                break

            # Records number of points in the article.
            no_of_elements = [int(s) for s in article.text.split() if s.isdigit()]
            if not no_of_elements:
                break

            article_title_lowercase = article.text.lower()
            if any(words in article_title_lowercase for words in helper_methods.BREAK_WORDS):
                break
            try:
                post_made = helper_methods.post_made_check(article_title_lowercase, no_of_elements[0], subreddit_name)
            except IndexError:
                post_made = helper_methods.post_made_check(article_title_lowercase, 0, subreddit_name)

            if post_made:
                break

            list_article_link = article['href']

            # Avoids rare case of when there is an index error.
            # Occurs when article starts with number immediately followed by a symbol.
            try:
                article_list = get_article_list(list_article_link, no_of_elements[0])
                if not article_list:
                    article_list = paragraph_article_text(list_article_link, no_of_elements[0])

                if article_list:
                    print("BuzzFeed list article found: " + article.text)
                    helper_methods.post_to_reddit(article.text, article_list, list_article_link, subreddit_name, website_name)
                    articles_searched_count += current_iter
                    set_total_articles_searched_today(yesterdays_date, articles_searched_count)
                    return True

            except IndexError:
                pass
            break  # Only finds first link

    set_total_articles_searched_today(yesterdays_date, articles_searched_count + current_iter)

    print("No BuzzFeed list articles were found to parse at this time.")
    return False


def get_article_list(link_to_check, total_points):
    """Concatenates the list elements of the article into a single string and also makes sure the string isn't empty.
    Also ensures proper list formatting before making a post."""

    list_counter = 1
    this_when_counter = 0
    full_list = ''

    soup = helper_methods.soup_session(link_to_check)

    for article in soup.find_all('h2'):

        list_element_check = False

        for list_element in article.find_all('span', attrs={'class': 'subbuzz__number'}):
            if list_element:
                list_element_check = True
                break

        if not list_element_check:
            continue

        for list_element in article.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
            if len(list_element.text) < 4 or list_element.text.endswith(':') or this_when_counter == 3:
                return ''

            if list_element.text.startswith(('When ', 'This ', 'And this ')):
                this_when_counter += 1
            else:
                this_when_counter = 0

            # Tries to add a hyperlink to the article list element being searched, if it has any
            try:
                for link in list_element.find_all('a', href=True):
                    if 'amazon' in link['href']:
                        link_to_use = link['href'].split('?', 1)[0]
                    else:
                        link_to_use = link['href']

                    # removes redirect link if there is any
                    if link_to_use.startswith('http:') and (r'/https:' in link_to_use or r'/http:' in link_to_use):
                        link_to_use = 'http' + link_to_use.split(r'/http', 1)[1]

                    link_to_use = link_to_use.replace(')', r'\)')

                    if re.search("^[0-9]+[.]", list_element.text):
                        full_list += str(list_counter) + '. [' + list_element.text.split('.', 1)[1] + '](' + link_to_use + ')' + '\n'
                    if re.search("^[0-9]+[)]", list_element.text):
                        full_list += str(list_counter) + '. [' + list_element.text.split(')', 1)[1] + '](' + link_to_use + ')' + '\n'
                    else:
                        full_list += str(list_counter) + '. ' + '[' + list_element.text + '](' + link_to_use + ')' + '\n'
                    break
            except KeyError as e:
                print("Key Error: " + str(e))
                pass

            # If the list element doesn't have a link associated to it, post it as plain text
            if not list_element.find_all('a', href=True):
                if list_element.text.startswith(str(list_counter)+')'):
                    list_element.text.replace(str(list_counter)+')', str(list_counter)+'. ')
                if list_element.text.startswith(str(list_counter)+'.'):
                    full_list += list_element.text + '\n'
                else:
                    full_list += str(list_counter) + '. ' + list_element.text + '\n'

            list_counter += 1

    if total_points != list_counter-1 or not helper_methods.is_correctly_formatted_list(full_list, list_counter):
        return ''

    return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse("buzzfeedbot", "BuzzFeed")
    print("Buzzfeed script ran for " + str(round((time.time()-start_time), 2)) + " seconds")
