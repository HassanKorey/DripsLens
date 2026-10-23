"""Repository analytics and listing router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.repo import Repo

router = APIRouter(prefix="/repos", tags=["Repositories"])


@router.get("")
@router.get("/")
async def list_repos(
    language: str | None = None,
    multiplier: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List tracked repositories with optional language and multiplier filtering."""
    stmt = select(Repo)
    if language:
        stmt = stmt.where(Repo.language.ilike(language))
    if multiplier:
        stmt = stmt.where(Repo.multiplier == multiplier)

    stmt = stmt.order_by(Repo.id.asc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    repos = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "language": r.language,
            "multiplier": r.multiplier,
            "issue_count": r.issue_count,
            "health_score": r.health_score,
            "is_verified": r.is_verified,
        }
        for r in repos
    ]


@router.get("/{repo_id}/health")
async def get_repo_health(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve repository health score breakdown and verification status."""
    stmt = select(Repo).where(Repo.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "repo_id": repo.id,
        "name": repo.name,
        "health_score": repo.health_score,
        "is_verified": repo.is_verified,
    }
