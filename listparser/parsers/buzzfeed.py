import time

import helpers.list_validation_methods as lvm
from config import buzzfeed_article_archive_link as archive_link
from config import buzzfeed_max_articles_to_search as max_articles_to_search
from helpers.enums import *
from helpers.reddit import post_to_reddit


def paragraph_article_text(link_to_check, total_list_elements):
    """Parses BuzzFeed list articles that are in paragraph form (has the 'p' HTML tag)."""

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


def find_article_to_parse():
    """Finds a list article in BuzzFeed's latest article archive and posts the list article to Reddit."""

    website = ArticleType.BuzzFeed
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    soup = lvm.soup_session(archive_link)

    for link in soup.find_all('article', attrs={'data-buzzblock': 'story-card'}, limit=max_articles_to_search):

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

        if article_list_text and not lvm.post_previously_made(article_link):
            print(f"{website_name} list article found: " + article_title.text)
            post_to_reddit(article_title.text, article_list_text, article_link, website)
            return True

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
    find_article_to_parse()
    print("BuzzFeed script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
