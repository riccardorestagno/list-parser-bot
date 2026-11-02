from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth import check_token

bearer_scheme = HTTPBearer(auto_error=False)


def require_signed_in(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    """Every route but /health: the dashboard's token, sent as ``Authorization: Bearer``."""
    return check_token(credentials.credentials if credentials else None)
