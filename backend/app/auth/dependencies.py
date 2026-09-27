"""
`get_current_user`: the single FastAPI dependency every authenticated
route depends on. Reads the access-token cookie, validates it, and
loads the corresponding user — or raises 401.

Every other authorization decision in the app (collections, and later
documents/conversations) builds on top of this dependency rather than
re-implementing token parsing per route.

Read via `Request.cookies` rather than a `Cookie(...)`-typed parameter:
the cookie name is environment-configurable
(`settings.auth_cookie_name`), and FastAPI's `Cookie()` parameter
declaration needs a name fixed at import time, not one resolved from
settings at request time.
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import InvalidTokenError, decode_access_token
from app.core.config import get_settings
from app.db.session import get_db

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if token is None:
        raise _credentials_error

    try:
        user_id: uuid.UUID = decode_access_token(token)
    except InvalidTokenError as exc:
        raise _credentials_error from exc

    user = db.get(User, user_id)
    if user is None:
        # Token is valid but the user no longer exists (e.g. deleted
        # account with an old token still floating around) — treat
        # identically to "not authenticated", not a 404/500.
        raise _credentials_error
    return user
