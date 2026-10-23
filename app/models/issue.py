"""SQLAlchemy model for tracked issues."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.db.database import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String, unique=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=True)
    complexity = Column(String, default="Medium")
    points = Column(Integer, default=150)
    is_claimed = Column(Boolean, default=False)
