"""Checks the token the tools dashboard gave someone when they signed in.

The dashboard signs tokens with its private key; this checks them with its
public key, so this API can tell a token is genuine but can't make one. A token
opens this API only when its audience names this app.
"""
from typing import Optional

import jwt
from jwt import InvalidTokenError

from services.errors import AppError
from settings import AUTH_AUDIENCE, AUTH_DISABLED, AUTH_ISSUER, AUTH_PUBLIC_KEY

ALGORITHM = "EdDSA"


class NotSignedIn(AppError):
    status = 401


def check_token(token: Optional[str], public_key: str = AUTH_PUBLIC_KEY, disabled: bool = AUTH_DISABLED) -> dict:
    """The token's claims (``sub``, ``email``, ``name``), or ``NotSignedIn``.

    With sign-in turned off (``LISTBOT_AUTH_DISABLED``) anyone gets through, as nobody.
    """
    if disabled:
        return {}
    if not public_key:
        # Refuse rather than let everyone in when the key was left out of the settings
        raise AppError("Sign-in isn't set up on this server: LISTBOT_AUTH_PUBLIC_KEY is missing", status=503)
    if not token:
        raise NotSignedIn("Sign in to continue")
    try:
        return jwt.decode(token, public_key, algorithms=[ALGORITHM], audience=AUTH_AUDIENCE, issuer=AUTH_ISSUER,
                          options={"require": ["exp", "sub", "aud", "iss"]})
    except InvalidTokenError:
        # Expired, for another app, or not the dashboard's: the same answer, back to the sign-in page
        raise NotSignedIn("Your sign-in has expired or doesn't open this app. Sign in again.")
