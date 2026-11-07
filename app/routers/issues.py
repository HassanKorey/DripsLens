"""Issues router for tracking bounties and Wave tasks."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.issue import Issue

router = APIRouter(prefix="/issues", tags=["Issues"])


class IssueSummaryResponse(BaseModel):
    """Schema representing a tracked Drips Wave issue and complexity tier."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "docs(openapi): enrich OpenAPI route metadata and filter query parameter examples",
                "url": "https://github.com/HassanKorey/DripsLens/issues/31",
                "repo_id": 1,
                "complexity": "Trivial",
                "points": 100,
                "is_claimed": False,
            }
        }
    )

    id: int = Field(description="Unique internal issue identifier", examples=[1])
    title: str = Field(description="GitHub issue title", examples=["Add unit tests for Soroban client"])
    url: str | None = Field(
        default=None,
        description="HTML URL to the GitHub issue",
        examples=["https://github.com/HassanKorey/DripsLens/issues/31"],
    )
    repo_id: int | None = Field(default=None, description="Associated repository internal ID", examples=[1])
    complexity: str = Field(
        default="Medium",
        description="Drips Wave complexity classification (Trivial, Medium, High)",
        examples=["Trivial", "Medium", "High"],
    )
    points: int = Field(default=150, description="Base Wave point value (100, 150, or 200)", examples=[100, 150, 200])
    is_claimed: bool = Field(default=False, description="Whether the issue is currently assigned/claimed", examples=[False])


@router.get(
    "",
    summary="List tracked Wave bounty issues",
    description=(
        "Retrieve a paginated list of open Drips Wave issues filtered by complexity tier "
        "(`Trivial`, `Medium`, `High`) and assignment claim status (`is_claimed`)."
    ),
    response_model=list[IssueSummaryResponse],
)
@router.get(
    "/",
    summary="List tracked Wave bounty issues",
    description=(
        "Retrieve a paginated list of open Drips Wave issues filtered by complexity tier "
        "(`Trivial`, `Medium`, `High`) and assignment claim status (`is_claimed`)."
    ),
    response_model=list[IssueSummaryResponse],
    include_in_schema=False,
)
async def list_issues(
    complexity: str | None = Query(
        default=None,
        description="Filter issues by Drips Wave complexity tier (Trivial, Medium, High)",
        examples=["Trivial", "Medium", "High"],
    ),
    is_claimed: bool | None = Query(
        default=None,
        description="Filter issues by claim/assignment status (true for claimed, false for open/unclaimed)",
        examples=[False, True],
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of issue records to skip for pagination",
        examples=[0, 20],
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of issue records to return (1-100)",
        examples=[10, 50],
    ),
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
