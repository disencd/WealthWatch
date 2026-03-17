import asyncio
import logging
import ssl
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.database_url

    # SSL for Neon / Supabase (sslmode=require in DATABASE_URL)
    connect_args: dict = {}
    if settings.requires_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # Neon/Supabase use trusted CAs, but asyncpg needs this
        connect_args["ssl"] = ctx

    # Cloud Run or serverless DB: smaller pool, aggressive recycle
    if settings.is_cloud_run or settings.DATABASE_URL:
        return create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
            pool_recycle=300,   # Neon closes idle connections aggressively
            pool_timeout=30,
            connect_args=connect_args,
        )

    # Local / docker-compose: default pool settings
    return create_async_engine(url, echo=False, pool_pre_ping=True, connect_args=connect_args)


engine = _build_engine()
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def init_db(max_retries: int = 10) -> None:
    from app.models import (  # noqa: F401 – ensure all models are imported
        User, Family, FamilyMembership, Category, SubCategory, Budget,
        BudgetExpense, Group, GroupMember, Expense, Split, Settlement,
        Account, InvestmentHolding, NetWorthSnapshot, RecurringTransaction,
        AutoCategoryRule,
    )

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            return
        except Exception as exc:
            logger.warning("DB init attempt %d/%d failed: %s", attempt, max_retries, exc)
            await asyncio.sleep(attempt * 2)

    raise RuntimeError(f"Failed to initialise database after {max_retries} attempts")


async def dispose_engine() -> None:
    """Cleanly close all pooled connections (called on shutdown)."""
    await engine.dispose()
