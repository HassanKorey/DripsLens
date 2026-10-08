from typing import Any

from fastapi import APIRouter

from app.schemas.soroban import ContractEventSchema

router = APIRouter(prefix="/soroban", tags=["Soroban Analytics"])


@router.get("/events", response_model=list[ContractEventSchema])
async def get_soroban_events() -> list[dict[str, Any]]:
    """
    Fetch indexed Soroban events.
    """
    return [
        {
            "id": "evt_1",
            "contract_id": "C...",
            "topic": "transfer",
            "data": {"amount": 100},
            "ledger_sequence": 12345,
        }
    ]


@router.get("/contracts/{contract_id}/metrics")
async def get_contract_metrics(contract_id: str) -> dict[str, Any]:
    """
    Fetch smart contract metrics.
    """
    return {"contract_id": contract_id, "wasm_size_bytes": 1024, "invocation_count": 50}


@router.get("/contracts/{contract_id}/ttl")
async def get_contract_ttl(contract_id: str) -> dict[str, Any]:
    """
    Fetch contract TTL.
    """
    return {"contract_id": contract_id, "liveUntilLedgerSeq": 999999, "remaining_days": 30}


@router.get("/contracts/{contract_id}/health")
async def get_contract_health(contract_id: str) -> dict[str, Any]:
    """
    Fetch WASM analyzer health score.
    """
    return {"contract_id": contract_id, "health_score": 95, "exported_functions": 5}
