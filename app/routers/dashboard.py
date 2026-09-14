"""Server-rendered dashboard (Jinja2) + meta endpoints (robots, sitemap)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func as safunc
from sqlalchemy.orm import Session

from app import __version__
from app.db.database import get_db
from app.models import Issue, Repo

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]):
    repos = (
        db.query(Repo)
        .filter(Repo.is_active.is_(True))
        .order_by(Repo.health_score.desc().nulls_last())
        .limit(50)
        .all()
    )
    issues = (
        db.query(Issue)
        .filter(Issue.state == "open", Issue.claimed.is_(False))
        .order_by(Issue.points.desc().nulls_last())
        .limit(25)
        .all()
    )
    stats = {
        "repos": db.query(safunc.count(Repo.id)).scalar() or 0,
        "open_issues": db.query(safunc.count(Issue.id)).filter(Issue.state == "open").scalar() or 0,
        "verified": db.query(safunc.count(Repo.id)).filter(Repo.stellar_verified.is_(True)).scalar() or 0,
    }
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"repos": repos, "issues": issues, "stats": stats, "version": __version__},
    )


@router.get("/repos/view/{repo_id}", response_class=HTMLResponse)
def repo_page(request: Request, repo_id: int, db: Annotated[Session, Depends(get_db)]):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if repo is None:
        return templates.TemplateResponse(request, "404.html", {"path": f"/repos/view/{repo_id}"}, status_code=404)
    issues = (
        db.query(Issue)
        .filter(Issue.repo_id == repo_id, Issue.state == "open")
        .order_by(Issue.points.desc().nulls_last())
        .all()
    )
    return templates.TemplateResponse(
        request, "repo.html", {"repo": repo, "issues": issues, "version": __version__}
    )


@router.get("/robots.txt")
def robots_txt():
    return HTMLResponse(
        content="User-agent: *\nAllow: /\nSitemap: /sitemap.xml", media_type="text/plain"
    )


@router.get("/sitemap.xml")
def sitemap_xml(request: Request):
    base = str(request.base_url).rstrip("/")
    entries = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in ("/",):
        entries.append(f"<url><loc>{base}{path}</loc></url>")
    entries.append("</urlset>")
    return HTMLResponse(content="\n".join(entries), media_type="application/xml")
