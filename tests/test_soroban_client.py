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
