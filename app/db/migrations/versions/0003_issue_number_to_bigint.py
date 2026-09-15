"""convert issues.number column from Integer to BigInteger

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-16

GitHub issue numbers are unlikely to exceed int32 today, but the column
should be future-proof against extremely large or edge-case values.
Convert issues.number to BigInteger (int64, max ~9.2 quintillion) to
prevent sqlalchemy.exc.DataError: integer out of range on insert.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        # SQLite has dynamic typing; the int32/int64 distinction is a no-op.
        return

    op.alter_column(
        "issues", "number", existing_type=sa.Integer(), type_=sa.BigInteger()
    )


def downgrade() -> None:
    if _is_sqlite():
        return

    op.alter_column(
        "issues", "number", existing_type=sa.BigInteger(), type_=sa.Integer()
    )
