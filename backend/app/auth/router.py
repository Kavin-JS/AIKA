"""
Auth endpoints: register, login, logout, me.

Anti-enumeration note: `login` returns the exact same status code and
detail message for "no such email" and "wrong password". Don't
"improve" this later by returning a more specific error for one case —
that reintroduces a user-enumeration side channel.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import LoginRequest, RegisterRequest, UserResponse
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_invalid_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password",
)

# A precomputed hash of a value nobody will ever submit as a password,
# used to keep the "user not found" and "wrong password" branches
# doing comparable work. Without this, skipping verify_password()
# entirely when no user is found makes that branch measurably faster,
# letting an attacker distinguish "no such email" from "wrong password"
# by response latency — the same class of leak the identical 401
# message is meant to close.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password-used-only-for-timing-padding")


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    db.refresh(user)
    logger.info("user_registered", extra={"user_id": str(user.id)})
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == payload.email).first()

    # Constant-shape failure path: run a hash verification unconditionally
    # (against the real hash when the user exists, against a dummy hash
    # otherwise — see _DUMMY_PASSWORD_HASH) so the two failure cases are
    # not distinguishable by response shape or timing, and return the
    # identical 401 either way.
    password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_ok = verify_password(payload.password, password_hash)

    if user is None or not password_ok:
        raise _invalid_credentials_error

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    logger.info("user_logged_in", extra={"user_id": str(user.id)})
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
