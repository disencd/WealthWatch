"""Pure unit tests for app.config.Settings - no database required."""

import os

# Set minimum env vars so importing app.config never blows up.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PASSWORD", "test")

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
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_USER="u",
        DB_PASSWORD="p",
        DB_NAME="d",
        DATABASE_URL="",
        CLOUD_SQL_CONNECTION_NAME="",
        JWT_SECRET="secret",
        JWT_EXPIRES_IN="168h",
        ALLOWED_ORIGINS="",
        K_SERVICE="",
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# database_url_async — TCP fallback (branch 3)
# ---------------------------------------------------------------------------


def test_database_url_tcp_default():
    _clear_settings_cache()
    s = _make(DB_HOST="myhost", DB_PORT=5432, DB_USER="u", DB_PASSWORD="p", DB_NAME="d")
    assert s.database_url_async == "postgresql+asyncpg://u:p@myhost:5432/d"


def test_database_url_tcp_custom_port():
    _clear_settings_cache()
    s = _make(DB_HOST="10.0.0.1", DB_PORT=6543, DB_USER="admin", DB_PASSWORD="s3cr3t", DB_NAME="mydb")
    assert s.database_url_async == "postgresql+asyncpg://admin:s3cr3t@10.0.0.1:6543/mydb"


# ---------------------------------------------------------------------------
# database_url_async — DATABASE_URL present (branch 1)
# ---------------------------------------------------------------------------


def test_database_url_neon_swaps_driver_and_strips_sslmode():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require")
    url = s.database_url_async
    assert url.startswith("postgresql+asyncpg://")
    assert "user:pass@ep-xxx.neon.tech/neondb" in url
    assert "sslmode" not in url


def test_database_url_postgres_scheme():
    """Handles the shorter 'postgres://' scheme used by some providers."""
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgres://user:pass@host.supabase.com:6543/postgres")
    url = s.database_url_async
    assert url.startswith("postgresql+asyncpg://")
    assert "user:pass@host.supabase.com:6543/postgres" in url


def test_database_url_preserves_other_query_params():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db?sslmode=require&options=-c+search_path%3Dpublic")
    url = s.database_url_async
    assert "sslmode" not in url
    assert "options=" in url  # other params kept


# ---------------------------------------------------------------------------
# database_url_async — Cloud SQL Unix socket (branch 2)
# ---------------------------------------------------------------------------


def test_database_url_cloud_sql_unix_socket():
    _clear_settings_cache()
    s = _make(
        CLOUD_SQL_CONNECTION_NAME="proj:us-central1:inst",
        DB_USER="pguser",
        DB_PASSWORD="pgpass",
        DB_NAME="mydb",
    )
    url = s.database_url_async
    assert url == "postgresql+asyncpg://pguser:pgpass@/mydb?host=/cloudsql/proj:us-central1:inst"


# ---------------------------------------------------------------------------
# database_url_async — priority: DATABASE_URL > CLOUD_SQL > TCP
# ---------------------------------------------------------------------------


def test_database_url_priority_database_url_wins():
    """DATABASE_URL takes precedence over CLOUD_SQL_CONNECTION_NAME."""
    _clear_settings_cache()
    s = _make(
        DATABASE_URL="postgresql://u:p@neon/db",
        CLOUD_SQL_CONNECTION_NAME="proj:region:inst",
    )
    assert "neon/db" in s.database_url_async
    assert "cloudsql" not in s.database_url_async


# ---------------------------------------------------------------------------
# database_url (backward-compat alias)
# ---------------------------------------------------------------------------


def test_database_url_alias():
    _clear_settings_cache()
    s = _make()
    assert s.database_url == s.database_url_async


# ---------------------------------------------------------------------------
# requires_ssl
# ---------------------------------------------------------------------------


def test_requires_ssl_true_for_require():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db?sslmode=require")
    assert s.requires_ssl is True


def test_requires_ssl_true_for_verify_full():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db?sslmode=verify-full")
    assert s.requires_ssl is True


def test_requires_ssl_true_for_verify_ca():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db?sslmode=verify-ca")
    assert s.requires_ssl is True


def test_requires_ssl_false_when_no_database_url():
    _clear_settings_cache()
    s = _make(DATABASE_URL="")
    assert s.requires_ssl is False


def test_requires_ssl_false_for_disable():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db?sslmode=disable")
    assert s.requires_ssl is False


def test_requires_ssl_false_when_no_sslmode_param():
    _clear_settings_cache()
    s = _make(DATABASE_URL="postgresql://u:p@host/db")
    assert s.requires_ssl is False


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
