from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.soroban.client import (
    SorobanRPCException,
    get_events,
    get_health,
    get_ledger_entries,
    rpc_request,
)


@pytest.mark.asyncio
async def test_rpc_request_success():
    fake_response = httpx.Response(
        status_code=200,
        json={"jsonrpc": "2.0", "id": 1, "result": {"status": "healthy"}},
        request=httpx.Request("POST", "https://soroban-testnet.stellar.org:443"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        result = await rpc_request("getHealth")
        assert result == {"status": "healthy"}
        mock_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_rpc_request_error_raises():
    fake_response = httpx.Response(
        status_code=200,
        json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid Request"}},
        request=httpx.Request("POST", "https://soroban-testnet.stellar.org:443"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        with pytest.raises(SorobanRPCException, match="RPC Error"):
            await rpc_request("invalidMethod")


@pytest.mark.asyncio
async def test_get_health():
    with patch("app.soroban.client.rpc_request", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = {"status": "healthy"}
        result = await get_health()
        assert result == {"status": "healthy"}
        mock_rpc.assert_awaited_once_with("getHealth")


@pytest.mark.asyncio
async def test_get_events():
    with patch("app.soroban.client.rpc_request", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = {"events": []}
        result = await get_events(1234)
        assert result == {"events": []}
        mock_rpc.assert_awaited_once_with("getEvents", {"startLedger": 1234})


@pytest.mark.asyncio
async def test_get_ledger_entries():
    with patch("app.soroban.client.rpc_request", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = {"entries": []}
        result = await get_ledger_entries(["key1", "key2"])
        assert result == {"entries": []}
        mock_rpc.assert_awaited_once_with("getLedgerEntries", {"keys": ["key1", "key2"]})


@pytest.mark.asyncio
async def test_rpc_request_retries_on_503_and_succeeds():
    request = httpx.Request("POST", "https://soroban-testnet.stellar.org:443")
    unavailable_response = httpx.Response(status_code=503, text="Service Unavailable", request=request)
    rate_limit_response = httpx.Response(status_code=429, text="Too Many Requests", request=request)
    ok_response = httpx.Response(
        status_code=200,
        json={"jsonrpc": "2.0", "id": 1, "result": {"status": "healthy"}},
        request=request,
    )
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_post.side_effect = [unavailable_response, rate_limit_response, ok_response]
        result = await rpc_request("getHealth")
        assert result == {"status": "healthy"}
        assert mock_post.await_count == 3


@pytest.mark.asyncio
async def test_rpc_request_exhausts_retries_on_503_and_raises_soroban_exception():
    request = httpx.Request("POST", "https://soroban-testnet.stellar.org:443")
    unavailable_response = httpx.Response(status_code=503, text="Service Unavailable", request=request)
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_post.return_value = unavailable_response
        with pytest.raises(SorobanRPCException, match="failed after 3 attempts"):
            await rpc_request("getHealth")
        assert mock_post.await_count == 3


@pytest.mark.asyncio
async def test_rpc_request_retries_on_connect_timeout_and_raises_soroban_exception():
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_post.side_effect = httpx.ConnectTimeout("Connection timed out")
        with pytest.raises(SorobanRPCException, match="failed after 3 attempts"):
            await rpc_request("getEvents", {"startLedger": 100})
        assert mock_post.await_count == 3
