from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import soroban, stream, analytics
from app.scheduler.tasks import start_scheduler

app = FastAPI(title="DripsLens Soroban Analytics")

app.include_router(soroban.router)
app.include_router(stream.router)
app.include_router(analytics.router)

templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def on_startup():
    start_scheduler()

@app.get("/soroban/explorer", response_class=HTMLResponse)
async def explorer(request: Request):
    return templates.TemplateResponse("soroban_explorer.html", {"request": request})
