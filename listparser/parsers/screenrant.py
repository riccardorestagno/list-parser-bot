import time
from bs4 import NavigableString

import helpers.list_validation_methods as lvm
from config import screen_rant_article_archive_link as archive_link
from config import screen_rant_max_articles_to_search as max_articles_to_search
from helpers.enums import *
from helpers.reddit import post_to_reddit


def find_article_to_parse(create_post=True):
    """Finds a list article in Screen Rant's latest article archive and posts the list article to Reddit."""

    website = ArticleType.Screen_Rant
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    soup = lvm.soup_session(archive_link)

    for article in soup.find_all("h5", attrs={"class": "display-card-title"}, limit=max_articles_to_search):
        article = article.find("a", href=True)

        if article:

            article_title = article.text.strip()
            article_link = article['href'] if article['href'].startswith("http") else "http://www.screenrant.com" + article['href']

            print(f"Parsing article: {article_link}")
            time.sleep(1)

            if not lvm.article_title_meets_posting_requirements(website, article_title):
                continue

            article_list_text = get_article_list_text(article_link, lvm.get_article_list_count(article_title))
            if article_list_text and not lvm.post_previously_made(article_link):
                print(f"{website_name} list article found: {article_title}")
                if create_post:
                    post_to_reddit(article_title, article_list_text, article_link, website)
                return True

    print(f"No {website_name} list articles were found to parse at this time.")
    return False


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
        if not full_list.startswith('1. '):
            full_list = lvm.reverse_list(full_list)

        return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse(create_post=False)
    print("Screen Rant script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
