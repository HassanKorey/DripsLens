"""Repository analytics and listing router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.repo import Repo

router = APIRouter(prefix="/repos", tags=["Repositories"])


class RepoSummaryResponse(BaseModel):
    """Schema representing a tracked Drips Wave repository."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "HassanKorey/DripsLens",
                "language": "Python",
                "multiplier": 2,
                "issue_count": 12,
                "health_score": 98,
                "is_verified": True,
            }
        }
    )

    id: int = Field(description="Unique internal repository identifier", examples=[1])
    name: str = Field(description="Full GitHub repository name (owner/repo)", examples=["HassanKorey/DripsLens"])
    language: str | None = Field(default=None, description="Primary programming language", examples=["Python"])
    multiplier: int = Field(default=1, description="Drips Wave point multiplier tier", examples=[2])
    issue_count: int = Field(default=0, description="Count of open tracked bounty issues", examples=[12])
    health_score: int = Field(default=0, description="Composite repository health score (0-100)", examples=[98])
    is_verified: bool = Field(default=False, description="Stellar Horizon / Soroban verification status", examples=[True])


class RepoHealthResponse(BaseModel):
    """Schema representing repository health score and verification telemetry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_id": 1,
                "name": "HassanKorey/DripsLens",
                "health_score": 98,
                "is_verified": True,
            }
        }
    )

    repo_id: int = Field(description="Unique internal repository identifier", examples=[1])
    name: str = Field(description="Full GitHub repository name (owner/repo)", examples=["HassanKorey/DripsLens"])
    health_score: int = Field(description="Composite repository health score (0-100)", examples=[98])
    is_verified: bool = Field(description="Whether the Stellar address is verified on-chain", examples=[True])


@router.get(
    "",
    summary="List tracked Wave repositories",
    description=(
        "Retrieve a paginated list of tracked Drips Wave repositories with optional case-insensitive "
        "language filtering and point multiplier filtering."
    ),
    response_model=list[RepoSummaryResponse],
)
@router.get(
    "/",
    summary="List tracked Wave repositories",
    description=(
        "Retrieve a paginated list of tracked Drips Wave repositories with optional case-insensitive "
        "language filtering and point multiplier filtering."
    ),
    response_model=list[RepoSummaryResponse],
    include_in_schema=False,
)
async def list_repos(
    language: str | None = Query(
        default=None,
        description="Filter repositories by primary programming language (case-insensitive)",
        examples=["Python", "Rust", "TypeScript"],
    ),
    multiplier: int | None = Query(
        default=None,
        ge=1,
        description="Filter repositories by active Drips Wave point multiplier",
        examples=[1, 2, 3],
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
        examples=[0, 10],
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of repository records to return (1-100)",
        examples=[10, 25],
    ),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List tracked repositories with optional language and multiplier filtering."""
    stmt = select(Repo)
    if language:
        stmt = stmt.where(Repo.language.ilike(language))
    if multiplier:
        stmt = stmt.where(Repo.multiplier == multiplier)

    stmt = stmt.offset(skip).limit(limit)
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


@router.get(
    "/{repo_id}/health",
    summary="Get repository health score and verification status",
    description="Retrieve composite health metrics and Stellar on-chain verification status for a specific repository ID.",
    response_model=RepoHealthResponse,
    responses={
        404: {
            "description": "Repository not found",
            "content": {"application/json": {"example": {"detail": "Repository not found"}}},
        }
    },
)
async def get_repo_health(
    repo_id: int = Path(
        ...,
        ge=1,
        description="Unique internal ID of the tracked repository",
        examples=[1],
    ),
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
