import re
import time

import helpers.list_validation_methods as lvm
from config import business_insider_article_archive_link as archive_link
from helpers.enums import *
from helpers.reddit import post_to_reddit


def find_article_to_parse(create_post=True):
    """Finds a list article in Business Insider's latest article archive and posts the list article to Reddit."""

    website = ArticleType.Business_Insider
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    soup = lvm.soup_session(archive_link)

    for link in soup.find_all('h3', attrs={'class': 'tout-title'}):

        article_title = link.find('a', href=True)
        article_link = article_title['href'] if article_title['href'].startswith("http") else "http://www.businessinsider.com" + article_title['href']

        print("Parsing article: " + article_link)
        time.sleep(1)

        if not lvm.article_title_meets_posting_requirements(website, article_title.text):
            continue

        article_list_text = get_article_list_text(article_link, lvm.get_article_list_count(article_title.text))
        if article_list_text and not lvm.post_previously_made(article_link):
            print(f"{website_name} list article found: " + article_title.text)
            if create_post:
                post_to_reddit(article_title.text, article_list_text, article_link, website)
            return True

    print(f"No {website_name} list articles were found to parse at this time.")
    return False


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
            if not full_list.startswith('1. '):
                full_list = lvm.reverse_list(full_list)
            break
        else:
            list_counter = 1
            full_list = ""

    return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse(create_post=False)
    print("Business Insider script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
