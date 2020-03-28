import app.helper_methods.list_parser_helper_methods as helper_methods
import time
from datetime import date, timedelta


def find_article_to_parse(subreddit_name, website_name):
	"""Gets the link to the article that will be posted on the subreddit.
	The validations below check if:
		(1) The article contains a number
		(2) The post hasn't been made already
		(3) The articles main points contain text
		(4) The article title doesn't contain certain pre-defined keywords
	If all these conditions are met, this module will get the articles text using the get_article_list() module
	and then posts the corresponding text to Reddit using the post_to_reddit() module."""

	archive_link = 'http://www.collegehumor.com/articles'

	print("Searching CollegeHumors's archive")
	soup = helper_methods.soup_session(archive_link)

	for article in soup.find_all('h3', attrs={'class': 'title'}):
		
		no_of_points = [int(s) for s in article.text.split() if s.isdigit()]
		
		if not no_of_points:
			continue
		
		article_title_lowercase = article.text.lower()
		if any(words in article_title_lowercase for words in helper_methods.BREAK_WORDS):
			continue
			
		post_made = helper_methods.post_made_check(article_title_lowercase, no_of_points[0], subreddit_name)
		
		if post_made:
			continue
		
		link = article.find('a')
			
		list_article_link = 'http://www.collegehumor.com' + link['href']
		
		if compare_date(list_article_link):
			# Avoids rare case of when there is an index error
			# Occurs when article starts with number immediately followed by a symbol.
			try:
				article_text_to_use = get_article_list(list_article_link, no_of_points[0])
				if article_text_to_use:
					print("CollegeHumor list article found: " + article.text)
					helper_methods.post_to_reddit(article.text, article_text_to_use, list_article_link, subreddit_name, website_name)
					return True
				
			except IndexError as e:
				print(e)
				print('there was an error')

	print("No CollegeHumor list articles were found to parse at this time.")
	return False


def get_article_list(link_to_check, total_points):
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


def compare_date(link):
	""" Compares the date the article was written with today's date."""

	soup = helper_methods.soup_session(link)
	
	todays_date = (date.today() - timedelta(0)).strftime("%B %#d, %Y")  # The # is platform specific
	
	for date_to_check in soup.find_all('time', attrs={'class': 'date'}):
		if date_to_check.text == todays_date:
			return True
			
	return False


if __name__ == "__main__":
	start_time = round(time.time(), 2)
	find_article_to_parse("buzzfeedbot", "CollegeHumor")
	print("CollegeHumor script ran for " + str(round((time.time() - start_time), 2)) + " seconds")
