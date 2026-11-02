"""Tokens like the tools dashboard signs, with a key made for the tests."""
from datetime import datetime, timedelta, timezone

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
