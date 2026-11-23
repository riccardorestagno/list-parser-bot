import re

import bot.helpers.list_validation_methods as lvm
from bot.config import business_insider_article_archive_link as archive_link
from bot.config import business_insider_max_articles_to_search as max_articles_to_search
from bot.helpers.enums import *
from bot.helpers.post import Article


def find_articles():
    """The latest articles in Business Insider's archive, up to its limit."""

    soup = lvm.soup_session(archive_link)
    articles = []

    for heading in soup.find_all('h3', attrs={'class': 'tout-title'}, limit=max_articles_to_search):
        link = heading.find('a', href=True)
        if link is None:
            continue

        # Kept as it always was: the links in earlier posts are what tells an article was posted before
        article_link = link['href'] if link['href'].startswith("http") else "http://www.businessinsider.com" + link['href']
        articles.append(Article(link.text.strip(), article_link))

    return articles


def get_article_list_text(link_to_check, total_list_elements):
    """Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

    list_counter = 1
    full_list = ""
    parser_options = {
        "slide_parser": {
            "wrapper": ["div", "class", "slide-content"],
            "body": ["h2", "class", "heading-md"]
        },
        "list_header_parser": {
            "wrapper": ["h2"],
            "body": ["strong"]
        }
    }

    soup = lvm.soup_session(link_to_check)

    for option in parser_options.values():

        wrapper = option["wrapper"]
        body = option["body"]

        for article_point_wrapper in soup.find_all(wrapper[0], attrs=None if len(wrapper) == 1 else {wrapper[1]: wrapper[2]}):
            for article_point in article_point_wrapper.find_all(body[0], attrs=None if len(body) == 1 else {body[1]: body[2]}):
                if re.search("^[0-9]+[.]", article_point.text):
                    full_list += article_point.text.strip() + '\n'
                else:
                    full_list += str(list_counter) + '. ' + article_point.text.strip() + '\n'

                list_counter += 1

        if lvm.article_text_meets_posting_requirements(ArticleType.Business_Insider, full_list, list_counter, total_list_elements):
            full_list = lvm.put_list_in_order(full_list)
            break
        else:
            list_counter = 1
            full_list = ""

    return full_list

