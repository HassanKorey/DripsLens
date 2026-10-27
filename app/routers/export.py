"""Data export router for streaming CSV and JSON snapshots of DripsLens analytics."""

import csv
import io
import json
from collections.abc import Iterator
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contributor import Contributor
from app.models.repo import Repo

router = APIRouter(prefix="/export", tags=["Export"])

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_field(value: Any) -> Any:
    """Sanitize string values against CSV formula injection while preserving numbers and booleans."""
    if value is None:
        return ""
    if isinstance(value, str):
        cleaned = value.replace("\r", " ").replace("\n", " ").strip()
        if cleaned.startswith(FORMULA_PREFIXES):
            return f"'{cleaned}"
        return cleaned
    return value


class RepoExportRecord(BaseModel):
    """Validated schema record for repository export snapshots."""

    id: int
    name: str
    language: str | None = None
    multiplier: int = 1
    issue_count: int = 0
    health_score: int = 100
    is_verified: bool = False


class ContributorExportRecord(BaseModel):
    """Validated schema record for contributor ranking export snapshots."""

    id: int
    github_username: str
    merged_prs: int = 0
    points_earned: int = 0


def _stream_csv(fieldnames: list[str], rows: list[dict[str, Any]]) -> Iterator[str]:
    """Yield CSV header and rows incrementally using an in-memory buffer."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    for row in rows:
        sanitized_row = {k: sanitize_csv_field(row.get(k)) for k in fieldnames}
        writer.writerow(sanitized_row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def _stream_json(records: list[dict[str, Any]]) -> Iterator[str]:
    """Yield a valid JSON array incrementally without building one giant string."""
    yield "["
    for idx, record in enumerate(records):
        prefix = ",\n" if idx > 0 else "\n"
        yield f"{prefix}{json.dumps(record)}"
    yield "\n]\n" if records else "]\n"


@router.get("/repos")
async def export_repos(
    format: Literal["csv", "json"] = Query("json", description="Export file format: 'csv' or 'json'"),
    language: str | None = Query(None, description="Optional programming language filter"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export tracked repositories as a streaming CSV or JSON download."""
    stmt = select(Repo).order_by(Repo.id.asc())
    if language:
        stmt = stmt.where(Repo.language.ilike(language))

    result = await db.execute(stmt)
    repos = result.scalars().all()

    validated_records = [
        RepoExportRecord(
            id=r.id,
            name=r.name,
            language=r.language,
            multiplier=r.multiplier,
            issue_count=r.issue_count,
            health_score=r.health_score,
            is_verified=bool(r.is_verified),
        ).model_dump()
        for r in repos
    ]

    if format == "csv":
        fieldnames = [
            "id",
            "name",
            "language",
            "multiplier",
            "issue_count",
            "health_score",
            "is_verified",
        ]
        return StreamingResponse(
            _stream_csv(fieldnames, validated_records),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="repos.csv"'},
        )

    return StreamingResponse(
        _stream_json(validated_records),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="repos.json"'},
    )


@router.get("/contributors")
async def export_contributors(
    format: Literal["csv", "json"] = Query("json", description="Export file format: 'csv' or 'json'"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export contributor rankings as a streaming CSV or JSON download."""
    stmt = select(Contributor).order_by(
        Contributor.points_earned.desc(),
        Contributor.merged_prs.desc(),
        Contributor.id.asc(),
    )
    result = await db.execute(stmt)
    contributors = result.scalars().all()

    validated_records = [
        ContributorExportRecord(
            id=c.id,
            github_username=c.github_username,
            merged_prs=c.merged_prs,
            points_earned=c.points_earned,
        ).model_dump()
        for c in contributors
    ]

    if format == "csv":
        fieldnames = ["id", "github_username", "merged_prs", "points_earned"]
        return StreamingResponse(
            _stream_csv(fieldnames, validated_records),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="contributors.csv"'},
        )

    return StreamingResponse(
        _stream_json(validated_records),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="contributors.json"'},
    )
