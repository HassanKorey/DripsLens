"""Health check router for DripsLens monitoring and uptime tracking."""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.scheduler.tasks import is_scheduler_running

router = APIRouter(tags=["Health"])

START_TIME = time.time()


@router.get("/health")
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
