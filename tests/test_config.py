"""Pure unit tests for app.config.Settings - no database required."""

import os

# Set minimum env vars so importing app.config never blows up.
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_settings_cache():
    """Clear the lru_cache on get_settings so each test gets a fresh object."""
    get_settings.cache_clear()


def _make(**overrides) -> Settings:
    """Build a Settings with sensible defaults, overridden by *overrides*."""
    defaults = dict(
        SQLITE_DB_PATH="wealthwatch.db",
        JWT_SECRET="secret",
        JWT_EXPIRES_IN="168h",
        ALLOWED_ORIGINS="",
        K_SERVICE="",
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# database_url — SQLite
# ---------------------------------------------------------------------------


def test_database_url_default():
    _clear_settings_cache()
    s = _make()
    assert s.database_url == "sqlite+aiosqlite:///wealthwatch.db"


def test_database_url_custom_path():
    _clear_settings_cache()
    s = _make(SQLITE_DB_PATH="/data/wealthwatch.db")
    assert s.database_url == "sqlite+aiosqlite:////data/wealthwatch.db"


def test_database_url_memory():
    _clear_settings_cache()
    s = _make(SQLITE_DB_PATH=":memory:")
    assert s.database_url == "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# cors_origins
# ---------------------------------------------------------------------------


def test_cors_origins_default_dev():
    """Empty ALLOWED_ORIGINS + not Cloud Run → ["*"]."""
    _clear_settings_cache()
    s = _make(ALLOWED_ORIGINS="", K_SERVICE="")
    assert s.cors_origins == ["*"]


def test_cors_origins_default_cloud_run():
    """Empty ALLOWED_ORIGINS + Cloud Run → [] (locked down)."""
    _clear_settings_cache()
    s = _make(ALLOWED_ORIGINS="", K_SERVICE="my-service")
    assert s.cors_origins == []


def test_cors_origins_parsed_from_comma_string():
    _clear_settings_cache()
    s = _make(ALLOWED_ORIGINS="https://a.com, https://b.com , https://c.com")
    assert s.cors_origins == ["https://a.com", "https://b.com", "https://c.com"]


def test_cors_origins_single_value():
    _clear_settings_cache()
    s = _make(ALLOWED_ORIGINS="https://only.one")
    assert s.cors_origins == ["https://only.one"]


def test_cors_origins_ignores_blank_entries():
    _clear_settings_cache()
    s = _make(ALLOWED_ORIGINS="https://a.com,,, ,https://b.com")
    assert s.cors_origins == ["https://a.com", "https://b.com"]


# ---------------------------------------------------------------------------
# jwt_expiry_seconds
# ---------------------------------------------------------------------------


def test_jwt_expiry_hours():
    _clear_settings_cache()
    s = _make(JWT_EXPIRES_IN="168h")
    assert s.jwt_expiry_seconds == 604800  # 168 * 3600


def test_jwt_expiry_minutes():
    _clear_settings_cache()
    s = _make(JWT_EXPIRES_IN="30m")
    assert s.jwt_expiry_seconds == 1800  # 30 * 60


def test_jwt_expiry_raw_seconds():
    _clear_settings_cache()
    s = _make(JWT_EXPIRES_IN="3600")
    assert s.jwt_expiry_seconds == 3600


def test_jwt_expiry_one_hour():
    _clear_settings_cache()
    s = _make(JWT_EXPIRES_IN="1h")
    assert s.jwt_expiry_seconds == 3600


# ---------------------------------------------------------------------------
# is_cloud_run
# ---------------------------------------------------------------------------


def test_is_cloud_run_true():
    _clear_settings_cache()
    s = _make(K_SERVICE="my-svc")
    assert s.is_cloud_run is True


def test_is_cloud_run_false():
    _clear_settings_cache()
    s = _make(K_SERVICE="")
    assert s.is_cloud_run is False


# ---------------------------------------------------------------------------
# get_settings caching
# ---------------------------------------------------------------------------


def test_get_settings_returns_same_object():
    _clear_settings_cache()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_settings_cache_clear_gives_new_object():
    _clear_settings_cache()
    a = get_settings()
    _clear_settings_cache()
    b = get_settings()
    # Both are Settings, but they should be distinct objects
    assert a is not b
