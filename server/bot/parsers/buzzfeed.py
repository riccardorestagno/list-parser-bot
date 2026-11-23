import bot.helpers.list_validation_methods as lvm
from bot.config import buzzfeed_article_archive_link as archive_link
from bot.config import buzzfeed_max_articles_to_search as max_articles_to_search
from bot.helpers.enums import *
from bot.helpers.post import Article


def find_articles():
    """The latest articles in BuzzFeed's archive, up to its limit."""

    soup = lvm.soup_session(archive_link)
    articles = []

    for card in soup.find_all('article', attrs={'data-buzzblock': 'story-card'}, limit=max_articles_to_search):
        link = card.find('a', href=True)
        if link:
            articles.append(Article(link.text.strip(), link['href']))

    return articles


def get_article_list_text(link_to_check, total_list_elements):
    """The article's list, from its numbered headings or, failing that, its numbered paragraphs: one fetch for both."""

    soup = lvm.soup_session(link_to_check)
    return heading_list_text(soup, total_list_elements) or paragraph_list_text(soup, total_list_elements)


def heading_list_text(soup, total_list_elements):
    """Reads BuzzFeed list articles whose points are numbered headings (the 'h2' HTML tag)."""

    list_counter = 1
    full_list = ""

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
        return lvm.put_list_in_order(full_list)


def paragraph_list_text(soup, total_list_elements):
    """Reads BuzzFeed list articles that are in paragraph form (has the 'p' HTML tag)."""

    list_counter = 1
    full_list = ""

    for list_element in soup.find_all('p'):
        if list_element.text and list_element.text[0].isdigit():
            full_list += list_element.text.replace(') ', '. ', 1) + '\n'
            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.BuzzFeed, full_list, list_counter, total_list_elements):
        return lvm.put_list_in_order(full_list)
