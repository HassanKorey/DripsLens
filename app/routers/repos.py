"""/repos endpoints: browse, filter, paginate and inspect Wave repos."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as safunc
from sqlalchemy.orm import Session

from app.cache.redis_client import cache_get, cache_set
from app.db.database import get_db
from app.models import Repo
from app.scheduler.tasks import compute_health_score

router = APIRouter(prefix="/repos", tags=["repos"])


def _repo_out(r: Repo) -> dict:
    return {
        "id": r.id,
        "full_name": r.full_name,
        "owner": r.owner,
        "name": r.name,
        "description": r.description,
        "html_url": r.html_url,
        "language": r.language,
        "topics": r.topics or [],
        "point_multiplier": r.point_multiplier,
        "stellar_verified": r.stellar_verified,
        "open_issues_count": r.open_issues_count,
        "stars": r.stars,
        "forks": r.forks,
        "last_commit_at": r.last_commit_at.isoformat() if r.last_commit_at else None,
        "has_ci": r.has_ci,
        "health_score": r.health_score,
        "last_fetched_at": r.last_fetched_at.isoformat() if r.last_fetched_at else None,
    }


def _repo_detail(r: Repo) -> dict:
    return {
        **_repo_out(r),
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "stellar_account": r.stellar_account,
        "last_push_at": r.last_push_at.isoformat() if r.last_push_at else None,
        "readme_score": r.readme_score,
        "is_active": r.is_active,
        "updated_at": r.updated_at.isoformat(),
    }


@router.get("")
async def list_repos(
    db: Annotated[Session, Depends(get_db)],
    language: str | None = Query(None, description="Filter by primary language"),
    multiplier: float | None = Query(None, description="Filter by point multiplier (1/2/4)"),
    min_health: float | None = Query(None, ge=0, le=100, description="Minimum health score"),
    q: str | None = Query(None, max_length=100, description="Search name/description"),
    verified: bool | None = Query(None, description="Stellar verification filter"),
    sort: str = Query("health", pattern="^(health|issues|stars|updated|name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    """Browse approved repos. Filter by language, multiplier, health, search."""
    cache_key = (
        f"dripslens:repos:list:{language}:{multiplier}:{min_health}:{q}:{verified}:{sort}:{order}:{page}:{per_page}"
    )
    if (cached := await cache_get(cache_key)) is not None:
        return cached

    query = db.query(Repo).filter(Repo.is_active.is_(True))
    if language:
        query = query.filter(Repo.language.ilike(language))
    if multiplier is not None:
        query = query.filter(Repo.point_multiplier == multiplier)
    if min_health is not None:
        query = query.filter(Repo.health_score >= min_health)
    if verified is not None:
        query = query.filter(Repo.stellar_verified.is_(verified))
    if q:
        like = f"%{q}%"
        query = query.filter(safunc.coalesce(Repo.description, "").ilike(like) | Repo.full_name.ilike(like))

    sort_cols = {
        "health": Repo.health_score,
        "issues": Repo.open_issues_count,
        "stars": Repo.stars,
        "updated": Repo.last_push_at,
        "name": Repo.full_name,
    }
    col = sort_cols[sort]
    query = query.order_by((col.asc() if order == "asc" else col.desc()).nulls_last())

    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    payload = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [_repo_out(r) for r in rows],
    }
    await cache_set(cache_key, payload)
    return payload


@router.get("/meta")
def repos_meta(db: Annotated[Session, Depends(get_db)]):
    """Aggregate counts for dashboard cards (languages, multipliers, totals)."""
    return {
        "total_repos": db.query(safunc.count(Repo.id)).scalar() or 0,
        "total_open_issues": db.query(safunc.coalesce(safunc.sum(Repo.open_issues_count), 0)).scalar(),
        "languages": [row[0] for row in db.query(Repo.language).distinct().order_by(Repo.language) if row[0]],
        "multipliers": [
            row[0] for row in db.query(Repo.point_multiplier).distinct().order_by(Repo.point_multiplier)
        ],
        "verified_repos": db.query(safunc.count(Repo.id)).filter(Repo.stellar_verified.is_(True)).scalar() or 0,
        "avg_health": db.query(safunc.avg(Repo.health_score)).scalar(),
    }


@router.get("/{repo_id}/health")
def repo_health(repo_id: int, db: Annotated[Session, Depends(get_db)]):
    """Health score with component breakdown for one repo."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")

    age_days = None
    ref = repo.last_commit_at or repo.last_push_at
    if ref is not None:
        age_days = max((datetime.now(UTC) - ref).days, 0)

    breakdown = {
        "issues_available": min(repo.open_issues_count, 20) / 20 * 40,
        "ci": 15.0 if repo.has_ci else (7.5 if repo.has_ci is None else 0.0),
        "recency": max(0.0, 25.0 * (1 - age_days / 365)) if age_days is not None else 0.0,
        "readme": (repo.readme_score or 0.0) * 20,
    }
    return {
        "repo": repo.full_name,
        "health_score": repo.health_score
        if repo.health_score is not None
        else compute_health_score(
            repo.open_issues_count, repo.has_ci, ref, repo.readme_score
        ),
        "components": {k: round(v, 1) for k, v in breakdown.items()},
        "last_commit_at": repo.last_commit_at.isoformat() if repo.last_commit_at else None,
        "age_days": age_days,
    }


@router.get("/{repo_id_or_name:path}")
def get_repo(repo_id_or_name: str, db: Annotated[Session, Depends(get_db)]):
    """Repo detail. Accepts numeric id or 'owner/repo'."""
    query = db.query(Repo)
    if repo_id_or_name.isdigit():
        repo = query.filter(Repo.id == int(repo_id_or_name)).first()
    else:
        repo = query.filter(Repo.full_name == repo_id_or_name).first()
    if repo is None:
        raise HTTPException(status_code=404, detail="repo not found")
    return _repo_detail(repo)
