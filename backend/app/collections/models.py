"""
Collection model — the first tenant-owned resource. Every query against
this table that isn't an internal migration/admin task must be scoped
by `owner_id`; see `app.collections.router` for the enforcement pattern.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # index=True: the dominant query pattern is "list my collections"
    # (WHERE owner_id = :current_user_id) and "get my collection by id"
    # (WHERE owner_id = :x AND id = :y). The second already benefits
    # from the primary-key index on `id`; this index on `owner_id`
    # covers the first and doesn't need to be a composite with `id` at
    # this scale — see docs/architecture.md.
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
