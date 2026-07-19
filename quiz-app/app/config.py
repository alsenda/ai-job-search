"""Application settings.

Settings are read from environment variables (and a local ``.env`` file in
development). This is the single place where deployment-specific values live,
so the rest of the code never touches ``os.environ`` directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Attributes:
        database_url: SQLAlchemy connection URL. Defaults to a local SQLite
            file so the app runs with zero setup. In production (Vercel) set
            ``DATABASE_URL`` to the Neon Postgres URL.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./quiz.db"

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
