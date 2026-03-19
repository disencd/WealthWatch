import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import dispose_engine, engine, get_db, init_db
from app.models import User
from app.routers import (
    account,
    auth,
    balances,
    budget,
    expenses,
    family,
    groups,
    investment,
    recurring,
    reports,
    rules,
    settlements,
    ui,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    settings = get_settings()
    logger.info("Starting WealthWatch (Python/FastAPI)")
    if settings.is_cloud_run:
        logger.info("Running on Cloud Run (service=%s)", settings.K_SERVICE)
    logger.info("Database: SQLite at %s", settings.SQLITE_DB_PATH)
    await init_db()
    logger.info("Database tables ready")
    yield
    # ── Shutdown ──
    await dispose_engine()
    logger.info("Database connections closed")


app = FastAPI(
    title="WealthWatch",
    description="Personal finance & expense tracking API",
    version="2.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
app.include_router(reports.router)
app.include_router(expenses.router)
app.include_router(groups.router)
app.include_router(balances.router)
app.include_router(settlements.router)

# Serve static assets (CSS, JS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# UI pages (Alpine.js + Jinja2 templates) — must be registered after API routers
app.include_router(ui.router)


@app.get("/api/v1/profile", tags=["auth"])
async def profile_shortcut(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == current_user.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "created_at": str(user.created_at),
        "updated_at": str(user.updated_at),
    }


@app.get("/health")
async def health():
    """Health check — verifies DB connectivity on Cloud Run."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return {"status": "degraded", "db": "unreachable"}
