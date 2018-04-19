import time
import buzzfeedbot

def article_info():
	"""Gets the link to the article that will be posted on the sub"""
	
	soup = buzzfeedbot.soup_session(archive_link)

	for link in soup.find_all('h3'):
		
		article_to_open = link.find('a', href=True)
		
		try:
			no_of_points = [int(s) for s in article_to_open.text.split() if s.isdigit()] #Records number of points in the article 
		except AttributeError:
			continue
			
		if not no_of_points:
			continue
		
		article_title_lowercase = article_to_open.text.lower()
		if any(words in article_title_lowercase for words in buzzfeedbot.break_words):
			continue
			
		post_made = buzzfeedbot.post_made_check(article_title_lowercase, no_of_points[0], my_subreddit)
		
		if post_made == True:
			continue
		
		top_x_link = article_to_open['href']
		
		
		try: #Avoids rare case of when there is an index error (occurs when article starts with number immediately followed by a symbol)
			
			article_text_to_use = article_text(top_x_link, no_of_points[0])
			if article_text_to_use == '':
				article_text_to_use = buzzfeedbot.paragraph_article_text(top_x_link, no_of_points[0])
				
			if article_text_to_use != '':
				print(top_x_link)
				print(article_to_open.text)
				buzzfeedbot.reddit_bot(article_to_open.text, article_text_to_use, top_x_link, my_subreddit, website)
				
				return True
			
		except IndexError as e:
			print(e)
			print('there was an error')
		
	return False
	
def article_text(link_to_check, total_points):
	"""Concatenates the main points of the article into a single string and also makes sure the string isn't empty.
Also checks to make sure  the number of sub-points in the article is equal to the number the article title starts with"""
	
	i=1
	top_x_final = ''
	
	soup = buzzfeedbot.soup_session(link_to_check)
		
	for article_point in soup.find_all('h2', attrs={'class': 'slide-title-text'}):
				
		if article_point.text[0].isdigit() and (article_point.text[1] == '.' or article_point.text[2] == '.'):
			top_x_final = article_point.text  + '\n' + top_x_final
		else:
			top_x_final = str(i) + '. ' + article_point.text  + '\n' + top_x_final
		
		i+=1

	if total_points != i-1:
		top_x_final = ''
	return top_x_final
	
if __name__ == "__main__":
	my_subreddit = 'buzzfeedbot'
	website = 'Business Insider'
	archive_link = 'http://www.businessinsider.com/latest'
	
	start_time = round(time.time(), 2)
	
	article_info()

	print('Script ran for ' + str(round(((time.time()-start_time)),2)) + ' seconds' )
