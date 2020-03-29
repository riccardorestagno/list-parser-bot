import app.helper_methods.list_parser_helper_methods as helper_methods
import re
import time


def find_article_to_parse(subreddit, website):
    """Finds a list article in Business Insider's latest article archive and posts the list article to Reddit."""

    archive_link = 'http://www.businessinsider.com/latest'

    print("Searching Business Insider's archive")
    soup = helper_methods.soup_session(archive_link)

    for link in soup.find_all('h2'):

        article_title = link.find('a', href=True)
        print("Parsing article: " + article_title['href'])
        time.sleep(1)

        if not helper_methods.article_meets_posting_requirements(subreddit, website, article_title.text):
            continue

        if article_title['href'].startswith("http"):
            list_article_link = article_title['href']
        else:
            list_article_link = "http://www.businessinsider.com" + article_title['href']

        article_list_text = get_article_list_text(list_article_link, helper_methods.get_article_list_count(article_title.text))
        if article_list_text:
            print("BuzzFeed list article found: " + article_title.text)
            helper_methods.post_to_reddit(article_title.text, article_list_text, list_article_link, subreddit, website)
            return True

    print("No Business Insider list articles were found to parse at this time.")
    return False


def get_article_list_text(link_to_check, total_elements):
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
        full_list = helper_methods.sort_list_numerically(full_list, list_counter)

    return full_list


if __name__ == "__main__":
    start_time = round(time.time(), 2)
    find_article_to_parse("buzzfeedbot", "Business Insider")
    print("Business Insider script ran for " + str(round((time.time()-start_time), 2)) + " seconds")
