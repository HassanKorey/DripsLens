"""APScheduler background tasks for DripsLens.

Provides asynchronous scheduled tasks for indexing Soroban contract events,
refreshing repository signals, and updating contributor leaderboards.
Handles HTTP 429 and 503 transient errors gracefully without crashing the scheduler.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.soroban.indexer import ingest_soroban_events

logger = logging.getLogger(__name__)

scheduler_instance: AsyncIOScheduler | None = None


async def resilient_job_wrapper(job_func, *args, **kwargs):
    """Wrap background jobs to catch and log transient failures, preventing task crashes."""
    try:
        await job_func(*args, **kwargs)
    except Exception as e:
        logger.error("Handled exception in background scheduler job %s: %s", getattr(job_func, "__name__", str(job_func)), e)


def start_scheduler() -> AsyncIOScheduler:
    """Initialize and start the background task scheduler."""
    global scheduler_instance

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        resilient_job_wrapper,
        "interval",
        minutes=15,
        args=[ingest_soroban_events],
        id="soroban_event_indexer",
        replace_existing=True,
    )
    scheduler.start()
    scheduler_instance = scheduler
    logger.info("APScheduler background scheduler started successfully")
    return scheduler


def is_scheduler_running() -> bool:
    """Return whether the background scheduler is currently active."""
    return scheduler_instance is not None and scheduler_instance.running
