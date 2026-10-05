from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates
from datetime import datetime
from app.routers import repos, issues, contributors, health
from app.scheduler.tasks import start_scheduler
import os

app = FastAPI(title="DripsLens")

app.include_router(repos.router)
app.include_router(issues.router)
app.include_router(contributors.router)
app.include_router(health.router)

templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.middleware("http")
async def add_last_updated_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Last-Updated"] = datetime.utcnow().isoformat()
    return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "DripsLens Dashboard"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    return "User-agent: *\nDisallow: /"

@app.get("/sitemap.xml", response_class=Response)
def get_sitemap():
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://dripslens.example.com/</loc>
    <lastmod>2026-10-01</lastmod>
  </url>
</urlset>"""
    return Response(content=sitemap_content, media_type="application/xml")
