"""Health check router for DripsLens monitoring and uptime tracking."""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.scheduler.tasks import is_scheduler_running

router = APIRouter(tags=["Health"])

START_TIME = time.time()


class HealthCheckResponse(BaseModel):
    """Schema representing system liveness, database connectivity, and scheduler telemetry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "app": "DripsLens",
                "version": "2.0.0",
                "uptime_seconds": 3600.4215,
                "timestamp": "2026-11-07T07:00:00+00:00",
                "database": "connected",
                "scheduler": "running",
            }
        }
    )

    status: str = Field(description="Service liveness status indicator", examples=["ok"])
    app: str = Field(description="Application service name", examples=["DripsLens"])
    version: str = Field(description="Deployed semantic version string", examples=["2.0.0"])
    uptime_seconds: float = Field(description="Process uptime in seconds since boot", examples=[3600.4215])
    timestamp: str = Field(
        description="Current server UTC timestamp in ISO-8601 format",
        examples=["2026-11-07T07:00:00+00:00"],
    )
    database: str = Field(
        description="Database connectivity state (connected or disconnected)",
        examples=["connected", "disconnected"],
    )
    scheduler: str = Field(
        description="Background ingestion scheduler status (running or idle)",
        examples=["running", "idle"],
    )


@router.get(
    "/health",
    summary="Check service health and telemetry",
    description=(
        "Return service health status, process uptime in seconds, UTC ISO-8601 timestamp, "
        "database connectivity status, and background scheduler state."
    ),
    response_model=HealthCheckResponse,
)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return health status, database connection, and background scheduler state.

    Confirms 200 OK along with uptime and timestamp telemetry.
    """
    uptime_seconds = time.time() - START_TIME

    # Verify database connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Verify scheduler status
    scheduler_status = "running" if is_scheduler_running() else "idle"

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "2.0.0",
        "uptime_seconds": round(uptime_seconds, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "scheduler": scheduler_status,
    }
