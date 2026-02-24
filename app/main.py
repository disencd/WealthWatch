import logging
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db, init_db
from app.models import User
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

# Serve SvelteKit SPA
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.isdir(WEB_DIR):
    app.mount("/_app", StaticFiles(directory=os.path.join(WEB_DIR, "_app")), name="svelte-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Try to serve static file first
        file_path = os.path.join(WEB_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            import mimetypes
            mt, _ = mimetypes.guess_type(file_path)
            with open(file_path, "rb") as f:
                from fastapi.responses import Response
                return Response(content=f.read(), media_type=mt or "application/octet-stream")
        # Fall back to index.html for SPA client-side routing
        index_path = os.path.join(WEB_DIR, "index.html")
        with open(index_path) as f:
            return HTMLResponse(content=f.read())


@app.get("/api/v1/profile", tags=["auth"])
async def profile_shortcut(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == current_user.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id, "first_name": user.first_name, "last_name": user.last_name,
        "email": user.email, "phone": user.phone, "avatar": user.avatar,
        "created_at": str(user.created_at), "updated_at": str(user.updated_at),
    }


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
