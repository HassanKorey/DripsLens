"""convert numeric ID/count columns from Integer to BigInteger

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-15

GitHub's global numeric IDs (e.g. issues.github_id) already exceed the int32
maximum of 2,147,483,647, which caused psycopg2.errors.NumericValueOutOfRange
on insert. Convert all ID and count columns to BigInteger (int64, max
~9.2 quintillion).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, columns) converted from Integer to BigInteger.
# "number" (per-repo issue number) intentionally stays Integer.
_COLUMNS: dict[str, list[str]] = {
    "repos": ["id", "open_issues_count", "stars", "forks"],
    "issues": ["id", "github_id", "repo_id"],
    "contributors": ["id", "merged_prs", "points"],
}

# Postgres auto-generated name for the inline ForeignKey in 0001.
FK_NAME = "issues_repo_id_fkey"


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        # SQLite has dynamic typing; the int32/int64 distinction is a no-op.
        return

    # Postgres refuses to ALTER TYPE on a column referenced by a FK,
    # so drop the constraint first and recreate it after.
    op.drop_constraint(FK_NAME, "issues", type_="foreignkey")

    for table, columns in _COLUMNS.items():
        for column in columns:
            op.alter_column(
                table, column, existing_type=sa.Integer(), type_=sa.BigInteger()
            )

    op.create_foreign_key(
        FK_NAME, "issues", "repos", ["repo_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    if _is_sqlite():
        return

    op.drop_constraint(FK_NAME, "issues", type_="foreignkey")

    for table, columns in _COLUMNS.items():
        for column in columns:
            op.alter_column(
                table, column, existing_type=sa.BigInteger(), type_=sa.Integer()
            )

    op.create_foreign_key(
        FK_NAME, "issues", "repos", ["repo_id"], ["id"], ondelete="CASCADE"
    )
