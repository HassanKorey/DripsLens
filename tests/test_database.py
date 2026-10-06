import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soroban import ContractEvent, SorobanContract, StorageMetric


@pytest.mark.asyncio
async def test_database_crud(db_session: AsyncSession):
    # Create
    contract = SorobanContract(
        id="CONTRACT_123",
        wasm_id="wasm_abc",
        health_score=85,
        is_verified=True,
    )
    db_session.add(contract)
    await db_session.commit()

    # Read
    result = await db_session.execute(select(SorobanContract).where(SorobanContract.id == "CONTRACT_123"))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.health_score == 85
    assert fetched.is_verified is True

    # Related event
    event = ContractEvent(
        id="EVT_999",
        contract_id="CONTRACT_123",
        topic="init",
        data={"admin": "G..."},
        ledger_sequence=54321,
    )
    db_session.add(event)

    # Storage metric
    metric = StorageMetric(
        contract_id="CONTRACT_123",
        live_until_ledger_seq=100000,
    )
    db_session.add(metric)
    await db_session.commit()

    # Query event
    event_result = await db_session.execute(select(ContractEvent).where(ContractEvent.id == "EVT_999"))
    fetched_event = event_result.scalar_one_or_none()
    assert fetched_event is not None
    assert fetched_event.topic == "init"
    assert fetched_event.data == {"admin": "G..."}
