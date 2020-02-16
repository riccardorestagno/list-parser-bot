import app.helper_scripts.list_parser_helper_methods as helper_methods
import time
from datetime import date, timedelta


def article_info():
	"""Gets the link to the article that will be posted on the sub.
The three if-statements below check if (1) the article starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english,(4) if the articles main points actually have text and not images and
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will get the articles text using the article_text() module
and then posts the corresponding text to Reddit using the reddit_bot() module"""
	
	soup = helper_methods.soup_session(archive_link)

	for article_to_open in soup.find_all('h3', attrs={'class': 'title'}):
		
		no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()] # Records number of points in the article
		
		if not no_of_points:
			continue
		
		article_title_lowercase = article_to_open.text.lower()
		if any(words in article_title_lowercase for words in helper_methods.BREAK_WORDS):
			continue
			
		post_made = helper_methods.post_made_check(article_title_lowercase, no_of_points[0], my_subreddit)
		
		if post_made:
			continue
		
		link = article_to_open.find('a')
			
		top_x_link = 'http://www.collegehumor.com' + link['href']
		
		if compare_date(top_x_link) == True:
			try:  # Avoids rare case of when there is an index error (occurs when article starts with number immediately followed by a symbol)
				article_text_to_use = article_text(top_x_link, no_of_points[0])
				if article_text_to_use == '':
					pass
				else:	
					print(top_x_link)
					print(article_to_open.text)
					print(article_text_to_use)
					helper_methods.reddit_bot(article_to_open.text, article_text_to_use, top_x_link, my_subreddit, website)
					
					return True
				
			except IndexError as e:
				print(e)
				print('there was an error')
		
	return False


def article_text(link_to_check, total_points):
	"""Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of list elements in the article is equal to the number the article title starts with"""
	
	i = 1
	this_when_counter = 0
	top_x_final = ''

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
	
			if article.text.startswith((str(i)+'.', str(i)+')')):
				top_x_final += article.text + '\n'
			else:
				top_x_final += str(i) + '. ' + article.text  + '\n'
		i += 1

	if total_points != i-1:
		top_x_final = ''

	return top_x_final


def compare_date(link):
	""" Compares the date the article was written with today's date"""

	soup = helper_methods.soup_session(link)
	
	todays_date = (date.today() - timedelta(0)).strftime("%B %#d, %Y")  # The # is platform specific
	
	for date_to_check in soup.find_all('time', attrs={'class': 'date'}):
		if date_to_check.text == todays_date:
			return True
			
	return False


if __name__ == "__main__":
	my_subreddit = 'buzzfeedbot'
	website = 'CollegeHumor'
	archive_link = 'http://www.collegehumor.com/articles'
	
	start_time = round(time.time(), 2)
	
	article_info()

	print('Script ran for ' + str(round((time.time() - start_time), 2)) + ' seconds')
