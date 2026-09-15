"""DB model for a GitHub issue belonging to a Wave repo."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# SQLite auto-generates IDs only for INTEGER primary keys; Postgres gets real BIGINT.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")

# Drips Wave complexity tiers -> point values
COMPLEXITY_POINTS = {"trivial": 100, "medium": 150, "high": 200}


class Issue(Base):
    __tablename__ = "issues"

    # BigInteger: GitHub's global numeric IDs (github_id) already exceed int32 (2,147,483,647)
    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    repo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("repos.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(JSON, nullable=True)  # truncated markdown
    state: Mapped[str] = mapped_column(String(16), default="open", index=True)
    html_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    labels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    complexity: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    assignees: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at_gh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at_gh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    repo = relationship("Repo", back_populates="issues")
