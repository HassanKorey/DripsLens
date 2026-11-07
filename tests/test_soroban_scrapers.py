from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.soroban.indexer import ingest_soroban_events, parse_soroban_event


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
        count = await ingest_soroban_events()
        assert count == 0
        mock_get_events.assert_awaited_once_with(0)


@pytest.mark.asyncio
async def test_ingest_soroban_events_persists_and_deduplicates_records():
    raw_rpc_payload = {
        "events": [
            {
                "id": "evt_101",
                "contractId": "CA3D5KRYM6",
                "topic": ["transfer", "GABC"],
                "value": {"amount": 500},
                "ledger": 98765,
            },
            {
                "id": "evt_101",
                "contractId": "CA3D5KRYM6",
                "topic": ["transfer", "GABC"],
                "value": {"amount": 500},
                "ledger": 98765,
            },
        ]
    }
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    with patch("app.soroban.indexer.get_events", new_callable=AsyncMock) as mock_get_events:
        mock_get_events.return_value = raw_rpc_payload
        inserted = await ingest_soroban_events(start_ledger=98000, session=mock_session)
        assert inserted == 1
        mock_get_events.assert_awaited_once_with(98000)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()


def test_parse_soroban_event_normalizes_rpc_envelope():
    parsed = parse_soroban_event(
        {
            "id": "evt_202",
            "contractId": "CCONTRACT1",
            "topic": ["mint"],
            "value": 1000,
            "ledger": 1234,
        }
    )
    assert parsed == {
        "id": "evt_202",
        "contract_id": "CCONTRACT1",
        "topic": "mint",
        "data": {"value": 1000},
        "ledger_sequence": 1234,
    }
    assert parse_soroban_event({"id": ""}) is None
