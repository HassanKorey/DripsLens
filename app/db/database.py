"""SQLAlchemy engine, session factory and declarative base."""

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

DB_CONNECT_MAX_ATTEMPTS = 5
DB_CONNECT_RETRY_DELAY_SECONDS = 2


class Base(DeclarativeBase):
    pass


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create tables (used for local dev / tests; prod uses Alembic)."""
    from app import models  # noqa: F401  (ensure models are imported)

    _ensure_database_ready()
    Base.metadata.create_all(bind=engine)


def _ensure_database_ready() -> None:
    """Block startup until the database answers a trivial query.

    Railway starts the DB and app containers nearly simultaneously, so the app
    often boots before Postgres accepts connections. Retry a lightweight
    connection a few times instead of crashing the container on first boot.
    """
    for attempt in range(1, DB_CONNECT_MAX_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            logger.warning(
                "Database not ready (attempt %d/%d): %s",
                attempt,
                DB_CONNECT_MAX_ATTEMPTS,
                exc,
            )
            if attempt == DB_CONNECT_MAX_ATTEMPTS:
                raise
            time.sleep(DB_CONNECT_RETRY_DELAY_SECONDS)
