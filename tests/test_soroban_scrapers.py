from unittest.mock import AsyncMock, patch

import pytest

from app.soroban.indexer import ingest_soroban_events


@pytest.mark.asyncio
async def test_ingest_soroban_events_success():
    with patch("app.soroban.indexer.get_events", new_callable=AsyncMock) as mock_get_events:
        mock_get_events.return_value = [{"id": "event_1"}]
        await ingest_soroban_events()
        mock_get_events.assert_awaited_once_with(0)


@pytest.mark.asyncio
async def test_ingest_soroban_events_handles_exception():
    with patch("app.soroban.indexer.get_events", new_callable=AsyncMock) as mock_get_events:
        mock_get_events.side_effect = RuntimeError("RPC connection failure")
        # Should not raise exception
        await ingest_soroban_events()
        mock_get_events.assert_awaited_once_with(0)
