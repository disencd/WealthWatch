import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(max_retries: int = 10) -> None:
    from app.models import (  # noqa: F401 – ensure all models are imported
        User, Family, FamilyMembership, Category, SubCategory, Budget,
        BudgetExpense, Group, GroupMember, Expense, Split, Settlement,
        Account, InvestmentHolding, NetWorthSnapshot, RecurringTransaction,
        AutoCategoryRule, Receipt,
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
