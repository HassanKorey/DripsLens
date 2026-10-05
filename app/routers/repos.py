from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.repo import Repo
from app.cache.redis_client import cache_response

router = APIRouter(prefix="/repos", tags=["repos"])

@router.get("/")
@cache_response(ttl_seconds=300)
async def get_repos(
    language: Optional[str] = None,
    multiplier: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Repo)
    if language:
        query = query.filter(Repo.language == language)
    if multiplier:
        query = query.filter(Repo.multiplier == multiplier)
    
    repos = query.offset(skip).limit(limit).all()
    # Pydantic serialization might be needed for real app
    return [{"id": r.id, "name": r.name, "language": r.language, "multiplier": r.multiplier, "issue_count": r.issue_count, "health_score": r.health_score, "is_verified": r.is_verified} for r in repos]

@router.get("/{repo_id}/health")
async def get_repo_health(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found"}
    return {"repo_id": repo.id, "health_score": repo.health_score}
