"""Shared fixtures for WealthWatch tests.

Provides an async SQLite-backed test DB, a FastAPI test client,
and helper functions to register users and get auth tokens.
"""

import os

# Set test env vars BEFORE any app imports
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["SQLITE_DB_PATH"] = ":memory:"

# Ensure web/_app directory exists so FastAPI StaticFiles mount doesn't fail
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "web", "_app"), exist_ok=True)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

# In-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DB_URL, echo=False)
async_session_test = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with async_session_test() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db():
    """Direct DB session for seeding test data."""
    async with async_session_test() as session:
        yield session


# ── Helper functions ──────────────────────────────────────────────


async def register_user(client: AsyncClient, **kwargs) -> dict:
    """Register a user and return the response JSON (access_token + user)."""
    defaults = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "password123",
    }
    defaults.update(kwargs)
    resp = await client.post("/api/v1/auth/register", json=defaults)
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_header(token: str) -> dict:
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
