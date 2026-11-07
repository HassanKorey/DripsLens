from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.scrapers.stellar import check_stellar_account, verify_stellar_account
from app.scrapers.stellar_verifier import StellarVerifier, query_horizon_rpc

VALID_PUBKEY = "G" + "A" * 55


@pytest.mark.asyncio
async def test_verify_stellar_account_valid():
    fake_response = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", f"https://horizon-testnet.stellar.org/accounts/{VALID_PUBKEY}"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        is_valid = await verify_stellar_account(VALID_PUBKEY)
        assert is_valid is True


@pytest.mark.asyncio
async def test_verify_stellar_account_invalid():
    fake_response = httpx.Response(
        status_code=404,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/INVALID_ACC"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        is_valid = await verify_stellar_account("INVALID_ACC")
        assert is_valid is False


@pytest.mark.asyncio
async def test_verify_stellar_account_handles_429_and_503():
    req = httpx.Request("GET", f"https://horizon-testnet.stellar.org/accounts/{VALID_PUBKEY}")
    resp_429 = httpx.Response(status_code=429, headers={"Retry-After": "1"}, request=req)
    resp_503 = httpx.Response(status_code=503, request=req)

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = resp_429
        assert await verify_stellar_account(VALID_PUBKEY) is False

        mock_get.return_value = resp_503
        assert await verify_stellar_account(VALID_PUBKEY) is False


@pytest.mark.asyncio
async def test_check_stellar_account_200_404_429_503_and_connect_error():
    req = httpx.Request("GET", f"https://horizon-testnet.stellar.org/accounts/{VALID_PUBKEY}")
    resp_200 = httpx.Response(
        status_code=200,
        json={"balances": [{"asset_type": "native", "balance": "250.50"}]},
        request=req,
    )
    resp_404 = httpx.Response(status_code=404, request=req)
    resp_429 = httpx.Response(status_code=429, headers={"Retry-After": "1"}, request=req)
    resp_503 = httpx.Response(status_code=503, request=req)

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = resp_200
        res_ok = await check_stellar_account(VALID_PUBKEY)
        assert res_ok["status"] == "verified"
        assert res_ok["native_balance"] == "250.50"
        assert "250.50 XLM" in res_ok["detail"]

        mock_get.return_value = resp_404
        res_404 = await check_stellar_account(VALID_PUBKEY)
        assert res_404["status"] == "unverified"

        mock_get.return_value = resp_429
        res_429 = await check_stellar_account(VALID_PUBKEY)
        assert res_429["status"] == "unknown"
        assert "429" in res_429["detail"]

        mock_get.return_value = resp_503
        res_503 = await check_stellar_account(VALID_PUBKEY)
        assert res_503["status"] == "unknown"
        assert "503" in res_503["detail"]

        mock_get.side_effect = httpx.ConnectError("boom")
        res_err = await check_stellar_account(VALID_PUBKEY)
        assert res_err["status"] == "unknown"


@pytest.mark.asyncio
async def test_query_horizon_rpc_recovery_and_failure():
    req = httpx.Request("GET", "https://horizon-testnet.stellar.org/ledgers")
    resp_503 = httpx.Response(status_code=503, request=req)
    resp_200 = httpx.Response(status_code=200, json={"_embedded": {"records": []}}, request=req)

    verifier = StellarVerifier(max_retries=2)
    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.side_effect = [resp_503, resp_200]
        data = await verifier.query_horizon_rpc("ledgers")
        assert "_embedded" in data

        mock_get.side_effect = None
        mock_get.return_value = resp_503
        err_data = await query_horizon_rpc("ledgers")
        assert err_data["error"] == "service_unavailable"
