from twilio.rest import Client

import helpers.list_validation_methods as lvm


def send_text(text_body):
    account_sid = ""
    auth_token = ""

    client = Client(account_sid, auth_token)

    client.api.account.messages.create(
        to="",
        from_="",
        body=text_body)


if __name__ == "__main__":
    keyword = False
    reddit = lvm.connect_to_reddit()

    subreddit = reddit.subreddit('askreddit')
    submissions = subreddit.new(limit=100)
    for submission in submissions:
        if "subreddit" in submission.title.lower():
            keyword = True
            send_text(submission.title + '\n' + submission.url)

    if keyword:
        send_text('''Check out /r/buzzfeedbot - A subreddit that posts all 
of buzzfeeds top X articles as a reddit text post. 
So you never need to click on a Buzzfeed article again.''')
