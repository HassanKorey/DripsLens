from sqlalchemy import Column, Integer, String
from app.db.database import Base

class Contributor(Base):
    __tablename__ = "contributors"

    id = Column(Integer, primary_key=True, index=True)
    github_username = Column(String, unique=True, index=True)
    merged_prs = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
