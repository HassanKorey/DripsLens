import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.soroban import ContractEvent
from app.soroban.client import get_events

logger = logging.getLogger(__name__)


def parse_soroban_event(raw_event: dict[str, Any]) -> dict[str, Any] | None:
    """Extract normalized ContractEvent fields from a Soroban RPC event envelope."""
    if not isinstance(raw_event, dict):
        return None
    event_id = str(raw_event.get("id") or "").strip()
    if not event_id:
        return None
    contract_id = str(raw_event.get("contract_id") or raw_event.get("contractId") or "C_UNKNOWN")
    raw_topic = raw_event.get("topic")
    if isinstance(raw_topic, list):
        topic = "/".join(str(t) for t in raw_topic) if raw_topic else "unknown"
    else:
        topic = str(raw_topic or "unknown")
    payload = raw_event.get("data")
    if payload is None:
        payload = raw_event.get("value") if isinstance(raw_event.get("value"), dict) else {"value": raw_event.get("value")}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    ledger_seq = int(raw_event.get("ledger_sequence") or raw_event.get("ledger") or 0)
    return {
        "id": event_id,
        "contract_id": contract_id,
        "topic": topic,
        "data": payload,
        "ledger_sequence": ledger_seq,
    }


async def _persist_events(session: AsyncSession, parsed_events: list[dict[str, Any]]) -> int:
    inserted = 0
    seen_ids: set[str] = set()
    for item in parsed_events:
        eid = item["id"]
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        existing = await session.execute(select(ContractEvent).where(ContractEvent.id == eid))
        if existing.scalar_one_or_none() is not None:
            continue
        session.add(
            ContractEvent(
                id=eid,
                contract_id=item["contract_id"],
                topic=item["topic"],
                data=item["data"],
                ledger_sequence=item["ledger_sequence"],
            )
        )
        inserted += 1
    if inserted > 0:
        await session.commit()
    return inserted


async def ingest_soroban_events(
    start_ledger: int = 0,
    session: AsyncSession | None = None,
) -> int:
    """Poll Soroban RPC getEvents and persist new ContractEvent records without duplicates."""
    logger.info("Ingesting soroban events...")
    try:
        raw = await get_events(start_ledger)
        logger.info("Fetched events: %s", raw)
        if isinstance(raw, dict):
            raw_list = raw.get("events", [])
        elif isinstance(raw, list):
            raw_list = raw
        else:
            raw_list = []

        parsed = [p for e in raw_list if (p := parse_soroban_event(e)) is not None]
        if not parsed:
            return 0

        try:
            if session is not None:
                return await _persist_events(session, parsed)
            async with AsyncSessionLocal() as db_session:
                return await _persist_events(db_session, parsed)
        except Exception as db_err:
            logger.warning("Database persistence skipped or failed during event ingestion: %s", db_err)
            return 0
    except Exception as e:
        logger.error("Error ingesting events: %s", e)
        return 0
