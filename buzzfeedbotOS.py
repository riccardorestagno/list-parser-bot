from bs4 import BeautifulSoup
from langdetect import detect, lang_detect_exception
from datetime import date, timedelta
import time
import requests
import praw
import prawcore

def reddit_bot(headline, main_text, link):
	"""Module that takes the title, main text and link to article and posts directly to reddit"""
	reddit = praw.Reddit(client_id='',
					client_secret= '',
					user_agent='BuzzFeed bot',
					username='autobuzzfeedbot',
					password='')

	reddit.subreddit('buzzfeedbot').submit(title=headline, selftext=main_text+'\n'+link)
	
	
def post_made_check(post_title, subpoints):
	"""Checks if the post has already been submitted. 
Returns True if post was submitted already and returns False otherwise"""
	post_made = False
	reddit = praw.Reddit(client_id='',
			client_secret= '',
			user_agent='BuzzFeed bot')
	subreddit = reddit.subreddit('buzzfeedbot')
	submissions = subreddit.new(limit=40)
	for submission in submissions:
		if submission.title.lower() == post_title:
			post_made = True
			break
		subpoints_to_check = [int(s) for s in submission.title.split() if s.isdigit()]
		if subpoints_to_check == subpoints:
			sameWords = set.intersection(set(post_title.split(" ")), set(submission.title.lower().split(" ")))
			numberOfWords = len(sameWords)
			if numberOfWords >=4:
				post_made = True
				break
	return (post_made)


def article_info(date):
	"""Gets the link to the article that will be posted on the sub.
The two if-statements below check if (1) the aretile starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english, and (4) if the articles main points actually have text and not images.
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will get the articles text using the article_text() module
and then posts the corresponding text to reddit using the reddit_bot() module"""
	
	post_limit = 0
	break_words = [' pictures', ' photos', ' gifs', 'images', \
		       'twitter', 'must see', 'tweets', 'memes',\
		       'instagram', 'tumblr']
	session = requests.Session()
	daily_archive = session.get('https://www.buzzfeed.com/archive/' + date )
	soup = BeautifulSoup(daily_archive.content, 'html.parser')
	for article_to_open in soup.find_all('li', attrs={'class': 'bf_dom'}):
		try:
			if not ((article_to_open.text[0].isdigit() or article_to_open.text.lower().startswith(('top', 'the'))) \
			and detect(article_to_open.text) == 'en'):
				continue
		except lang_detect_exception.LangDetectException:
			continue
		
		article_title_lowercase = article_to_open.text.lower()
		if any(words in article_title_lowercase for words in break_words):
			continue
			
		no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()] #Records number of points in the article 
		post_made = post_made_check(article_title_lowercase, no_of_points)
		if post_made == True:
			continue

		for link in article_to_open.find_all('a', href=True):
			top_x_link = 'https://www.buzzfeed.com' + link['href']
			try: #Avoids rare case of when there is an index error (occurs when article starts with number immediately followed by a symbol)
				article_text_to_use = clickbait_meat(top_x_link, no_of_points[0])
				if article_text_to_use == '':
					pass
				else:
					reddit_bot(article_to_open.text, article_text_to_use, top_x_link)
					post_limit+=1
					print(article_to_open.text)
					if post_limit == 1:
						return post_limit
					time.sleep(1)
				break
			except IndexError:
				break
	return post_limit

def article_text(link_to_check, total_points):
	"""Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of subpoints in the article is equal to the numbe rthe atricle title starts with"""
	i=1
	this_when_counter = 0
	top_x_final = ''
	top_x_final_temp = ''
	session = requests.Session()
	clickbait_article = session.get(link_to_check)
	soup = BeautifulSoup(clickbait_article.content, 'html.parser')

	for title in soup.find_all('h3'):
		
		subpoint_check = False
	
		for subpoint in title.find_all('span', attrs={'class': 'subbuzz__number'}):
			subpoint_check = True
			break
		
		if subpoint_check == False:
			continue
			
		for article in title.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
			if len(article.text)<4 or article.text.endswith(':'):
				return ''
			else:
				top_x_final_temp = top_x_final
				if this_when_counter == 3:
					this_when_counter = 0
					return ''
				if article.text.startswith(('When ', 'This ')):
					this_when_counter += 1
				else:
					this_when_counter = 0
				try:
					for link in article.find_all('a', href=True):
						link_to_use = link['href']
						
						if link_to_use.startswith('http:') and 'https:' in link_to_use: #removes redirect link if there is any
							link_to_use = 'https:' + link_to_use.split('https:', 1)[1]
						if 'amazon' in link['href']: #removes buzzfeed tag in all amazon links
							link_to_use = link_to_use.split('?', 1)[0]
							
						if article.text.startswith((str(i)+'.', str(i)+')')):
							top_x_final += '[' + article.text +']('+ link['href']+')' + '\n'
						else:
							top_x_final += str(i) + '. [' + article.text +']('+ link['href']+')' + '\n'
						break
				except KeyError:
					pass
				if top_x_final_temp == top_x_final:
					if article.text.startswith((str(i)+'.', str(i)+')')):
						top_x_final += article.text  + '\n'
					else:
						top_x_final += str(i) + '. '+ article.text  + '\n'
			i+=1

	if total_points != i-1:
		top_x_final = ''
	return(top_x_final)

if __name__ == "__main__":
	post_made = 0
	start_time = round(time.time(), 2)
	yesterday = date.today() - timedelta(1)
	leading_zero_date = yesterday.strftime("%Y/%m/%d")

	while True:
		try:
			
			print('Searching first link')
			post_made = article_info(leading_zero_date)
			
			remove_one_leading_zero_date = leading_zero_date.replace('/0', '/', 1)
			if leading_zero_date != remove_one_leading_zero_date and posts_made == 0:
				print('Searching second link')
				article_info(remove_one_leading_zero_date)

			remove_all_leading_zero_date = leading_zero_date.replace('/0', '/')
			if remove_one_leading_zero_date != remove_all_leading_zero_date and posts_made == 0:
				print('Searching third link')
				article_info(remove_all_leading_zero_date)

		except (requests.exceptions.RequestException, prawcore.exceptions.ResponseException, \
		prawcore.exceptions.RequestException) as e:
			print('Connection Error! Script will restart soon')
			print(e)
			print('Script ran for ' + str(round(((time.time()-start_time)),2))+ ' seconds' )
			time.sleep(15*60)
			leading_zero_date = yesterday.strftime("%Y/%m/%d")
			start_time = round(time.time(), 2)
			continue
			
		print('Script ran for ' + str(round(((time.time()-start_time)),2))+ ' seconds' )
			
		break
