from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.database import Base

class Repo(Base):
    __tablename__ = "repos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    language = Column(String, index=True)
    multiplier = Column(Integer, default=1)  # 1x, 2x, 4x
    issue_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    health_score = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
