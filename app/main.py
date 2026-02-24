import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import get_settings
from app.database import init_db
from app.routers import (
    auth, family, budget, account, investment,
    recurring, rules, receipts, reports,
    expenses, groups, balances, settlements,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WealthWatch",
    description="Personal finance & expense tracking API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(family.router)
app.include_router(budget.router)
app.include_router(account.router)
app.include_router(investment.router)
app.include_router(recurring.router)
app.include_router(rules.router)
app.include_router(receipts.router)
app.include_router(reports.router)
app.include_router(expenses.router)
app.include_router(groups.router)
app.include_router(balances.router)
app.include_router(settlements.router)

# Serve static web UI
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.isdir(WEB_DIR):
    templates = Jinja2Templates(directory=WEB_DIR)

    @app.get("/app.js", include_in_schema=False)
    async def app_js():
        path = os.path.join(WEB_DIR, "app.js")
        with open(path) as f:
            return HTMLResponse(content=f.read(), media_type="application/javascript")

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    settings = get_settings()
    logger.info("Starting WealthWatch (Python/FastAPI)")
    logger.info("Database: %s@%s:%s/%s", settings.DB_USER, settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)
    await init_db()
    logger.info("Database tables ready")
    logger.info("Web UI available at http://localhost:%s", settings.PORT)
