from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite database file path (on Cloud Run, mounted via GCS FUSE at /data)
    SQLITE_DB_PATH: str = "db/wealthwatch.db"

    JWT_SECRET: str = ""
    JWT_EXPIRES_IN: str = "168h"
    JWT_ALGORITHM: str = "HS256"
    GOOGLE_CLIENT_ID: str = ""
    PORT: int = 8075
    ALLOWED_ORIGINS: str = ""
    K_SERVICE: str = ""

    @property
    def is_cloud_run(self) -> bool:
        return bool(self.K_SERVICE)

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"

    @property
    def cors_origins(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"]
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
