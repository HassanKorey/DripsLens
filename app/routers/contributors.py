"""/contributors endpoints: leaderboard ranked by merged PRs and points."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.cache.redis_client import cache_get, cache_set, get_redis
from app.db.database import get_db
from app.models import Contributor

router = APIRouter(prefix="/contributors", tags=["contributors"])


def _contributor_out(c: Contributor) -> dict:
    return {
        "github_login": c.github_login,
        "avatar_url": c.avatar_url,
        "profile_url": c.profile_url,
        "merged_prs": c.merged_prs,
        "points": c.points,
        "repos_contributed": c.repos_contributed or [],
        "recent_prs": (c.recent_prs or [])[:10],
    }


@router.get("/top")
async def top_contributors(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(25, ge=1, le=100),
    repo: str | None = Query(None, description="Only count PRs to this owner/repo"),
):
    """Leaderboard: contributors ranked by points earned across Wave repos."""
    cache_key = f"dripslens:contributors:top:{limit}:{repo}"
    # Skip caching entirely when Redis is unavailable — query the DB directly.
    if await get_redis() is not None:
        if (cached := await cache_get(cache_key)) is not None:
            return cached

    query = db.query(Contributor)
    rows = query.order_by(Contributor.points.desc(), Contributor.merged_prs.desc()).limit(limit).all()

    if repo:
        # Filter to contributors with at least one PR to this repo
        rows = [c for c in rows if repo in (c.repos_contributed or [])]

    payload = {"total": len(rows), "items": [_contributor_out(c) for c in rows]}
    if await get_redis() is not None:
        await cache_set(cache_key, payload)
    return payload
