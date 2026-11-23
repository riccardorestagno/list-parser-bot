from bot.helpers.enums import *

subreddit = "buzzfeedbot"

reddit_max_post_text_length = 40000

# Supported parsers
active_parsers = {
    ArticleType.Business_Insider: True,
    ArticleType.BuzzFeed: True,
    ArticleType.Cracked: True,
    ArticleType.Screen_Rant: True,
}

# Archive links
business_insider_article_archive_link = "http://www.businessinsider.com/latest"
buzzfeed_article_archive_link = "https://www.buzzfeed.com/buzz"
cracked_article_archive_link = "https://www.cracked.com/funny-articles.html"
screen_rant_article_archive_link = "https://screenrant.com/lists/"

# Maximum articles to search per parser method call
business_insider_max_articles_to_search = 30
buzzfeed_max_articles_to_search = 15
cracked_max_articles_to_search = 10
screen_rant_max_articles_to_search = 10

# If the list article title from a specific website contains any of the words below, the list will not be posted to Reddit.
# This avoids posting content which contains lists of ads and images.
title_exclusion_words = {
    ArticleType.All: ['pics', 'pictures', 'photos', 'gifs', 'images', 'deals', 'memes', 'tweets', 'must see'],
    ArticleType.BuzzFeed: ['amazon', 'twitter', 'instagram', 'tumblr', 'gifts', 'products']
}

# Seconds to wait before opening each article, so a sweep never hurries a site
pause_before_each_article = 1

# The subreddit's newest posts, read once per sweep: an article linked from one was posted before, and their flairs
# set the order the sites are searched in. Reddit gives up to 100 in one request
post_previously_made_search_limit = 100
