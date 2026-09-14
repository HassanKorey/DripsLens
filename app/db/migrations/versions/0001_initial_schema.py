"""initial schema: repos, issues, contributors

Revision ID: 0001
Revises:
Create Date: 2026-09-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("topics", sa.JSON(), nullable=True),
        sa.Column("point_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stellar_account", sa.String(length=128), nullable=True),
        sa.Column("stellar_verified", sa.Boolean(), nullable=True),
        sa.Column("open_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_commit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_ci", sa.Boolean(), nullable=True),
        sa.Column("readme_score", sa.Float(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("full_name"),
    )
    op.create_index("ix_repos_full_name", "repos", ["full_name"])
    op.create_index("ix_repos_language", "repos", ["language"])
    op.create_index("ix_repos_point_multiplier", "repos", ["point_multiplier"])
    op.create_index("ix_repos_health_score", "repos", ["health_score"])

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("html_url", sa.String(length=512), nullable=True),
        sa.Column("labels", sa.JSON(), nullable=True),
        sa.Column("complexity", sa.String(length=16), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("assignees", sa.JSON(), nullable=True),
        sa.Column("created_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("github_id"),
    )
    op.create_index("ix_issues_github_id", "issues", ["github_id"])
    op.create_index("ix_issues_repo_id", "issues", ["repo_id"])
    op.create_index("ix_issues_state", "issues", ["state"])
    op.create_index("ix_issues_complexity", "issues", ["complexity"])
    op.create_index("ix_issues_claimed", "issues", ["claimed"])

    op.create_table(
        "contributors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_login", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("profile_url", sa.String(length=512), nullable=True),
        sa.Column("merged_prs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repos_contributed", sa.JSON(), nullable=True),
        sa.Column("recent_prs", sa.JSON(), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("github_login"),
    )
    op.create_index("ix_contributors_github_login", "contributors", ["github_login"])
    op.create_index("ix_contributors_points", "contributors", ["points"])


def downgrade() -> None:
    op.drop_table("contributors")
    op.drop_table("issues")
    op.drop_table("repos")
