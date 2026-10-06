import logging

from app.soroban.client import get_events

logger = logging.getLogger(__name__)


async def ingest_soroban_events() -> None:
    logger.info("Ingesting soroban events...")
    # Polling Soroban RPC for new contract events
    try:
        events = await get_events(0)
        logger.info("Fetched events: %s", events)
        # Store to DB logic would go here
    except Exception as e:
        logger.error("Error ingesting events: %s", e)
