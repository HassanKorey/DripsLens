"""/issues endpoints: browse open Wave issues across all repos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as safunc
from sqlalchemy.orm import Session, joinedload

from app.cache.redis_client import cache_get, cache_set, get_redis
from app.db.database import get_db
from app.models import Issue, Repo

router = APIRouter(prefix="/issues", tags=["issues"])


def _issue_out(i: Issue, include_repo: bool = True) -> dict:
    out = {
        "github_id": i.github_id,
        "number": i.number,
        "title": i.title,
        "state": i.state,
        "html_url": i.html_url,
        "labels": i.labels or [],
        "complexity": i.complexity,
        "points": i.points,
        "claimed": i.claimed,
        "assignees": i.assignees or [],
        "created_at": i.created_at_gh.isoformat() if i.created_at_gh else None,
        "updated_at": i.updated_at_gh.isoformat() if i.updated_at_gh else None,
    }
    if include_repo:
        out["repo"] = i.repo.full_name if i.repo else None
    return out


@router.get("")
async def list_issues(
    db: Annotated[Session, Depends(get_db)],
    complexity: str | None = Query(None, pattern="^(trivial|medium|high)$"),
    claimed: bool | None = Query(None, description="Filter by claimed status"),
    repo: str | None = Query(None, description="Filter by owner/repo"),
    min_points: int | None = Query(None, ge=0),
    q: str | None = Query(None, max_length=100, description="Search titles"),
    sort: str = Query("points", pattern="^(points|created|updated)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    """All open Wave issues in one place, filterable by complexity (100/150/200 pts)."""
    cache_key = f"dripslens:issues:list:{complexity}:{claimed}:{repo}:{min_points}:{q}:{sort}:{order}:{page}:{per_page}"
    # Skip caching entirely when Redis is unavailable — query the DB directly.
    if await get_redis() is not None:
        if (cached := await cache_get(cache_key)) is not None:
            return cached

    query = db.query(Issue).options(joinedload(Issue.repo)).filter(Issue.state == "open")
    if complexity:
        query = query.filter(Issue.complexity == complexity)
    if claimed is not None:
        query = query.filter(Issue.claimed.is_(claimed))
    if repo:
        query = query.join(Repo).filter(Repo.full_name == repo)
    if min_points is not None:
        query = query.filter(Issue.points >= min_points)
    if q:
        query = query.filter(Issue.title.ilike(f"%{q}%"))

    sort_cols = {"points": Issue.points, "created": Issue.created_at_gh, "updated": Issue.updated_at_gh}
    col = sort_cols[sort]
    query = query.order_by((col.asc() if order == "asc" else col.desc()).nulls_last())

    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    counts = dict(
        db.query(Issue.complexity, safunc.count(Issue.id))
        .filter(Issue.state == "open")
        .group_by(Issue.complexity)
        .all()
    )

    payload = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "open_by_complexity": {k: counts.get(k, 0) for k in ("trivial", "medium", "high", None)},
        "items": [_issue_out(i) for i in rows],
    }
    if await get_redis() is not None:
        await cache_set(cache_key, payload)
    return payload


@router.get("/stats")
def issue_stats(db: Annotated[Session, Depends(get_db)]):
    """Claimed vs unclaimed breakdown, total potential points."""
    total = db.query(safunc.count(Issue.id)).filter(Issue.state == "open").scalar() or 0
    claimed = db.query(safunc.count(Issue.id)).filter(Issue.state == "open", Issue.claimed.is_(True)).scalar() or 0
    potential_points = (
        db.query(safunc.coalesce(safunc.sum(Issue.points), 0)).filter(Issue.state == "open").scalar()
    )
    return {
        "open_issues": total,
        "claimed": claimed,
        "unclaimed": total - claimed,
        "potential_points": potential_points,
    }
