"""Tests for the /health endpoint."""

import time
from datetime import datetime


def test_health_contract(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert data["app"] == "DripsLens"
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0

    assert isinstance(data["uptime_seconds"], float)
    assert data["uptime_seconds"] >= 0.0

    parsed_ts = datetime.fromisoformat(data["timestamp"])
    assert parsed_ts is not None


def test_health_uptime_and_timestamp_progression(client):
    start_time = time.monotonic()
    resp1 = client.get("/health")
    data1 = resp1.json()

    time.sleep(0.05)

    resp2 = client.get("/health")
    end_time = time.monotonic()
    data2 = resp2.json()

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    uptime1 = data1["uptime_seconds"]
    uptime2 = data2["uptime_seconds"]

    assert isinstance(uptime1, float)
    assert isinstance(uptime2, float)
    assert uptime1 >= 0.0
    assert uptime2 >= uptime1

    wall_clock_gap = end_time - start_time
    uptime_gap = uptime2 - uptime1
    assert uptime_gap <= wall_clock_gap + 1.0

    ts1 = datetime.fromisoformat(data1["timestamp"])
    ts2 = datetime.fromisoformat(data2["timestamp"])
    assert ts2 >= ts1
