import bot.helpers.list_validation_methods as lvm
from bot.config import cracked_article_archive_link as archive_link
from bot.config import cracked_max_articles_to_search as max_articles_to_search
from bot.helpers.enums import *
from bot.helpers.post import Article


def find_articles():
    """The latest articles in Cracked's archive, up to its limit."""

    soup = lvm.soup_session(archive_link)
    articles = []

    for card in soup.find_all("article", attrs={"class": "content-card"}, limit=max_articles_to_search):
        link = card.find("a", href=True)
        if link:
            articles.append(Article(link['title'].strip(), link['href']))

    return articles


def get_article_list_text(link_to_check, total_list_elements):
    """Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

    list_counter = 1
    full_list = ""

    soup = lvm.soup_session(link_to_check)

    for article in soup.find_all("h2", attrs={"class": "subheading subheading-num"}):

        # Expecting two items in contents list (number and header text).
        if len(article.contents) != 2:
            return ""

        list_item_number_element = article.contents[0] if article.contents[0].name == 'label' else None
        list_item_text_element = article.contents[1] if article.contents[1].name == 'span' else None

        list_item_number = list_item_number_element.text.strip() if list_item_number_element else None
        list_item_text = list_item_text_element.text.strip() if list_item_text_element else None

        if list_item_text:
            full_list += f"{list_item_number}. {list_item_text}\n"
            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.Cracked, full_list, list_counter, total_list_elements):
        return lvm.put_list_in_order(full_list)
