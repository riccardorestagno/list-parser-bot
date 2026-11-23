import bot.helpers.list_validation_methods as lvm
from bot.config import screen_rant_article_archive_link as archive_link
from bot.config import screen_rant_max_articles_to_search as max_articles_to_search
from bot.helpers.enums import *
from bot.helpers.post import Article


def find_articles():
    """The latest articles in Screen Rant's archive, up to its limit."""

    soup = lvm.soup_session(archive_link)
    articles = []

    for heading in soup.find_all("h5", attrs={"class": "display-card-title"}, limit=max_articles_to_search):
        link = heading.find("a", href=True)
        if link:
            # Kept as it always was: the links in earlier posts are what tells an article was posted before
            article_link = link['href'] if link['href'].startswith("http") else "http://www.screenrant.com" + link['href']
            articles.append(Article(link.text.strip(), article_link))

    return articles


def get_article_list_text(link_to_check, total_list_elements):
    """Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

    list_counter = 1
    full_list = ""

    soup = lvm.soup_session(link_to_check)

    for header in soup.find_all("h2"):
        if header.find('span', class_='item-num') and len(header.find_all('span')) == 2:
            list_item_number = header.find('span', class_='item-num').text.strip()
            list_item_text = header.find('span', class_=False).text.strip()
        else:
            continue  # Not supported

        if list_item_number and list_item_number.isdigit() and list_item_text:
            full_list += f"{list_item_number}. {list_item_text}\n"
            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.Screen_Rant, full_list, list_counter, total_list_elements):
        return lvm.put_list_in_order(full_list)
