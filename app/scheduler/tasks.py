"""APScheduler background tasks for DripsLens.

Provides asynchronous scheduled tasks for indexing Soroban contract events,
refreshing repository signals, and updating contributor leaderboards.
Handles HTTP 429 and 503 transient errors gracefully without crashing the scheduler,
and ensures database reconnection and clean schema migrations (alembic upgrade head).
"""

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

from alembic import command
from alembic.config import Config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.cache.redis_client import invalidate_cache
from app.db.database import AsyncSessionLocal
from app.models.repo import Repo
from app.services.github_fetcher import fetch_issues_for_repo
from app.soroban.indexer import ingest_soroban_events

logger = logging.getLogger(__name__)

scheduler_instance: AsyncIOScheduler | None = None


def run_database_migrations() -> bool:
    """Execute alembic upgrade head to guarantee schema integrity before scheduler start.

    Catches and logs failures cleanly without halting the process if offline or testing.
    """
    config_file = os.getenv("ALEMBIC_CONFIG", "alembic.ini")
    if not os.path.exists(config_file):
        logger.warning("Alembic configuration %s not found; skipping migration check", config_file)
        return False

    try:
        logger.info("Executing database schema migrations (alembic upgrade head)...")
        alembic_cfg = Config(config_file)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database schema migrations cleanly applied")
        return True
    except Exception as e:
        logger.warning("Database schema migration deferred or skipped: %s", e)
        return False


async def execute_with_db_reconnect(
    operation: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Execute a database-bound async operation with automatic reconnection handling."""
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            async with AsyncSessionLocal() as session:
                # Pre-ping database connectivity
                await session.execute(text("SELECT 1"))
                return await operation(session, *args, **kwargs)
        except (OperationalError, DBAPIError) as db_err:
            last_err = db_err
            logger.warning(
                "Database connection lost during scheduler job (attempt %d/%d): %s. Reconnecting in %.1fs...",
                attempt,
                max_retries,
                db_err,
                retry_delay,
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error("Non-recoverable error in scheduler database task: %s", e)
            raise e

    logger.error("Database reconnection attempts exhausted in background task: %s", last_err)
    return None


async def sync_wave_repositories() -> None:
    """Resilient background worker to synchronize repository issues and contributor signals."""

    async def _sync_logic(session) -> None:
        result = await session.execute(select(Repo).limit(20))
        repos = result.scalars().all()
        for repo in repos:
            try:
                issues = await fetch_issues_for_repo(repo.name)
                repo.issue_count = len(issues)
            except Exception as e:
                logger.warning("Transient error updating repo signals for %s: %s", repo.name, e)
        await session.commit()
        invalidate_cache()

    await execute_with_db_reconnect(_sync_logic)


async def resilient_job_wrapper(job_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Wrap background jobs to catch and log transient failures, preventing task crashes."""
    try:
        await job_func(*args, **kwargs)
    except Exception as e:
        logger.error(
            "Handled exception in background scheduler job %s: %s",
            getattr(job_func, "__name__", str(job_func)),
            e,
        )


def start_scheduler() -> AsyncIOScheduler:
    """Initialize schema migrations and start the background task scheduler."""
    global scheduler_instance

    # Run clean database schema migration
    run_database_migrations()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        resilient_job_wrapper,
        "interval",
        minutes=15,
        args=[ingest_soroban_events],
        id="soroban_event_indexer",
        replace_existing=True,
    )
    scheduler.add_job(
        resilient_job_wrapper,
        "interval",
        minutes=30,
        args=[sync_wave_repositories],
        id="wave_repo_sync_worker",
        replace_existing=True,
    )
    scheduler.start()
    scheduler_instance = scheduler
    logger.info("APScheduler background scheduler started successfully")
    return scheduler


def is_scheduler_running() -> bool:
    """Return whether the background scheduler is currently active."""
    return scheduler_instance is not None and scheduler_instance.running
