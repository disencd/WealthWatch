"""Tests for the auth API endpoints (/api/v1/auth/*)."""

from tests.conftest import auth_header, register_user

# ── Registration ─────────────────────────────────────────────────


async def test_register_success(client):
    """Successful registration returns 201 with token and user data."""
    data = await register_user(client)
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["first_name"] == "Test"
    assert data["user"]["last_name"] == "User"
    assert data["user"]["id"] is not None


async def test_register_duplicate_email(client):
    """Registering with an existing email returns 409."""
    await register_user(client)
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Another",
            "last_name": "Person",
            "email": "test@example.com",
            "password": "different123",
        },
    )
    assert resp.status_code == 409


async def test_register_with_optional_phone(client):
    """Phone field is optional and returned in user payload."""
    data = await register_user(client, phone="555-1234")
    assert data["user"]["phone"] == "555-1234"


# ── Login ────────────────────────────────────────────────────────


async def test_login_success(client):
    """Login with valid credentials returns token and user."""
    await register_user(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "test@example.com"


async def test_login_wrong_password(client):
    """Login with incorrect password returns 401."""
    await register_user(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    """Login with an email that was never registered returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


# ── Profile (auth router: /api/v1/auth/profile) ─────────────────


async def test_profile_with_token(client):
    """GET /api/v1/auth/profile with valid token returns the user."""
    data = await register_user(client)
    token = data["access_token"]
    resp = await client.get(
        "/api/v1/auth/profile",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert body["first_name"] == "Test"


async def test_profile_without_token(client):
    """GET /api/v1/auth/profile without a token returns 401/403."""
    resp = await client.get("/api/v1/auth/profile")
    assert resp.status_code in (401, 403)
