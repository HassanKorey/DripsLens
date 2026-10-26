"""Integration tests for core API routes: /health, /repos, /issues, /leaderboard.

Verifies route responses, query filtering, pagination, and offline fallback modes.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient

from app.services.github_fetcher import GitHubClient
from app.services.stellar_verifier import StellarVerifier


@pytest.mark.asyncio
async def test_health_endpoint_contract(async_client: AsyncClient):
    """GET /health returns 200 with ok status, uptime, timestamp, database, and scheduler status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["app"] == "DripsLens"
    assert data["version"] == "2.0.0"
    assert isinstance(data["uptime_seconds"], float)
    assert data["uptime_seconds"] >= 0.0

    # Ensure ISO-8601 parsable
    ts = datetime.fromisoformat(data["timestamp"])
    assert ts is not None

    # Assert database connection and scheduler status are reported
    assert data["database"] == "connected"
    assert data["scheduler"] in ("running", "idle")


@pytest.mark.asyncio
async def test_repos_endpoint(async_client: AsyncClient, seed_drips_data):
    """GET /repos returns seeded repositories and supports filtering."""
    # Test unfiltered listing
    response = await async_client.get("/repos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "HassanKorey/DripsLens"

    # Test filtering by language
    py_resp = await async_client.get("/repos?language=Python")
    assert py_resp.status_code == 200
    py_data = py_resp.json()
    assert len(py_data) == 1
    assert py_data[0]["language"] == "Python"

    # Test filtering by multiplier
    mult_resp = await async_client.get("/repos?multiplier=1")
    assert mult_resp.status_code == 200
    mult_data = mult_resp.json()
    assert len(mult_data) == 1
    assert mult_data[0]["multiplier"] == 1


@pytest.mark.asyncio
async def test_repo_health_endpoint(async_client: AsyncClient, seed_drips_data):
    """GET /repos/{id}/health returns repository health metrics."""
    response = await async_client.get("/repos/1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["repo_id"] == 1
    assert data["health_score"] == 98
    assert data["is_verified"] is True

    # Non-existent repo returns 404
    not_found_resp = await async_client.get("/repos/999/health")
    assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_issues_endpoint(async_client: AsyncClient, seed_drips_data):
    """GET /issues returns seeded issues and supports complexity and claim filters."""
    response = await async_client.get("/issues")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    # Filter by complexity
    trivial_resp = await async_client.get("/issues?complexity=Trivial")
    assert trivial_resp.status_code == 200
    trivial_data = trivial_resp.json()
    assert len(trivial_data) == 1
    assert trivial_data[0]["complexity"] == "Trivial"
    assert trivial_data[0]["points"] == 100

    # Filter by is_claimed
    claimed_resp = await async_client.get("/issues?is_claimed=true")
    assert claimed_resp.status_code == 200
    claimed_data = claimed_resp.json()
    assert len(claimed_data) == 1
    assert claimed_data[0]["is_claimed"] is True


@pytest.mark.asyncio
async def test_repos_pagination_and_empty_filters(async_client: AsyncClient, seed_drips_data):
    """GET /repos verifies pagination parameters (skip, limit) and empty filter matches."""
    # Test pagination
    paginated_resp = await async_client.get("/repos?skip=1&limit=1")
    assert paginated_resp.status_code == 200
    p_data = paginated_resp.json()
    assert len(p_data) == 1
    assert p_data[0]["name"] == "stellar/soroban-example-dapp"

    # Test non-matching filter
    empty_resp = await async_client.get("/repos?language=Haskell")
    assert empty_resp.status_code == 200
    assert empty_resp.json() == []


@pytest.mark.asyncio
async def test_issues_pagination_and_unclaimed_filter(async_client: AsyncClient, seed_drips_data):
    """GET /issues verifies pagination and is_claimed=false filtering."""
    unclaimed_resp = await async_client.get("/issues?is_claimed=false")
    assert unclaimed_resp.status_code == 200
    u_data = unclaimed_resp.json()
    assert len(u_data) == 1
    assert u_data[0]["is_claimed"] is False
    assert u_data[0]["points"] == 100

    # Test pagination skip
    skip_resp = await async_client.get("/issues?skip=1&limit=1")
    assert skip_resp.status_code == 200
    s_data = skip_resp.json()
    assert len(s_data) == 1
    assert s_data[0]["id"] == 2


@pytest.mark.asyncio
async def test_leaderboard_pagination(async_client: AsyncClient, seed_drips_data):
    """GET /leaderboard verifies limit query parameter."""
    resp = await async_client.get("/leaderboard?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["github_username"] == "HassanKorey"


@pytest.mark.asyncio
async def test_health_endpoint_db_disconnected_handling(async_client: AsyncClient):
    """GET /health reports database: disconnected when DB connection throws error."""
    with patch("app.routers.health.AsyncSession.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = Exception("DB Connection Refused")
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "disconnected"


@pytest.mark.asyncio
async def test_leaderboard_endpoint(async_client: AsyncClient, seed_drips_data):
    """GET /leaderboard and /contributors/top return ranked contributors."""
    response = await async_client.get("/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # First place should have highest points
    assert data[0]["github_username"] == "HassanKorey"
    assert data[0]["points_earned"] == 2700
    assert data[1]["github_username"] == "HirthikBalaji"

    # Alias /contributors/top
    alias_resp = await async_client.get("/contributors/top")
    assert alias_resp.status_code == 200
    alias_data = alias_resp.json()
    assert alias_data == data


@pytest.mark.asyncio
async def test_offline_fallback_mode_horizon_network_down():
    """Verify system degrades gracefully when Stellar Horizon network is unreachable."""
    verifier = StellarVerifier(horizon_url="https://horizon-down.invalid", max_retries=1)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Network unreachable")
        # Should not crash, returns False
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is False

        # Detail check reports status unknown
        details = await verifier.check_account_details("GA" + "A" * 54)
        assert details["status"] == "unknown"


@pytest.mark.asyncio
async def test_offline_fallback_mode_github_network_down():
    """Verify GitHub client handles offline/unreachable network safely."""
    client = GitHubClient(token="", base_url="https://api.github-down.invalid", max_retries=1)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("DNS lookup failed")
        # Should catch error and return empty list rather than crashing
        issues = await client.fetch_open_issues("HassanKorey/DripsLens")
        assert issues == []


@pytest.mark.asyncio
async def test_offline_fallback_mode_stellar_503_and_429_graceful():
    """Verify StellarVerifier gracefully reports false without crashing when 503 or 429 occur."""
    verifier = StellarVerifier(horizon_url="https://horizon-mock.stellar.org", max_retries=1)

    resp_503 = httpx.Response(status_code=503, request=httpx.Request("GET", "https://horizon-mock.stellar.org/accounts/GA"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_503
        verified = await verifier.verify_account("GA" + "A" * 54)
        assert verified is False

    resp_429 = httpx.Response(status_code=429, headers={"Retry-After": "10"}, request=httpx.Request("GET", "https://horizon-mock.stellar.org/accounts/GA"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_429
        verified = await verifier.verify_account("GA" + "A" * 54)
        assert verified is False


@pytest.mark.asyncio
async def test_offline_fallback_mode_github_rate_limit_graceful():
    """Verify fetch_issues_for_repo returns empty list on primary rate limit exhaustion."""
    from app.services.github_fetcher import fetch_issues_for_repo

    resp_403 = httpx.Response(
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1730000000"},
        request=httpx.Request("GET", "https://api.github.com/repos/HassanKorey/DripsLens/issues"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_403
        issues = await fetch_issues_for_repo("HassanKorey/DripsLens")
        assert issues == []
