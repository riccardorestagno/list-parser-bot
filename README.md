List Parser Bot
=========================


Description
===========

Reddit bot that posts list articles from BuzzFeed, Business Insider and Polygon to Reddit.


Dependencies
=================
Supported Python versions: 3.6.0+ 

- BeautifulSoup (https://www.crummy.com/software/BeautifulSoup)
- langdetect (https://pypi.python.org/pypi/langdetect)
- PRAW (https://github.com/praw-dev/praw)


Script Functionality
=====================

Three separate scripts are used to parse article archives from BuzzFeed, Business Insider and Polygon looking for all English list articles (distinguishable by numbers in the article title). The script then posts the title as well as all of the list elements as a Reddit text post to /r/buzzfeedbot


### Buzzfeed Archive:

The script parses https://www.buzzfeed.com/archive/ [yesterdays date EST] and finds all English article titles (langdetect library used to check this) that contain a number. Once the article is found, the script checks if the number of list elementsin the article matches the number in the article title. If so, BeautifulSoup concatenates all the subpoints into a single string and then PRAW is used to post the article title as the post title and the concatenated list as the posts main text.


### Business Insider Archive:

The script parses http://www.businessinsider.com/latest and searches for the most recent Business Insider article written. If the article being searched matches the post requirements from BuzzFeed's script, then the same procedure from BuzzFeed's script is used to post the article to Reddit.


### Polygon Archive:

The script parses http://www.polygon.com/news and searches for the most recent Polygon article written.


Author
==============
Rick Restagno
