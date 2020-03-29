import app.helper_methods.list_parser_helper_methods as helper_methods
import time
from datetime import date, timedelta


def article_published_today(link):
	""" Compares the date the article was written with today's date."""

	soup = helper_methods.soup_session(link)

	todays_date = (date.today() - timedelta(0)).strftime("%B %#d, %Y")  # The # is platform specific
	date_to_check = soup.find('time', attrs={'class': 'date'})

	return date_to_check == todays_date


def find_article_to_parse(subreddit, website):
	"""Finds a list article in CollegeHumor's latest article archive and posts the list article to Reddit."""

	archive_link = 'http://www.collegehumor.com/articles'

	print("Searching CollegeHumors's archive")
	soup = helper_methods.soup_session(archive_link)

	for article in soup.find_all('h3', attrs={'class': 'title'}):
		
		if not helper_methods.article_meets_posting_requirements(subreddit, website, article.text):
			continue
		
		list_article_link = 'http://www.collegehumor.com' + article.find('a')['href']
		
		if article_published_today(list_article_link):
			article_list_text = get_article_list_text(list_article_link, helper_methods.get_article_list_count(article.text))
			if article_list_text:
				print("CollegeHumor list article found: " + article.text)
				helper_methods.post_to_reddit(article.text, article_list_text, list_article_link, subreddit, website)
				return True

	print("No CollegeHumor list articles were found to parse at this time.")
	return False


def get_article_list_text(link_to_check, total_points):
	"""Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also ensures the number of list elements in the article is equal to the number the article title starts with."""
	
	list_counter = 1
	this_when_counter = 0
	full_list = ''

	soup = helper_methods.soup_session(link_to_check)
		
	for article in soup.find_all('h2'):
		try:
			if not article.text[0].isdigit():
				continue
		except IndexError:
			continue

		if len(article.text) < 4 or article.text.endswith(':'):
			return ''
		else:
			if this_when_counter == 3:
				return ''
				
			if article.text.startswith(('When ', 'This ', 'And this ')):
				this_when_counter += 1
			else:
				this_when_counter = 0
	
			if article.text.startswith((str(list_counter)+'.', str(list_counter)+')')):
				full_list += article.text + '\n'
			else:
				full_list += str(list_counter) + '. ' + article.text + '\n'

		list_counter += 1

	if total_points != list_counter-1:
		return ''

	return full_list


if __name__ == "__main__":
	start_time = round(time.time(), 2)
	find_article_to_parse("buzzfeedbot", "CollegeHumor")
	print("CollegeHumor script ran for " + str(round((time.time() - start_time), 2)) + " seconds")
