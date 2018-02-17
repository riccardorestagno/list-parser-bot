from bs4 import BeautifulSoup
from langdetect import detect, lang_detect_exception
from datetime import date, timedelta
import time
import requests
import praw

break_words = [' pictures', ' photos', ' gifs', 'images', \
		'twitter', 'must see', 'tweets', 'memes',\
		'instagram', 'tumblr', 'gifts', 'products']

def connect_to_reddit():
	
	reddit = praw.Reddit(client_id='',
			client_secret= '',
			user_agent='BuzzFeed bot',
			username='autobuzzfeedbot',
			password='')

	return reddit

def soup_session(link):
	"""BeautifulSoup session"""
	session = requests.Session()
	daily_archive = session.get(link)
	soup = BeautifulSoup(daily_archive.content, 'html.parser')
	return soup

def reddit_bot(headline, main_text, link, my_subreddit, website_name):
	"""Module that takes the title, main text and link to article and posts directly to reddit"""
	reddit = connect_to_reddit()

	reddit.subreddit(my_subreddit).submit(title=headline, selftext=main_text+'\n'+link).mod.flair(text=website_name)
	
def total_articles_today(article_completed_count = 0, modify = False):
	""" Saves the progress of amount of links already searched through in an external file if modify = true
		Returns the current progress of the amount of links/articles already searched if modify = false"""
		
	filepath = r'C:\Users\Riccardo\Desktop\Python Scripts\BuzzFeed Reddit Bot\Posts_Made_Today.txt'
	
	if modify == False:
		with open(filepath, 'r') as file:
			articles_searched = file.read()
		return int(articles_searched)
	
	else:
		with open(filepath, 'w') as file:
			file.write(str(article_completed_count))
		return 0

def post_reset():
	"""Resets total articles searched file if post is run at the beginning of the day"""
	import datetime
	current_time = datetime.datetime.now().time()
	min_time = datetime.time(2, 55)
	max_time = datetime.time(3, 5)
	if current_time >= min_time and current_time <= max_time:
		total_articles_today(0, True)
		print('reset done')
		
def post_made_check(post_title, subpoints, my_subreddit):
	"""Checks if the post has already been submitted. 
Returns True if post was submitted already and returns False otherwise"""
	post_made = False
	reddit = connect_to_reddit()
	subreddit = reddit.subreddit(my_subreddit)
	submissions = subreddit.new(limit=40)
	for submission in submissions:
		if submission.title.lower() == post_title:
			post_made = True
			break
		subpoints_to_check = [int(s) for s in submission.title.split() if s.isdigit()][0]
		if subpoints_to_check == subpoints:
			sameWords = set.intersection(set(post_title.split()), set(submission.title.lower().split()))
			numberOfWords = len(sameWords)
			if numberOfWords >=4:
				post_made = True
				break
	return post_made


def article_info(date, start_iter):
	"""Gets the link to the article that will be posted on the sub.
The two if-statements below check if (1) the aretile starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english, and (4) if the articles main points actually have text and not images.
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will get the articles text using the article_text() module
and then posts the corresponding text to reddit using the reddit_bot() module"""
	
	current_iter = 0
	
	soup = soup_session(archive_link + date)
	
	for link in list(soup.find_all('a', attrs={'class': 'link-gray'}, href=True))[start_iter:]:
		current_iter += 1
		for article_to_open in link.find_all('h2', attrs={'class': 'xs-mb05 xs-pt05 sm-pt0 xs-text-4 sm-text-2 bold'}):
			
			try:
				if not detect(article_to_open.text) == 'en':
					break
			except lang_detect_exception.LangDetectException:
				break
			
			no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()] #Records number of points in the article 
			if not no_of_points:
				break
				
			article_title_lowercase = article_to_open.text.lower()
			if any(words in article_title_lowercase for words in break_words):
				break
				
			post_made = post_made_check(article_title_lowercase, no_of_points, my_subreddit)
			if post_made == True:
				break
		
			top_x_link = 'https://www.buzzfeed.com' + link['href']
			
			try: #Avoids rare case of when there is an index error (occurs when article starts with number immediately followed by a symbol)
				article_text_to_use = article_text(top_x_link, no_of_points[0])
				if article_text_to_use == '':
					article_text_to_use = paragraph_article_text(top_x_link, no_of_points[0])
								
				if article_text_to_use != '':
					reddit_bot(article_to_open.text, article_text_to_use, top_x_link, my_subreddit, website)
					print(article_to_open.text)
					start_iter += current_iter
					unused_value = total_articles_today(article_completed_count = start_iter, modify = True)
					return
				break
			except IndexError:
				break
	unused_value = total_articles_today(start_iter + current_iter, modify = True)

def paragraph_article_text(link_to_check, total_points):
	"""Parses list articles that are in paragraph form (have the 'p' HTML tag)"""

	i=1
	top_x_final = ''
	
	soup = soup_session(link_to_check)

	for subpoint in soup.find_all('p'):
		try:
			if subpoint.text[0].isdigit():
				top_x_final += subpoint.text.replace(')', '. ', 1)  + '\n'
				i+=1
		except IndexError:
			continue
	
	if total_points != i-1:
		top_x_final = ''
	return top_x_final

def article_text(link_to_check, total_points):
	"""Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of subpoints in the article is equal to the numbe rthe atricle title starts with"""
	i=1
	this_when_counter = 0
	top_x_final = ''
	top_x_final_temp = ''
	
	soup = soup_session(link_to_check)

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
				if article.text.startswith(('When ', 'This ', 'And this ')):
					this_when_counter += 1
				else:
					this_when_counter = 0
				try:
					for link in article.find_all('a', href=True):
						if 'amazon' in link['href']:
							link_to_use = link['href'].split('?', 1)[0]
						else:
							link_to_use = link['href']
						
						if link_to_use.startswith('http:') and (r'/https:' in link_to_use or r'/http:' in link_to_use): #removes redirect link if there is any
							link_to_use = 'http' + link_to_use.split(r'/http', 1)[1]
						
						link_to_use = link_to_use.replace(')', r'\)') 
						
						if article.text.startswith((str(i)+'.', str(i)+')')):
							top_x_final += '[' + article.text + '](' + link_to_use + ')' + '\n'
						else:
							top_x_final += str(i) + '. ' + '[' + article.text + '](' + link_to_use + ')' + '\n'
						break
				except KeyError:
					pass
				if top_x_final_temp == top_x_final:
					if article.text.startswith(str(i)+')'):
						article.text.replace(str(i)+')', str(i)+'. ')
					if article.text.startswith(str(i)+'.'):
						top_x_final += article.text  + '\n'
					else:
						top_x_final += str(i) + '. '+ article.text  + '\n'
			i+=1

	if total_points != i-1:
		top_x_final = ''
	return top_x_final

def url_to_search():
	""" Gets URL of the archive of yesterdays data"""

	i=0
	yesterday = date.today() - timedelta(1)
	formatted_date = yesterday.strftime("%Y/%m/%d")

	article_count = total_articles_today()

	article_info(formatted_date, article_count)
		
if __name__ == "__main__":

	my_subreddit = 'buzzfeedbot'
	website = 'BuzzFeed'
	archive_link = 'https://www.buzzfeed.com/archive/'
	
	start_time = round(time.time(), 2)
	post_reset()
	
	print('Searching Yesterdays Archive')
	url_to_search()

	print('Script ran for ' + str(round(((time.time()-start_time)),2)) + ' seconds' )
