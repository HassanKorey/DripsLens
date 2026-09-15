"""Admin endpoints: manual data refresh trigger.

Used to backfill repos whose data failed to save (e.g. the int32 overflow
before the BigInteger migration) or to re-fetch at any time without waiting
for the 6-hour cycle.
"""

import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.scheduler.tasks import scheduler, trigger_manual_refresh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _authorize(admin_token: str | None) -> None:
    """Reject requests unless ADMIN_TOKEN is unset (open mode) or matches."""
    expected = getattr(settings, "admin_token", None)
    if expected and admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )


@router.post("/refresh")
def trigger_refresh(
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Schedule one full refresh cycle (Drips -> GitHub -> Stellar -> DB).

    Returns immediately with the scheduler job id; watch the logs for the
    per-repo results. Requires the X-Admin-Token header when ADMIN_TOKEN is set.
    """
    _authorize(admin_token)
    job_id = trigger_manual_refresh()
    logger.info("Manual refresh triggered via POST /admin/refresh (job %s)", job_id)
    return {
        "status": "scheduled",
        "job_id": job_id,
        "note": "Refresh runs in the background; check application logs for progress.",
    }


@router.get("/refresh/status")
def refresh_status(
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Show whether a refresh job is queued/running and when the next cycle runs."""
    _authorize(admin_token)
    job = scheduler.get_job("refresh-manual")
    next_run = scheduler.get_job("refresh").next_run_time if scheduler.get_job("refresh") else None
    return {
        "manual_refresh": {
            "job_id": "refresh-manual",
            "scheduled": job is not None,
            "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        },
        "regular_refresh_next_run": next_run.isoformat() if next_run else None,
    }
