"""Issues router for tracking bounties and Wave tasks."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.issue import Issue

router = APIRouter(prefix="/issues", tags=["Issues"])


@router.get("")
@router.get("/")
async def list_issues(
    complexity: str | None = None,
    is_claimed: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List issues filtered by complexity tier (Trivial, Medium, High) or claim status."""
    stmt = select(Issue)
    if complexity:
        stmt = stmt.where(Issue.complexity.ilike(complexity))
    if is_claimed is not None:
        stmt = stmt.where(Issue.is_claimed == is_claimed)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    issues = result.scalars().all()

    return [
        {
            "id": i.id,
            "title": i.title,
            "url": i.url,
            "repo_id": i.repo_id,
            "complexity": i.complexity,
            "points": i.points,
            "is_claimed": i.is_claimed,
        }
        for i in issues
    ]
