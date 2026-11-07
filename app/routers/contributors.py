"""Leaderboard and contributor ranking router."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contributor import Contributor

router = APIRouter(tags=["Leaderboard"])


class ContributorRankingResponse(BaseModel):
    """Schema representing a ranked Drips Wave contributor on the leaderboard."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "github_username": "HassanKorey",
                "merged_prs": 18,
                "points_earned": 2700,
            }
        }
    )

    id: int = Field(description="Unique internal contributor identifier", examples=[1])
    github_username: str = Field(description="Contributor GitHub username", examples=["HassanKorey"])
    merged_prs: int = Field(default=0, description="Total number of merged Wave pull requests", examples=[18])
    points_earned: int = Field(default=0, description="Cumulative Drips Wave points earned", examples=[2700])


@router.get(
    "/leaderboard",
    summary="Get top ecosystem contributors",
    description=(
        "Retrieve the Drips Wave contributor leaderboard ordered descending by total points earned "
        "and merged pull request count."
    ),
    response_model=list[ContributorRankingResponse],
)
@router.get(
    "/contributors/top",
    summary="Get top ecosystem contributors (alias)",
    description=(
        "Alias endpoint returning top Drips Wave contributors ordered by points earned and merged PRs."
    ),
    response_model=list[ContributorRankingResponse],
)
async def get_leaderboard(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of ranked contributors to return (1-100)",
        examples=[10, 25],
    ),
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
