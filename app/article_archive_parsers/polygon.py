import article_archive_parsers.helper_methods.list_parser_helper_methods as helper_methods
import re
import time
from article_archive_parsers.helper_methods.enums import *


def find_article_to_parse(subreddit, website):
    """Finds a list article in Polygons's latest article archive and posts the list article to Reddit."""

    archive_link = 'http://www.polygon.com'
    website_name = convert_enum_to_string(website)

    print(f"Searching {website_name}'s archive.")
    soup = helper_methods.soup_session(archive_link)

    for link in soup.find_all('h2', attrs={'class': 'c-entry-box--compact__title'}):

        article_header = link.find('a', href=True)
        print("Parsing article: " + article_header['href'])
        time.sleep(1)

        if not helper_methods.article_meets_posting_requirements(subreddit, website, article_header.text):
            continue

        list_article_link = article_header['href']

        article_list_text = get_article_list_text(list_article_link, helper_methods.get_article_list_count(article_header.text))
        if article_list_text:
            print(f"{website_name} list article found: " + article_header.text)
            helper_methods.post_to_reddit(article_header.text, article_list_text, list_article_link, subreddit, website)
            return True

    print(f"No {website_name} list articles were found to parse at this time.")
    return False


def get_article_list_text(link_to_check, total_list_elements):
    """Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

    article_point_found = False
    list_counter = 1
    full_list = ""
    formatting_options = {
        # Header formatting
        "html_format_1": {
            "wrapper": ["h2"],
            "body": ["strong"]
        }
    }

    soup = helper_methods.soup_session(link_to_check)

    for option in formatting_options.values():

        wrapper = option["wrapper"]
        body = option["body"]

        for article_point_wrapper in soup.find_all(wrapper[0], attrs=None if len(wrapper) == 1 else {wrapper[1]: wrapper[2]}):
            article_point_text = ""
            for article_point in article_point_wrapper.find_all(body[0], attrs=None if len(body) == 1 else {body[1]: body[2]}):
                article_point_found = True
                if re.search("^[0-9]+[.]", article_point_text):
                    article_point_text += article_point.text
                else:
                    article_point_text += str(list_counter) + '. ' + article_point.text.strip()

            if article_point_found:
                full_list += article_point_text + '\n'
                list_counter += 1
                article_point_found = False

        if total_list_elements == list_counter-1 and helper_methods.is_correctly_formatted_list(full_list, list_counter):
            break
        else:
            list_counter = 1
            full_list = ""

    if full_list.startswith(str(list_counter-1)):
        full_list = helper_methods.sort_list_numerically(full_list, list_counter)

    return full_list


if __name__ == "__main__":

    start_time = round(time.time(), 2)
    find_article_to_parse("buzzfeedbot", ArticleType.Polygon)
    print("Polygon script ran for " + str(round((time.time()-start_time), 2)) + " seconds.")
