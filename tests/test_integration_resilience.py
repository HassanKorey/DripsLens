"""Hermetic async mock integration tests for GitHub REST and Horizon API resilience.

Validates complete offline recovery, network latency simulation, connection dropouts,
malformed JSON payloads, and persistent 429/503 cascades with tenacity backoff.
Closes #40.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.services.github_fetcher import (
    GitHubClient,
    GitHubRateLimited,
)
from app.services.stellar_verifier import (
    StellarVerifier,
)
from tenacity import RetryError


@pytest.fixture
def offline_github_client():
    """Create an isolated GitHubClient configured for fast deterministic test runs."""
    client = GitHubClient(token="ghp_test_mock_token", base_url="https://api.github.com")
    return client


@pytest.fixture
def offline_stellar_verifier():
    """Create an isolated StellarVerifier targeting mocked horizon endpoints."""
    return StellarVerifier(horizon_url="https://horizon-testnet.stellar.org")


# ==============================================================================
# 1. Network Latency & Connection Dropout Simulation
# ==============================================================================

@pytest.mark.asyncio
async def test_github_connection_timeout_and_dropout_recovery(offline_github_client):
    """Test resilience when network drops connection or times out intermittently before succeeding."""
    mock_responses = [
        httpx.ConnectTimeout("Connection dropped to api.github.com"),
        httpx.ReadTimeout("Read timeout waiting for response payload"),
        MagicMock(
            status_code=200,
            json=lambda: [{"id": 1, "name": "drips-mock-repo", "stargazers_count": 42}],
            headers={"content-type": "application/json"},
            raise_for_status=lambda: None,
        ),
    ]

    with patch.object(httpx.AsyncClient, "send", AsyncMock(side_effect=mock_responses)):
        data = await offline_github_client.get("/repos/HassanKorey/DripsLens")
        assert isinstance(data, list)
        assert data[0]["name"] == "drips-mock-repo"
        assert data[0]["stargazers_count"] == 42


@pytest.mark.asyncio
async def test_stellar_network_latency_backoff(offline_stellar_verifier):
    """Test Horizon client behavior when high latency induces connection resets."""
    mock_responses = [
        httpx.ConnectError("Network is unreachable"),
        MagicMock(
            status_code=200,
            json=lambda: {"id": "00001", "account_id": "GBBD47IF6LWK7P7MDEVTEST", "sequence": "12345"},
            headers={"content-type": "application/json"},
            raise_for_status=lambda: None,
        ),
    ]

    with patch.object(httpx.AsyncClient, "send", AsyncMock(side_effect=mock_responses)):
        account = await offline_stellar_verifier.get_account("GBBD47IF6LWK7P7MDEVTEST")
        assert account["account_id"] == "GBBD47IF6LWK7P7MDEVTEST"
        assert account["sequence"] == "12345"


# ==============================================================================
# 2. Malformed JSON & Degraded Payloads
# ==============================================================================

@pytest.mark.asyncio
async def test_github_malformed_json_handling(offline_github_client):
    """Test that malformed JSON or corrupted gateway responses do not crash the pipeline."""
    bad_json_response = MagicMock(
        status_code=200,
        headers={"content-type": "application/json"},
    )
    bad_json_response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

    with (
        patch.object(httpx.AsyncClient, "send", AsyncMock(return_value=bad_json_response)),
        pytest.raises(ValueError, match="Expecting value"),
    ):
        await offline_github_client.get("/orgs/drips/repos")


@pytest.mark.asyncio
async def test_stellar_malformed_horizon_response(offline_stellar_verifier):
    """Test that unexpected non-JSON HTTP 200 payload triggers clean validation handling."""
    corrupted_resp = MagicMock(status_code=200)
    corrupted_resp.json.side_effect = ValueError("Invalid JSON token")

    with (
        patch.object(httpx.AsyncClient, "send", AsyncMock(return_value=corrupted_resp)),
        pytest.raises(ValueError),
    ):
        await offline_stellar_verifier.get_account("GANYTEST")


# ==============================================================================
# 3. Persistent 429 & 503 Cascades with Exponential Backoff
# ==============================================================================

@pytest.mark.asyncio
async def test_github_secondary_rate_limit_and_retry_after(offline_github_client):
    """Validate secondary abuse limits (403 with Retry-After) and recovery."""
    abuse_resp = MagicMock(
        status_code=403,
        headers={"retry-after": "1", "x-ratelimit-remaining": "0"},
        text="You have triggered an abuse detection mechanism.",
    )
    ok_resp = MagicMock(
        status_code=200,
        json=lambda: {"total_count": 1, "items": [{"id": 100}]},
        headers={"content-type": "application/json"},
        raise_for_status=lambda: None,
    )

    with patch.object(httpx.AsyncClient, "send", AsyncMock(side_effect=[abuse_resp, ok_resp])):
        res = await offline_github_client.get("/search/repositories?q=soroban")
        assert res["total_count"] == 1


@pytest.mark.asyncio
async def test_stellar_horizon_429_cascade_recovery(offline_stellar_verifier):
    """Verify that transient Horizon 429 rate limit resolves cleanly when backoff elapses."""
    horizon_429 = MagicMock(
        status_code=429,
        headers={"retry-after": "2"},
        text="Rate limit exceeded",
    )
    horizon_ok = MagicMock(
        status_code=200,
        json=lambda: {"successful": True, "ledger": 5420199},
        headers={"content-type": "application/json"},
        raise_for_status=lambda: None,
    )

    with patch.object(httpx.AsyncClient, "send", AsyncMock(side_effect=[horizon_429, horizon_ok])):
        status = await offline_stellar_verifier.verify_payment_transaction("tx_mock_hash_123")
        assert status["successful"] is True
        assert status["ledger"] == 5420199


@pytest.mark.asyncio
async def test_persistent_503_service_unavailable_cascade(offline_github_client):
    """Ensure persistent 503 upstream gateway outage raises RetryError within bounded retry ceiling."""
    unavailable_resp = MagicMock(
        status_code=503,
        headers={},
        text="Service Unavailable - Maintenance in progress",
    )

    with (
        patch.object(httpx.AsyncClient, "send", AsyncMock(return_value=unavailable_resp)),
        pytest.raises((GitHubRateLimited, RetryError, httpx.HTTPStatusError)),
    ):
        await offline_github_client.get("/rate_limit")
