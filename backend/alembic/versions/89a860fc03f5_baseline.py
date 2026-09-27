"""baseline

This is a deliberately empty baseline revision. v0.1 Foundation ships no
domain tables — that starts in v0.2 (users/collections). Its purpose is
to prove the migration mechanism (`alembic upgrade head`) works
end-to-end against a real database as part of the v0.1 acceptance
criteria, and to give every future migration a stable `down_revision`
to chain from.

Revision ID: 89a860fc03f5
Revises:
Create Date: 2026-08-31

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "89a860fc03f5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
