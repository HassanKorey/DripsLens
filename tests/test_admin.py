"""Tests for the manual refresh trigger and admin endpoints."""

import threading

from app.scheduler import tasks as scheduler_tasks
from app.scheduler.tasks import trigger_manual_refresh


class _FakeScheduler:
    """Minimal stand-in for the module-level AsyncIOScheduler singleton."""

    def __init__(self, running: bool):
        self.running = running
        self.added_jobs: list[dict] = []

    def add_job(self, *args, **kwargs) -> None:
        self.added_jobs.append(kwargs)


def test_trigger_manual_refresh_schedules_one_shot_job(monkeypatch):
    fake = _FakeScheduler(running=True)
    monkeypatch.setattr(scheduler_tasks, "scheduler", fake)

    job_id = trigger_manual_refresh()

    assert job_id == "refresh-manual"
    assert len(fake.added_jobs) == 1
    kwargs = fake.added_jobs[0]
    assert kwargs.get("id") == "refresh-manual"
    assert kwargs.get("replace_existing") is True


def test_trigger_manual_refresh_without_scheduler_uses_thread(monkeypatch):
    """With the scheduler stopped (e.g. SCHEDULER_ENABLED=false), a background
    thread runs the refresh instead of crashing on a missing event loop."""
    started = threading.Event()

    monkeypatch.setattr(scheduler_tasks, "scheduler", _FakeScheduler(running=False))
    monkeypatch.setattr(
        scheduler_tasks,
        "refresh_repos",
        lambda: started.set(),  # avoid real network work
    )

    job_id = trigger_manual_refresh()
    assert job_id == "refresh-thread"

    assert started.wait(timeout=5), "background refresh thread did not run"


def test_admin_refresh_endpoint_schedules_job(client, monkeypatch):
    from app.routers import admin as admin_router

    calls: list[str] = []

    def fake_trigger():
        calls.append("refresh")
        return "refresh-manual"

    monkeypatch.setattr(admin_router, "trigger_manual_refresh", fake_trigger)
    resp = client.post("/admin/refresh")
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
    assert calls == ["refresh"]


def test_admin_refresh_rejects_bad_token(client, monkeypatch):
    from app.config import settings
    from app.routers import admin as admin_router

    monkeypatch.setattr(settings, "admin_token", "secret-token")
    resp = client.post("/admin/refresh", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401

    # Correct token passes
    monkeypatch.setattr(
        admin_router, "trigger_manual_refresh", lambda: "refresh-manual"
    )
    resp = client.post("/admin/refresh", headers={"X-Admin-Token": "secret-token"})
    assert resp.status_code == 200


def test_admin_refresh_status_endpoint(client):
    resp = client.get("/admin/refresh/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "manual_refresh" in body
    assert "regular_refresh_next_run" in body
