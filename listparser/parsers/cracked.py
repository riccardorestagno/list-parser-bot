import time

import helpers.list_validation_methods as lvm
from config import cracked_article_archive_link as archive_link
from config import cracked_max_articles_to_search as max_articles_to_search
from helpers.enums import *
from helpers.reddit import post_to_reddit


def find_article_to_parse():
    """Finds a list article in Cracked's latest article archive and posts the list article to Reddit."""

    website = ArticleType.Cracked
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    soup = lvm.soup_session(archive_link)

    for article in soup.find_all("div", attrs={"class": "content-cards-info"}, limit=max_articles_to_search):

        article_title = article.find("span", attrs={"class": "content-card-title"}).find("a", href=True)
        if article_title:
            article_link = article_title['href']
            print("Parsing article: " + article_link)
            time.sleep(1)

            if not lvm.article_title_meets_posting_requirements(website, article_title.text):
                continue

            article_list_text = get_article_list_text(article_link, lvm.get_article_list_count(article_title.text))
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

    for article in soup.find_all("h2", attrs={"class": "subheading"}):

        list_item_number_element = article.find("div", attrs={"class": "num-wrap"})
        list_item_text_element = article.find("div", attrs={"class": None}).find("div", attrs={"class": None}) if list_item_number_element else None

        list_item_number = list_item_number_element.text if list_item_number_element else str(list_counter)
        list_item_text = list_item_text_element.text.strip() if list_item_text_element else article.text.strip()

        if list_item_text:
            full_list += f"{list_item_number}. {list_item_text}\n"
            list_counter += 1

    if lvm.article_text_meets_posting_requirements(ArticleType.Cracked, full_list, list_counter, total_list_elements):
        if not full_list.startswith('1. '):
            full_list = lvm.reverse_list(full_list)

        return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse()
    print("Cracked script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
