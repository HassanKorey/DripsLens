"""SQLAlchemy model for tracked repositories."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.database import Base


class Repo(Base):
    __tablename__ = "repos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    language = Column(String, index=True, nullable=True)
    multiplier = Column(Integer, default=1)
    issue_count = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    health_score = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
