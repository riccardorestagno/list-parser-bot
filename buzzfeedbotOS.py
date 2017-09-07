from bs4 import BeautifulSoup
from langdetect import detect, lang_detect_exception
import datetime
import time
import requests
import praw
import prawcore

'''Module that takes the title, main text and link to article and posts directly to reddit '''
def reddit_bot(headline, main_text, link):
	reddit = praw.Reddit(client_id='',
					client_secret= '',
					user_agent='BuzzFeed bot',
					username='autobuzzfeedbot',
					password='')

	reddit.subreddit('buzzfeedbot').submit(title=headline, selftext=main_text+'\n'+link)

'''Checks if there are numbered bullet points in the article. If there is at least one, returns true, 
if there are none, returns false''' 
def check_for_numbered_points(link_to_check):
	i=0
	session = requests.Session()
	clickbait_article = session.get(link_to_check)
	soup = BeautifulSoup(clickbait_article.content, 'html.parser')
	for title in soup.find_all('h3'):
		for number in title.find_all('span', attrs={'class': 'subbuzz__number'}):
			i+=1
	if i > 0:
		return (True)
	else:
		return (False)
		
'''Gets current time in EST'''
def current_time_eastern():
	from time import gmtime, strftime
	time_diff = 4
	gm_time = strftime("%#H:%M:%S", gmtime())
	gm_hour, min_secs =  gm_time.split(':', 1)
	if int(gm_hour)>= time_diff:
		est_hour = str(int(gm_hour)-time_diff)
	else:
		est_hour = str(int(gm_hour)+24-time_diff)
	es_time = est_hour + ':'+ min_secs
	return es_time
	
'''Checks if the post has already been submitted 
Returns True if post was submitted already and returns False otherwise'''
def post_made_check(post_title):
	post_made = False
	reddit = praw.Reddit(client_id='',
					client_secret= '',
					user_agent='BuzzFeed bot')
	subreddit = reddit.subreddit('buzzfeedbot')
	submissions = subreddit.new(limit=40)
	for submission in submissions:
		if submission.title == post_title:
			post_made = True
			break
	return (post_made)

'''Gets the link to the article that will be posted on the sub.
The two if-statements below check if (1) the aretile starts with a number, (2) the post hasn't been made already,
(3) the articles language is in english, and (4) if the articles main points actually have text and not images.
(5) If the article title doesn't contain any keywords listed below
If all these conditions are met, this module will return the corresponding link and headline of the article. '''
def article_info(date):
	break_words = [' pictures', ' photos', ' gifs', 'twitter', 'must see', 'tweets', 'memes']
	session = requests.Session()
	daily_archive = session.get('https://www.buzzfeed.com/archive/' + date )
	soup = BeautifulSoup(daily_archive.content, 'html.parser')
	for article_to_open in soup.find_all('li', attrs={'class': 'bf_dom'}):
		#End script if post was already made longer than one hour ago
		post_made = post_made_check(article_to_open.text)
		if post_made == True:
			continue
		lc_art_title = article_to_open.text.lower()
		try:
			if (article_to_open.text[0].isdigit() or article_to_open.text.lower().startswith('top')) \
			and detect(article_to_open.text) == 'en' and not any(words in lc_art_title for words in break_words):
	
				no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()] #Records number of points in the article 
				for link in article_to_open.find_all('a', href=True):
					top_x_link = 'https://www.buzzfeed.com' + link['href']
					try: #Avoids rare case of when there is an index error (occurs when article starts with number immediately followed by a symbol)
						article_text_to_use = clickbait_meat(top_x_link, no_of_points[0])
						if article_text_to_use == '':
							break
						else:
							reddit_bot(article_to_open.text, article_text_to_use, top_x_link)
							print(article_to_open.text)
							time.sleep(1)
							break
					except IndexError:
						break
		except lang_detect_exception.LangDetectException:
			continue
	session.close #Necessary or else will use the same archive that was originally loaded without the updated articles

'''Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  '''			
def clickbait_meat(link_to_check, total_points):
	i=1
	top_x_final = ''
	top_x_final_temp = ''
	bullet_point = False
	session = requests.Session()
	clickbait_article = session.get(link_to_check)
	soup = BeautifulSoup(clickbait_article.content, 'html.parser')
	any_numbered_points = check_for_numbered_points(link_to_check)
	for title in soup.find_all('h3'):
		for number in title.find_all('span', attrs={'class': 'subbuzz__number'}):
			bullet_point = True
		if bullet_point == True or any_numbered_points == False:
			for article in title.find_all('span', attrs={'class': 'js-subbuzz__title-text'}):
				if len(article.text)<4 or article.text.endswith(':'):
					return ''
				else:
					top_x_final_temp = top_x_final
					try:
						for link in article.find_all('a', href=True):
							top_x_final += str(i) + '. [' + article.text +']('+ link['href']+')' + '\n'
							break
					except KeyError:
						pass
					if top_x_final_temp == top_x_final:
						top_x_final += str(i) + '. '+ article.text  + '\n'
				i+=1
		bullet_point = False
	if total_points != i-1:
		top_x_final = ''
	return(top_x_final)

if __name__ == "__main__":
	start_time = round(time.time(), 2)
	now = datetime.datetime.now()
	leading_zero_date = now.strftime("%Y/%m/%d")

	while True:
		try:
			print('Searching first link')
			article_info(leading_zero_date)
			
			print('Searching second link')
			non_leading_zero_date = now.strftime("%Y/%m/%d").replace('/0', '/', 1)
			article_info(non_leading_zero_date)

		except (requests.exceptions.RequestException, prawcore.exceptions.ResponseException, \
		prawcore.exceptions.RequestException) as e:
			print('Connection Error! Script will restart soon')
			print(e)
			print('Script ran for ' + str((round(time.time())-start_time)/60)+ ' minutes' )
			time.sleep(15*60)
			leading_zero_date = now.strftime("%Y/%m/%d")
			start_time = round(time.time(), 2)
			continue
		print('Script ran for ' + str(round(((time.time()-start_time)/60),2))+ ' minutes' )
		print('Script sleeping for 4 hours')
		print(current_time_eastern())
		
		time.sleep(4*60*60) #Runs script every 4 hours
		
		print('Restarting Script')
		start_time = round(time.time())
		leading_zero_date = now.strftime("%Y/%m/%d")
