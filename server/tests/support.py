"""Helpers shared by the tests (``conftest.py`` sets up the app): tokens like the tools dashboard signs,
with a key made for the tests, and a Reddit the tests make."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ISSUER = "riccardorestagno.com/tools"

_KEY = Ed25519PrivateKey.generate()
PUBLIC_KEY_PEM = _KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")


def make_token(audience=("tools-dashboard", "list-parser-bot"), issuer: str = ISSUER,
               expires_in: timedelta = timedelta(hours=1), key: Ed25519PrivateKey = _KEY) -> str:
    now = datetime.now(timezone.utc)
    claims = {"iss": issuer, "sub": "1", "email": "person@example.com", "name": "Person",
              "aud": list(audience), "ver": 0, "iat": now, "exp": now + expires_in}
    return jwt.encode(claims, key, algorithm="EdDSA")


def reddit_post(flair=None, selftext=""):
    """One of the subreddit's posts, as the bot reads it: its flair (the site) and its text (the list, then the link)."""
    return SimpleNamespace(link_flair_text=flair, selftext=selftext)


def fake_reddit(posts=()):
    """Reddit as the bot uses it: the subreddit's newest posts (newest first), posting, and messaging someone."""
    reddit = SimpleNamespace(asked=[], submitted=[], messages=[])

    def subreddit(name):
        def new(limit):
            reddit.asked.append((name, limit))
            return iter(list(posts)[:limit])

        def submit(title, selftext):
            post = SimpleNamespace(title=title, selftext=selftext, flair=None, permalink=f"/r/{name}/comments/new/")
            post.mod = SimpleNamespace(flair=lambda text: setattr(post, "flair", text))
            reddit.submitted.append(post)
            return post

        return SimpleNamespace(new=new, submit=submit)

    reddit.subreddit = subreddit
    reddit.redditor = lambda name: SimpleNamespace(message=lambda subject, text: reddit.messages.append((name, subject, text)))
    return reddit
