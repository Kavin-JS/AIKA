"""
Database engine and session management.

Provides a FastAPI dependency (`get_db`) that yields a scoped session per
request and always closes it, even on error. Nothing outside this module
should construct a `Session` directly.

Engine and sessionmaker construction is lazy and cached (`lru_cache`),
mirroring the same pattern `app.core.config.get_settings` already uses,
rather than building them as import-time side effects. This is a small
but real testability boundary: `get_engine()`/`get_sessionmaker()` can
be cache-cleared and re-constructed against a different DATABASE_URL by
a test fixture without needing a repository pattern, a DI framework, or
any other abstraction beyond what FastAPI/SQLAlchemy already provide.
For endpoint-level unit tests (e.g. simulating a DB failure), overriding
the `get_db` FastAPI dependency directly with `app.dependency_overrides`
remains the simplest approach and needs none of this — see
`tests/test_health.py`.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,  # detects stale connections (e.g. after DB restart)
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: `db: Session = Depends(get_db)`."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
