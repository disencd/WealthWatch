from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database (TCP — local dev, docker-compose)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "wealthwatch_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "wealthwatch_db"
    DB_SSLMODE: str = "disable"

    # Full DATABASE_URL (Neon, Supabase, or any PostgreSQL).
    # This is the PRIMARY way to configure the database on Cloud Run.
    # Examples:
    #   Neon:     postgresql://user:pass@ep-cool-rain-123.us-east-2.aws.neon.tech/neondb?sslmode=require
    #   Supabase: postgresql://postgres.xxxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    DATABASE_URL: str = ""

    # Cloud SQL (set to "project:region:instance" for Unix socket — optional fallback)
    CLOUD_SQL_CONNECTION_NAME: str = ""

    # JWT
    JWT_SECRET: str = ""
    JWT_EXPIRES_IN: str = "168h"
    JWT_ALGORITHM: str = "HS256"

    # App
    PORT: int = 8080
    ALLOWED_ORIGINS: str = ""  # comma-separated origins, "*" for dev

    # Cloud Run
    K_SERVICE: str = ""  # set automatically by Cloud Run

    @property
    def is_cloud_run(self) -> bool:
        return bool(self.K_SERVICE)

    @property
    def requires_ssl(self) -> bool:
        """Check if DATABASE_URL requests SSL (Neon, Supabase, etc.)."""
        if not self.DATABASE_URL:
            return False
        qs = parse_qs(urlparse(self.DATABASE_URL).query)
        return qs.get("sslmode", [""])[0] in ("require", "verify-ca", "verify-full")

    @property
    def database_url_async(self) -> str:
        # 1. Explicit DATABASE_URL (Neon, Supabase, any external PG)
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Swap driver to asyncpg
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            # Strip sslmode from query string — asyncpg handles SSL via connect_args
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            qs.pop("sslmode", None)
            clean_query = urlencode(qs, doseq=True)
            url = urlunparse(parsed._replace(query=clean_query))
            return url

        # 2. Cloud SQL Unix socket
        if self.CLOUD_SQL_CONNECTION_NAME:
            return (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@/{self.DB_NAME}"
                f"?host=/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}"
            )

        # 3. TCP (local dev, docker-compose)
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url(self) -> str:
        """Alias kept for backward compatibility."""
        return self.database_url_async

    @property
    def cors_origins(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"] if not self.is_cloud_run else []
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def jwt_expiry_seconds(self) -> int:
        s = self.JWT_EXPIRES_IN
        if s.endswith("h"):
            return int(s[:-1]) * 3600
        if s.endswith("m"):
            return int(s[:-1]) * 60
        return int(s)

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
