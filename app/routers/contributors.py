from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.contributor import Contributor

router = APIRouter(prefix="/contributors", tags=["contributors"])

@router.get("/top")
def get_top_contributors(db: Session = Depends(get_db)):
    contributors = db.query(Contributor).order_by(Contributor.points_earned.desc()).limit(10).all()
    return [{"id": c.id, "github_username": c.github_username, "merged_prs": c.merged_prs, "points_earned": c.points_earned} for c in contributors]
