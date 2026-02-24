from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "wealthwatch_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "wealthwatch_db"
    DB_SSLMODE: str = "disable"

    # JWT
    JWT_SECRET: str = ""
    JWT_EXPIRES_IN: str = "168h"
    JWT_ALGORITHM: str = "HS256"

    # App
    PORT: int = 8080
    GIN_MODE: str = "release"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

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
