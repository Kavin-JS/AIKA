"""
User model — the tenancy root. Every owned resource (collections, and
later documents/conversations) traces back to a user via an `owner_id`
foreign key, enforced at query time, not just at the schema level.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Application-generated UUID default (uuid.uuid4) rather than a
    # Postgres-side gen_random_uuid(), so no extension (pgcrypto) needs
    # to be enabled by a migration — one less moving part for v0.1/v0.2.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Argon2id hash string (includes algorithm/params/salt) — never the
    # plaintext password, never a reversible encoding of it.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
