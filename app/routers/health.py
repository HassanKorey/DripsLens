from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])

uptime_start = datetime.utcnow()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime": str(datetime.utcnow() - uptime_start)
    }
