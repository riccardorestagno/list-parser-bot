from helpers.list_validation_methods import soup_session


def test_check_html_tags_correct():
    no_of_elements = 0
    correct_html_tags = False
    soup = soup_session("http://www.insider.com/latest")

    for link in soup.find_all('h2'):

        article_to_open = link.find('a', href=True)

        try:
            no_of_elements = [int(s) for s in article_to_open.text.split() if s.isdigit()]
        except AttributeError:
            continue

        if not no_of_elements:
            continue

    if no_of_elements:

        if article_to_open['href'].startswith("http"):
            list_article_link = article_to_open['href']
        else:
            list_article_link = "http://www.insider.com" + article_to_open['href']

        soup = soup_session(list_article_link)

        if soup.find('h2', attrs={'class': 'slide-title-text'}):
            correct_html_tags = True
    else:
        correct_html_tags = True

    assert correct_html_tags
