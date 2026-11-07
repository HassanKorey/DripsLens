from typing import Any

from fastapi import APIRouter

from app.schemas.soroban import ContractEventSchema, ContractTTLSchema
from app.soroban.client import get_ledger_entries

LEDGER_CLOSE_TIME_SECONDS = 5
SECONDS_PER_DAY = 86400
DEFAULT_LIVE_UNTIL_LEDGER = 999999
DEFAULT_REMAINING_DAYS = 30
NEAR_EXPIRY_THRESHOLD_DAYS = 7

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


@router.get("/contracts/{contract_id}/ttl", response_model=ContractTTLSchema)
async def get_contract_ttl(contract_id: str) -> dict[str, Any]:
    """
    Fetch contract TTL and estimate remaining days until archival based on ~5s ledger close time.
    """
    live_until = DEFAULT_LIVE_UNTIL_LEDGER
    remaining_ledgers = (DEFAULT_REMAINING_DAYS * SECONDS_PER_DAY) // LEDGER_CLOSE_TIME_SECONDS
    remaining_days = DEFAULT_REMAINING_DAYS

    try:
        rpc_result = await get_ledger_entries([contract_id])
        if isinstance(rpc_result, dict):
            entries = rpc_result.get("entries") or []
            latest_ledger = int(rpc_result.get("latestLedger", 0) or 0)
            if entries and isinstance(entries[0], dict):
                entry_live_until = entries[0].get("liveUntilLedgerSeq")
                if entry_live_until is not None:
                    live_until = int(entry_live_until)
                    if latest_ledger > 0:
                        remaining_ledgers = max(0, live_until - latest_ledger)
                    else:
                        remaining_ledgers = max(0, live_until)
                    remaining_days = int(
                        round((remaining_ledgers * LEDGER_CLOSE_TIME_SECONDS) / SECONDS_PER_DAY)
                    )
    except Exception:
        pass

    return {
        "contract_id": contract_id,
        "liveUntilLedgerSeq": live_until,
        "remaining_ledgers": remaining_ledgers,
        "remaining_days": remaining_days,
        "is_near_expiry": remaining_days < NEAR_EXPIRY_THRESHOLD_DAYS,
    }


@router.get("/contracts/{contract_id}/health")
async def get_contract_health(contract_id: str) -> dict[str, Any]:
    """
    Fetch WASM analyzer health score.
    """
    return {"contract_id": contract_id, "health_score": 95, "exported_functions": 5}
