"""Unit tests for auth utilities (no DB required)."""
import os
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PASSWORD", "test")

from app.auth import hash_password, verify_password, create_token, decode_token


def test_hash_and_verify_password():
    hashed = hash_password("mysecretpassword")
    assert hashed != "mysecretpassword"
    assert verify_password("mysecretpassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_decode_token():
    token = create_token(user_id=1, email="test@example.com", family_id=10, role="superadmin")
    assert isinstance(token, str)

    data = decode_token(token)
    assert data.user_id == 1
    assert data.email == "test@example.com"
    assert data.family_id == 10
    assert data.role == "superadmin"


def test_decode_invalid_token():
    with pytest.raises(Exception):
        decode_token("invalid.token.here")


def test_password_different_hashes():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt salts differ
    assert verify_password("same", h1)
    assert verify_password("same", h2)
