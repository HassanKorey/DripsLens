"""Shared pytest fixtures: isolated SQLite DB + FastAPI TestClient."""

import os
import sys
from pathlib import Path

import pytest

# Ensure app imports work when tests run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Isolated, per-test-run SQLite DB (set before app modules import settings)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_dripslens.db")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "")

from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Contributor, Issue, Repo  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    """Fresh schema per run (drops any stale DB from a previous run)."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    try:
        os.remove("./test_dripslens.db")
    except OSError:
        pass


@pytest.fixture()
def db_session():
    """A DB session that rolls back after each test."""
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture()
def client():
    """TestClient with the scheduler disabled."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seed_repos(db_session):
    """A handful of repos, issues and a contributor for endpoint tests."""
    # Wipe tables so every test starts from a clean slate
    db_session.query(Issue).delete()
    db_session.query(Contributor).delete()
    db_session.query(Repo).delete()
    db_session.commit()

    repos = []
    for i, (name, lang, mult, health, issues_n, verified) in enumerate(
        [
            ("stellar/soroban-examples", "Rust", 4.0, 88.0, 42, True),
            ("acme/cool-python-app", "Python", 2.0, 72.0, 15, False),
            ("acme/tiny-js-tool", "JavaScript", 1.0, 55.0, 3, None),
        ],
        start=1,
    ):
        owner, _, name_only = name.partition("/")
        r = Repo(
            id=i,
            full_name=name,
            owner=owner,
            name=name_only,
            language=lang,
            point_multiplier=mult,
            health_score=health,
            open_issues_count=issues_n,
            stellar_verified=verified,
            html_url=f"https://github.com/{name}",
            is_active=True,
        )
        db_session.add(r)
        repos.append(r)

    db_session.add(
        Issue(
            github_id=1001,
            repo_id=1,
            number=7,
            title="Fix flaky integration test",
            state="open",
            complexity="medium",
            points=150,
            claimed=False,
            labels=["medium", "bug"],
        )
    )
    db_session.add(
        Issue(
            github_id=1002,
            repo_id=1,
            number=9,
            title="Add /health endpoint",
            state="open",
            complexity="trivial",
            points=100,
            claimed=True,
            assignees=["octocat"],
            labels=["trivial"],
        )
    )
    db_session.add(
        Contributor(
            github_login="octocat",
            merged_prs=12,
            points=1800,
            repos_contributed=["stellar/soroban-examples"],
        )
    )
    db_session.commit()
    try:
        yield repos
    finally:
        db_session.rollback()
