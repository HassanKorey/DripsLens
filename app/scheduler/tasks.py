from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.soroban.indexer import ingest_soroban_events


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ingest_soroban_events, "interval", minutes=15)
    scheduler.start()
