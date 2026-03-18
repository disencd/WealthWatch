"""Tests for the Google OAuth endpoint (/api/v1/auth/google)."""

from unittest.mock import patch

from tests.conftest import auth_header, register_user

MOCK_GOOGLE_IDINFO = {
    "sub": "google-uid-123",
    "email": "googleuser@gmail.com",
    "given_name": "Google",
    "family_name": "User",
    "picture": "https://lh3.googleusercontent.com/photo.jpg",
}


# ── Google Auth disabled ─────────────────────────────────────────


async def test_google_auth_not_configured(client):
    """Returns 501 when GOOGLE_CLIENT_ID is not set."""
    resp = await client.post("/api/v1/auth/google", json={"credential": "fake-token"})
    assert resp.status_code == 501


# ── Google Auth enabled (mocked) ─────────────────────────────────


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_invalid_token(mock_verify, mock_settings):
    """Returns 401 when Google token verification fails."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_verify.side_effect = ValueError("Invalid token")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/google", json={"credential": "bad-token"})
    assert resp.status_code == 401


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_new_user(mock_verify, mock_settings, client):
    """First-time Google sign-in creates a new user with family."""
    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_settings.return_value.JWT_SECRET = "test-secret-key"
    mock_settings.return_value.JWT_EXPIRES_IN = "168h"
    mock_settings.return_value.JWT_ALGORITHM = "HS256"
    mock_verify.return_value = MOCK_GOOGLE_IDINFO

    resp = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["user"]["email"] == "googleuser@gmail.com"
    assert body["user"]["first_name"] == "Google"
    assert body["user"]["last_name"] == "User"
    assert body["user"]["avatar"] == "https://lh3.googleusercontent.com/photo.jpg"


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_existing_user_by_email(mock_verify, mock_settings, client):
    """Google sign-in for a user who already registered with email/password."""
    # Register with email/password first
    await register_user(client, email="googleuser@gmail.com")

    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_settings.return_value.JWT_SECRET = "test-secret-key"
    mock_settings.return_value.JWT_EXPIRES_IN = "168h"
    mock_settings.return_value.JWT_ALGORITHM = "HS256"
    mock_verify.return_value = MOCK_GOOGLE_IDINFO

    resp = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    # Should keep the original name from registration
    assert body["user"]["email"] == "googleuser@gmail.com"
    assert body["user"]["first_name"] == "Test"


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_returning_user(mock_verify, mock_settings, client):
    """Second Google sign-in finds the user by google_id."""
    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_settings.return_value.JWT_SECRET = "test-secret-key"
    mock_settings.return_value.JWT_EXPIRES_IN = "168h"
    mock_settings.return_value.JWT_ALGORITHM = "HS256"
    mock_verify.return_value = MOCK_GOOGLE_IDINFO

    # First login creates the user
    resp1 = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    assert resp1.status_code == 200
    user1 = resp1.json()["user"]

    # Second login finds existing user
    resp2 = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    assert resp2.status_code == 200
    user2 = resp2.json()["user"]

    assert user1["id"] == user2["id"]
    assert user2["email"] == "googleuser@gmail.com"


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_no_email(mock_verify, mock_settings, client):
    """Returns 400 when Google account has no email."""
    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_verify.return_value = {"sub": "google-uid-456"}

    resp = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    assert resp.status_code == 400


@patch("app.routers.auth.get_settings")
@patch("app.routers.auth.google_id_token.verify_oauth2_token")
async def test_google_auth_profile_accessible(mock_verify, mock_settings, client):
    """After Google auth, the profile endpoint works with the returned token."""
    mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
    mock_settings.return_value.JWT_SECRET = "test-secret-key"
    mock_settings.return_value.JWT_EXPIRES_IN = "168h"
    mock_settings.return_value.JWT_ALGORITHM = "HS256"
    mock_verify.return_value = MOCK_GOOGLE_IDINFO

    resp = await client.post("/api/v1/auth/google", json={"credential": "valid-google-token"})
    token = resp.json()["token"]

    profile_resp = await client.get("/api/v1/auth/profile", headers=auth_header(token))
    assert profile_resp.status_code == 200
    assert profile_resp.json()["email"] == "googleuser@gmail.com"
