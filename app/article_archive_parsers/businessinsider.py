import app.helper_scripts.list_parser_helper_methods as helper_methods
import re
import time


def find_article_to_parse(subreddit_name):
    """Gets the link to the article that will be posted on the sub"""

    website_name = 'Business Insider'
    archive_link = 'http://www.businessinsider.com/latest'

    print("Searching Business Insider's archive")
    soup = helper_methods.soup_session(archive_link)

    for link in soup.find_all('h2'):

        article = link.find('a', href=True)
        print("Parsing article: " + article['href'])
        time.sleep(1)

        # Records number of points in the article
        try:
            no_of_elements = [int(s) for s in article.text.split() if s.isdigit()]
        except AttributeError:
            continue

        if not no_of_elements:
            continue

        article_title_lowercase = article.text.lower()

        if any(words in article_title_lowercase for words in helper_methods.BREAK_WORDS):
            continue

        post_made = helper_methods.post_made_check(article_title_lowercase, no_of_elements[0], subreddit_name)

        if post_made:
            continue

        if article['href'].startswith("http"):
            list_article_link = article['href']
        else:
            list_article_link = "http://www.businessinsider.com" + article['href']

        # Avoids rare case of when there is an index error
        # Occurs when article starts with number immediately followed by a symbol.
        try:
            article_list = get_article_list(list_article_link, no_of_elements[0])
            if article_list:
                print("BuzzFeed list article found: " + article.text)
                helper_methods.post_to_reddit(article.text, article_list, list_article_link, subreddit_name, website_name)
                return True

        except IndexError as e:
            print("Index Error: " + str(e))

    print("No Business Insider list articles were found to parse at this time.")
    return False


def get_article_list(link_to_check, total_elements):
    """Concatenates the list elements of the article into a single string and also makes sure the string isn't empty.
    Also ensures proper list formatting before making a post."""

    list_counter = 1
    full_list = ""
    formatting_options = {
        # Header formatting
        "html_format_1": {
            "wrapper": ["div", "class", "slide-title clearfix"],
            "body": ["h2", "class", "slide-title-text"]
        },
        # Slide formatting
        "html_format_2": {
            "wrapper": ["div", "class", "slide-module"],
            "body": ["h3"]
        },
        # Paragraph formatting
        "html_format_3": {
            "wrapper": ["ol"],
            "body": ["li"]
        }
    }

    soup = helper_methods.soup_session(link_to_check)

    for option in formatting_options.values():

        wrapper = option["wrapper"]
        body = option["body"]

        for article_point_wrapper in soup.find_all(wrapper[0], attrs=None if len(wrapper) == 1 else {wrapper[1]: wrapper[2]}):
            for article_point in article_point_wrapper.find_all(body[0], attrs=None if len(body) == 1 else {body[1]: body[2]}):
                if re.search("^[0-9]+[.]", article_point.text):
                    full_list += article_point.text + '\n'
                else:
                    full_list += str(list_counter) + '. ' + article_point.text + '\n'

                list_counter += 1

        if total_elements == list_counter-1 and helper_methods.is_correctly_formatted_list(full_list, list_counter):
            break
        else:
            list_counter = 1
            full_list = ""

    if full_list.startswith(str(list_counter-1)):
        full_list = helper_methods.chronological_list_maker(full_list, list_counter)

    return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse("buzzfeedbot")
    print("Business Insider script ran for " + str(round((time.time()-start_time), 2)) + " seconds")
