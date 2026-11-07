import logging
from typing import Any

from app.soroban.client import get_events

logger = logging.getLogger(__name__)


async def ingest_soroban_events(start_ledger: int = 0) -> Any:
    logger.info("Ingesting soroban events...")
    # Polling Soroban RPC for new contract events
    try:
        events = await get_events(start_ledger)
        logger.info("Fetched events: %s", events)
        return events
    except Exception as e:
        logger.error("Error ingesting events: %s", e)
        return None
