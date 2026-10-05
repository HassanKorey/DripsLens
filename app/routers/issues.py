from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.issue import Issue

router = APIRouter(prefix="/issues", tags=["issues"])

@router.get("/")
def get_issues(
    complexity: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Issue)
    if complexity:
        query = query.filter(Issue.complexity == complexity)
    
    issues = query.offset(skip).limit(limit).all()
    return [{"id": i.id, "title": i.title, "url": i.url, "repo_id": i.repo_id, "complexity": i.complexity, "points": i.points, "is_claimed": i.is_claimed} for i in issues]
