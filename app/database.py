import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.database_url

    # Ensure the parent directory exists for the SQLite file
    db_path = settings.SQLITE_DB_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    return create_async_engine(url, echo=False)


engine = _build_engine()


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    """Configure SQLite for production use."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def init_db(max_retries: int = 10) -> None:
    from app.models import (  # noqa: F401
        AutoCategoryRule,
        Budget,
        BudgetExpense,
        Category,
        Family,
        FamilyMembership,
        RecurringTransaction,
        SubCategory,
        User,
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
    await engine.dispose()
