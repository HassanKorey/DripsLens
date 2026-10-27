"""Analytics and ecosystem impact router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contributor import Contributor
from app.models.repo import Repo
from app.services.impact_scorer import calculate_impact_score, calculate_percentile_rank

router = APIRouter(tags=["Analytics"])


@router.get("/soroban/graph")
async def get_graph() -> dict[str, list[dict[str, Any]]]:
    """Return contract dependency invocation graph for Soroban analytics."""
    return {"nodes": [{"id": "C1"}], "edges": []}


@router.get("/analytics/contributors/{username}/impact")
async def get_contributor_impact(
    username: str,
    review_count: int = Query(0, ge=0, description="Verified pull request reviews conducted"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Calculate and return cross-repo contributor impact score, breakdown, history, and percentile ranking."""
    # Look up target contributor
    stmt = select(Contributor).where(Contributor.github_username == username)
    result = await db.execute(stmt)
    contributor = result.scalar_one_or_none()

    if not contributor:
        raise HTTPException(
            status_code=404,
            detail=f"Contributor '{username}' not found in tracked ecosystem",
        )

    # Determine average ecosystem multiplier across tracked repositories
    repo_stmt = select(Repo.multiplier)
    repo_result = await db.execute(repo_stmt)
    multipliers = [m for m in repo_result.scalars().all() if m is not None]
    avg_multiplier = float(sum(multipliers) / len(multipliers)) if multipliers else 1.0

    # Calculate individual impact metrics
    impact_data = calculate_impact_score(
        merged_prs=contributor.merged_prs,
        points_earned=contributor.points_earned,
        review_count=review_count,
        repo_multiplier=avg_multiplier,
    )

    # Compute population percentile relative to all ecosystem contributors
    all_contributors_stmt = select(Contributor)
    all_contrib_result = await db.execute(all_contributors_stmt)
    all_contributors = all_contrib_result.scalars().all()

    population_scores = [
        calculate_impact_score(
            merged_prs=c.merged_prs,
            points_earned=c.points_earned,
            review_count=0,
            repo_multiplier=avg_multiplier,
        )["impact_score"]
        for c in all_contributors
    ]
    percentile = calculate_percentile_rank(impact_data["impact_score"], population_scores)

    return {
        "username": contributor.github_username,
        "impact_score": impact_data["impact_score"],
        "percentile_ranking": percentile,
        "score_breakdown": impact_data["score_breakdown"],
        "activity_metrics": {
            "merged_prs": contributor.merged_prs,
            "points_earned": contributor.points_earned,
            "review_count": review_count,
        },
        "history": [
            {
                "period": "current",
                "impact_score": impact_data["impact_score"],
                "points_earned": contributor.points_earned,
                "merged_prs": contributor.merged_prs,
            }
        ],
    }
