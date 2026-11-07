"""DripsLens FastAPI Application.

Real-time analytics engine and search platform that makes the Drips Wave ecosystem
trackable, searchable, and verifiable.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contributor import Contributor
from app.models.issue import Issue
from app.models.repo import Repo
from app.routers import analytics, contributors, health, issues, repos, soroban, stream
from app.scheduler.tasks import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to start and stop background schedulers."""
    scheduler = start_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="DripsLens",
    description=(
        "DripsLens is a real-time analytics engine and search platform that makes the "
        "Drips Wave ecosystem trackable, searchable, and verifiable."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Core Drips Wave Ecosystem & Monitoring Routers
app.include_router(health.router)
app.include_router(repos.router)
app.include_router(issues.router)
app.include_router(contributors.router)

# Soroban Smart Contract & Stellar Analytics Routers
app.include_router(soroban.router)
app.include_router(stream.router)
app.include_router(analytics.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request) -> HTMLResponse:
    """Root landing redirect or dashboard view."""
    return templates.TemplateResponse(request, "soroban_explorer.html")


@app.get("/soroban/explorer", response_class=HTMLResponse, include_in_schema=False)
async def explorer(request: Request) -> HTMLResponse:
    """Interactive Soroban explorer dashboard."""
    return templates.TemplateResponse(request, "soroban_explorer.html")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_view(request: Request, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """Interactive contributor growth and points distribution dashboard."""
    repo_rows = (await db.execute(select(Repo).limit(50))).scalars().all()
    issue_rows = (await db.execute(select(Issue).limit(100))).scalars().all()
    contrib_rows = (
        await db.execute(select(Contributor).order_by(Contributor.points_earned.desc()).limit(10))
    ).scalars().all()

    tier_counts = {"Trivial": 0, "Medium": 0, "High": 0}
    for iss in issue_rows:
        if iss.complexity in tier_counts:
            tier_counts[iss.complexity] += 1

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "DripsLens Ecosystem Dashboard",
            "repos": repo_rows,
            "issues": issue_rows,
            "contributors": contrib_rows,
            "tier_counts": tier_counts,
        },
    )

