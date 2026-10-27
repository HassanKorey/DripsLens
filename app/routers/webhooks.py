"""Webhook ingestion router and background worker for newly approved Wave repositories."""

import hmac
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import AsyncSessionLocal, get_db
from app.models.issue import Issue
from app.models.repo import Repo
from app.services.github_fetcher import fetch_issues_for_repo
from app.services.stellar_verifier import verify_stellar_account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class RepoRegisteredPayload(BaseModel):
    """Payload emitted when a repository is approved for a Drips Wave."""

    name: str = Field(..., min_length=3, description="Full GitHub repository name (owner/repo)")
    language: str | None = Field(default=None, description="Primary repository language")
    multiplier: int = Field(default=1, ge=1, le=10, description="Wave points multiplier")
    stellar_account: str | None = Field(
        default=None,
        description="Optional Stellar G... public key for Horizon verification",
    )


def get_expected_webhook_secret() -> str:
    """Resolve the active webhook secret token from environment or settings."""
    return (
        os.getenv("WEBHOOK_SECRET")
        or os.getenv("ADMIN_TOKEN")
        or settings.webhook_secret
        or "dripslens-webhook-secret"
    )


def verify_webhook_token(
    x_webhook_token: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    """Validate incoming webhook token header using constant-time comparison."""
    candidate = x_webhook_token or x_admin_token
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()

    expected = get_expected_webhook_secret()
    if not candidate or not hmac.compare_digest(candidate, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook authorization token",
        )
    return candidate


def compute_repo_health_score(issue_count: int, is_verified: bool, multiplier: int = 1) -> int:
    """Calculate repository health score bounded in [0, 100]."""
    base_score = 50
    verified_bonus = 30 if is_verified else 0
    issue_bonus = min(max(issue_count, 0) * 4, 15)
    multiplier_bonus = min(max(multiplier - 1, 0) * 5, 5)
    return min(base_score + verified_bonus + issue_bonus + multiplier_bonus, 100)


async def ingest_registered_repository(
    db: AsyncSession,
    payload: RepoRegisteredPayload,
) -> Repo:
    """Idempotently ingest a newly registered repository, fetch open issues, and verify Stellar account."""
    clean_name = payload.name.strip()

    issues = await fetch_issues_for_repo(clean_name)
    is_verified = (
        await verify_stellar_account(payload.stellar_account)
        if payload.stellar_account
        else False
    )
    issue_count = len(issues)
    health_score = compute_repo_health_score(
        issue_count=issue_count,
        is_verified=is_verified,
        multiplier=payload.multiplier,
    )

    stmt = select(Repo).where(Repo.name == clean_name)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo is None:
        repo = Repo(
            name=clean_name,
            language=payload.language,
            multiplier=payload.multiplier,
            issue_count=issue_count,
            last_activity=datetime.utcnow(),
            health_score=health_score,
            is_verified=is_verified,
        )
        db.add(repo)
        await db.flush()
    else:
        if payload.language is not None:
            repo.language = payload.language
        repo.multiplier = payload.multiplier
        repo.issue_count = issue_count
        repo.last_activity = datetime.utcnow()
        repo.health_score = health_score
        repo.is_verified = is_verified
        await db.flush()

    for item in issues:
        issue_url = item.get("url") or ""
        if not issue_url:
            continue
        existing_issue_res = await db.execute(select(Issue).where(Issue.url == issue_url))
        existing_issue = existing_issue_res.scalar_one_or_none()
        if existing_issue is None:
            db.add(
                Issue(
                    title=item.get("title", "Untitled Issue"),
                    url=issue_url,
                    repo_id=repo.id,
                    complexity=item.get("complexity", "Medium"),
                    points=int(item.get("points", 150)),
                    is_claimed=bool(item.get("is_claimed", False)),
                )
            )
        else:
            existing_issue.title = item.get("title", existing_issue.title)
            existing_issue.repo_id = repo.id
            existing_issue.complexity = item.get("complexity", existing_issue.complexity)
            existing_issue.points = int(item.get("points", existing_issue.points))
            existing_issue.is_claimed = bool(item.get("is_claimed", existing_issue.is_claimed))

    await db.commit()
    await db.refresh(repo)
    return repo


async def notify_repo_registered_worker(repo_name: str, health_score: int, is_verified: bool) -> None:
    """Background notification worker task executed after webhook ingestion."""
    logger.info(
        "Processed Wave repository registration for %s (health_score=%d, is_verified=%s)",
        repo_name,
        health_score,
        is_verified,
    )


async def run_standalone_repo_registration_worker(payload: RepoRegisteredPayload) -> dict[str, Any]:
    """Standalone async worker entry point using its own database session."""
    async with AsyncSessionLocal() as session:
        repo = await ingest_registered_repository(session, payload)
        return {
            "id": repo.id,
            "name": repo.name,
            "issue_count": repo.issue_count,
            "health_score": repo.health_score,
            "is_verified": repo.is_verified,
        }


@router.post("/repo-registered")
async def receive_repo_registered_webhook(
    payload: RepoRegisteredPayload,
    background_tasks: BackgroundTasks,
    _token: str = Depends(verify_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Receive newly approved Wave repository webhook and trigger idempotent indexing."""
    repo = await ingest_registered_repository(db, payload)
    background_tasks.add_task(
        notify_repo_registered_worker,
        repo.name,
        repo.health_score,
        repo.is_verified,
    )
    return {
        "status": "processed",
        "repo": {
            "id": repo.id,
            "name": repo.name,
            "language": repo.language,
            "multiplier": repo.multiplier,
            "issue_count": repo.issue_count,
            "health_score": repo.health_score,
            "is_verified": repo.is_verified,
        },
    }
