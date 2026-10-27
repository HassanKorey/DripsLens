"""Leaderboard and contributor ranking router."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import cache_response
from app.db.database import get_db
from app.models.contributor import Contributor

router = APIRouter(tags=["Leaderboard"])


@router.get("/leaderboard")
@router.get("/contributors/top")
@cache_response(ttl_seconds=300)
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve top contributor rankings by points earned and merged pull requests."""
    stmt = select(Contributor).order_by(Contributor.points_earned.desc(), Contributor.merged_prs.desc()).limit(limit)
    result = await db.execute(stmt)
    contributors = result.scalars().all()

    return [
        {
            "id": c.id,
            "github_username": c.github_username,
            "merged_prs": c.merged_prs,
            "points_earned": c.points_earned,
        }
        for c in contributors
    ]
