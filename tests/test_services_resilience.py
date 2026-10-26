"""Tests for services resilience: tenacity exponential backoff and 429/503 handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.scheduler.tasks import resilient_job_wrapper
from app.services.github_fetcher import (
    GitHubClient,
    GitHubRateLimited,
)
from app.services.stellar_verifier import (
    StellarVerifier,
)


@pytest.mark.asyncio
async def test_stellar_verifier_200_success():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org")
    fake_response = httpx.Response(
        status_code=200,
        json={"balances": [{"asset_type": "native", "balance": "150.50"}]},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is True

        details = await verifier.check_account_details("GA" + "A" * 54)
        assert details["status"] == "verified"
        assert details["native_balance"] == "150.50"


@pytest.mark.asyncio
async def test_stellar_verifier_404_unverified():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org")
    fake_response = httpx.Response(
        status_code=404,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is False

        details = await verifier.check_account_details("GA" + "A" * 54)
        assert details["status"] == "unverified"


@pytest.mark.asyncio
async def test_stellar_verifier_429_backoff_and_recovery():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org", max_retries=3)
    resp_429 = httpx.Response(
        status_code=429,
        headers={"Retry-After": "1"},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"balances": [{"asset_type": "native", "balance": "500.00"}]},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # First call 429, second call 200
        mock_get.side_effect = [resp_429, resp_200]
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is True
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_stellar_verifier_503_backoff_and_recovery():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org", max_retries=3)
    resp_503 = httpx.Response(
        status_code=503,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"balances": []},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [resp_503, resp_200]
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is True
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_stellar_verifier_persistent_429_does_not_crash():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org", max_retries=2)
    resp_429 = httpx.Response(
        status_code=429,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/GA" + "A" * 54),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_429
        # Should not raise exception to caller
        result = await verifier.verify_account("GA" + "A" * 54)
        assert result is False

        details = await verifier.check_account_details("GA" + "A" * 54)
        assert details["status"] == "unknown"


@pytest.mark.asyncio
async def test_github_client_primary_rate_limit_exceeded():
    client = GitHubClient(token="fake_token", max_retries=2)
    resp_403 = httpx.Response(
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1730000000"},
        request=httpx.Request("GET", "https://api.github.com/repos/HassanKorey/DripsLens"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_403
        with pytest.raises(GitHubRateLimited):
            await client.get_json("repos/HassanKorey/DripsLens")


@pytest.mark.asyncio
async def test_github_client_secondary_limit_retry():
    client = GitHubClient(token="fake_token", max_retries=3)
    resp_secondary = httpx.Response(
        status_code=403,
        headers={"Retry-After": "1"},
        request=httpx.Request("GET", "https://api.github.com/repos/HassanKorey/DripsLens/issues"),
    )
    resp_200 = httpx.Response(
        status_code=200,
        json=[{"id": 1, "number": 10, "title": "Test Issue", "state": "open"}],
        request=httpx.Request("GET", "https://api.github.com/repos/HassanKorey/DripsLens/issues"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        with patch("asyncio.sleep", return_value=None):
            mock_get.side_effect = [resp_secondary, resp_200]
            data = await client.get_json("repos/HassanKorey/DripsLens/issues")
            assert len(data) == 1
            assert data[0]["number"] == 10


@pytest.mark.asyncio
async def test_github_fetch_open_issues_filters_prs():
    client = GitHubClient(token="fake_token")
    mock_issues = [
        {"id": 1, "title": "Good first issue", "labels": [{"name": "trivial"}], "assignees": []},
        {"id": 2, "title": "Pull Request", "pull_request": {"url": "https://..."}, "labels": []},
        {"id": 3, "title": "Architecture Redesign", "labels": [{"name": "high"}], "assignees": [{"login": "dev"}]},
    ]

    with patch.object(client, "get_json", new_callable=AsyncMock) as mock_get_json:
        mock_get_json.return_value = mock_issues
        issues = await client.fetch_open_issues("HassanKorey/DripsLens")
        assert len(issues) == 2
        assert issues[0]["complexity"] == "Trivial"
        assert issues[0]["points"] == 100
        assert issues[0]["is_claimed"] is False
        assert issues[1]["complexity"] == "High"
        assert issues[1]["points"] == 200
        assert issues[1]["is_claimed"] is True


@pytest.mark.asyncio
async def test_resilient_job_wrapper_catches_errors():
    async def failing_job():
        raise RuntimeError("Transient network outage")

    # Should not raise exception
    await resilient_job_wrapper(failing_job)


@pytest.mark.asyncio
async def test_horizon_rpc_query_success_and_rate_limit_retry():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org", max_retries=3)
    resp_429 = httpx.Response(
        status_code=429,
        headers={"Retry-After": "1"},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/fee_stats"),
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"fee_charged": {"mode": "100"}},
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/fee_stats"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [resp_429, resp_200]
        data = await verifier.query_horizon_rpc("fee_stats")
        assert "fee_charged" in data
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_horizon_rpc_query_503_service_unavailable():
    verifier = StellarVerifier(horizon_url="https://horizon-testnet.stellar.org", max_retries=1)
    resp_503 = httpx.Response(
        status_code=503,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/ledgers"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp_503
        data = await verifier.query_horizon_rpc("ledgers")
        assert data["error"] == "service_unavailable"


def test_run_database_migrations_clean_execution():
    from app.scheduler.tasks import run_database_migrations
    # Run with existing alembic configuration
    result = run_database_migrations()
    assert result is True


@pytest.mark.asyncio
async def test_execute_with_db_reconnect_recovers():
    from sqlalchemy.exc import OperationalError

    from app.scheduler.tasks import execute_with_db_reconnect

    call_count = 0

    async def flaky_task(session):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OperationalError("server closed the connection unexpectedly", None, None)
        return "success"

    with patch("asyncio.sleep", return_value=None):
        result = await execute_with_db_reconnect(flaky_task, max_retries=3, retry_delay=0.01)
        assert result == "success"
        assert call_count == 2
