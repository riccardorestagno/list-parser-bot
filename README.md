Buzzfeed Reddit Bot
=========================

Description
===========

Reddit bot that posts main points of BuzzFeed's 'Top X' articles to /r/buzzfeedbot


Dependencies
=================
Supported Python versions: 3.4.0+ 

BeautifulSoup (https://www.crummy.com/software/BeautifulSoup)

langdetect (https://pypi.python.org/pypi/langdetect)

PRAW (https://github.com/praw-dev/praw)

urllib.request (included in Python 3.6+ default library)


Script Functionality
=====================

The script begins by parsing https://www.buzzfeed.com/archive/ [current-date-EST] and finding all english article titles that begin with a number (reason being is that most/all article titles that begin with a number by Buzzfeed tend to be Top X articles. Once the article is found, the script checks if the number of subpoints in the article matches the number in the article title. If so, PRAW is used to post the article title as the post title and the articles subpoints as the posts main text. This is then repreated till the whole daily archive is parsed.

Script repeats every 4 hours.


Author
==============
Rick Restagno
