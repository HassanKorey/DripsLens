"""Unit and integration tests for POST /webhooks/repo-registered."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.issue import Issue
from app.models.repo import Repo
from app.routers.webhooks import (
    RepoRegisteredPayload,
    compute_repo_health_score,
    run_standalone_repo_registration_worker,
)


@pytest.mark.asyncio
async def test_webhook_repo_registered_rejects_missing_or_invalid_token(async_client: AsyncClient):
    """POST /webhooks/repo-registered returns 401 when token is missing or invalid."""
    payload = {"name": "stellar/new-wave-repo", "language": "Rust", "multiplier": 2}

    no_token_resp = await async_client.post("/webhooks/repo-registered", json=payload)
    assert no_token_resp.status_code == 401

    bad_token_resp = await async_client.post(
        "/webhooks/repo-registered",
        json=payload,
        headers={"X-Webhook-Token": "wrong-secret"},
    )
    assert bad_token_resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_repo_registered_ingests_and_verifies_account(
    async_client: AsyncClient,
    db_session,
    monkeypatch,
):
    """POST /webhooks/repo-registered ingests repo issues, verifies Stellar account, and computes health score."""
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-token")

    sample_issues = [
        {
            "id": 101,
            "number": 1,
            "title": "Add Soroban auth guard",
            "url": "https://github.com/stellar/new-wave-repo/issues/1",
            "complexity": "High",
            "points": 200,
            "is_claimed": False,
        },
        {
            "id": 102,
            "number": 2,
            "title": "Fix ledger TTL bump",
            "url": "https://github.com/stellar/new-wave-repo/issues/2",
            "complexity": "Medium",
            "points": 150,
            "is_claimed": True,
        },
    ]

    with (
        patch("app.routers.webhooks.fetch_issues_for_repo", new_callable=AsyncMock) as mock_issues,
        patch("app.routers.webhooks.verify_stellar_account", new_callable=AsyncMock) as mock_verify,
    ):
        mock_issues.return_value = sample_issues
        mock_verify.return_value = True

        resp = await async_client.post(
            "/webhooks/repo-registered",
            json={
                "name": "stellar/new-wave-repo",
                "language": "Rust",
                "multiplier": 2,
                "stellar_account": "G" + "A" * 55,
            },
            headers={"Authorization": "Bearer test-secret-token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    repo_data = body["repo"]
    assert repo_data["name"] == "stellar/new-wave-repo"
    assert repo_data["language"] == "Rust"
    assert repo_data["multiplier"] == 2
    assert repo_data["issue_count"] == 2
    assert repo_data["is_verified"] is True
    assert repo_data["health_score"] == compute_repo_health_score(2, True, 2)

    repo_count = await db_session.scalar(select(func.count()).select_from(Repo))
    issue_count = await db_session.scalar(select(func.count()).select_from(Issue))
    assert repo_count == 1
    assert issue_count == 2


@pytest.mark.asyncio
async def test_webhook_repo_registered_is_idempotent_on_duplicate_deliveries(
    async_client: AsyncClient,
    db_session,
    monkeypatch,
):
    """Repeated webhook deliveries upsert the existing repo and issues without duplicates."""
    monkeypatch.setenv("WEBHOOK_SECRET", "idempotent-secret")

    initial_issues = [
        {
            "id": 201,
            "number": 10,
            "title": "Initial title",
            "url": "https://github.com/stellar/idempotent-repo/issues/10",
            "complexity": "Medium",
            "points": 150,
            "is_claimed": False,
        }
    ]
    updated_issues = [
        {
            "id": 201,
            "number": 10,
            "title": "Updated title",
            "url": "https://github.com/stellar/idempotent-repo/issues/10",
            "complexity": "High",
            "points": 200,
            "is_claimed": True,
        }
    ]

    with (
        patch("app.routers.webhooks.fetch_issues_for_repo", new_callable=AsyncMock) as mock_issues,
        patch("app.routers.webhooks.verify_stellar_account", new_callable=AsyncMock) as mock_verify,
    ):
        mock_issues.return_value = initial_issues
        mock_verify.return_value = False

        r1 = await async_client.post(
            "/webhooks/repo-registered",
            json={"name": "stellar/idempotent-repo", "language": "Python", "multiplier": 1},
            headers={"X-Webhook-Token": "idempotent-secret"},
        )
        assert r1.status_code == 200
        first_id = r1.json()["repo"]["id"]

        # Fire webhook a second time with updated metadata and issue state
        mock_issues.return_value = updated_issues
        mock_verify.return_value = True

        r2 = await async_client.post(
            "/webhooks/repo-registered",
            json={
                "name": "stellar/idempotent-repo",
                "language": "Python",
                "multiplier": 3,
                "stellar_account": "G" + "B" * 55,
            },
            headers={"X-Webhook-Token": "idempotent-secret"},
        )
        assert r2.status_code == 200
        second_repo = r2.json()["repo"]
        assert second_repo["id"] == first_id
        assert second_repo["multiplier"] == 3
        assert second_repo["is_verified"] is True

    repo_count = await db_session.scalar(select(func.count()).select_from(Repo))
    issue_count = await db_session.scalar(select(func.count()).select_from(Issue))
    assert repo_count == 1
    assert issue_count == 1

    stored_issue = (await db_session.execute(select(Issue))).scalar_one()
    assert stored_issue.title == "Updated title"
    assert stored_issue.points == 200
    assert stored_issue.is_claimed is True


@pytest.mark.asyncio
async def test_standalone_repo_registration_worker():
    """run_standalone_repo_registration_worker executes cleanly with its own session."""
    with (
        patch("app.routers.webhooks.fetch_issues_for_repo", new_callable=AsyncMock) as mock_issues,
        patch("app.routers.webhooks.verify_stellar_account", new_callable=AsyncMock) as mock_verify,
    ):
        mock_issues.return_value = []
        mock_verify.return_value = True

        result = await run_standalone_repo_registration_worker(
            RepoRegisteredPayload(
                name="stellar/worker-repo",
                language="Go",
                multiplier=1,
                stellar_account="G" + "C" * 55,
            )
        )
        assert result["name"] == "stellar/worker-repo"
        assert result["is_verified"] is True
        assert result["health_score"] == 80
