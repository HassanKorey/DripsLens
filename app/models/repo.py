"""DB model for a Drips Wave approved repository."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # "owner/repo"
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    html_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    topics: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Drips Wave metadata
    point_multiplier: Mapped[float] = mapped_column(Float, default=1.0, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stellar_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stellar_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = unknown

    # Health / activity signals
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_ci: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    readme_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1 quality signal
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)  # 0..100

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    issues: Mapped[list["Issue"]] = relationship(  # noqa: F821
        back_populates="repo", cascade="all, delete-orphan"
    )
