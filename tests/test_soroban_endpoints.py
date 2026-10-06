from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.routers.stream import event_generator
from app.scheduler.tasks import start_scheduler


@pytest.mark.asyncio
async def test_get_events_endpoint(async_client: AsyncClient):
    response = await async_client.get("/soroban/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["topic"] == "transfer"


@pytest.mark.asyncio
async def test_get_contract_metrics(async_client: AsyncClient):
    response = await async_client.get("/soroban/contracts/CA3D5KRYM6/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == "CA3D5KRYM6"
    assert "wasm_size_bytes" in data


@pytest.mark.asyncio
async def test_get_contract_ttl(async_client: AsyncClient):
    response = await async_client.get("/soroban/contracts/CA3D5KRYM6/ttl")
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == "CA3D5KRYM6"
    assert data["remaining_days"] == 30


@pytest.mark.asyncio
async def test_get_contract_health(async_client: AsyncClient):
    response = await async_client.get("/soroban/contracts/CA3D5KRYM6/health")
    assert response.status_code == 200
    data = response.json()
    assert data["contract_id"] == "CA3D5KRYM6"
    assert data["health_score"] == 95


@pytest.mark.asyncio
async def test_get_analytics_graph(async_client: AsyncClient):
    response = await async_client.get("/soroban/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_explorer_page(async_client: AsyncClient):
    response = await async_client.get("/soroban/explorer")
    assert response.status_code == 200
    assert "Soroban Event Explorer" in response.text


@pytest.mark.asyncio
async def test_stream_event_generator():
    gen = event_generator()
    with patch("asyncio.sleep", return_value=None):
        event = await anext(gen)
        assert "data" in event
        assert "evt_stream" in event["data"]


def test_start_scheduler():
    mock_scheduler = MagicMock()
    with patch("app.scheduler.tasks.AsyncIOScheduler", return_value=mock_scheduler):
        start_scheduler()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
