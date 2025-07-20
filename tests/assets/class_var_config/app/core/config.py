from __future__ import annotations

from typing import Any, Literal

from pydantic import computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "aerich_dev"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URI(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgres",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def TORTOISE_ORM(self) -> dict[str, dict[str, Any]]:
        db_url = (
            "sqlite://db.sqlite3"
            if self.ENVIRONMENT == "local"
            else str(self.DATABASE_URI)
        )
        return {
            "connections": {"default": db_url},
            "apps": {"models": {"models": ["app.models", "aerich.models"]}},
        }


settings = Settings()
