import time
from datetime import date, timedelta

import helpers.list_validation_methods as lvm
from config import collegehumor_article_archive_link as archive_link
from helpers.enums import *
from helpers.reddit import post_to_reddit


def article_published_today(link):
	""" Compares the date the article was written with today's date."""

	soup = lvm.soup_session(link)

	todays_date = (date.today() - timedelta(0)).strftime("%B %#d, %Y")  # The # is platform specific
	date_to_check = soup.find('time', attrs={'class': 'date'})

	return date_to_check == todays_date


def find_article_to_parse():
	"""Finds a list article in CollegeHumor's latest article archive and posts the list article to Reddit."""

	website = ArticleType.CollegeHumor
	website_name = convert_enum_to_string(website)

	print(f"Searching {website_name}'s archive.")
	soup = lvm.soup_session(archive_link)

	for article in soup.find_all('h3', attrs={'class': 'title'}):

		article_link = 'http://www.collegehumor.com' + article.find('a')['href']

		if not lvm.article_title_meets_posting_requirements(website, article.text):
			continue

		if article_published_today(article_link):
			article_list_text = get_article_list_text(article_link, lvm.get_article_list_count(article.text))
			if article_list_text and not lvm.post_previously_made(article_link):
				print(f"{website_name} list article found: " + article.text)
				post_to_reddit(article.text, article_list_text, article_link, website)
				return True

	print(f"No {website_name} list articles were found to parse at this time.")
	return False


def get_article_list_text(link_to_check, total_list_elements):
	"""Concatenates the list elements of the article into a single string. Ensures proper list formatting before making a post."""

	list_counter = 1
	full_list = ''

	soup = lvm.soup_session(link_to_check)
		
	for article in soup.find_all('h2'):
		if not article.text or article.text[0].isdigit():
			continue

		full_list += str(list_counter) + '. ' + article.text.strip() + '\n'
		list_counter += 1

	if lvm.article_text_meets_posting_requirements(ArticleType.CollegeHumor, full_list, list_counter, total_list_elements):
		return full_list


if __name__ == "__main__":
	start_time = round(time.time(), 2)
	find_article_to_parse()
	print("CollegeHumor script ran for " + str(round((time.time() - start_time), 2)) + " seconds.")
