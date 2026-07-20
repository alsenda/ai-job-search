"""Application settings.

Settings are read from environment variables (and a local ``.env`` file in
development). This is the single place where deployment-specific values live,
so the rest of the code never touches ``os.environ`` directly.
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    """A SQLite file with zero setup, on a path that is actually writable.

    Vercel's function bundle is read-only except for ``/tmp``, so the plain
    working-directory default used in local dev would crash the app on
    startup there. Vercel sets ``VERCEL=1`` in every build and runtime
    environment. This is a fallback only — set ``DATABASE_URL`` to a real
    Postgres connection string for persistence in production.
    """
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/quiz.db"
    return "sqlite:///./quiz.db"


class Settings(BaseSettings):
    """Runtime configuration.

    Attributes:
        database_url: SQLAlchemy connection URL. Defaults to a local SQLite
            file so the app runs with zero setup. In production (Vercel) set
            ``DATABASE_URL`` to the Neon Postgres URL.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(default_factory=_default_database_url)

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize the URL for SQLAlchemy + psycopg3.

        Neon/Vercel hand out URLs starting with ``postgres://`` or
        ``postgresql://``; SQLAlchemy needs ``postgresql+psycopg://`` to pick
        the psycopg3 driver.
        """
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance (one per process)."""
    return Settings()
