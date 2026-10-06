from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.scrapers.stellar import verify_stellar_account


@pytest.mark.asyncio
async def test_verify_stellar_account_valid():
    fake_response = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", "https://horizon-testnet.stellar.org/accounts/VALID_ACC"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_response
        is_valid = await verify_stellar_account("VALID_ACC")
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
