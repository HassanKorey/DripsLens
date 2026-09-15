"""DB model for a contributor ranked by merged PRs and points."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

# SQLite auto-generates IDs only for INTEGER primary keys; Postgres gets real BIGINT.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


class Contributor(Base):
    __tablename__ = "contributors"

    # BigInteger: internal IDs and accumulating counts should never overflow int32
    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True)
    github_login: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    merged_prs: Mapped[int] = mapped_column(BigInteger, default=0)
    points: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    repos_contributed: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["owner/repo"]
    recent_prs: Mapped[list | None] = mapped_column(JSON, nullable=True)  # compact PR summaries

    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
