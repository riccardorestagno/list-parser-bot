import helpers.list_parser_helper_methods as helpers
	

def paragraph_article_text(link_to_check, point_no):
	"""Parses list articles that are in paragraph form (have the 'p' HTML tag)"""
	details = ''
	
	print(link_to_check)
	soup = helpers.soup_session(link_to_check)
	start = soup.find_all('span', attrs={'class': 'subbuzz__number'})[point_no].parent.parent
	
	try:
		subpoint = start.find('div', class_="subbuzz__description")
		if subpoint is None:
			return "No extra information available"
	except IndexError:
		return "No extra information available"
	
	for description in subpoint.find_all('p'):
		details += description.text + "\n\n"
		
	if details == '':
		return "No extra information available"
	else:
		return details


def check_inbox():

	reddit = helpers.connect_to_reddit()
	
	bot_inbox = reddit.inbox.unread(limit=None)
	unread_messages = []
	
	for message in bot_inbox:
		if message.body.lower().startswith('!details'):
			text_to_reply = get_details(message.submission.selftext, message.body)
			if text_to_reply != "Pass":
				message.reply(text_to_reply)
	
		unread_messages.append(message)
		
	reddit.inbox.mark_read(unread_messages)


def get_details(post_text, comment_text):
		
	link = post_text.split('[Link to article](')[1].rsplit(')', 1)[0]
	
	try:
		subpoint_to_get = [int(s) for s in comment_text.split() if s.isdigit()][0] - 1
		text = paragraph_article_text(link, subpoint_to_get)
		return text
	except IndexError:
		return "Pass"	
	

if __name__ == "__main__":

	check_inbox()
