from helpers.enums import *

subreddit = "buzzfeedbot"

script_execution_delay_in_seconds = 1.5 * 60 * 60

reddit_max_post_text_length = 40000

# Supported parsers
active_parsers = {
    ArticleType.BuzzFeed: True,
    ArticleType.CollegeHumor: False,
    ArticleType.Cracked: True,
    ArticleType.Insider: True,
    ArticleType.Polygon: False,
    ArticleType.Screen_Rant: True,
}

# Archive links
buzzfeed_article_archive_link = "https://www.buzzfeed.com/buzz"
collegehumor_article_archive_link = "http://www.collegehumor.com/articles"
cracked_article_archive_link = "https://www.cracked.com/funny-articles.html"
insider_article_archive_link = "http://www.insider.com/latest"
polygon_article_archive_link = "http://www.polygon.com/news"
screen_rant_article_archive_link = "https://screenrant.com/lists/"

# Maximum articles to search per parser method call
buzzfeed_max_articles_to_search = 15
cracked_max_articles_to_search = 5
polygon_max_articles_to_search = 5
screen_rant_max_articles_to_search = 10

# If the list article title from a specific website contains any of the words below, the list will not be posted to Reddit.
# This avoids posting content which contains lists of ads and images.
title_exclusion_words = {
    ArticleType.All: ['pics', 'pictures', 'photos', 'gifs', 'images', 'deals', 'memes', 'tweets', 'must see'],
    ArticleType.BuzzFeed: ['amazon', 'twitter', 'instagram', 'tumblr', 'gifts', 'products']
}

# New posts to search to determine if article was previously posted to the subreddit
post_previously_made_search_limit = 25
