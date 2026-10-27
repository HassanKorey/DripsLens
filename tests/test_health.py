"""Tests for the /health endpoint contract, database disconnection resilience, and uptime monitoring."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import OperationalError

from app.db.database import get_db
from app.main import app

EXPECTED_HEALTH_KEYS = {
    "status",
    "app",
    "version",
    "uptime_seconds",
    "timestamp",
    "database",
    "scheduler",
}


def test_health_status_and_metadata(client):
    """GET /health returns 200 with status ok, app name, version string, and complete schema."""
    resp = client.get("/health")
    assert resp.status_code == 200

    data = resp.json()
    assert set(data.keys()) == EXPECTED_HEALTH_KEYS
    assert data["status"] == "ok"
    assert data["app"] == "DripsLens"
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
    assert data["database"] == "connected"
    assert data["scheduler"] in ("running", "idle")


def test_health_uptime_non_negative_and_monotonic(client):
    """uptime_seconds is a non-negative float and non-decreasing over consecutive calls."""
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    data1 = resp1.json()

    uptime1 = data1["uptime_seconds"]
    assert isinstance(uptime1, float)
    assert uptime1 >= 0.0

    time.sleep(0.02)

    resp2 = client.get("/health")
    assert resp2.status_code == 200
    data2 = resp2.json()

    uptime2 = data2["uptime_seconds"]
    assert isinstance(uptime2, float)
    assert uptime2 >= uptime1


def test_health_timestamp_iso8601_and_uptime_gap(client):
    """timestamp parses as ISO-8601 and uptime delta never exceeds wall-clock gap."""
    t_start = time.perf_counter()
    resp1 = client.get("/health")
    assert resp1.status_code == 200

    time.sleep(0.05)

    resp2 = client.get("/health")
    assert resp2.status_code == 200
    t_end = time.perf_counter()

    data1 = resp1.json()
    data2 = resp2.json()

    # Assert timestamp parses as ISO-8601
    dt1 = datetime.fromisoformat(data1["timestamp"])
    dt2 = datetime.fromisoformat(data2["timestamp"])
    assert dt1 is not None and dt2 is not None
    assert dt2 >= dt1

    # Uptime delta should not exceed wall-clock elapsed time (plus 1s tolerance)
    wall_clock_gap = t_end - t_start
    uptime_delta = data2["uptime_seconds"] - data1["uptime_seconds"]
    assert uptime_delta >= 0.0
    assert uptime_delta <= wall_clock_gap + 1.0


def test_health_database_disconnection_graceful_200(client):
    """When the database session raises an OperationalError, /health still returns HTTP 200 with database='disconnected'."""
    failing_session = AsyncMock()
    failing_session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("database engine connection refused")
    )

    async def override_failing_db():
        yield failing_session

    app.dependency_overrides[get_db] = override_failing_db
    try:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == EXPECTED_HEALTH_KEYS
        assert data["status"] == "ok"
        assert data["database"] == "disconnected"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_health_scheduler_running_and_idle_states(client):
    """Verify scheduler field reflects both active ('running') and inactive ('idle') states."""
    with patch("app.routers.health.is_scheduler_running", return_value=True):
        resp_running = client.get("/health")
        assert resp_running.status_code == 200
        assert resp_running.json()["scheduler"] == "running"

    with patch("app.routers.health.is_scheduler_running", return_value=False):
        resp_idle = client.get("/health")
        assert resp_idle.status_code == 200
        assert resp_idle.json()["scheduler"] == "idle"
