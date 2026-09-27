"""
Declarative base for all ORM models.

v0.1 intentionally defines no domain models yet (no users, collections,
documents, ...). Those arrive in v0.2+ alongside the migrations that
create them. This module exists now so that:

1. Alembic has a stable `target_metadata` to point at from day one.
2. Later model modules (app/auth/models.py, app/collections/models.py, ...)
   all import the same `Base` and register onto the same metadata object.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
