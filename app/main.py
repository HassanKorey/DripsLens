"""DripsLens FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.cache import redis_client as cache
from app.config import settings
from app.db.database import create_all
from app.routers import contributors, dashboard, health, issues, repos
from app.scheduler.tasks import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lightweight startup: create tables if missing (prod path is Alembic)
    create_all()
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()
    await cache.close_redis()


app = FastAPI(
    title=settings.app_name,
    description="Aggregates, caches and serves data about Drips Wave (Stellar) approved repositories.",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(repos.router)
app.include_router(issues.router)
app.include_router(contributors.router)
app.include_router(dashboard.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
