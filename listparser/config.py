from helpers.enums import *

subreddit = "buzzfeedbot"

script_execution_delay = 1.5 * 60 * 60

# Supported parsers
active_parsers = {
    ArticleType.Business_Insider: True,
    ArticleType.BuzzFeed: True,
    ArticleType.CollegeHumor: False,
    ArticleType.Cracked: True,
    ArticleType.Polygon: False
}

# Archive links
business_insider_article_archive_link = "http://www.businessinsider.com/latest"
buzzfeed_article_archive_link = "https://www.buzzfeed.com/buzz"
collegehumor_article_archive_link = "http://www.collegehumor.com/articles"
cracked_article_archive_link = "https://www.cracked.com/funny-articles.html"
polygon_article_archive_link = "http://www.polygon.com/news"

# Maximum articles to search per parser method call
buzzfeed_max_articles_to_search = 15
cracked_max_articles_to_search = 5
polygon_max_articles_to_search = 5

# If the list article title from a specific website contains any of the words below, the list will not be posted to Reddit.
# This avoids posting content which contains lists of ads and images.
title_exclusion_words = {
    ArticleType.All: ['pics', 'pictures', 'photos', 'gifs', 'images', 'deals', 'memes', 'tweets', 'must see'],
    ArticleType.BuzzFeed: ['amazon', 'twitter', 'instagram', 'tumblr', 'gifts', 'products']
}

# New posts to search to determine if article was previously posted to the subreddit
post_previously_made_search_limit = 25
