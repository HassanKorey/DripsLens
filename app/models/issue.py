from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.db.database import Base

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String, unique=True)
    repo_id = Column(Integer, ForeignKey("repos.id"))
    complexity = Column(String)  # Trivial, Medium, High
    points = Column(Integer)     # 100, 150, 200
    is_claimed = Column(Boolean, default=False)
