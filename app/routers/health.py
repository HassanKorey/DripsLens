"""Health check endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app import __version__

router = APIRouter(tags=["meta"])

_STARTED_AT = datetime.now(UTC)


def _uptime_seconds() -> float:
    return (datetime.now(UTC) - _STARTED_AT).total_seconds()


@router.get("/health")
def health() -> dict:
    """App version and uptime — used by CI smoke checks and monitoring."""
    return {
        "status": "ok",
        "app": "DripsLens",
        "version": __version__,
        "uptime_seconds": round(_uptime_seconds(), 3),
        "timestamp": datetime.now(UTC).isoformat(),
    }
