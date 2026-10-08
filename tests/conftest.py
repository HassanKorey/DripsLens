"""Shared pytest fixtures: isolated async SQLite DB + TestClient / AsyncClient."""

import os
import sys
from pathlib import Path

# Ensure app imports work when tests run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Isolated, in-memory async SQLite DB (set before app modules import settings)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "")

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.db.database import AsyncSessionLocal, Base, engine, get_db
from app.main import app
from app.models.soroban import ContractEvent, SorobanContract, StorageMetric


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create fresh schema before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    """An AsyncSession for tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture()
def client():
    """Synchronous TestClient."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture()
async def async_client(db_session):
    """AsyncClient wired with test database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def seed_contracts(db_session):
    """Seed sample Soroban contract, event, and storage metric records."""
    contract = SorobanContract(
        id="CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
        wasm_id="wasm_abc123",
        health_score=95,
        is_verified=True,
    )
    event = ContractEvent(
        id="evt_1",
        contract_id="CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
        topic="transfer",
        data={"amount": 100},
        ledger_sequence=12345,
    )
    metric = StorageMetric(
        contract_id="CA3D5KRYM6CB7OWQ6TWYRR3Z4T7GNZLKERYNZGGA5CW",
        live_until_ledger_seq=999999,
    )
    db_session.add(contract)
    db_session.add(event)
    db_session.add(metric)
    await db_session.commit()
    return [contract]
